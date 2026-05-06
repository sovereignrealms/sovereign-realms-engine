from __future__ import print_function

import copy
import os

from sovereign.data.buildings import BUILDINGS
from sovereign.data.resources import RESOURCES
from sovereign.data.units import UNITS
from sovereign.scenario import (
    DEFAULT_SETUP_PROFILE as SCENARIO_DEFAULT_SETUP_PROFILE,
    SETUP_PROFILES,
    STARTING_RESOURCE_PRESETS,
    load_scenario,
    require_valid_scenario,
    save_scenario,
    validate_scenario,
)


DEFAULT_PLAYERS = (
    {
        "id": 1,
        "name": "Sovereign",
        "civilization_id": "sovereign_default",
        "faction_color": [40, 90, 255, 255],
        "start": [64.0, 72.0],
        "starting_resources": {
            "food": 260,
            "wood": 240,
            "gold": 140,
            "stone": 100,
        },
    },
    {
        "id": 2,
        "name": "Opponent",
        "civilization_id": "sovereign_default",
        "faction_color": [220, 50, 50, 255],
        "start": [120.0, 72.0],
        "starting_resources": {
            "food": 500,
            "wood": 500,
            "gold": 200,
            "stone": 100,
        },
    },
)


DEFAULT_PALETTE = {
    "units": ["villager", "militia", "archer"],
    "buildings": ["town_center", "house", "barracks"],
    "resources": ["food", "wood", "gold", "stone"],
}

DEFAULT_PLACED_RESOURCES = (
    {"id": "p1_food", "resource_id": "food", "owner_player_id": 0, "point": [58.0, 88.0], "amount": 300},
    {"id": "p1_wood", "resource_id": "wood", "owner_player_id": 0, "point": [48.0, 70.0], "amount": 300},
    {"id": "p1_gold", "resource_id": "gold", "owner_player_id": 0, "point": [84.0, 74.0], "amount": 300},
    {"id": "p1_stone", "resource_id": "stone", "owner_player_id": 0, "point": [82.0, 92.0], "amount": 300},
)

DEFAULT_PLACED_OBJECTS = (
    {"id": "p1_guard", "kind": "unit", "object_id": "militia", "owner_player_id": 1, "point": [96.0, 90.0]},
    {"id": "p2_forward_barracks", "kind": "building", "object_id": "barracks", "owner_player_id": 2, "point": [148.0, 86.0]},
)

DEFAULT_MAP_SEED = 20260505
DEFAULT_AUTHOR_NOTES = ""
DEFAULT_VICTORY_MODE = "conquest"
DEFAULT_SETUP_PROFILE = SCENARIO_DEFAULT_SETUP_PROFILE
DEFAULT_STARTING_RESOURCE_PRESET = SETUP_PROFILES[DEFAULT_SETUP_PROFILE]["starting_resource_preset"]
VICTORY_LABELS = {
    "conquest": "Conquest",
}

EDITOR_AUTHORING_STATE = None


def _offset_point(point, delta=6.0):
    return [round(float(point[0]) + delta, 2), round(float(point[1]) + delta, 2)]


def _unique_id(existing, base):
    if base not in existing:
        return base
    suffix = 2
    while "{0}_{1}".format(base, suffix) in existing:
        suffix += 1
    return "{0}_{1}".format(base, suffix)


def _next_player_id(players):
    return max(player["id"] for player in players) + 1


def _default_authoring_state():
    return {
        "scenario_id": None,
        "name": None,
        "map_seed": DEFAULT_MAP_SEED,
        "author_notes": DEFAULT_AUTHOR_NOTES,
        "victory_mode": DEFAULT_VICTORY_MODE,
        "setup_profile": DEFAULT_SETUP_PROFILE,
        "starting_resource_preset": DEFAULT_STARTING_RESOURCE_PRESET,
        "players": [copy.deepcopy(player) for player in DEFAULT_PLAYERS],
        "palette": copy.deepcopy(DEFAULT_PALETTE),
        "placed_resources": [copy.deepcopy(resource) for resource in DEFAULT_PLACED_RESOURCES],
        "placed_objects": [copy.deepcopy(obj) for obj in DEFAULT_PLACED_OBJECTS],
        "selected_placement": {
            "kind": "player_start",
            "player_id": 1,
            "resource_index": 0,
            "object_index": 0,
        },
        "export_status": {
            "state": "not_saved",
            "path": None,
            "message": "Sovereign sidecar has not been exported",
        },
        "validation_errors": [],
        "validation_issues": [],
        "export_report": {},
        "diplomacy_state": "war",
    }


