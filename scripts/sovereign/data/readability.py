import os
import struct
import zlib

from sovereign.data.units import UNITS


TEAM_COLOR_MODES = ("texture_mask", "pending_mask", "not_applicable")
PRODUCTION_ASSET_STATUSES = ("production_ready", "placeholder_needs_replacement")
DEFAULT_TEAM_COLOR_MASK_MAX_COVERAGE = 0.35


def _unit_asset_dir(unit, basedir):
    asset = unit.get("asset") or {}
    path = asset.get("path")
    if not path:
        return None
    asset_path = os.path.join(basedir, path)
    if asset.get("pfobj"):
        return asset_path
    return os.path.dirname(asset_path)


def _unit_asset_path(unit, basedir):
    asset = unit.get("asset") or {}
    path = asset.get("path")
    if not path:
        return None
    asset_path = os.path.join(basedir, path)
    if asset.get("pfobj"):
        return os.path.join(asset_path, asset["pfobj"])
    return asset_path


def _png_dimensions(path):
    try:
        with open(path, "rb") as infile:
            header = infile.read(24)
    except IOError:
        return None
    if len(header) < 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", header[16:24])


def _png_chunks(path):
    try:
        with open(path, "rb") as infile:
            data = infile.read()
    except IOError:
        return None
    if len(data) < 8 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return None

    chunks = []
    offset = 8
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        ctype = data[offset + 4:offset + 8]
        start = offset + 8
        end = start + length
        if end + 4 > len(data):
            return None
        chunks.append((ctype, data[start:end]))
        offset = end + 4
        if ctype == b"IEND":
            break
    return chunks


