import argparse
import json
import math
import os
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import sovereign.globals as sovereign_globals
from sovereign.data.units import UNITS
from sovereign.entities.runtime import create_entity, place_entity
from sovereign.scenario import build_runtime_scene, load_scenario, scenario_summary
from sovereign.systems.skirmish import BranchingStrategyPlanner, ScriptedSkirmishAI


PROBE_PATH = "/tmp/pf_sovereign_ai_branching_strategy_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_branching_strategy_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "branching_profile": False,
        "defense_split": False,
        "expansion_income": False,
        "multi_base": False,
        "harass_training": False,
        "harass_launch": False,
        "defense_motion": False,
        "harass_motion": False,
    },
    "runtime": {},
    "ai": {},
    "movement": {},
    "entities": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign AI branching-strategy probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-branching-strategy")
    parser.add_argument("--expect-backend", default="METAL")
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    print("SOVEREIGN_AI_BRANCHING_STRATEGY_PHASE {0}".format(name))
    sys.stdout.flush()


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _dist(a, b):
    dx = a[0] - b[0]
    dz = a[1] - b[1]
    return math.sqrt(dx * dx + dz * dz)


def _snapshot_entity(ent):
    payload = {
        "name": getattr(ent, "name", None),
        "position": _ent_xz(ent),
        "faction_id": getattr(ent, "faction_id", None),
    }
    try:
        payload["hp"] = int(ent.hp)
    except (AttributeError, RuntimeError):
        payload["hp"] = None
    try:
        payload["anim"] = ent.get_anim()
    except (AttributeError, RuntimeError):
        payload["anim"] = None
    return payload


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_branching_strategy.json")


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "runtime": STATE["runtime"],
        "ai": STATE["ai"],
        "movement": STATE["movement"],
        "entities": {
            key: _snapshot_entity(ent)
            for key, ent in STATE["entities"].items()
        },
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_AI_BRANCHING_STRATEGY_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_BRANCHING_STRATEGY_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_BRANCHING_STRATEGY_PROBE_PASS profile={profile} "
        "defense={defense} expand={expand} bases={bases} train={train} "
        "harass={harass} defense_motion={defense_motion} harass_motion={harass_motion}"
    ).format(
        profile=int(STATE["checks"]["branching_profile"]),
        defense=int(STATE["checks"]["defense_split"]),
        expand=int(STATE["checks"]["expansion_income"]),
        bases=int(STATE["checks"]["multi_base"]),
        train=int(STATE["checks"]["harass_training"]),
        harass=int(STATE["checks"]["harass_launch"]),
        defense_motion=int(STATE["checks"]["defense_motion"]),
        harass_motion=int(STATE["checks"]["harass_motion"]),
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
        name="sovereign_ai_branching_strategy_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 132.0, center[1] + 10.0),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_branching_strategy_region",
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


def _create_forward_villager(scene_objs):
    definition = UNITS["villager"]
    ent = create_entity({
        "kind": "unit",
        "id": "villager",
        "name": "player_branching_forward_worker",
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


def _run_branching_strategy():
    scenario = load_scenario(os.path.join(pf.get_basedir(), "assets/sovereign/scenarios/two_player_skirmish.json"))
    scene_objs = []
    runtime = build_runtime_scene(scenario, scene_objs=scene_objs)
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
        _fail("required branching-strategy fixture entity was not spawned")

    enemy_town_center.name = "ai_branching_enemy_town_center"
    enemy_barracks.name = "ai_branching_enemy_barracks"
    guard.name = "player_branching_military_threat"
    place_entity(
        guard,
        (122.0, 88.0),
        faction_id=1,
        radius=UNITS["militia"].get("selection_radius"),
        scale=UNITS["militia"].get("scale"),
    )

    militia_1 = _create_existing_militia(scene_objs, enemy_state, "ai_branching_defender_1", (146.0, 92.0))
    militia_2 = _create_existing_militia(scene_objs, enemy_state, "ai_branching_defender_2", (144.0, 94.0))
    forward_villager = _create_forward_villager(scene_objs)
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
    enemy_state.population_cap = max(enemy_state.population_used + 4, enemy_state.population_cap)

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
        difficulty_id="hard",
        expansion_points=[(160.0, 106.0), (170.0, 112.0)],
        target_bases=3,
        harassment_target_roles=("villagers", "buildings", "town_center"),
        threat_radius=56.0,
    )

    STATE["movement"] = {
        "defense_target": _ent_xz(guard),
        "defense_units_before": [_ent_xz(militia_1), _ent_xz(militia_2)],
    }
    decisions = []
    for _idx in range(22):
        decision = planner.step()
        decisions.append(dict(decision))
        if decision.get("action") == "counterattack" and decision.get("reason") == "branching_harass":
            break

    if not any(item.get("reason") == "branching_harass" for item in decisions):
        _fail("branching strategy did not launch harassment")

    harassment_units = ai.wave_units("archer")
    STATE["movement"]["harass_target"] = _ent_xz(forward_villager)
    STATE["movement"]["harass_units_before"] = [_ent_xz(ent) for ent in harassment_units]
    STATE["entities"] = {
        "player_town_center": player_town_center,
        "player_villager": player_villager,
        "forward_villager": forward_villager,
        "player_barracks": player_barracks,
        "enemy_town_center": enemy_town_center,
        "enemy_barracks": enemy_barracks,
        "threat": guard,
        "militia_1": militia_1,
        "militia_2": militia_2,
    }
    for idx, ent in enumerate(harassment_units):
        STATE["entities"]["branching_archer_{0}".format(idx + 1)] = ent
    for idx, record in enumerate(enemy_state.buildings):
        if record.get("id") == "town_center" and getattr(record.get("entity"), "name", "").startswith("ai_branching_expansion"):
            STATE["entities"]["branching_expansion_{0}".format(idx + 1)] = record["entity"]

    expansion_decisions = [
        item for item in decisions
        if item.get("action") == "build_building" and item.get("reason") == "branching_expansion"
    ]
    harass_decision = [item for item in decisions if item.get("reason") == "branching_harass"][-1]
    defense_decision = [item for item in decisions if item.get("reason") == "branching_defense"][0]
    STATE["runtime"] = scenario_summary(runtime)
    STATE["runtime"]["scene_obj_count_after_branching_strategy"] = len(scene_objs)
    STATE["ai"] = {
        "decisions": decisions,
        "planner": planner.snapshot(),
        "snapshot": ai.snapshot(),
        "expansion_decisions": expansion_decisions,
        "defense_decision": defense_decision,
        "harass_decision": harass_decision,
    }
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 25 and len(runtime["players"]) == 2
    STATE["checks"]["branching_profile"] = (
        planner.profile["id"] == "hard"
        and planner.profile["defense_min_units"] == 1
        and planner.profile["harass_min_units"] == 2
        and "harass" in planner.profile["build_order"]
    )
    STATE["checks"]["defense_split"] = (
        defense_decision.get("action") == "defend"
        and defense_decision.get("strategy_branch") == "branching_defense"
        and defense_decision.get("target_role") == "military"
    )
    STATE["checks"]["expansion_income"] = any(
        item.get("reason") == "branching_expansion_income"
        for item in decisions
    )
    STATE["checks"]["multi_base"] = (
        planner.snapshot()["base_count"] >= 3
        and len(expansion_decisions) >= 2
    )
    STATE["checks"]["harass_training"] = ai.unit_count("archer") >= 2
    STATE["checks"]["harass_launch"] = (
        harass_decision.get("action") == "counterattack"
        and harass_decision.get("target_role") == "villagers"
        and harass_decision.get("strategy_branch") == "branching_harass"
    )


def _sample_motion():
    defense_target = STATE["movement"]["defense_target"]
    defense_units = [STATE["entities"]["militia_1"], STATE["entities"]["militia_2"]]
    defense_before = STATE["movement"].get("defense_units_before", [])
    defense_after = [_ent_xz(ent) for ent in defense_units]
    defense_improvements = []
    for idx, pos in enumerate(defense_after):
        start = defense_before[idx] if idx < len(defense_before) else pos
        defense_improvements.append(round(_dist(start, defense_target) - _dist(pos, defense_target), 3))

    harass_target = STATE["movement"]["harass_target"]
    harass_units = [
        ent for key, ent in STATE["entities"].items()
        if key.startswith("branching_archer_")
    ]
    harass_before = STATE["movement"].get("harass_units_before", [])
    harass_after = [_ent_xz(ent) for ent in harass_units]
    harass_improvements = []
    for idx, pos in enumerate(harass_after):
        start = harass_before[idx] if idx < len(harass_before) else pos
        harass_improvements.append(round(_dist(start, harass_target) - _dist(pos, harass_target), 3))

    STATE["movement"]["defense_units_after"] = defense_after
    STATE["movement"]["defense_distance_improvements"] = defense_improvements
    STATE["movement"]["harass_units_after"] = harass_after
    STATE["movement"]["harass_distance_improvements"] = harass_improvements
    STATE["checks"]["defense_motion"] = any(value > 0.25 for value in defense_improvements)
    STATE["checks"]["harass_motion"] = any(value > 0.1 for value in harass_improvements)


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _run_branching_strategy()
        _set_phase("settle")
        return

    if STATE["phase"] == "settle" and STATE["ticks"] >= 120:
        _sample_motion()
        if all(STATE["checks"].values()):
            _succeed()
            return
        _fail("branching-strategy checks did not all pass: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["phase_started_at"] = time.monotonic()
    for path in (PROBE_PATH, ERROR_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
