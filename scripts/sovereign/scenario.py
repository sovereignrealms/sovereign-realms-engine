from __future__ import print_function

import copy
import json
import math
import random

import pf

import sovereign.globals as sovereign_globals
from sovereign.data.buildings import BUILDINGS
from sovereign.data.civilizations import CIVILIZATIONS
from sovereign.data.resources import RESOURCES
from sovereign.data.units import UNITS
from sovereign.factory import spawn_minimal_test_scene, validate_registries
from sovereign.systems.production import player_state_from_spawn_result


RESOURCE_IDS = ("food", "wood", "gold", "stone")
DIPLOMACY_STATES = {
    "peace": pf.DIPLOMACY_STATE_PEACE,
    "war": pf.DIPLOMACY_STATE_WAR,
}
SUPPORTED_VICTORY_MODES = {
    "conquest": "Conquest",
}
STARTING_RESOURCE_PRESETS = {
    "standard": {
        "label": "Standard",
        "resources": {"food": 260, "wood": 240, "gold": 140, "stone": 100},
    },
    "generous": {
        "label": "Generous",
        "resources": {"food": 500, "wood": 500, "gold": 200, "stone": 100},
    },
    "low": {
        "label": "Low Resources",
        "resources": {"food": 100, "wood": 100, "gold": 50, "stone": 0},
    },
}
SETUP_PROFILES = {
    "standard_skirmish": {
        "label": "Standard Skirmish",
        "starting_resource_preset": "standard",
        "victory_mode": "conquest",
    },
    "fast_skirmish": {
        "label": "Fast Skirmish",
        "starting_resource_preset": "generous",
        "victory_mode": "conquest",
    },
}
DEFAULT_SETUP_PROFILE = "standard_skirmish"


def load_scenario(path):
    with open(path, "r") as infile:
        return json.load(infile)


def save_scenario(scenario, path):
    with open(path, "w") as outfile:
        json.dump(scenario, outfile, indent=2, sort_keys=True)
        outfile.write("\n")


def _is_number(value):
    return isinstance(value, (int, float))


def _start_distance(a, b):
    dx = float(a[0]) - float(b[0])
    dz = float(a[1]) - float(b[1])
    return math.sqrt(dx * dx + dz * dz)


def scenario_metadata(scenario):
    metadata = copy.deepcopy(scenario.get("metadata") or {})
    try:
        map_seed = int(metadata.get("map_seed", 0))
    except (TypeError, ValueError):
        map_seed = 0
    metadata["map_seed"] = map_seed
    metadata["author_notes"] = metadata.get("author_notes") or ""
    return metadata


def scenario_victory(scenario):
    victory = copy.deepcopy(scenario.get("victory") or {})
    mode = victory.get("mode") or "conquest"
    victory["mode"] = mode
    victory["label"] = victory.get("label") or SUPPORTED_VICTORY_MODES.get(
        mode,
        mode.replace("_", " ").title(),
    )
    return victory


def scenario_setup(scenario):
    setup = copy.deepcopy(scenario.get("setup") or {})
    profile_id = setup.get("profile") or DEFAULT_SETUP_PROFILE
    profile = SETUP_PROFILES.get(profile_id, SETUP_PROFILES[DEFAULT_SETUP_PROFILE])
    preset_id = setup.get("starting_resource_preset") or profile["starting_resource_preset"]
    preset = STARTING_RESOURCE_PRESETS.get(preset_id, STARTING_RESOURCE_PRESETS[profile["starting_resource_preset"]])
    return {
        "profile": profile_id,
        "profile_label": profile["label"],
        "starting_resource_preset": preset_id,
        "starting_resource_preset_label": preset["label"],
        "starting_resources": copy.deepcopy(preset["resources"]),
        "victory_mode": setup.get("victory_mode") or profile["victory_mode"],
    }


def scenario_player_starting_resources(scenario, player):
    resources = copy.deepcopy(scenario_setup(scenario)["starting_resources"])
    resources.update(player.get("starting_resources", {}))
    return {
        resource_id: int(resources.get(resource_id, 0))
        for resource_id in RESOURCE_IDS
    }


def scenario_seed(scenario):
    return scenario_metadata(scenario)["map_seed"]


def scenario_rng(scenario, salt=0):
    return random.Random(scenario_seed(scenario) + int(salt))


def scenario_seeded_choice(scenario, choices, salt=0):
    if not choices:
        return None
    rng = scenario_rng(scenario, salt=salt)
    return list(choices)[rng.randrange(len(choices))]


def scenario_runtime_state(scenario):
    return {
        "id": scenario.get("id"),
        "name": scenario.get("name"),
        "map": copy.deepcopy(scenario.get("map", {})),
        "setup": scenario_setup(scenario),
        "metadata": scenario_metadata(scenario),
        "victory": scenario_victory(scenario),
    }


