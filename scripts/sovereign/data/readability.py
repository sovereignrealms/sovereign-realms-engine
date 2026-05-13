import os

from sovereign.data.units import UNITS


TEAM_COLOR_MODES = ("texture_mask", "pending_mask", "not_applicable")


def _unit_asset_dir(unit, basedir):
    asset = unit.get("asset") or {}
    path = asset.get("path")
    if not path:
        return None
    return os.path.dirname(os.path.join(basedir, path))


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
        elif asset_dir and not os.path.isfile(os.path.join(asset_dir, mask)):
            errors.append("unit '{0}' missing team-color mask: {1}".format(unit_id, os.path.join(asset_dir, mask)))
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
