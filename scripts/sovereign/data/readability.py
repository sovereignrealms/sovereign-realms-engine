import os
import struct

from sovereign.data.units import UNITS


TEAM_COLOR_MODES = ("texture_mask", "pending_mask", "not_applicable")


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
    elif mode == "pending_mask":
        warnings.append("unit '{0}' still needs production team-color mask".format(unit_id))

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
    units_out = {}
    for unit_id in sorted(units):
        readability = units[unit_id].get("readability") or {}
        team_color = readability.get("team_color") or {}
        far_view = readability.get("far_view") or {}
        mode = team_color.get("mode")
        if mode == "texture_mask":
            production_ready += 1
        elif mode == "pending_mask":
            pending_team_masks += 1
        silhouette = readability.get("silhouette", "missing")
        far_class = far_view.get("class", "missing")
        silhouettes[silhouette] = silhouettes.get(silhouette, 0) + 1
        far_view_classes[far_class] = far_view_classes.get(far_class, 0) + 1
        units_out[unit_id] = {
            "silhouette": silhouette,
            "far_view_class": far_class,
            "minimum_pixels": far_view.get("minimum_pixels"),
            "marker_policy": far_view.get("marker_policy"),
            "team_color_mode": mode,
            "team_color_mask": team_color.get("mask"),
            "team_color_mask_size": _unit_mask_dimensions(
                units[unit_id], basedir, team_color.get("mask")
            ),
            "team_color_priority": team_color.get("priority"),
        }
    return {
        "units": units_out,
        "production_ready_units": production_ready,
        "pending_team_masks": pending_team_masks,
        "silhouettes": silhouettes,
        "far_view_classes": far_view_classes,
        "errors": validation["errors"],
        "warnings": validation["warnings"],
    }
