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
from sovereign.factory import spawn_minimal_test_scene, validate_registries
from sovereign.scenario import load_scenario, scenario_runtime_state, scenario_seeded_choice
from sovereign.session_state import attach_state, snapshot_gameplay_state
from sovereign.systems.combat_rules import apply_damage
from sovereign.systems.production import ProductionQueue, player_state_from_spawn_result
from sovereign.systems.skirmish import victory_progress_state
from sovereign.systems.technology import ResearchQueue


PROBE_PATH = "/tmp/pf_sovereign_save_load_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_save_load_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "output_dir": None,
    "expected_backend": None,
    "phase_started_at": None,
    "phase_log": [],
    "checks": {
        "registry": False,
        "spawn": False,
        "setup_profile": False,
        "state_attached": False,
        "session_save": False,
        "session_load_requested": False,
    },
    "session": {},
    "player": {},
    "production_queue": {},
    "research_queue": {},
    "combat": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign save/load roundtrip probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-save-load-probe")
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
    print("SOVEREIGN_SAVE_LOAD_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_save_load.json")


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "session": STATE["session"],
        "player": STATE["player"],
        "production_queue": STATE["production_queue"],
        "research_queue": STATE["research_queue"],
        "combat": STATE["combat"],
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_SAVE_LOAD_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_SAVE_LOAD_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _ensure_factions():
    while len(pf.get_factions_list()) < 3:
        idx = len(pf.get_factions_list())
        if idx == 0:
            pf.add_faction("Neutral", (160, 160, 160, 255))
        elif idx == 1:
            pf.add_faction("Sovereign", (40, 90, 255, 255))
        else:
            pf.add_faction("Opponent", (220, 50, 50, 255))
    pf.set_diplomacy_state(1, 2, pf.DIPLOMACY_STATE_WAR)


def _complete_building(ent):
    if hasattr(ent, "completed") and not ent.completed:
        ent.mark()
        ent.found(force=True)
        ent.supply()
        ent.complete()


def _unit_entry(unit_id, name):
    return {
        "kind": "unit",
        "id": unit_id,
        "name": name,
        "definition": UNITS[unit_id],
    }


def _setup_scene():
    scenario = load_scenario(os.path.join(pf.get_basedir(), "assets/sovereign/scenarios/two_player_skirmish.json"))
    scenario_state = scenario_runtime_state(scenario)
    seeded_choice = scenario_seeded_choice(scenario, ("militia", "archer"), salt=7)
    pf.load_map("assets/maps", "plain.pfmap")
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    _ensure_factions()

    center = (68.0, 68.0)
    camera = pf.Camera(
        name="sovereign_save_load_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 110.0, center[1]),
        pitch=-62.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)

    sovereign_globals.scene_objs = []
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_save_load_region",
            position=center,
            dimensions=(80.0, 80.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]

    result = spawn_minimal_test_scene(center=center, faction_id=1, scene_objs=sovereign_globals.scene_objs)
    by_name = {getattr(ent, "name", ""): ent for ent in result["entities"]}
    town_center = by_name["town_center"]
    house = by_name["house"]
    barracks = by_name["barracks"]
    for ent in (town_center, house, barracks):
        _complete_building(ent)

    player = player_state_from_spawn_result(
        result,
        completed_buildings=("town_center", "house", "barracks"),
    )
    player.resources["food"] = 760
    barracks.rally_point = (88.0, 76.0)
    production_queue = ProductionQueue(
        player,
        "barracks",
        barracks,
        faction_id=1,
        scene_objs=sovereign_globals.scene_objs,
    )
    production_queue.enqueue("militia")
    trained = production_queue.finish_next()
    production_queue.enqueue("militia")

    research_queue = ResearchQueue(player, "town_center", town_center)
    research_queue.enqueue("advance_to_rising")
    researched = research_queue.finish_next()

    attacker = create_entity(_unit_entry("militia", "save_load_attacker"))
    target = create_entity(_unit_entry("militia", "save_load_target"))
    place_entity(attacker, (74.0, 82.0), faction_id=1, radius=3.25, scale=UNITS["militia"].get("scale"))
    place_entity(target, (80.0, 82.0), faction_id=2, radius=3.25, scale=UNITS["militia"].get("scale"))
    sovereign_globals.scene_objs.extend([attacker, target])
    combat = apply_damage("militia", "militia", target)
    combat["target_name"] = target.name
    combat["target_hp_after"] = int(target.hp)
    victory_state = victory_progress_state(
        scenario_state,
        {
            1: [attacker, target],
            2: [trained],
        },
        hp_threshold=1,
        elapsed_ticks=37,
    )

    payload = snapshot_gameplay_state(
        player,
        production_queue,
        research_queue,
        combat,
        sovereign_globals.scene_objs,
        scenario_state=scenario_state,
        victory_state=victory_state,
    )
    attach_state(town_center, payload)

    sovereign_globals.player_state = player
    sovereign_globals.production_queue = production_queue
    sovereign_globals.research_queue = research_queue
    sovereign_globals.session_state = payload
    sovereign_globals.scenario_state = scenario_state

    STATE["checks"]["spawn"] = len(sovereign_globals.scene_objs) >= 13
    STATE["checks"]["setup_profile"] = (
        scenario_state["setup"]["profile"] == "standard_skirmish"
        and scenario_state["setup"]["starting_resource_preset"] == "standard"
        and seeded_choice == scenario_seeded_choice(scenario, ("militia", "archer"), salt=7)
    )
    STATE["checks"]["state_attached"] = True
    STATE["session"]["scenario_state_before_save"] = scenario_state
    STATE["session"]["victory_state_before_save"] = victory_state
    STATE["session"]["seeded_choice"] = seeded_choice
    STATE["player"]["before_save"] = player.snapshot()
    STATE["production_queue"]["before_save"] = production_queue.snapshot()
    STATE["research_queue"]["before_save"] = research_queue.snapshot()
    STATE["combat"]["before_save"] = {
        "damage": combat["total_damage"],
        "hp_before": combat["hp_before"],
        "hp_after": combat["hp_after"],
        "target": target.name,
        "trained": trained.name,
        "researched": researched,
    }


def _request_save():
    save_path = os.path.join(STATE["output_dir"], "sovereign_roundtrip.pfsave")
    STATE["session"]["save_path"] = save_path
    os.environ["PF_PY3_SESSION_GLOBALS_MODULE"] = "sovereign.globals"
    os.environ["PF_PY3_SESSION_RESTORE_MODULE"] = "sovereign.entities.runtime"
    os.environ["PF_SOVEREIGN_SESSION_RESTORE_SUMMARY"] = _summary_path()
    os.environ["PF_SOVEREIGN_SESSION_RESTORE_MARKER"] = PROBE_PATH
    os.environ["PF_SOVEREIGN_SESSION_RESTORE_AUTOQUIT"] = "1"
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
        _fail("session save file was not written")
    STATE["session"]["save_size_bytes"] = os.path.getsize(save_path)
    STATE["checks"]["session_load_requested"] = True
    _write_summary("load_requested")
    pf.load_session(save_path)
    _set_phase("wait_load")


def _on_session_save_fail(user, event):
    del user
    _fail("session save failed: {0}".format(event))


def _on_session_load_fail(user, event):
    del user
    _fail("session load failed: {0}".format(event))


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        errors = validate_registries()
        if errors:
            _fail("registry validation failed: " + "; ".join(errors))
        STATE["checks"]["registry"] = True
        _setup_scene()
        _request_save()
        return

    if STATE["phase"] in ("wait_save", "wait_load") and time.monotonic() - STATE["phase_started_at"] > 20.0:
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