def validate_scenario(scenario):
    errors = list(validate_registries())

    if int(scenario.get("version", 0)) != 1:
        errors.append("scenario version must be 1")

    map_info = scenario.get("map", {})
    if not map_info.get("path") or not map_info.get("pfmap"):
        errors.append("scenario must define map.path and map.pfmap")

    victory = scenario_victory(scenario)
    if victory.get("mode") not in SUPPORTED_VICTORY_MODES:
        errors.append("only conquest victory is supported in the first Sovereign scenario slice")
    if victory.get("label") is not None and not isinstance(victory.get("label"), str):
        errors.append("victory label must be text when provided")

    metadata = scenario.get("metadata", {})
    if metadata:
        map_seed = metadata.get("map_seed")
        if not isinstance(map_seed, int) or map_seed < 0:
            errors.append("metadata.map_seed must be a non-negative integer")
        if not isinstance(metadata.get("author_notes", ""), str):
            errors.append("metadata.author_notes must be text")

    setup = scenario.get("setup", {})
    if setup:
        profile = setup.get("profile", DEFAULT_SETUP_PROFILE)
        if profile not in SETUP_PROFILES:
            errors.append("setup references unknown profile '{0}'".format(profile))
        preset = setup.get("starting_resource_preset", SETUP_PROFILES.get(profile, SETUP_PROFILES[DEFAULT_SETUP_PROFILE])["starting_resource_preset"])
        if preset not in STARTING_RESOURCE_PRESETS:
            errors.append("setup references unknown starting_resource_preset '{0}'".format(preset))
        victory_mode = setup.get("victory_mode")
        if victory_mode is not None and victory_mode not in SUPPORTED_VICTORY_MODES:
            errors.append("setup references unsupported victory_mode '{0}'".format(victory_mode))

    palette = scenario.get("palette", {})
    for unit_id in palette.get("units", []):
        if unit_id not in UNITS:
            errors.append("palette references unknown unit '{0}'".format(unit_id))
    for building_id in palette.get("buildings", []):
        if building_id not in BUILDINGS:
            errors.append("palette references unknown building '{0}'".format(building_id))
    for resource_id in palette.get("resources", []):
        if resource_id not in RESOURCES or resource_id == "population":
            errors.append("palette references unknown resource '{0}'".format(resource_id))

    players = scenario.get("players", [])
    if len(players) < 2:
        errors.append("scenario needs at least two players")

    seen_ids = set()
    starts = []
    for player in players:
        player_id = player.get("id")
        if not isinstance(player_id, int) or player_id <= 0:
            errors.append("player id must be a positive integer")
            continue
        if player_id in seen_ids:
            errors.append("duplicate player id {0}".format(player_id))
        seen_ids.add(player_id)

        civilization_id = player.get("civilization_id")
        if civilization_id not in CIVILIZATIONS:
            errors.append("player {0} references unknown civilization".format(player_id))

        color = player.get("faction_color")
        if not (
            isinstance(color, list)
            and len(color) == 4
            and all(isinstance(channel, int) and 0 <= channel <= 255 for channel in color)
        ):
            errors.append("player {0} needs an RGBA faction_color".format(player_id))

        start = player.get("start")
        if not (
            isinstance(start, list)
            and len(start) == 2
            and _is_number(start[0])
            and _is_number(start[1])
        ):
            errors.append("player {0} needs a numeric [x,z] start".format(player_id))
        else:
            starts.append((player_id, start))

        for resource_id, amount in player.get("starting_resources", {}).items():
            if resource_id not in RESOURCE_IDS:
                errors.append("player {0} has unknown starting resource '{1}'".format(player_id, resource_id))
            elif int(amount) < 0:
                errors.append("player {0} has negative starting resource '{1}'".format(player_id, resource_id))

    for idx, first in enumerate(starts):
        for second in starts[idx + 1:]:
            if _start_distance(first[1], second[1]) < 20.0:
                errors.append("player starts {0} and {1} are too close".format(first[0], second[0]))

    for row in scenario.get("diplomacy", []):
        if row.get("a") not in seen_ids or row.get("b") not in seen_ids:
            errors.append("diplomacy row references unknown player")
        if row.get("state") not in DIPLOMACY_STATES:
            errors.append("diplomacy row has unsupported state '{0}'".format(row.get("state")))

    placed_resources = scenario.get("placed_resources")
    if placed_resources is not None:
        seen_resources = set()
        if not isinstance(placed_resources, list) or not placed_resources:
            errors.append("placed_resources must contain at least one resource cluster")
        else:
            for idx, resource in enumerate(placed_resources):
                resource_id = resource.get("resource_id")
                if resource_id not in RESOURCE_IDS:
                    errors.append("placed resource {0} has unknown resource_id".format(idx))
                else:
                    seen_resources.add(resource_id)
                owner = resource.get("owner_player_id", 0)
                if owner != 0 and owner not in seen_ids:
                    errors.append("placed resource {0} references unknown owner_player_id".format(idx))
                point = resource.get("point")
                if not (
                    isinstance(point, list)
                    and len(point) == 2
                    and _is_number(point[0])
                    and _is_number(point[1])
                ):
                    errors.append("placed resource {0} needs a numeric [x,z] point".format(idx))
                if int(resource.get("amount", 0)) <= 0:
                    errors.append("placed resource {0} needs a positive amount".format(idx))
        for resource_id in RESOURCE_IDS:
            if resource_id not in seen_resources:
                errors.append("placed_resources is missing a {0} cluster".format(resource_id))

    placed_objects = scenario.get("placed_objects")
    if placed_objects is not None:
        seen_object_ids = set()
        if not isinstance(placed_objects, list):
            errors.append("placed_objects must be a list")
        else:
            for idx, obj in enumerate(placed_objects):
                authoring_id = obj.get("id")
                if not authoring_id:
                    errors.append("placed object {0} needs an id".format(idx))
                elif authoring_id in seen_object_ids:
                    errors.append("placed object id '{0}' is duplicated".format(authoring_id))
                else:
                    seen_object_ids.add(authoring_id)

                kind = obj.get("kind")
                object_id = obj.get("object_id")
                if kind == "unit":
                    if object_id not in UNITS:
                        errors.append("placed object {0} references unknown unit '{1}'".format(idx, object_id))
                elif kind == "building":
                    if object_id not in BUILDINGS:
                        errors.append("placed object {0} references unknown building '{1}'".format(idx, object_id))
                else:
                    errors.append("placed object {0} needs kind 'unit' or 'building'".format(idx))

                owner = obj.get("owner_player_id")
                if owner not in seen_ids:
                    errors.append("placed object {0} references unknown owner_player_id".format(idx))

                point = obj.get("point")
                if not (
                    isinstance(point, list)
                    and len(point) == 2
                    and _is_number(point[0])
                    and _is_number(point[1])
                ):
                    errors.append("placed object {0} needs a numeric [x,z] point".format(idx))

    export_report = scenario.get("export_report")
    if export_report is not None:
        counts = export_report.get("counts", {}) if isinstance(export_report, dict) else {}
        validation = export_report.get("validation", {}) if isinstance(export_report, dict) else {}
        if not isinstance(export_report, dict):
            errors.append("export_report must be an object")
        elif not isinstance(counts.get("markers", 0), int) or counts.get("markers", 0) < 0:
            errors.append("export_report.counts.markers must be a non-negative integer")
        elif validation.get("status") not in ("ready", "blocked"):
            errors.append("export_report.validation.status must be ready or blocked")

    return errors