def reset_editor_authoring_state():
    global EDITOR_AUTHORING_STATE
    EDITOR_AUTHORING_STATE = _default_authoring_state()
    return EDITOR_AUTHORING_STATE


def get_editor_authoring_state():
    global EDITOR_AUTHORING_STATE
    if EDITOR_AUTHORING_STATE is None:
        reset_editor_authoring_state()
    return EDITOR_AUTHORING_STATE


def set_export_status(state_name, path=None, message=None):
    state = get_editor_authoring_state()
    state["export_status"] = {
        "state": state_name,
        "path": path,
        "message": message or "",
    }
    return state["export_status"]


def _diplomacy_state_from_scenario(scenario):
    rows = scenario.get("diplomacy", [])
    if not rows:
        return "war"
    first = rows[0].get("state") or "war"
    for row in rows[1:]:
        if row.get("state") != first:
            return "war"
    return first


def _resolve_setup_ids(setup):
    setup = setup or {}
    setup_profile = setup.get("profile") or DEFAULT_SETUP_PROFILE
    if setup_profile not in SETUP_PROFILES:
        setup_profile = DEFAULT_SETUP_PROFILE
    default_preset = SETUP_PROFILES[setup_profile]["starting_resource_preset"]
    preset = setup.get("starting_resource_preset") or default_preset
    if preset not in STARTING_RESOURCE_PRESETS:
        preset = default_preset
    return setup_profile, preset


def _authoring_state_from_scenario(scenario, sidecar_path):
    players = copy.deepcopy(scenario.get("players") or DEFAULT_PLAYERS)
    placed_resources = copy.deepcopy(scenario.get("placed_resources") or DEFAULT_PLACED_RESOURCES)
    placed_objects = copy.deepcopy(scenario.get("placed_objects") or DEFAULT_PLACED_OBJECTS)
    metadata = scenario.get("metadata") or {}
    victory = scenario.get("victory") or {}
    setup_profile, preset = _resolve_setup_ids(scenario.get("setup"))
    selected_player_id = players[0]["id"] if players else 1
    return {
        "scenario_id": scenario.get("id"),
        "name": scenario.get("name"),
        "map_seed": metadata.get("map_seed", DEFAULT_MAP_SEED),
        "author_notes": metadata.get("author_notes", DEFAULT_AUTHOR_NOTES),
        "victory_mode": victory.get("mode", DEFAULT_VICTORY_MODE),
        "setup_profile": setup_profile,
        "starting_resource_preset": preset,
        "players": players,
        "palette": copy.deepcopy(scenario.get("palette") or DEFAULT_PALETTE),
        "placed_resources": placed_resources,
        "placed_objects": placed_objects,
        "selected_placement": {
            "kind": "player_start",
            "player_id": selected_player_id,
            "resource_index": 0,
            "object_index": 0,
        },
        "export_status": {
            "state": "loaded",
            "path": sidecar_path,
            "message": "Loaded {0} player(s), {1} resource cluster(s), {2} placed object(s)".format(
                len(players),
                len(placed_resources),
                len(placed_objects),
            ),
        },
        "validation_errors": [],
        "validation_issues": [],
        "export_report": copy.deepcopy(scenario.get("export_report") or {}),
        "diplomacy_state": _diplomacy_state_from_scenario(scenario),
    }