def _png_recon_scanline(filter_type, raw, prev, bpp):
    out = bytearray(raw)
    for i in range(len(out)):
        left = out[i - bpp] if i >= bpp else 0
        up = prev[i] if prev else 0
        up_left = prev[i - bpp] if prev and i >= bpp else 0
        if filter_type == 1:
            out[i] = (out[i] + left) & 0xff
        elif filter_type == 2:
            out[i] = (out[i] + up) & 0xff
        elif filter_type == 3:
            out[i] = (out[i] + ((left + up) // 2)) & 0xff
        elif filter_type == 4:
            p = left + up - up_left
            pa = abs(p - left)
            pb = abs(p - up)
            pc = abs(p - up_left)
            pred = left if pa <= pb and pa <= pc else (up if pb <= pc else up_left)
            out[i] = (out[i] + pred) & 0xff
    return out


def _png_mask_coverage(path, threshold=5):
    chunks = _png_chunks(path)
    if not chunks:
        return None

    ihdr = None
    idat = []
    for ctype, payload in chunks:
        if ctype == b"IHDR":
            ihdr = payload
        elif ctype == b"IDAT":
            idat.append(payload)
    if not ihdr or not idat or len(ihdr) < 13:
        return None

    width, height = struct.unpack(">II", ihdr[:8])
    bit_depth = ihdr[8]
    color_type = ihdr[9]
    compression = ihdr[10]
    filter_method = ihdr[11]
    interlace = ihdr[12]
    if bit_depth != 8 or compression != 0 or filter_method != 0 or interlace != 0:
        return None

    channels_by_color_type = {
        0: 1,
        2: 3,
        4: 2,
        6: 4,
    }
    channels = channels_by_color_type.get(color_type)
    if not channels:
        return None

    try:
        inflated = zlib.decompress(b"".join(idat))
    except zlib.error:
        return None

    row_len = width * channels
    expected = height * (row_len + 1)
    if len(inflated) < expected:
        return None

    covered = 0
    prev = None
    offset = 0
    for _ in range(height):
        filter_type = inflated[offset]
        offset += 1
        raw = inflated[offset:offset + row_len]
        offset += row_len
        row = _png_recon_scanline(filter_type, raw, prev, channels)
        for x in range(width):
            px = x * channels
            if color_type == 0:
                active = row[px] > threshold
            elif color_type == 2:
                active = max(row[px], row[px + 1], row[px + 2]) > threshold
            elif color_type == 4:
                active = row[px] > threshold
            else:
                active = max(row[px], row[px + 1], row[px + 2]) > threshold
            if active:
                covered += 1
        prev = row

    total = width * height
    if total <= 0:
        return None
    return float(covered) / float(total)


def _jpeg_dimensions(path):
    try:
        with open(path, "rb") as infile:
            data = infile.read()
    except IOError:
        return None
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    offset = 2
    while offset + 9 < len(data):
        if data[offset] != 0xff:
            offset += 1
            continue
        marker = data[offset + 1]
        offset += 2
        while marker == 0xff and offset < len(data):
            marker = data[offset]
            offset += 1
        if marker in (0xd8, 0xd9):
            continue
        if offset + 2 > len(data):
            return None
        length = struct.unpack(">H", data[offset:offset + 2])[0]
        if length < 2 or offset + length > len(data):
            return None
        if marker in (0xc0, 0xc1, 0xc2):
            if length < 7:
                return None
            height, width = struct.unpack(">HH", data[offset + 3:offset + 7])
            return (width, height)
        offset += length
    return None


def _image_dimensions(path):
    return _png_dimensions(path) or _jpeg_dimensions(path)


def _unit_texture_path(unit, basedir):
    asset_path = _unit_asset_path(unit, basedir)
    asset_dir = _unit_asset_dir(unit, basedir)
    if not asset_path or not asset_dir:
        return None
    try:
        with open(asset_path, "r") as infile:
            for line in infile:
                fields = line.strip().split()
                if len(fields) >= 2 and fields[0] == "texture":
                    return os.path.join(asset_dir, fields[1])
    except IOError:
        return None
    return None


def _unit_mask_dimensions(unit, basedir, mask):
    asset_dir = _unit_asset_dir(unit, basedir)
    if not asset_dir or not mask:
        return None
    return _png_dimensions(os.path.join(asset_dir, mask))


def _validate_unit(unit_id, unit, basedir):
    errors = []
    warnings = []
    readability = unit.get("readability")
    if not readability:
        errors.append("unit '{0}' is missing readability metadata".format(unit_id))
        return errors, warnings

    silhouette = readability.get("silhouette")
    if not silhouette:
        errors.append("unit '{0}' is missing readability.silhouette".format(unit_id))

    far_view = readability.get("far_view") or {}
    if not far_view.get("class"):
        errors.append("unit '{0}' is missing far-view class".format(unit_id))
    if not far_view.get("marker_policy"):
        errors.append("unit '{0}' is missing far-view marker policy".format(unit_id))
    minimum_pixels = far_view.get("minimum_pixels")
    if not isinstance(minimum_pixels, int) or minimum_pixels <= 0:
        errors.append("unit '{0}' has invalid far-view minimum_pixels".format(unit_id))

    close_view = readability.get("close_view") or {}
    preferred_height = close_view.get("preferred_camera_height")
    if not (
        isinstance(preferred_height, (list, tuple))
        and len(preferred_height) == 2
        and all(isinstance(value, (int, float)) for value in preferred_height)
        and preferred_height[0] > 0
        and preferred_height[0] < preferred_height[1]
    ):
        errors.append("unit '{0}' has invalid close-view preferred_camera_height".format(unit_id))
    proof_poses = close_view.get("proof_poses")
    if not isinstance(proof_poses, (list, tuple)) or not proof_poses:
        errors.append("unit '{0}' is missing close-view proof poses".format(unit_id))
    minimum_close_pixels = close_view.get("minimum_pixels")
    if not isinstance(minimum_close_pixels, int) or minimum_close_pixels <= 0:
        errors.append("unit '{0}' has invalid close-view minimum_pixels".format(unit_id))

    production_asset = readability.get("production_asset") or {}
    asset_status = production_asset.get("status")
    if asset_status not in PRODUCTION_ASSET_STATUSES:
        errors.append("unit '{0}' has invalid production asset status".format(unit_id))

    team_color = readability.get("team_color") or {}
    mode = team_color.get("mode")
    if mode not in TEAM_COLOR_MODES:
        errors.append("unit '{0}' has invalid team-color mode".format(unit_id))
        return errors, warnings
    if team_color.get("priority") not in ("required", "optional", "none"):
        errors.append("unit '{0}' has invalid team-color priority".format(unit_id))

    if mode == "texture_mask":
        mask = team_color.get("mask")
        asset_dir = _unit_asset_dir(unit, basedir)
        if not mask:
            errors.append("unit '{0}' uses texture_mask without a mask path".format(unit_id))
        elif asset_dir:
            mask_path = os.path.join(asset_dir, mask)
            if not os.path.isfile(mask_path):
                errors.append("unit '{0}' missing team-color mask: {1}".format(unit_id, mask_path))
            else:
                mask_dims = _png_dimensions(mask_path)
                texture_path = _unit_texture_path(unit, basedir)
                texture_dims = _image_dimensions(texture_path) if texture_path else None
                if not mask_dims:
                    errors.append("unit '{0}' team-color mask is not a PNG: {1}".format(unit_id, mask_path))
                elif texture_dims and mask_dims != texture_dims:
                    errors.append(
                        "unit '{0}' team-color mask size {1} does not match texture size {2}".format(
                            unit_id, mask_dims, texture_dims
                        )
                    )
                else:
                    coverage = _png_mask_coverage(mask_path)
                    max_coverage = team_color.get(
                        "max_coverage", DEFAULT_TEAM_COLOR_MASK_MAX_COVERAGE
                    )
                    if coverage is None:
                        errors.append(
                            "unit '{0}' team-color mask coverage could not be read: {1}".format(
                                unit_id, mask_path
                            )
                        )
                    elif coverage > max_coverage:
                        errors.append(
                            "unit '{0}' team-color mask coverage {1:.1f}% exceeds max {2:.1f}%".format(
                                unit_id, coverage * 100.0, max_coverage * 100.0
                            )
                        )
    elif mode == "pending_mask":
        warnings.append("unit '{0}' still needs production team-color mask".format(unit_id))
    elif mode == "not_applicable" and team_color.get("mask"):
        errors.append("unit '{0}' disables world team-color tint but still references a mask".format(unit_id))

    return errors, warnings


def validate_unit_readability(units=None, basedir="."):
    if units is None:
        units = UNITS
    errors = []
    warnings = []
    for unit_id in sorted(units):
        unit_errors, unit_warnings = _validate_unit(unit_id, units[unit_id], basedir)
        errors.extend(unit_errors)
        warnings.extend(unit_warnings)
    return {
        "errors": errors,
        "warnings": warnings,
    }


def summarize_unit_readability(units=None, basedir="."):
    if units is None:
        units = UNITS
    validation = validate_unit_readability(units, basedir)
    production_ready = 0
    pending_team_masks = 0
    silhouettes = {}
    far_view_classes = {}
    close_view_classes = {}
    production_asset_statuses = {}
    units_out = {}
    for unit_id in sorted(units):
        readability = units[unit_id].get("readability") or {}
        team_color = readability.get("team_color") or {}
        far_view = readability.get("far_view") or {}
        close_view = readability.get("close_view") or {}
        production_asset = readability.get("production_asset") or {}
        mode = team_color.get("mode")
        if mode in ("texture_mask", "not_applicable"):
            production_ready += 1
        elif mode == "pending_mask":
            pending_team_masks += 1
        silhouette = readability.get("silhouette", "missing")
        far_class = far_view.get("class", "missing")
        close_class = close_view.get("class", "missing")
        asset_status = production_asset.get("status", "missing")
        silhouettes[silhouette] = silhouettes.get(silhouette, 0) + 1
        far_view_classes[far_class] = far_view_classes.get(far_class, 0) + 1
        close_view_classes[close_class] = close_view_classes.get(close_class, 0) + 1
        production_asset_statuses[asset_status] = production_asset_statuses.get(asset_status, 0) + 1
        units_out[unit_id] = {
            "silhouette": silhouette,
            "far_view_class": far_class,
            "minimum_pixels": far_view.get("minimum_pixels"),
            "marker_policy": far_view.get("marker_policy"),
            "close_view_class": close_class,
            "close_view_preferred_camera_height": close_view.get("preferred_camera_height"),
            "close_view_minimum_pixels": close_view.get("minimum_pixels"),
            "close_view_proof_poses": close_view.get("proof_poses"),
            "production_asset_status": asset_status,
            "production_asset_notes": production_asset.get("notes"),
            "team_color_mode": mode,
            "team_color_mask": team_color.get("mask"),
            "team_color_mask_size": _unit_mask_dimensions(
                units[unit_id], basedir, team_color.get("mask")
            ),
            "team_color_mask_coverage": (
                _png_mask_coverage(
                    os.path.join(
                        _unit_asset_dir(units[unit_id], basedir) or "",
                        team_color.get("mask") or "",
                    )
                )
                if team_color.get("mask") else None
            ),
            "team_color_priority": team_color.get("priority"),
        }
    return {
        "units": units_out,
        "production_ready_units": production_ready,
        "pending_team_masks": pending_team_masks,
        "silhouettes": silhouettes,
        "far_view_classes": far_view_classes,
        "close_view_classes": close_view_classes,
        "production_asset_statuses": production_asset_statuses,
        "units_needing_production_assets": production_asset_statuses.get(
            "placeholder_needs_replacement", 0
        ),
        "errors": validation["errors"],
        "warnings": validation["warnings"],
    }
