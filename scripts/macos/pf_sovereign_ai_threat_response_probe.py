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
from sovereign.entities.runtime import place_entity
from sovereign.scenario import build_runtime_scene, load_scenario, scenario_summary
from sovereign.systems.skirmish import ScriptedSkirmishAI, TacticalResponsePlanner, compact_scout_report


PROBE_PATH = "/tmp/pf_sovereign_ai_threat_response_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_threat_response_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "scout_report": False,
        "threat_detected": False,
        "threat_income": False,
        "house_built": False,
        "defenders_trained": False,
        "defense_launched": False,
        "defender_motion": False,
        "decision_log": False,
    },
    "runtime": {},
    "ai": {},
    "movement": {},
    "entities": {},
    "session": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign AI tactical threat-response probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-threat-response")
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
    print("SOVEREIGN_AI_THREAT_RESPONSE_PHASE {0}".format(name))
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
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_threat_response.json")


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
    print("SOVEREIGN_AI_THREAT_RESPONSE_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_THREAT_RESPONSE_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_THREAT_RESPONSE_PROBE_PASS scout={scout} threat={threat} "
        "income={income} house={house} train={train} defend={defend} motion={motion}"
    ).format(
        scout=int(STATE["checks"]["scout_report"]),
        threat=int(STATE["checks"]["threat_detected"]),
        income=int(STATE["checks"]["threat_income"]),
        house=int(STATE["checks"]["house_built"]),
        train=int(STATE["checks"]["defenders_trained"]),
        defend=int(STATE["checks"]["defense_launched"]),
        motion=int(STATE["checks"]["defender_motion"]),
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


def _setup_render_state(scenario):
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    center = (126.0, 86.0)
    camera = pf.Camera(
        name="sovereign_ai_threat_response_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 122.0, center[1] + 10.0),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_threat_response_region",
            position=center,
            dimensions=(104.0, 80.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _run_threat_response():
    scenario = load_scenario(os.path.join(pf.get_basedir(), "assets/sovereign/scenarios/two_player_skirmish.json"))
    scene_objs = []
    runtime = build_runtime_scene(scenario, scene_objs=scene_objs)
    _setup_render_state(scenario)

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
        _fail("required threat-response fixture entity was not spawned")

    enemy_town_center.name = "ai_threat_enemy_town_center"
    enemy_barracks.name = "ai_threat_enemy_barracks"
    scout.name = "ai_threat_scout"
    guard.name = "player_forward_threat"
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

    enemy_state.resources["food"] = 0
    enemy_state.resources["gold"] = 0
    enemy_state.resources["wood"] = max(enemy_state.resources.get("wood", 0), 300)
    enemy_state.population_used = max(enemy_state.population_cap, enemy_state.population_used)
    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=runtime["map_seed"])
    planner = TacticalResponsePlanner(
        ai,
        scout_ent=scout,
        defended_assets=[enemy_barracks, enemy_town_center],
        min_defenders=2,
        threat_radius=56.0,
    )
    target_groups = {
        "town_center": [player_town_center],
        "villagers": [player_villager],
        "military": [guard],
        "buildings": [player_barracks],
    }

    decisions = []
    defender_positions_before = None
    for _idx in range(12):
        if ai.unit_count("militia") >= planner.min_defenders and not planner.defense_launched:
            defender_positions_before = [_ent_xz(ent) for ent in ai.wave_units("militia")]
        decision = planner.step(target_groups)
        decisions.append(dict(decision))
        if planner.defense_launched:
            break
    if not planner.defense_launched:
        _fail("tactical planner did not launch a defense response")
    if defender_positions_before is None:
        defender_positions_before = [_ent_xz(ent) for ent in ai.wave_units("militia")]

    defenders = ai.wave_units("militia")
    for ent in defenders:
        try:
            ent.face_towards(guard.pos)
        except (AttributeError, RuntimeError):
            pass

    report = planner.last_report or {}
    STATE["runtime"] = scenario_summary(runtime)
    STATE["runtime"]["scene_obj_count_after_threat_response"] = len(scene_objs)
    STATE["ai"] = {
        "decisions": decisions,
        "snapshot": ai.snapshot(),
        "planner": planner.snapshot(),
        "report": compact_scout_report(report),
    }
    STATE["movement"] = {
        "target_name": guard.name,
        "target_position": _ent_xz(guard),
        "defender_positions_before": defender_positions_before,
    }
    STATE["session"]["ai"] = ai
    STATE["session"]["planner"] = planner
    STATE["session"]["defenders"] = defenders
    STATE["entities"] = {
        "player_town_center": player_town_center,
        "player_villager": player_villager,
        "player_barracks": player_barracks,
        "enemy_town_center": enemy_town_center,
        "enemy_barracks": enemy_barracks,
        "scout": scout,
        "threat": guard,
    }
    for idx, ent in enumerate(defenders):
        STATE["entities"]["defender_{0}".format(idx + 1)] = ent

    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 24 and len(runtime["players"]) == 2
    STATE["checks"]["scout_report"] = len(report.get("observed", [])) > 0
    STATE["checks"]["threat_detected"] = (
        len(report.get("threats", [])) > 0
        and report["threats"][0].get("name") == guard.name
    )
    STATE["checks"]["threat_income"] = any(
        entry.get("action") == "gather_resources"
        and entry.get("reason") == "threat_response_income"
        for entry in planner.history
    )
    STATE["checks"]["house_built"] = any(
        entry.get("action") == "build_house"
        and entry.get("reason") == "build_order"
        for entry in ai.decision_log
    )
    STATE["checks"]["defenders_trained"] = ai.unit_count("militia") >= 2
    STATE["checks"]["defense_launched"] = any(
        entry.get("action") == "defend"
        and entry.get("reason") == "threat_response"
        and entry.get("target_name") == guard.name
        for entry in ai.decision_log
    )
    STATE["checks"]["decision_log"] = len(ai.decision_log) >= 8


def _sample_defender_motion():
    defenders = STATE["session"].get("defenders", [])
    target = STATE["entities"].get("threat")
    before = STATE["movement"].get("defender_positions_before", [])
    after = [_ent_xz(ent) for ent in defenders]
    target_pos = _ent_xz(target)
    improvements = []
    animations = []
    for idx, pos in enumerate(after):
        start = before[idx] if idx < len(before) else pos
        improvements.append(round(_dist(start, target_pos) - _dist(pos, target_pos), 3))
        try:
            animations.append(defenders[idx].get_anim())
        except (AttributeError, RuntimeError):
            animations.append(None)
    STATE["movement"]["defender_positions_after"] = after
    STATE["movement"]["distance_improvements"] = improvements
    STATE["movement"]["animations"] = animations
    STATE["checks"]["defender_motion"] = any(value > 0.25 for value in improvements)


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _run_threat_response()
        _set_phase("settle")
        return

    if STATE["phase"] == "settle" and STATE["ticks"] >= 16:
        _sample_defender_motion()
        if all(STATE["checks"].values()):
            _succeed()
            return
        _fail("AI threat-response checks did not all pass: {0}".format(STATE["checks"]))


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