def load_editor_scenario(map_path, sidecar_path=None):
    sidecar_path = sidecar_path or scenario_path_for_map(map_path)
    if not os.path.exists(sidecar_path):
        return None

    global EDITOR_AUTHORING_STATE
    scenario = load_scenario(sidecar_path)
    errors = validate_scenario(scenario)
    if errors:
        set_export_status(
            "error",
            sidecar_path,
            "{0} validation issue(s) blocked import".format(len(errors)),
        )
        raise ValueError("invalid Sovereign editor scenario: " + "; ".join(errors))

    EDITOR_AUTHORING_STATE = _authoring_state_from_scenario(scenario, sidecar_path)
    validate_editor_authoring_state(map_path, check_pathing=False)
    return EDITOR_AUTHORING_STATE


def duplicate_player(index):
    state = get_editor_authoring_state()
    players = state["players"]
    source = copy.deepcopy(players[index])
    new_id = _next_player_id(players)
    source["id"] = new_id
    source["name"] = "Player {0}".format(new_id)
    source["faction_color"] = [180, 180, 180, 255]
    source["start"] = _offset_point(source["start"], 12.0)
    players.insert(index + 1, source)
    state["selected_placement"]["player_id"] = new_id
    validate_editor_authoring_state(check_pathing=False)
    return index + 1


def remove_player(index):
    state = get_editor_authoring_state()
    players = state["players"]
    if len(players) <= 2:
        return index
    removed = players.pop(index)
    fallback_id = players[min(index, len(players) - 1)]["id"]
    for obj in state["placed_objects"]:
        if obj.get("owner_player_id") == removed["id"]:
            obj["owner_player_id"] = fallback_id
    for resource in state["placed_resources"]:
        if resource.get("owner_player_id") == removed["id"]:
            resource["owner_player_id"] = 0
    state["selected_placement"]["player_id"] = fallback_id
    validate_editor_authoring_state(check_pathing=False)
    return min(index, len(players) - 1)


def add_placed_resource(resource_id="food", owner_player_id=0, point=None):
    state = get_editor_authoring_state()
    resources = state["placed_resources"]
    existing = set(resource["id"] for resource in resources)
    resource = {
        "id": _unique_id(existing, "{0}_cluster".format(resource_id)),
        "resource_id": resource_id,
        "owner_player_id": owner_player_id,
        "point": list(point or [72.0, 92.0]),
        "amount": 300,
    }
    resources.append(resource)
    idx = len(resources) - 1
    state["selected_placement"]["kind"] = "resource"
    state["selected_placement"]["resource_index"] = idx
    validate_editor_authoring_state(check_pathing=False)
    return idx


def duplicate_placed_resource(index):
    state = get_editor_authoring_state()
    resources = state["placed_resources"]
    source = copy.deepcopy(resources[index])
    existing = set(resource["id"] for resource in resources)
    source["id"] = _unique_id(existing, source["id"])
    source["point"] = _offset_point(source["point"])
    resources.insert(index + 1, source)
    state["selected_placement"]["kind"] = "resource"
    state["selected_placement"]["resource_index"] = index + 1
    validate_editor_authoring_state(check_pathing=False)
    return index + 1


def remove_placed_resource(index):
    state = get_editor_authoring_state()
    resources = state["placed_resources"]
    if len(resources) <= 1:
        return index
    resources.pop(index)
    next_idx = min(index, len(resources) - 1)
    state["selected_placement"]["resource_index"] = next_idx
    validate_editor_authoring_state(check_pathing=False)
    return next_idx


def add_placed_object(kind="unit", object_id=None, owner_player_id=None, point=None):
    state = get_editor_authoring_state()
    objects = state["placed_objects"]
    players = state["players"]
    object_id = object_id or ("militia" if kind == "unit" else "barracks")
    owner_player_id = owner_player_id or players[0]["id"]
    existing = set(obj["id"] for obj in objects)
    obj = {
        "id": _unique_id(existing, "{0}_{1}".format(owner_player_id, object_id)),
        "kind": kind,
        "object_id": object_id,
        "owner_player_id": owner_player_id,
        "point": list(point or [96.0, 92.0]),
    }
    objects.append(obj)
    idx = len(objects) - 1
    state["selected_placement"]["kind"] = kind
    state["selected_placement"]["object_index"] = idx
    validate_editor_authoring_state(check_pathing=False)
    return idx


