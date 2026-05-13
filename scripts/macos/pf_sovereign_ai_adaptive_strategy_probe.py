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
from sovereign.systems.skirmish import (
    AdaptiveMemoryStrategyPlanner,
    ScoutingRoutePlanner,
    ScriptedSkirmishAI,
    ThreatMemory,
)


PROBE_PATH = "/tmp/pf_sovereign_ai_adaptive_strategy_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_adaptive_strategy_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "memory_recorded": False,
        "scout_scheduled": False,
        "preferred_archer": False,
        "regroup": False,
        "adaptive_income": False,
        "house": False,
        "archers_trained": False,
        "response": False,
        "counterattack": False,
        "scout_motion": False,
        "counterattack_motion": False,
    },
    "runtime": {},
    "ai": {},
    "movement": {},
    "entities": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign adaptive AI strategy probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-adaptive-strategy")
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
    print("SOVEREIGN_AI_ADAPTIVE_STRATEGY_PHASE {0}".format(name))
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
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_adaptive_strategy.json")


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
    print("SOVEREIGN_AI_ADAPTIVE_STRATEGY_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_ADAPTIVE_STRATEGY_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_ADAPTIVE_STRATEGY_PROBE_PASS memory={memory} scout={scout} "
        "choice={choice} regroup={regroup} income={income} house={house} "
        "archers={archers} response={response} counter={counter} "
        "scout_motion={scout_motion} counter_motion={counter_motion}"
    ).format(
        memory=int(STATE["checks"]["memory_recorded"]),
        scout=int(STATE["checks"]["scout_scheduled"]),
        choice=int(STATE["checks"]["preferred_archer"]),
        regroup=int(STATE["checks"]["regroup"]),
        income=int(STATE["checks"]["adaptive_income"]),
        house=int(STATE["checks"]["house"]),
        archers=int(STATE["checks"]["archers_trained"]),
        response=int(STATE["checks"]["response"]),
        counter=int(STATE["checks"]["counterattack"]),
        scout_motion=int(STATE["checks"]["scout_motion"]),
        counter_motion=int(STATE["checks"]["counterattack_motion"]),
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
        name="sovereign_ai_adaptive_strategy_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 128.0, center[1] + 10.0),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_adaptive_strategy_region",
            position=center,
            dimensions=(112.0, 84.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _create_existing_militia(scene_objs, enemy_state):
    definition = UNITS["militia"]
    ent = create_entity({
        "kind": "unit",
        "id": "militia",
        "name": "ai_adaptive_existing_militia",
        "definition": definition,
    })
    place_entity(
        ent,
        (146.0, 92.0),
        faction_id=2,
        radius=definition.get("selection_radius", 3.25),
        scale=definition.get("scale"),
    )
    scene_objs.append(ent)
    enemy_state.add_unit("militia", ent)
    return ent


def _run_adaptive_strategy():
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
    scout = _spawned_entity(enemy_result, "unit", "villager", "villager_1")
    guard = _entity_named(scene_objs, "p1_guard")
    if None in (player_town_center, player_villager, player_barracks, enemy_town_center, enemy_barracks, scout, guard):
        _fail("required adaptive-strategy fixture entity was not spawned")

    enemy_town_center.name = "ai_adaptive_enemy_town_center"
    enemy_barracks.name = "ai_adaptive_enemy_barracks"
    scout.name = "ai_adaptive_scout"
    guard.name = "player_adaptive_military_threat"
    place_entity(
        guard,
        (122.0, 88.0),
        faction_id=1,
        radius=UNITS["militia"].get("selection_radius"),
        scale=UNITS["militia"].get("scale"),
    )
    try:
        guard.face_towards(enemy_barracks.pos)
        scout.face_towards(guard.pos)
        enemy_barracks.rally_point = (148.0, 92.0)
    except (AttributeError, RuntimeError):
        pass

    existing_militia = _create_existing_militia(scene_objs, enemy_state)
    enemy_state.resources["food"] = 0
    enemy_state.resources["wood"] = 0
    enemy_state.resources["gold"] = 0
    enemy_state.population_used = max(enemy_state.population_cap, enemy_state.population_used)

    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=runtime["map_seed"])
    memory = ThreatMemory(ttl_steps=10)
    target_groups = {
        "town_center": [player_town_center],
        "villagers": [player_villager],
        "military": [guard],
        "buildings": [player_barracks],
    }
    scout_route = ScoutingRoutePlanner(
        ai,
        scout,
        route_points=[(112.0, 88.0), (146.0, 90.0)],
        target_groups=target_groups,
        defended_assets=[enemy_barracks, enemy_town_center],
        memory=memory,
        sight_radius=72.0,
        threat_radius=56.0,
    )
    scout_start = _ent_xz(scout)
    planner = AdaptiveMemoryStrategyPlanner(
        ai,
        memory,
        scout_planner=scout_route,
        counterattack_targets=target_groups,
        min_response_units=2,
        counterattack_units=2,
        scout_interval=2,
        regroup_point=_ent_xz(enemy_barracks),
    )
    decisions = []
    for _idx in range(12):
        decision = planner.step()
        decisions.append(dict(decision))
        if planner.counterattack_launched:
            break
    if not planner.counterattack_launched:
        _fail("adaptive strategy did not launch a counterattack")

    archers = ai.wave_units("archer")
    counter_units = ai.roster_units(("militia", "archer"))
    STATE["movement"] = {
        "scout_start": scout_start,
        "scout_after_strategy": _ent_xz(scout),
        "counter_target": _ent_xz(player_town_center),
        "counter_units_before": [_ent_xz(ent) for ent in counter_units],
    }
    STATE["entities"] = {
        "player_town_center": player_town_center,
        "player_villager": player_villager,
        "player_barracks": player_barracks,
        "enemy_town_center": enemy_town_center,
        "enemy_barracks": enemy_barracks,
        "scout": scout,
        "threat": guard,
        "existing_militia": existing_militia,
    }
    for idx, ent in enumerate(archers):
        STATE["entities"]["adaptive_archer_{0}".format(idx + 1)] = ent

    STATE["runtime"] = scenario_summary(runtime)
    STATE["runtime"]["scene_obj_count_after_adaptive_strategy"] = len(scene_objs)
    STATE["ai"] = {
        "decisions": decisions,
        "planner": planner.snapshot(),
        "scout_route": scout_route.snapshot(),
        "snapshot": ai.snapshot(),
        "remembered": memory.best_threat(current_step=planner.step_index),
    }
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 25 and len(runtime["players"]) == 2
    STATE["checks"]["memory_recorded"] = memory.best_threat(current_step=planner.step_index) is not None
    STATE["checks"]["scout_scheduled"] = len(planner.scout_history) >= 2 and scout_route.step_index >= 2
    STATE["checks"]["preferred_archer"] = any(
        item.get("role") == "military" and item.get("unit_id") == "archer"
        for item in planner.preferred_unit_history
    )
    STATE["checks"]["regroup"] = any(
        item.get("action") == "retreat_regroup"
        and item.get("reason") == "adaptive_memory_outnumbered"
        for item in planner.history
    )
    STATE["checks"]["adaptive_income"] = any(
        item.get("action") == "gather_resources"
        and item.get("reason") == "adaptive_build_order_income"
        and item.get("preferred_unit_id") == "archer"
        for item in planner.history
    )
    STATE["checks"]["house"] = any(
        item.get("action") == "build_house"
        and item.get("preferred_unit_id") == "archer"
        for item in planner.history
    )
    STATE["checks"]["archers_trained"] = ai.unit_count("archer") >= 2
    STATE["checks"]["response"] = any(
        item.get("action") == "defend"
        and item.get("reason") == "adaptive_memory_response"
        and item.get("preferred_unit_id") == "archer"
        for item in planner.history
    )
    STATE["checks"]["counterattack"] = any(
        item.get("action") == "counterattack"
        and item.get("reason") == "adaptive_counterattack"
        for item in planner.history
    )


def _sample_motion():
    scout = STATE["entities"]["scout"]
    target = STATE["movement"]["counter_target"]
    before = STATE["movement"].get("counter_units_before", [])
    units = []
    for key, ent in STATE["entities"].items():
        if key == "existing_militia" or key.startswith("adaptive_archer_"):
            units.append(ent)
    after = [_ent_xz(ent) for ent in units]
    improvements = []
    for idx, pos in enumerate(after):
        start = before[idx] if idx < len(before) else pos
        improvements.append(round(_dist(start, target) - _dist(pos, target), 3))
    STATE["movement"]["scout_after_settle"] = _ent_xz(scout)
    STATE["movement"]["counter_units_after"] = after
    STATE["movement"]["counter_distance_improvements"] = improvements
    STATE["checks"]["scout_motion"] = _dist(STATE["movement"]["scout_start"], _ent_xz(scout)) > 0.25
    STATE["checks"]["counterattack_motion"] = any(value > 0.25 for value in improvements)


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _run_adaptive_strategy()
        _set_phase("settle")
        return

    if STATE["phase"] == "settle" and STATE["ticks"] >= 16:
        _sample_motion()
        if all(STATE["checks"].values()):
            _succeed()
            return
        _fail("adaptive strategy checks did not all pass: {0}".format(STATE["checks"]))


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