def require_valid_scenario(scenario):
    errors = validate_scenario(scenario)
    if errors:
        raise ValueError("invalid Sovereign scenario: " + "; ".join(errors))


def _ensure_factions(scenario):
    max_player_id = max(player["id"] for player in scenario["players"])
    while len(pf.get_factions_list()) <= max_player_id:
        idx = len(pf.get_factions_list())
        if idx == 0:
            pf.add_faction("Neutral", (160, 160, 160, 255))
        else:
            match = None
            for player in scenario["players"]:
                if player["id"] == idx:
                    match = player
                    break
            if match is None:
                pf.add_faction("Player {0}".format(idx), (180, 180, 180, 255))
            else:
                pf.add_faction(match["name"], tuple(match.get("faction_color", (180, 180, 180, 255))))


def _apply_diplomacy(scenario):
    for row in scenario.get("diplomacy", []):
        pf.set_diplomacy_state(row["a"], row["b"], DIPLOMACY_STATES[row["state"]])


def _apply_starting_resources(player_state, scenario, player):
    for resource_id, amount in scenario_player_starting_resources(scenario, player).items():
        player_state.resources[resource_id] = int(amount)


def _nearest_pathable_or_error(point, radius, label):
    nearest = pf.map_nearest_pathable(tuple(point), radius=radius)
    if nearest is None:
        raise ValueError("{0} is not near pathable terrain".format(label))
    return nearest