def duplicate_placed_object(index):
    state = get_editor_authoring_state()
    objects = state["placed_objects"]
    source = copy.deepcopy(objects[index])
    existing = set(obj["id"] for obj in objects)
    source["id"] = _unique_id(existing, source["id"])
    source["point"] = _offset_point(source["point"])
    objects.insert(index + 1, source)
    state["selected_placement"]["kind"] = source["kind"]
    state["selected_placement"]["object_index"] = index + 1
    validate_editor_authoring_state(check_pathing=False)
    return index + 1


def remove_placed_object(index):
    state = get_editor_authoring_state()
    objects = state["placed_objects"]
    if len(objects) <= 1:
        return index
    objects.pop(index)
    next_idx = min(index, len(objects) - 1)
    state["selected_placement"]["object_index"] = next_idx
    validate_editor_authoring_state(check_pathing=False)
    return next_idx


def select_authoring_target(target_kind, target_index=None, player_id=None):
    state = get_editor_authoring_state()
    placement = state["selected_placement"]
    if target_kind == "player_start":
        if player_id is None:
            return None
        for idx, player in enumerate(state["players"]):
            if player["id"] == player_id:
                placement["kind"] = "player_start"
                placement["player_id"] = player_id
                return {"kind": "player_start", "player_index": idx, "player_id": player_id}
        return None

    if target_kind == "resource":
        if target_index is None:
            return None
        target_index = int(target_index)
        if 0 <= target_index < len(state["placed_resources"]):
            placement["kind"] = "resource"
            placement["resource_index"] = target_index
            return {"kind": "resource", "resource_index": target_index}
        return None

    if target_kind == "object":
        if target_index is None:
            return None
        target_index = int(target_index)
        if 0 <= target_index < len(state["placed_objects"]):
            object_kind = state["placed_objects"][target_index].get("kind", "unit")
            if object_kind not in ("unit", "building"):
                object_kind = "unit"
            placement["kind"] = object_kind
            placement["object_index"] = target_index
            return {"kind": "object", "object_index": target_index, "placement_kind": object_kind}
        return None

    return None


def select_validation_issue(issue_index):
    state = get_editor_authoring_state()
    issues = state.get("validation_issues", [])
    if issue_index < 0 or issue_index >= len(issues):
        return None
    issue = issues[issue_index]
    return select_authoring_target(
        issue.get("target_kind"),
        target_index=issue.get("target_index"),
        player_id=issue.get("player_id"),
    )


def scenario_path_for_map(map_path):
    root, _ext = os.path.splitext(map_path)
    return root + ".sovereign.json"


