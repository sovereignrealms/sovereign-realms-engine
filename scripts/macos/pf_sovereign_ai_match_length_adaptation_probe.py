import argparse
import json
import os
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import sovereign.globals as sovereign_globals
from sovereign.data.units import UNITS
from sovereign.entities.runtime import create_entity, place_entity
from sovereign.factory import spawn_minimal_test_scene
from sovereign.systems.production import player_state_from_spawn_result
from sovereign.systems.skirmish import MatchLengthBuildOrderPlanner, ScriptedSkirmishAI


PROBE_PATH = "/tmp/pf_sovereign_ai_match_length_adaptation_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_match_length_adaptation_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "opening_economy": False,
        "transition_timing": False,
        "expansion_timing": False,
        "military_transition": False,
        "attack_timing": False,
    },
    "profiles": {},
    "runtime": {},
}

PROFILE_LAYOUTS = {
    "standard": {"player": (64.0, 64.0), "enemy": (116.0, 76.0), "expansion": [(150.0, 92.0), (164.0, 100.0)]},
    "booming": {"player": (64.0, 116.0), "enemy": (116.0, 128.0), "expansion": [(150.0, 144.0), (164.0, 152.0)]},
    "hard": {"player": (64.0, 168.0), "enemy": (116.0, 180.0), "expansion": [(150.0, 196.0), (164.0, 204.0)]},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run Sovereign match-length build-order adaptation checks.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-match-length-adaptation")
    parser.add_argument("--expect-backend", default="METAL")
    parser.add_argument("--steps", type=int, default=18)
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    print("SOVEREIGN_AI_MATCH_LENGTH_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_match_length_adaptation.json")


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "profiles": STATE["profiles"],
        "runtime": STATE["runtime"],
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_AI_MATCH_LENGTH_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_MATCH_LENGTH_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_MATCH_LENGTH_ADAPTATION_PROBE_PASS runtime={runtime} "
        "opening={opening} transition={transition} expansion={expansion} "
        "military={military} attack={attack}"
    ).format(
        runtime=int(STATE["checks"]["runtime_scene"]),
        opening=int(STATE["checks"]["opening_economy"]),
        transition=int(STATE["checks"]["transition_timing"]),
        expansion=int(STATE["checks"]["expansion_timing"]),
        military=int(STATE["checks"]["military_transition"]),
        attack=int(STATE["checks"]["attack_timing"]),
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _ensure_factions():
    if len(pf.get_factions_list()) == 0:
        pf.add_faction("Neutral", (160, 160, 160, 255))
        pf.add_faction("Sovereign", (40, 90, 255, 255))
        pf.add_faction("Opponent", (220, 50, 50, 255))


def _setup_world():
    pf.load_map("assets/maps", "plain.pfmap")
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    _ensure_factions()
    center = (126.0, 132.0)
    camera = pf.Camera(
        name="sovereign_ai_match_length_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 190.0, center[1] + 26.0),
        pitch=-64.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_match_length_region",
            position=center,
            dimensions=(160.0, 180.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _rename_spawned(result, prefix):
    for ent in result["entities"]:
        ent.name = "{0}_{1}".format(prefix, ent.name)


def _spawned_entity(result, kind, entity_id, name=None):
    for entry, ent in zip(result["plan"]["entities"], result["entities"]):
        if entry["kind"] != kind or entry["id"] != entity_id:
            continue
        if name is not None and entry["name"] != name:
            continue
        return ent
    return None


def _create_starting_militia(scene_objs, enemy_state, profile_id, point):
    definition = UNITS["militia"]
    ent = create_entity({
        "kind": "unit",
        "id": "militia",
        "name": "ai_{0}_match_opening_guard".format(profile_id),
        "definition": definition,
    })
    place_entity(
        ent,
        point,
        faction_id=2,
        radius=definition.get("selection_radius", 3.25),
        scale=definition.get("scale"),
    )
    scene_objs.append(ent)
    enemy_state.add_unit("militia", ent)
    return ent


def _phase_counts(phases):
    counts = {}
    for phase in phases:
        counts[phase] = counts.get(phase, 0) + 1
    return counts


def _first_phase(phases, phase):
    for idx, value in enumerate(phases):
        if value == phase:
            return idx + 1
    return None


def _run_profile(profile_id, steps, scene_objs):
    layout = PROFILE_LAYOUTS[profile_id]
    player_result = spawn_minimal_test_scene(center=layout["player"], faction_id=1, scene_objs=scene_objs)
    enemy_result = spawn_minimal_test_scene(center=layout["enemy"], faction_id=2, scene_objs=scene_objs)
    _rename_spawned(player_result, "player_{0}".format(profile_id))
    _rename_spawned(enemy_result, "ai_{0}".format(profile_id))
    enemy_state = player_state_from_spawn_result(
        enemy_result,
        completed_buildings=("town_center", "house", "barracks"),
    )

    player_town_center = _spawned_entity(player_result, "building", "town_center")
    player_villager = _spawned_entity(player_result, "unit", "villager", "villager_1")
    player_barracks = _spawned_entity(player_result, "building", "barracks")
    enemy_barracks = _spawned_entity(enemy_result, "building", "barracks")
    enemy_town_center = _spawned_entity(enemy_result, "building", "town_center")
    if None in (player_town_center, player_villager, player_barracks, enemy_barracks, enemy_town_center):
        _fail("required match-length fixture entity was not spawned for {0}".format(profile_id))

    enemy_barracks.name = "ai_{0}_match_barracks".format(profile_id)
    enemy_town_center.name = "ai_{0}_match_town_center".format(profile_id)
    guard = _create_starting_militia(
        scene_objs,
        enemy_state,
        profile_id,
        (layout["enemy"][0] + 22.0, layout["enemy"][1] + 8.0),
    )
    try:
        guard.face_towards(player_barracks.pos)
        enemy_barracks.rally_point = (layout["enemy"][0] - 10.0, layout["enemy"][1] + 6.0)
    except (AttributeError, RuntimeError):
        pass

    enemy_state.resources["food"] = 0
    enemy_state.resources["wood"] = 0
    enemy_state.resources["gold"] = 0
    enemy_state.resources["stone"] = 0
    enemy_state.population_cap = max(enemy_state.population_used + 8, enemy_state.population_cap)

    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=6060)
    target_groups = {
        "town_center": [player_town_center],
        "villagers": [player_villager],
        "military": [],
        "buildings": [player_barracks],
    }
    planner = MatchLengthBuildOrderPlanner(
        ai,
        target_groups,
        defended_assets=[enemy_barracks, enemy_town_center],
        difficulty_id=profile_id,
        expansion_points=layout["expansion"],
        threat_radius=4.0,
    )

    decisions = []
    for _idx in range(int(steps)):
        decisions.append(dict(planner.step()))

    snapshot = planner.snapshot()
    phases = list(snapshot["phase_history"])
    return {
        "decision_count": len(decisions),
        "phase_counts": _phase_counts(phases),
        "first_expansion_step": _first_phase(phases, "expansion_timing"),
        "first_military_step": _first_phase(phases, "military_transition"),
        "first_attack_step": _first_phase(phases, "attack_timing"),
        "first_hold_step": _first_phase(phases, "match_hold"),
        "planner": snapshot,
        "ai": ai.snapshot(),
        "counts": {
            "bases": snapshot["base_count"],
            "army": snapshot["army_count"],
            "militia": ai.unit_count("militia"),
            "archer": ai.unit_count("archer"),
        },
    }


def _run_probe(steps):
    _setup_world()
    scene_objs = []
    sovereign_globals.scene_objs = scene_objs
    for profile_id in ("standard", "booming", "hard"):
        print("SOVEREIGN_AI_MATCH_LENGTH_PROFILE {0}".format(profile_id))
        sys.stdout.flush()
        STATE["profiles"][profile_id] = _run_profile(profile_id, steps, scene_objs)

    standard = STATE["profiles"]["standard"]
    booming = STATE["profiles"]["booming"]
    hard = STATE["profiles"]["hard"]
    STATE["runtime"] = {
        "profile_count": len(STATE["profiles"]),
        "steps_per_profile": int(steps),
        "scene_obj_count": len(scene_objs),
    }
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 36 and len(STATE["profiles"]) == 3
    STATE["checks"]["opening_economy"] = (
        standard["phase_counts"].get("opening_economy") == standard["planner"]["economy_opening_steps"]
        and booming["phase_counts"].get("opening_economy") == booming["planner"]["economy_opening_steps"]
        and hard["phase_counts"].get("opening_economy") == hard["planner"]["economy_opening_steps"]
        and hard["planner"]["economy_opening_steps"] < standard["planner"]["economy_opening_steps"] < booming["planner"]["economy_opening_steps"]
    )
    STATE["checks"]["transition_timing"] = (
        hard["planner"]["transition_step"] < standard["planner"]["transition_step"] < booming["planner"]["transition_step"]
    )
    STATE["checks"]["expansion_timing"] = (
        standard["first_expansion_step"] < standard["planner"]["transition_step"]
        and booming["counts"]["bases"] == 3
        and booming["first_expansion_step"] < booming["planner"]["transition_step"]
        and hard["planner"]["transition_step"] < hard["first_expansion_step"]
        and hard["counts"]["bases"] == 3
    )
    STATE["checks"]["military_transition"] = (
        standard["planner"]["attack_unit_id"] == "militia"
        and booming["planner"]["attack_unit_id"] == "militia"
        and hard["planner"]["attack_unit_id"] == "archer"
        and hard["counts"]["archer"] >= 3
        and standard["counts"]["militia"] >= 2
        and booming["counts"]["militia"] >= 2
    )
    STATE["checks"]["attack_timing"] = (
        standard["planner"]["attack_launched"]
        and booming["planner"]["attack_launched"]
        and hard["planner"]["attack_launched"]
        and standard["planner"]["attack_step"] > standard["planner"]["transition_step"]
        and booming["planner"]["attack_step"] > booming["planner"]["transition_step"]
        and hard["planner"]["attack_step"] > hard["planner"]["transition_step"]
    )


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _set_phase("match_length")
        _run_probe(STATE["steps"])
        if all(STATE["checks"].values()):
            _succeed()
            return
        _fail("match-length adaptation checks did not all pass: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["steps"] = int(args.steps)
    STATE["phase_started_at"] = time.monotonic()
    for path in (PROBE_PATH, ERROR_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
