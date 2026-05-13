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
from sovereign.session_state import attach_state, entity_binding, snapshot_gameplay_state
from sovereign.systems.skirmish import ScoutingRoutePlanner, ScriptedSkirmishAI, ThreatMemory
from sovereign.systems.technology import ResearchQueue


PROBE_PATH = "/tmp/pf_sovereign_ai_memory_save_load_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_memory_save_load_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "threat_observed": False,
        "memory_recorded": False,
        "state_attached": False,
        "session_save": False,
        "session_load_requested": False,
    },
    "runtime": {},
    "ai": {},
    "entities": {},
    "session": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign AI memory save/load probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-memory-save-load")
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
    print("SOVEREIGN_AI_MEMORY_SAVE_LOAD_PHASE {0}".format(name))
    sys.stdout.flush()


def _phase_elapsed():
    return time.monotonic() - STATE["phase_started_at"]


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_memory_save_load.json")


def _restore_summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_memory_save_load_restore.json")


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


def _session_summary():
    session = STATE["session"]
    ret = {
        "save_path": session.get("save_path"),
        "payload_before_save": session.get("payload_before_save"),
    }
    enemy_state = session.get("enemy_state")
    if enemy_state is not None:
        ret["enemy_state"] = enemy_state.snapshot()
    ai = session.get("ai")
    if ai is not None:
        ret["ai"] = ai.snapshot()
    scout_route = session.get("scout_route")
    if scout_route is not None:
        ret["scout_route"] = scout_route.snapshot()
    memory = session.get("memory")
    if memory is not None and scout_route is not None:
        ret["memory"] = memory.snapshot(scout_route.step_index)
    save_path = session.get("save_path")
    if save_path and os.path.exists(save_path):
        ret["save_size_bytes"] = os.path.getsize(save_path)
    return ret


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
        "session": _session_summary(),
        "entities": {
            key: _snapshot_entity(ent)
            for key, ent in STATE["entities"].items()
        },
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_AI_MEMORY_SAVE_LOAD_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_MEMORY_SAVE_LOAD_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


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
        name="sovereign_ai_memory_save_load_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 126.0, center[1] + 8.0),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_memory_save_load_region",
            position=center,
            dimensions=(112.0, 84.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _create_existing_defender(scene_objs, enemy_state):
    definition = UNITS["militia"]
    ent = create_entity({
        "kind": "unit",
        "id": "militia",
        "name": "ai_memory_existing_defender",
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


def _drive_memory_fixture():
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
        _fail("required AI memory save/load fixture entity was not spawned")

    enemy_town_center.name = "ai_memory_restore_town_center"
    enemy_barracks.name = "ai_memory_restore_barracks"
    scout.name = "ai_memory_restore_scout"
    guard.name = "player_memory_restore_threat"
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

    existing_defender = _create_existing_defender(scene_objs, enemy_state)
    enemy_state.resources["food"] = 0
    enemy_state.resources["gold"] = 0
    enemy_state.resources["wood"] = max(enemy_state.resources.get("wood", 0), 300)
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
        route_points=[(112.0, 88.0)],
        target_groups=target_groups,
        defended_assets=[enemy_barracks, enemy_town_center],
        memory=memory,
        sight_radius=72.0,
        threat_radius=56.0,
    )
    report = scout_route.step()
    remembered = memory.best_threat(current_step=scout_route.step_index)
    STATE["checks"]["threat_observed"] = (
        len(report.get("threats", [])) > 0
        and report["threats"][0].get("name") == guard.name
    )
    STATE["checks"]["memory_recorded"] = remembered is not None and remembered.get("name") == guard.name

    research_queue = ResearchQueue(enemy_state, "town_center", enemy_town_center)
    payload = snapshot_gameplay_state(
        enemy_state,
        ai.queue,
        research_queue,
        {"target_name": guard.name, "target_hp_after": int(guard.hp)},
        scene_objs,
        scenario_state=runtime["scenario_state"],
        victory_state={
            "mode": "conquest",
            "label": "Conquest",
            "winner": None,
            "alive_factions": [1, 2],
            "defeated_factions": [],
            "elapsed_ticks": 0,
        },
    )
    payload["ai_memory"] = {
        "memory": memory.snapshot(scout_route.step_index),
        "current_step": scout_route.step_index,
        "expected_threat_name": guard.name,
        "regroup_point": list(_ent_xz(enemy_barracks)),
        "min_defenders": 2,
        "faction_id": 2,
    }
    attach_state(enemy_town_center, payload)
    STATE["checks"]["state_attached"] = True

    STATE["entities"] = {
        "player_town_center": player_town_center,
        "player_villager": player_villager,
        "player_barracks": player_barracks,
        "enemy_town_center": enemy_town_center,
        "enemy_barracks": enemy_barracks,
        "scout": scout,
        "threat": guard,
        "existing_defender": existing_defender,
    }
    STATE["runtime"] = scenario_summary(runtime)
    STATE["runtime"]["scene_obj_count_after_memory_fixture"] = len(scene_objs)
    STATE["ai"] = {
        "first_report": {
            "observed_count": len(report.get("observed", [])),
            "threat_count": len(report.get("threats", [])),
        },
        "remembered": remembered,
        "scout_route": scout_route.snapshot(),
        "snapshot": ai.snapshot(),
        "distance_threat_to_barracks": _dist(_ent_xz(guard), _ent_xz(enemy_barracks)),
    }
    STATE["session"]["scenario_state"] = runtime["scenario_state"]
    STATE["session"]["enemy_state"] = enemy_state
    STATE["session"]["ai"] = ai
    STATE["session"]["memory"] = memory
    STATE["session"]["scout_route"] = scout_route
    STATE["session"]["research_queue"] = research_queue
    STATE["session"]["scene_objs"] = scene_objs
    STATE["session"]["payload_before_save"] = payload
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 25 and len(runtime["players"]) == 2


def _request_save():
    save_path = os.path.join(STATE["output_dir"], "sovereign_ai_memory_save_load.pfsave")
    STATE["session"]["save_path"] = save_path
    os.environ["PF_PY3_SESSION_GLOBALS_MODULE"] = "sovereign.globals"
    os.environ["PF_PY3_SESSION_RESTORE_MODULE"] = "sovereign.ai_memory_restore"
    os.environ["PF_SOVEREIGN_AI_MEMORY_RESTORE_SUMMARY"] = _restore_summary_path()
    os.environ["PF_SOVEREIGN_AI_MEMORY_RESTORE_MARKER"] = PROBE_PATH
    os.environ["PF_SOVEREIGN_AI_MEMORY_RESTORE_AUTOQUIT"] = "1"
    _write_summary("save_requested")
    pf.save_session(save_path)
    _set_phase("wait_save")


def _on_session_saved(user, event):
    del user
    del event
    if STATE["phase"] != "wait_save":
        return
    save_path = STATE["session"].get("save_path")
    STATE["checks"]["session_save"] = bool(save_path and os.path.exists(save_path) and os.path.getsize(save_path) > 0)
    if not STATE["checks"]["session_save"]:
        _fail("AI memory session save file was not written")
    STATE["checks"]["session_load_requested"] = True
    STATE["session"]["save_size_bytes"] = os.path.getsize(save_path)
    _write_summary("load_requested")
    pf.load_session(save_path)
    _set_phase("wait_load")


def _on_session_save_fail(user, event):
    del user
    _fail("AI memory session save failed: {0}".format(event))


def _on_session_load_fail(user, event):
    del user
    _fail("AI memory session load failed: {0}".format(event))


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _drive_memory_fixture()
        _set_phase("save")
        return

    if STATE["phase"] == "save":
        pending_save_keys = ("session_save", "session_load_requested")
        if all(STATE["checks"][key] for key in STATE["checks"] if key not in pending_save_keys):
            _request_save()
            return
        _fail("AI memory checks did not all pass before save: {0}".format(STATE["checks"]))

    if STATE["phase"] in ("wait_save", "wait_load") and _phase_elapsed() > 24.0:
        _fail("timed out in {0}".format(STATE["phase"]))


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
    pf.register_ui_event_handler(pf.EVENT_SESSION_SAVED, _on_session_saved, None)
    pf.register_ui_event_handler(pf.EVENT_SESSION_FAIL_SAVE, _on_session_save_fail, None)
    pf.register_ui_event_handler(pf.EVENT_SESSION_FAIL_LOAD, _on_session_load_fail, None)


main()
