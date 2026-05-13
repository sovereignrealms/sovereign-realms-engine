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
from sovereign.scenario import build_runtime_scene, load_scenario, scenario_summary
from sovereign.systems.skirmish import BranchingStrategyPlanner, ScriptedSkirmishAI, ai_difficulty_profile


PROBE_PATH = "/tmp/pf_sovereign_ai_difficulty_ab_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_difficulty_ab_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "profile_divergence": False,
        "expansion_tuning": False,
        "harassment_frequency": False,
        "target_priorities": False,
        "unit_composition": False,
        "extended_decisions": False,
    },
    "profiles": {},
    "runtime": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign AI difficulty A/B skirmish probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-difficulty-ab")
    parser.add_argument("--expect-backend", default="METAL")
    parser.add_argument("--steps", type=int, default=28)
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    print("SOVEREIGN_AI_DIFFICULTY_AB_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_difficulty_ab.json")


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


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
    print("SOVEREIGN_AI_DIFFICULTY_AB_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_DIFFICULTY_AB_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_DIFFICULTY_AB_PROBE_PASS runtime={runtime} "
        "profiles={profiles} expand={expand} harass={harass} "
        "targets={targets} units={units} extended={extended}"
    ).format(
        runtime=int(STATE["checks"]["runtime_scene"]),
        profiles=int(STATE["checks"]["profile_divergence"]),
        expand=int(STATE["checks"]["expansion_tuning"]),
        harass=int(STATE["checks"]["harassment_frequency"]),
        targets=int(STATE["checks"]["target_priorities"]),
        units=int(STATE["checks"]["unit_composition"]),
        extended=int(STATE["checks"]["extended_decisions"]),
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _spawned_entity(result, kind, entity_id, name=None):
    for entry, ent in zip(result["plan"]["entities"], result["entities"]):
        if entry["kind"] != kind or entry["id"] != entity_id:
            continue
        if name is not None and entry["name"] != name:
            continue
        return ent
    return None


def _entity_named(scene_objs, name):
    for ent in scene_objs:
        if getattr(ent, "name", None) == name:
            return ent
    return None


def _setup_render_state():
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    center = (124.0, 86.0)
    camera = pf.Camera(
        name="sovereign_ai_difficulty_ab_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 136.0, center[1] + 12.0),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_difficulty_ab_region",
            position=center,
            dimensions=(128.0, 96.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _create_existing_militia(scene_objs, enemy_state, name, point):
    definition = UNITS["militia"]
    ent = create_entity({
        "kind": "unit",
        "id": "militia",
        "name": name,
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


def _create_forward_villager(scene_objs, profile_id):
    definition = UNITS["villager"]
    ent = create_entity({
        "kind": "unit",
        "id": "villager",
        "name": "player_{0}_forward_worker".format(profile_id),
        "definition": definition,
    })
    place_entity(
        ent,
        (92.0, 80.0),
        faction_id=1,
        radius=definition.get("selection_radius", 2.5),
        scale=definition.get("scale"),
    )
    scene_objs.append(ent)
    return ent


def _decision_counts(decisions, key):
    counts = {}
    for item in decisions:
        value = item.get(key)
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _first_harass(decisions):
    for item in decisions:
        if item.get("action") == "counterattack" and item.get("reason") == "branching_harass":
            return item
    return {}


def _run_profile(profile_id, steps):
    scenario = load_scenario(os.path.join(pf.get_basedir(), "assets/sovereign/scenarios/two_player_skirmish.json"))
    scene_objs = []
    runtime = build_runtime_scene(scenario, scene_objs=scene_objs)
    if not sovereign_globals.scene_cameras:
        _setup_render_state()

    player_record = runtime["players"][1]
    enemy_record = runtime["players"][2]
    player_result = player_record["spawn_result"]
    enemy_result = enemy_record["spawn_result"]
    enemy_state = enemy_record["state"]

    player_town_center = _spawned_entity(player_result, "building", "town_center")
    player_villager = _spawned_entity(player_result, "unit", "villager", "villager_1")
    player_barracks = _spawned_entity(player_result, "building", "barracks")
    enemy_town_center = _spawned_entity(enemy_result, "building", "town_center")
    enemy_barracks = _spawned_entity(enemy_result, "building", "barracks")
    guard = _entity_named(scene_objs, "p1_guard")
    if None in (player_town_center, player_villager, player_barracks, enemy_town_center, enemy_barracks, guard):
        _fail("required difficulty A/B fixture entity was not spawned for {0}".format(profile_id))

    enemy_town_center.name = "ai_{0}_enemy_town_center".format(profile_id)
    enemy_barracks.name = "ai_{0}_enemy_barracks".format(profile_id)
    guard.name = "player_{0}_military_threat".format(profile_id)
    place_entity(
        guard,
        (122.0, 88.0),
        faction_id=1,
        radius=UNITS["militia"].get("selection_radius"),
        scale=UNITS["militia"].get("scale"),
    )

    militia_1 = _create_existing_militia(scene_objs, enemy_state, "ai_{0}_defender_1".format(profile_id), (146.0, 92.0))
    militia_2 = _create_existing_militia(scene_objs, enemy_state, "ai_{0}_defender_2".format(profile_id), (144.0, 94.0))
    forward_villager = _create_forward_villager(scene_objs, profile_id)
    try:
        guard.face_towards(militia_1.pos)
        forward_villager.face_towards(enemy_barracks.pos)
        militia_1.face_towards(guard.pos)
        militia_2.face_towards(guard.pos)
        enemy_barracks.rally_point = (100.0, 84.0)
    except (AttributeError, RuntimeError):
        pass

    enemy_state.resources["food"] = 0
    enemy_state.resources["wood"] = 0
    enemy_state.resources["gold"] = 0
    enemy_state.resources["stone"] = 0
    enemy_state.population_cap = max(enemy_state.population_used + 6, enemy_state.population_cap)

    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=runtime["map_seed"])
    target_groups = {
        "town_center": [player_town_center],
        "villagers": [forward_villager, player_villager],
        "military": [guard],
        "buildings": [player_barracks],
    }
    planner = BranchingStrategyPlanner(
        ai,
        target_groups,
        defended_assets=[enemy_barracks, enemy_town_center],
        difficulty_id=profile_id,
        expansion_points=[(160.0, 106.0), (170.0, 112.0)],
        target_bases=None,
        threat_radius=56.0,
    )

    decisions = []
    for _idx in range(int(steps)):
        decisions.append(dict(planner.step()))

    first_harass = _first_harass(decisions)
    expansion_events = [
        item for item in decisions
        if item.get("action") == "build_building" and item.get("reason") == "branching_expansion"
    ]
    training_events = [
        item for item in decisions
        if item.get("action") == "train" and item.get("strategy_branch") == "branching_harass"
    ]
    snapshot = planner.snapshot()
    profile = ai_difficulty_profile(profile_id)
    return {
        "profile": profile,
        "runtime": scenario_summary(runtime),
        "scene_obj_count": len(scene_objs),
        "decision_count": len(decisions),
        "action_counts": _decision_counts(decisions, "action"),
        "reason_counts": _decision_counts(decisions, "reason"),
        "strategy_counts": _decision_counts(decisions, "strategy_branch"),
        "first_harass": first_harass,
        "expansion_events": expansion_events,
        "training_events": training_events,
        "planner": snapshot,
        "ai": ai.snapshot(),
        "counts": {
            "bases": snapshot["base_count"],
            "army": snapshot["army_count"],
            "militia": ai.unit_count("militia"),
            "archer": ai.unit_count("archer"),
            "harass_waves": snapshot["harass_wave_count"],
            "expansions": len(expansion_events),
            "harass_training": len(training_events),
        },
        "expected": {
            "target_bases": profile["expansion_target_bases"],
            "harass_interval_steps": profile["harass_interval_steps"],
            "max_harass_waves": profile["max_harass_waves"],
            "harass_unit_id": profile["preferred_military_unit"],
            "first_target_role": profile["harass_target_roles"][0],
        },
    }


def _run_ab_probe(steps):
    for profile_id in ("standard", "booming", "hard"):
        print("SOVEREIGN_AI_DIFFICULTY_AB_PROFILE {0}".format(profile_id))
        sys.stdout.flush()
        STATE["profiles"][profile_id] = _run_profile(profile_id, steps)

    standard = STATE["profiles"]["standard"]
    booming = STATE["profiles"]["booming"]
    hard = STATE["profiles"]["hard"]
    STATE["runtime"] = {
        "profile_count": len(STATE["profiles"]),
        "steps_per_profile": int(steps),
        "scene_obj_counts": {
            key: value["scene_obj_count"]
            for key, value in STATE["profiles"].items()
        },
    }

    STATE["checks"]["runtime_scene"] = (
        len(STATE["profiles"]) == 3
        and all(value["scene_obj_count"] >= 25 for value in STATE["profiles"].values())
    )
    STATE["checks"]["profile_divergence"] = (
        standard["profile"]["personality_id"] == "balanced"
        and booming["profile"]["personality_id"] == "booming"
        and hard["profile"]["personality_id"] == "pressure"
        and standard["expected"]["target_bases"] == 2
        and booming["expected"]["target_bases"] == 3
        and hard["expected"]["target_bases"] == 3
        and standard["expected"]["harass_interval_steps"] > hard["expected"]["harass_interval_steps"]
        and booming["expected"]["harass_interval_steps"] > standard["expected"]["harass_interval_steps"]
    )
    STATE["checks"]["expansion_tuning"] = (
        standard["counts"]["bases"] == 2
        and booming["counts"]["bases"] == 3
        and hard["counts"]["bases"] == 3
        and booming["counts"]["expansions"] > standard["counts"]["expansions"]
    )
    STATE["checks"]["harassment_frequency"] = (
        standard["counts"]["harass_waves"] == 1
        and booming["counts"]["harass_waves"] == 1
        and hard["counts"]["harass_waves"] == 2
        and len(hard["planner"]["harass_launch_history"]) == 2
        and (
            hard["planner"]["harass_launch_history"][1]["step"]
            - hard["planner"]["harass_launch_history"][0]["step"]
        ) == hard["expected"]["harass_interval_steps"]
    )
    STATE["checks"]["target_priorities"] = (
        standard["first_harass"].get("target_role") == "buildings"
        and booming["first_harass"].get("target_role") == "buildings"
        and hard["first_harass"].get("target_role") == "villagers"
    )
    STATE["checks"]["unit_composition"] = (
        standard["planner"]["harass_unit_id"] == "militia"
        and booming["planner"]["harass_unit_id"] == "militia"
        and hard["planner"]["harass_unit_id"] == "archer"
        and hard["counts"]["archer"] >= 2
        and standard["counts"]["harass_training"] == 0
        and booming["counts"]["harass_training"] == 0
        and hard["counts"]["harass_training"] >= 2
    )
    STATE["checks"]["extended_decisions"] = all(
        value["decision_count"] >= int(steps)
        and value["reason_counts"].get("branching_strategy_complete", 0) > 0
        for value in STATE["profiles"].values()
    )


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _run_ab_probe(STATE["steps"])
        if all(STATE["checks"].values()):
            _succeed()
            return
        _fail("difficulty A/B checks did not all pass: {0}".format(STATE["checks"]))


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