def _safe_int(value, default_value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default_value


def _count_placed_objects(placed_objects):
    units = 0
    buildings = 0
    for obj in placed_objects:
        if obj.get("kind") == "unit":
            units += 1
        elif obj.get("kind") == "building":
            buildings += 1
    return units, buildings


def _build_export_report(scenario, validation_errors=None):
    players = scenario.get("players", [])
    placed_resources = scenario.get("placed_resources", [])
    placed_objects = scenario.get("placed_objects", [])
    palette = scenario.get("palette", {})
    errors = list(validation_errors or [])
    units, buildings = _count_placed_objects(placed_objects)
    marker_count = len(players) + len(placed_resources) + len(placed_objects)
    return {
        "version": 1,
        "scenario_id": scenario.get("id"),
        "map_seed": scenario.get("metadata", {}).get("map_seed"),
        "setup": copy.deepcopy(scenario.get("setup", {})),
        "victory_mode": scenario.get("victory", {}).get("mode"),
        "counts": {
            "players": len(players),
            "resource_clusters": len(placed_resources),
            "placed_objects": len(placed_objects),
            "units": units,
            "buildings": buildings,
            "markers": marker_count,
            "diplomacy_rows": len(scenario.get("diplomacy", [])),
            "palette_units": len(palette.get("units", [])),
            "palette_buildings": len(palette.get("buildings", [])),
            "palette_resources": len(palette.get("resources", [])),
        },
        "validation": {
            "status": "blocked" if errors else "ready",
            "issue_count": len(errors),
            "issues": errors[:20],
        },
    }


def _build_editor_scenario_doc(map_path, players=None, scenario_id=None, name=None):
    authoring = get_editor_authoring_state()
    map_dir = os.path.dirname(map_path) or "."
    map_file = os.path.basename(map_path)
    if scenario_id is None:
        scenario_id = authoring.get("scenario_id") or os.path.splitext(map_file)[0]
    if name is None:
        name = authoring.get("name") or scenario_id.replace("_", " ").replace("-", " ").title()
    scenario_players = players or authoring.get("players") or DEFAULT_PLAYERS
    palette = authoring.get("palette") or DEFAULT_PALETTE
    placed_resources = authoring.get("placed_resources") or [
        copy.deepcopy(resource) for resource in DEFAULT_PLACED_RESOURCES
    ]
    placed_objects = authoring.get("placed_objects") or [
        copy.deepcopy(obj) for obj in DEFAULT_PLACED_OBJECTS
    ]
    map_seed = _safe_int(authoring.get("map_seed"), DEFAULT_MAP_SEED)
    victory_mode = authoring.get("victory_mode") or DEFAULT_VICTORY_MODE
    setup_profile, preset = _resolve_setup_ids({
        "profile": authoring.get("setup_profile"),
        "starting_resource_preset": authoring.get("starting_resource_preset"),
    })
    victory_label = VICTORY_LABELS.get(victory_mode, victory_mode.replace("_", " ").title())
    diplomacy_state = authoring.get("diplomacy_state") or "war"
    diplomacy = []
    for idx, first in enumerate(scenario_players):
        for second in scenario_players[idx + 1:]:
            diplomacy.append({"a": first["id"], "b": second["id"], "state": diplomacy_state})

    scenario = {
        "version": 1,
        "id": scenario_id,
        "name": name,
        "metadata": {
            "map_seed": map_seed,
            "author_notes": authoring.get("author_notes") or DEFAULT_AUTHOR_NOTES,
        },
        "map": {
            "path": map_dir,
            "pfmap": map_file,
        },
        "setup": {
            "profile": setup_profile,
            "starting_resource_preset": preset,
            "victory_mode": victory_mode,
        },
        "victory": {
            "mode": victory_mode,
            "label": victory_label,
        },
        "palette": copy.deepcopy(palette),
        "players": copy.deepcopy(scenario_players),
        "placed_resources": copy.deepcopy(placed_resources),
        "placed_objects": copy.deepcopy(placed_objects),
        "diplomacy": diplomacy,
    }
    scenario["export_report"] = _build_export_report(scenario)
    return scenario


def build_editor_scenario(map_path, players=None, scenario_id=None, name=None):
    scenario = _build_editor_scenario_doc(map_path, players=players, scenario_id=scenario_id, name=name)
    require_valid_scenario(scenario)
    return scenario


def _pathing_errors_for_point(label, point, radius):
    try:
        import pf
    except ImportError:
        return []
    try:
        nearest = pf.map_nearest_pathable(tuple(point), radius=radius)
    except Exception:
        return []
    if nearest is None:
        return ["{0} is not near pathable terrain".format(label)]
    return []


def _validation_issue(message, target_kind=None, target_index=None, player_id=None):
    return {
        "message": message,
        "target_kind": target_kind,
        "target_index": target_index,
        "player_id": player_id,
    }


def _target_for_validation_error(message, scenario):
    parts = message.split()
    if len(parts) >= 3 and parts[0] == "player" and parts[1] == "starts":
        try:
            return _validation_issue(message, "player_start", player_id=int(parts[2]))
        except ValueError:
            return _validation_issue(message)

    if len(parts) >= 2 and parts[0] == "player":
        try:
            return _validation_issue(message, "player_start", player_id=int(parts[1]))
        except ValueError:
            return _validation_issue(message)

    if len(parts) >= 3 and parts[0] == "placed" and parts[1] == "resource":
        try:
            return _validation_issue(message, "resource", target_index=int(parts[2]))
        except ValueError:
            return _validation_issue(message)

    if len(parts) >= 3 and parts[0] == "placed" and parts[1] == "object":
        try:
            return _validation_issue(message, "object", target_index=int(parts[2]))
        except ValueError:
            pass

    if message.startswith("placed object id '") and "' is duplicated" in message:
        duplicate_id = message.split("'")[1]
        matches = [
            idx
            for idx, obj in enumerate(scenario.get("placed_objects", []))
            if obj.get("id") == duplicate_id
        ]
        if matches:
            return _validation_issue(message, "object", target_index=matches[-1])

    return _validation_issue(message)


def validate_editor_authoring_state(map_path=None, check_pathing=True):
    authoring = get_editor_authoring_state()
    scenario = _build_editor_scenario_doc(map_path or "sovereign_authoring_preview.pfmap")
    errors = validate_scenario(scenario)
    issues = [
        _target_for_validation_error(error, scenario)
        for error in errors
    ]

    if check_pathing:
        for idx, player in enumerate(scenario.get("players", [])):
            player_errors = _pathing_errors_for_point(
                "player {0} start".format(player.get("id")),
                player.get("start", (0.0, 0.0)),
                3.25,
            )
            errors.extend(player_errors)
            issues.extend([
                _validation_issue(error, "player_start", player_id=player.get("id"))
                for error in player_errors
            ])

        for idx, resource in enumerate(scenario.get("placed_resources", [])):
            resource_def = RESOURCES.get(resource.get("resource_id"), {})
            node = resource_def.get("node", {})
            resource_errors = _pathing_errors_for_point(
                "resource {0}".format(resource.get("id", resource.get("resource_id"))),
                resource.get("point", (0.0, 0.0)),
                node.get("selection_radius", 2.5),
            )
            errors.extend(resource_errors)
            issues.extend([
                _validation_issue(error, "resource", target_index=idx)
                for error in resource_errors
            ])

        for idx, obj in enumerate(scenario.get("placed_objects", [])):
            definitions = UNITS if obj.get("kind") == "unit" else BUILDINGS
            definition = definitions.get(obj.get("object_id"), {})
            object_errors = _pathing_errors_for_point(
                "object {0}".format(obj.get("id", obj.get("object_id"))),
                obj.get("point", (0.0, 0.0)),
                definition.get("selection_radius", 2.5),
            )
            errors.extend(object_errors)
            issues.extend([
                _validation_issue(error, "object", target_index=idx)
                for error in object_errors
            ])

    authoring["validation_errors"] = errors
    authoring["validation_issues"] = issues
    authoring["export_report"] = _build_export_report(scenario, errors)
    return errors


def write_editor_scenario(map_path, output_path=None, players=None):
    errors = validate_editor_authoring_state(map_path)
    if errors:
        set_export_status(
            "error",
            output_path or scenario_path_for_map(map_path),
            "{0} validation issue(s) blocked export".format(len(errors)),
        )
        raise ValueError("invalid Sovereign editor scenario: " + "; ".join(errors))
    scenario = build_editor_scenario(map_path, players=players)
    scenario["export_report"] = _build_export_report(scenario)
    sidecar_path = output_path or scenario_path_for_map(map_path)
    sidecar_dir = os.path.dirname(sidecar_path)
    if sidecar_dir and not os.path.isdir(sidecar_dir):
        os.makedirs(sidecar_dir)
    save_scenario(scenario, sidecar_path)
    get_editor_authoring_state()["export_report"] = copy.deepcopy(scenario["export_report"])
    set_export_status(
        "saved",
        sidecar_path,
        "Exported {0} player(s), {1} resource cluster(s), {2} placed object(s), {3} marker(s), seed {4}".format(
            len(scenario.get("players", [])),
            len(scenario.get("placed_resources", [])),
            len(scenario.get("placed_objects", [])),
            scenario["export_report"]["counts"]["markers"],
            scenario["metadata"]["map_seed"],
        ),
    )
    return sidecar_path, scenario