def _spawn_placed_resources(scenario, scene_objs):
    from sovereign.entities.runtime import create_entity, place_entity

    for idx, resource in enumerate(scenario.get("placed_resources", [])):
        resource_id = resource["resource_id"]
        definition = copy.deepcopy(RESOURCES[resource_id])
        definition["node"]["amount"] = int(resource["amount"])
        entry = {
            "kind": "resource",
            "id": resource_id,
            "name": resource.get("id") or "{0}_cluster_{1}".format(resource_id, idx + 1),
            "definition": definition,
        }
        ent = create_entity(entry)
        node = definition["node"]
        point = _nearest_pathable_or_error(resource["point"], node.get("selection_radius", 2.5), entry["name"])
        place_entity(
            ent,
            point,
            faction_id=int(resource.get("owner_player_id", 0)),
            radius=node.get("selection_radius", 2.5),
            scale=node.get("scale"),
            selectable=False,
        )
        scene_objs.append(ent)


def _spawn_placed_objects(scenario, scene_objs, player_records):
    from sovereign.entities.runtime import create_entity, place_entity

    for idx, obj in enumerate(scenario.get("placed_objects", [])):
        kind = obj["kind"]
        object_id = obj["object_id"]
        definition = UNITS[object_id] if kind == "unit" else BUILDINGS[object_id]
        entry = {
            "kind": kind,
            "id": object_id,
            "name": obj.get("id") or "{0}_{1}".format(object_id, idx + 1),
            "definition": definition,
        }
        ent = create_entity(entry)
        point = _nearest_pathable_or_error(
            obj["point"],
            definition.get("selection_radius", 2.5),
            entry["name"],
        )
        owner = int(obj["owner_player_id"])
        place_entity(
            ent,
            point,
            faction_id=owner,
            radius=definition.get("selection_radius", 2.5),
            scale=definition.get("scale"),
            selectable=True,
        )
        scene_objs.append(ent)
        player_state = player_records.get(owner, {}).get("state")
        if player_state is not None:
            if kind == "unit":
                player_state.add_unit(object_id, ent)
            else:
                if hasattr(ent, "completed") and not ent.completed:
                    ent.mark()
                    ent.found(force=True)
                    ent.supply()
                    ent.complete()
                player_state.add_building(object_id, ent)


def build_runtime_scene(scenario, scene_objs=None):
    require_valid_scenario(scenario)
    scenario_state = scenario_runtime_state(scenario)
    map_info = scenario["map"]
    pf.load_map(map_info["path"], map_info["pfmap"])
    _ensure_factions(scenario)
    _apply_diplomacy(scenario)

    if scene_objs is None:
        scene_objs = []
    player_records = {}
    completed = ("town_center", "house", "barracks")

    for player in scenario["players"]:
        _nearest_pathable_or_error(player["start"], 3.25, "player {0} start".format(player["id"]))
        result = spawn_minimal_test_scene(
            center=tuple(player["start"]),
            faction_id=player["id"],
            scene_objs=scene_objs,
            civilization_id=player["civilization_id"],
        )
        state = player_state_from_spawn_result(
            result,
            completed_buildings=completed,
            civilization_id=player["civilization_id"],
        )
        _apply_starting_resources(state, scenario, player)
        player_records[player["id"]] = {
            "definition": player,
            "spawn_result": result,
            "state": state,
        }

    _spawn_placed_resources(scenario, scene_objs)
    _spawn_placed_objects(scenario, scene_objs, player_records)

    sovereign_globals.scene_objs = scene_objs
    sovereign_globals.scenario_state = scenario_state
    return {
        "scenario": scenario,
        "scenario_state": scenario_state,
        "map_seed": scenario_state["metadata"]["map_seed"],
        "rng": scenario_rng(scenario),
        "scene_objs": scene_objs,
        "players": player_records,
    }


def scenario_summary(runtime):
    placed_resources = list(runtime["scenario"].get("placed_resources", []))
    placed_objects = list(runtime["scenario"].get("placed_objects", []))
    return {
        "id": runtime["scenario"].get("id"),
        "name": runtime["scenario"].get("name"),
        "players": {
            str(player_id): record["state"].snapshot()
            for player_id, record in runtime["players"].items()
        },
        "object_count": len(runtime["scene_objs"]),
        "placed_resource_count": len(placed_resources),
        "placed_resources": placed_resources,
        "placed_object_count": len(placed_objects),
        "placed_objects": placed_objects,
        "metadata": copy.deepcopy(runtime["scenario"].get("metadata", {})),
        "scenario_state": copy.deepcopy(runtime.get("scenario_state", {})),
        "map_seed": runtime.get("map_seed"),
        "victory": runtime["scenario"].get("victory", {}),
        "export_report": copy.deepcopy(runtime["scenario"].get("export_report", {})),
        "diplomacy": list(runtime["scenario"].get("diplomacy", [])),
    }
