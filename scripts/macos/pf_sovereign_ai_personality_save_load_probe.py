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
from sovereign.session_state import attach_state
from sovereign.systems.skirmish import BranchingStrategyPlanner, ScriptedSkirmishAI, ai_difficulty_profile
from sovereign.systems.technology import ResearchQueue


PROBE_PATH = "/tmp/pf_sovereign_ai_personality_save_load_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_personality_save_load_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "personality_profiles": False,
        "first_harass": False,
        "multi_base": False,
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
    parser = argparse.ArgumentParser(description="Run the Sovereign AI personality save/load probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-personality-save-load")
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
    print("SOVEREIGN_AI_PERSONALITY_SAVE_LOAD_PHASE {0}".format(name))
    sys.stdout.flush()


def _phase_elapsed():
    return time.monotonic() - STATE["phase_started_at"]


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_personality_save_load.json")


def _restore_summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_personality_save_load_restore.json")


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
    planner = session.get("planner")
    if planner is not None:
        ret["planner"] = planner.snapshot()
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
    print("SOVEREIGN_AI_PERSONALITY_SAVE_LOAD_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_PERSONALITY_SAVE_LOAD_FAIL {0}".format(reason))
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
        name="sovereign_ai_personality_save_load_camera",
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
            name="sovereign_ai_personality_save_load_region",
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
        "name": "player_personality_forward_worker",
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


def _planner_payload_for_save(planner):
    payload = planner.snapshot()
    payload["history"] = []
    payload["last_report"] = {}
    return payload


def _player_entity_names(player_state):
    return {
        "units": [getattr(record["entity"], "name", None) for record in player_state.units],
        "buildings": [getattr(record["entity"], "name", None) for record in player_state.buildings],
    }


def _minimal_queue_payload(queue):
    snapshot = queue.snapshot()
    return {
        "building_id": queue.building_id,
        "building_name": getattr(queue.building_ent, "name", None),
        "items": [],
        "completed": [],
        "snapshot": {
            "building_position": list(snapshot["building_position"]),
            "rally_point": list(snapshot["rally_point"]),
        },
    }


def _minimal_research_payload(queue):
    return {
        "building_id": queue.building_id,
        "building_name": getattr(queue.building_ent, "name", None),
        "items": [],
        "completed": [],
        "snapshot": queue.snapshot(),
    }


def _drive_personality_fixture():
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
        _fail("required AI personality save/load fixture entity was not spawned")

    enemy_town_center.name = "ai_personality_enemy_town_center"
    enemy_barracks.name = "ai_personality_enemy_barracks"
    guard.name = "player_personality_military_threat"
    place_entity(
        guard,
        (122.0, 88.0),
        faction_id=1,
        radius=UNITS["militia"].get("selection_radius"),
        scale=UNITS["militia"].get("scale"),
    )

    militia_1 = _create_existing_militia(scene_objs, enemy_state, "ai_personality_defender_1", (146.0, 92.0))
    militia_2 = _create_existing_militia(scene_objs, enemy_state, "ai_personality_defender_2", (144.0, 94.0))
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
        target_bases=None,
        threat_radius=56.0,
    )

    decisions = []
    for _idx in range(22):
        decision = planner.step()
        decisions.append(dict(decision))
        if decision.get("action") == "counterattack" and decision.get("reason") == "branching_harass":
            break

    first_harass = [item for item in decisions if item.get("reason") == "branching_harass"]
    if not first_harass:
        _fail("hard personality did not launch the first harassment wave")

    standard = ai_difficulty_profile("standard")
    booming = ai_difficulty_profile("booming")
    hard = ai_difficulty_profile("hard")
    STATE["checks"]["personality_profiles"] = (
        standard.get("personality_id") == "balanced"
        and booming.get("personality_id") == "booming"
        and booming.get("expansion_target_bases") == 3
        and booming.get("harass_interval_steps") == 7
        and hard.get("personality_id") == "pressure"
        and hard.get("harass_interval_steps") == 2
        and hard.get("max_harass_waves") == 2
        and hard.get("harass_target_roles", [None])[0] == "villagers"
    )
    STATE["checks"]["first_harass"] = (
        planner.profile.get("id") == "hard"
        and planner.profile.get("personality_id") == "pressure"
        and planner.harass_interval_steps == 2
        and planner.max_harass_waves == 2
        and planner.harass_wave_count == 1
        and planner.last_harass_step is not None
        and first_harass[-1].get("target_role") == "villagers"
    )
    STATE["checks"]["multi_base"] = planner.snapshot()["base_count"] >= 3
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 25 and len(runtime["players"]) == 2

    research_queue = ResearchQueue(enemy_state, "town_center", enemy_town_center)
    payload = {
        "version": 1,
        "scenario_state": {
            "metadata": {"map_seed": runtime["map_seed"]},
            "victory": {"mode": "conquest"},
        },
        "victory_state": {
            "mode": "conquest",
            "label": "Conquest",
            "winner": None,
            "alive_factions": [1, 2],
            "defeated_factions": [],
            "elapsed_ticks": 0,
        },
        "player": enemy_state.snapshot(),
        "player_entities": _player_entity_names(enemy_state),
        "production_queue": _minimal_queue_payload(ai.queue),
        "research_queue": _minimal_research_payload(research_queue),
        "combat": {
            "first_harass_target": first_harass[-1].get("target_name"),
            "distance_harass_target_to_barracks": round(_dist(_ent_xz(forward_villager), _ent_xz(enemy_barracks)), 3),
        },
    }
    payload["ai_branching"] = {
        "planner": _planner_payload_for_save(planner),
        "target_names": {
            "town_center": [player_town_center.name],
            "villagers": [forward_villager.name, player_villager.name],
            "military": [guard.name],
            "buildings": [player_barracks.name],
        },
        "defended_asset_names": [enemy_barracks.name, enemy_town_center.name],
        "expansion_points": [[160.0, 106.0], [170.0, 112.0]],
        "faction_id": 2,
        "expected_second_harass_target": forward_villager.name,
    }
    attach_state(enemy_town_center, payload)
    STATE["checks"]["state_attached"] = True

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
    for idx, ent in enumerate(ai.wave_units("archer")):
        STATE["entities"]["personality_archer_{0}".format(idx + 1)] = ent
    for idx, record in enumerate(enemy_state.buildings):
        ent = record.get("entity")
        if record.get("id") == "town_center" and getattr(ent, "name", "").startswith("ai_branching_expansion"):
            STATE["entities"]["personality_expansion_{0}".format(idx + 1)] = ent

    STATE["runtime"] = scenario_summary(runtime)
    STATE["runtime"]["scene_obj_count_after_personality_fixture"] = len(scene_objs)
    STATE["ai"] = {
        "decisions": decisions,
        "planner": planner.snapshot(),
        "snapshot": ai.snapshot(),
        "profiles": {
            "standard": standard,
            "booming": booming,
            "hard": hard,
        },
    }
    STATE["session"]["scenario_state"] = runtime["scenario_state"]
    STATE["session"]["enemy_state"] = enemy_state
    STATE["session"]["ai"] = ai
    STATE["session"]["planner"] = planner
    STATE["session"]["research_queue"] = research_queue
    STATE["session"]["scene_objs"] = scene_objs
    STATE["session"]["payload_before_save"] = payload


def _request_save():
    save_path = os.path.join(STATE["output_dir"], "sovereign_ai_personality_save_load.pfsave")
    STATE["session"]["save_path"] = save_path
    os.environ["PF_PY3_SESSION_GLOBALS_MODULE"] = "sovereign.globals"
    os.environ["PF_PY3_SESSION_RESTORE_MODULE"] = "sovereign.ai_branching_restore"
    os.environ["PF_SOVEREIGN_AI_BRANCHING_RESTORE_SUMMARY"] = _restore_summary_path()
    os.environ["PF_SOVEREIGN_AI_BRANCHING_RESTORE_MARKER"] = PROBE_PATH
    os.environ["PF_SOVEREIGN_AI_BRANCHING_RESTORE_AUTOQUIT"] = "1"
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
        _fail("AI personality session save file was not written")
    STATE["checks"]["session_load_requested"] = True
    STATE["session"]["save_size_bytes"] = os.path.getsize(save_path)
    _write_summary("load_requested")
    pf.load_session(save_path)
    _set_phase("wait_load")


def _on_session_save_fail(user, event):
    del user
    _fail("AI personality session save failed: {0}".format(event))


def _on_session_load_fail(user, event):
    del user
    _fail("AI personality session load failed: {0}".format(event))


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _drive_personality_fixture()
        _set_phase("save")
        return

    if STATE["phase"] == "save":
        pending_save_keys = ("session_save", "session_load_requested")
        if all(STATE["checks"][key] for key in STATE["checks"] if key not in pending_save_keys):
            _request_save()
            return
        _fail("AI personality checks did not all pass before save: {0}".format(STATE["checks"]))

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
