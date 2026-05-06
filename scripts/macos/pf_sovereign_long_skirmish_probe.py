import argparse
import json
import math
import os
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import sovereign.globals as sovereign_globals
from sovereign.data.buildings import BUILDINGS
from sovereign.data.units import UNITS
from sovereign.entities.runtime import create_entity, place_entity
from sovereign.scenario import build_runtime_scene, load_scenario, scenario_seeded_choice, scenario_summary
from sovereign.session_state import attach_state, entity_binding, snapshot_gameplay_state
from sovereign.systems.combat_rules import apply_damage, damage_breakdown
from sovereign.systems.production import ProductionQueue
from sovereign.systems.skirmish import ScriptedSkirmishAI, scenario_victory_winner, victory_progress_state
from sovereign.systems.technology import ResearchQueue


PROBE_PATH = "/tmp/pf_sovereign_long_skirmish_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_long_skirmish_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "output_dir": None,
    "expected_backend": None,
    "phase_started_at": None,
    "phase_log": [],
    "checks": {
        "runtime_scene": False,
        "scenario_setup": False,
        "economy_gather": False,
        "economy_dropoff": False,
        "building_constructed": False,
        "player_production": False,
        "enemy_waves": False,
        "wave_move": False,
        "attack_damage": False,
        "victory_progress": False,
        "state_attached": False,
        "session_save": False,
        "session_load_requested": False,
    },
    "events": {},
    "entities": {},
    "runtime": {},
    "economy": {},
    "production": {},
    "movement": {"samples": [], "max_step": 0.0},
    "combat": {},
    "victory": {},
    "session": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the longer Sovereign skirmish-session probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-long-skirmish-session")
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
    print("SOVEREIGN_LONG_SKIRMISH_PHASE {0}".format(name))
    sys.stdout.flush()


def _phase_elapsed():
    return time.monotonic() - STATE["phase_started_at"]


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_long_skirmish.json")


def _restore_summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_long_skirmish_restore.json")


def _event_count(name):
    return STATE["events"].get(name, 0)


def _record(name):
    STATE["events"][name] = _event_count(name) + 1


def _on_event(name):
    def handler(user, event):
        del user
        del event
        _record(name)
    return handler


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
        "uid": getattr(ent, "uid", None),
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
    for attr in ("resource_amount", "completed", "total_carry"):
        if hasattr(ent, attr):
            payload[attr] = getattr(ent, attr)
    return payload


def _session_summary():
    session = STATE["session"]
    ret = {
        "save_path": session.get("save_path"),
        "seeded_unit": session.get("seeded_unit"),
        "scenario_state": session.get("scenario_state"),
        "payload_before_save": session.get("payload_before_save"),
    }
    player_state = session.get("player_state")
    if player_state is not None:
        ret["player_state"] = player_state.snapshot()
    enemy_state = session.get("enemy_state")
    if enemy_state is not None:
        ret["enemy_state"] = enemy_state.snapshot()
    player_queue = session.get("player_queue")
    if player_queue is not None:
        ret["player_queue"] = player_queue.snapshot()
    research_queue = session.get("research_queue")
    if research_queue is not None:
        ret["research_queue"] = research_queue.snapshot()
    ai = session.get("ai")
    if ai is not None:
        ret["ai"] = ai.snapshot()
    scene_objs = session.get("scene_objs")
    if scene_objs is not None:
        ret["scene_obj_count"] = len(scene_objs)
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
        "events": STATE["events"],
        "runtime": STATE["runtime"],
        "economy": STATE["economy"],
        "production": STATE["production"],
        "movement": STATE["movement"],
        "combat": STATE["combat"],
        "victory": STATE["victory"],
        "session": _session_summary(),
        "entities": {
            key: _snapshot_entity(ent)
            for key, ent in STATE["entities"].items()
        },
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_LONG_SKIRMISH_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_LONG_SKIRMISH_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _unit_entry(unit_id, name):
    return {
        "kind": "unit",
        "id": unit_id,
        "name": name,
        "definition": UNITS[unit_id],
    }


def _building_entry(building_id, name):
    return {
        "kind": "building",
        "id": building_id,
        "name": name,
        "definition": BUILDINGS[building_id],
    }


def _spawned_entity(result, kind, entity_id, name=None):
    for entry, ent in zip(result["plan"]["entities"], result["entities"]):
        if entry["kind"] != kind or entry["id"] != entity_id:
            continue
        if name is not None and entry["name"] != name:
            continue
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
    starts = [player["start"] for player in scenario["players"]]
    center = (
        sum(float(start[0]) for start in starts) / len(starts),
        sum(float(start[1]) for start in starts) / len(starts) + 18.0,
    )
    camera = pf.Camera(
        name="sovereign_long_skirmish_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 142.0, center[1]),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_long_skirmish_region",
            position=center,
            dimensions=(128.0, 96.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _setup_scene():
    scenario = load_scenario(os.path.join(pf.get_basedir(), "assets/sovereign/scenarios/two_player_skirmish.json"))
    scene_objs = []
    runtime = build_runtime_scene(scenario, scene_objs=scene_objs)
    _setup_render_state(scenario)

    player_record = runtime["players"][1]
    enemy_record = runtime["players"][2]
    player_state = player_record["state"]
    enemy_state = enemy_record["state"]
    player_result = player_record["spawn_result"]
    enemy_result = enemy_record["spawn_result"]

    worker = _spawned_entity(player_result, "unit", "villager", "villager_1")
    storage = _spawned_entity(player_result, "building", "town_center")
    resource = _spawned_entity(player_result, "resource", "food")
    player_barracks = _spawned_entity(player_result, "building", "barracks")
    player_town_center = _spawned_entity(player_result, "building", "town_center")
    enemy_barracks = _spawned_entity(enemy_result, "building", "barracks")
    if None in (worker, storage, resource, player_barracks, player_town_center, enemy_barracks):
        _fail("required staged skirmish entity was not spawned")

    build_target = create_entity(_building_entry("house", "long_session_house"))
    place_entity(build_target, (84.0, 82.0), faction_id=1, radius=BUILDINGS["house"].get("selection_radius", 2.5), scale=BUILDINGS["house"].get("scale"))
    scene_objs.append(build_target)

    guard = create_entity(_unit_entry("militia", "long_session_player_guard"))
    place_entity(guard, (108.0, 92.0), faction_id=1, radius=UNITS["militia"].get("selection_radius"), scale=UNITS["militia"].get("scale"))
    scene_objs.append(guard)
    player_state.add_unit("militia", guard)

    try:
        player_barracks.rally_point = (92.0, 86.0)
        enemy_barracks.rally_point = (122.0, 92.0)
    except AttributeError:
        pass

    player_queue = ProductionQueue(player_state, "barracks", player_barracks, faction_id=1, scene_objs=scene_objs)
    research_queue = ResearchQueue(player_state, "town_center", player_town_center)
    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=runtime["map_seed"])
    ai.seed_opening_resources({"food": 620, "wood": 620, "gold": 260, "stone": 180})

    worker.register(pf.EVENT_HARVEST_BEGIN, _on_event("harvest_begin"), None)
    worker.register(pf.EVENT_HARVEST_END, _on_event("harvest_end"), None)
    worker.register(pf.EVENT_RESOURCE_DROPPED_OFF, _on_event("resource_dropped_off"), None)
    worker.register(pf.EVENT_BUILD_BEGIN, _on_event("build_begin"), None)
    worker.register(pf.EVENT_BUILD_END, _on_event("build_end"), None)
    build_target.register(pf.EVENT_BUILDING_COMPLETED, _on_event("building_completed"), None)

    STATE["entities"] = {
        "worker": worker,
        "storage": storage,
        "resource": resource,
        "build_target": build_target,
        "player_barracks": player_barracks,
        "player_town_center": player_town_center,
        "enemy_barracks": enemy_barracks,
        "guard": guard,
    }
    STATE["runtime"] = scenario_summary(runtime)
    STATE["runtime"]["scene_obj_count_after_setup"] = len(scene_objs)
    STATE["session"]["scenario_state"] = runtime["scenario_state"]
    STATE["session"]["seeded_unit"] = scenario_seeded_choice(scenario, ("militia",), salt=43)
    STATE["session"]["player_state"] = player_state
    STATE["session"]["enemy_state"] = enemy_state
    STATE["session"]["player_queue"] = player_queue
    STATE["session"]["research_queue"] = research_queue
    STATE["session"]["ai"] = ai
    STATE["session"]["scene_objs"] = scene_objs
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 24 and len(runtime["players"]) == 2
    STATE["checks"]["scenario_setup"] = (
        runtime["scenario_state"]["setup"]["profile"] == "standard_skirmish"
        and runtime["scenario_state"]["victory"]["mode"] == "conquest"
    )
    STATE["economy"] = {
        "food_node_start": resource.resource_amount,
        "storage_food_start": storage.get_curr_amount("food"),
    }


def _drive_economy():
    worker = STATE["entities"]["worker"]
    resource = STATE["entities"]["resource"]
    storage = STATE["entities"]["storage"]
    player_state = STATE["session"]["player_state"]

    if STATE["ticks"] == 1:
        worker.gather(resource)
    worker.notify(pf.EVENT_MOTION_END, None)
    if _event_count("harvest_begin") > 0:
        worker.notify(pf.EVENT_ANIM_CYCLE_FINISHED, None)

    if worker.get_curr_carry("food") > 0 or resource.resource_amount < STATE["economy"]["food_node_start"]:
        STATE["checks"]["economy_gather"] = True

    if worker.get_curr_carry("food") > 0 and not STATE["economy"].get("dropoff_issued"):
        worker.drop_off(storage)
        STATE["economy"]["dropoff_issued"] = True
    worker.notify(pf.EVENT_MOTION_END, None)

    storage_food = storage.get_curr_amount("food")
    if storage_food > STATE["economy"]["storage_food_start"]:
        gained = int(storage_food - STATE["economy"]["storage_food_start"])
        player_state.resources["food"] += gained
        STATE["checks"]["economy_dropoff"] = True
        STATE["economy"].update({
            "food_node_end": resource.resource_amount,
            "storage_food_end": storage_food,
            "player_food_after_dropoff": player_state.resources["food"],
        })
        _set_phase("building")
        return

    if _phase_elapsed() > 10.0:
        _fail("long skirmish economy stage timed out")


def _drive_building():
    worker = STATE["entities"]["worker"]
    build_target = STATE["entities"]["build_target"]
    player_state = STATE["session"]["player_state"]
    if STATE["ticks"] == 1:
        build_target.mark()
        build_target.found(force=True)
        build_target.supply()
        worker.build(build_target)
    worker.notify(pf.EVENT_MOTION_END, None)
    worker.notify(pf.EVENT_ANIM_CYCLE_FINISHED, None)
    if build_target.completed:
        player_state.add_building("house", build_target)
        STATE["checks"]["building_constructed"] = True
        STATE["production"]["player_pop_cap_after_house"] = player_state.population_cap
        _set_phase("production")
        return
    if _phase_elapsed() > 10.0:
        _fail("long skirmish building stage timed out")


def _drive_production():
    player_state = STATE["session"]["player_state"]
    player_queue = STATE["session"]["player_queue"]
    ai = STATE["session"]["ai"]
    guard = STATE["entities"]["guard"]

    player_state.resources["food"] = max(player_state.resources.get("food", 0), 420)
    player_state.resources["gold"] = max(player_state.resources.get("gold", 0), 160)
    player_queue.enqueue("militia")
    trained = player_queue.finish_next()
    player_queue.enqueue("militia")
    wave_one = ai.train_attack_unit("militia")
    wave_two = ai.train_attack_unit("militia")
    wave_one.name = "long_session_enemy_wave_1"
    wave_two.name = "long_session_enemy_wave_2"
    place_entity(wave_one, (126.0, 92.0), faction_id=2, radius=UNITS["militia"].get("selection_radius"), scale=UNITS["militia"].get("scale"))
    place_entity(wave_two, (132.0, 96.0), faction_id=2, radius=UNITS["militia"].get("selection_radius"), scale=UNITS["militia"].get("scale"))
    wave_one.face_towards(guard.pos)
    wave_two.face_towards(guard.pos)
    guard.face_towards(wave_one.pos)
    STATE["entities"]["player_trained_militia"] = trained
    STATE["entities"]["enemy_wave_one"] = wave_one
    STATE["entities"]["enemy_wave_two"] = wave_two
    STATE["checks"]["player_production"] = (
        trained is not None
        and player_queue.snapshot()["queue_len"] == 1
        and player_state.population_used >= 5
    )
    STATE["checks"]["enemy_waves"] = (
        wave_one is not None
        and wave_two is not None
        and ai.snapshot()["population_used"] >= 5
    )
    STATE["production"].update({
        "player": player_state.snapshot(),
        "player_queue": player_queue.snapshot(),
        "ai": ai.snapshot(),
    })
    _set_phase("moving")


def _sample_wave():
    wave = STATE["entities"]["enemy_wave_one"]
    pos = _ent_xz(wave)
    samples = STATE["movement"]["samples"]
    if samples:
        step = _dist(pos, samples[-1]["position"])
        STATE["movement"]["max_step"] = max(STATE["movement"]["max_step"], step)
    try:
        anim = wave.get_anim()
    except (AttributeError, RuntimeError):
        anim = None
    samples.append({"tick": STATE["ticks"], "position": pos, "anim": anim})
    return pos


def _drive_movement():
    wave = STATE["entities"]["enemy_wave_one"]
    guard = STATE["entities"]["guard"]
    if STATE["ticks"] == 1:
        STATE["movement"]["start"] = _ent_xz(wave)
        wave.face_towards(guard.pos)
        wave.move((112.0, 92.0))
    pos = _sample_wave()
    displacement = _dist(pos, STATE["movement"]["start"])
    STATE["movement"]["displacement"] = displacement
    if displacement >= 3.0 and len(STATE["movement"]["samples"]) >= 6 and STATE["movement"]["max_step"] <= 12.0:
        STATE["checks"]["wave_move"] = True
        if hasattr(wave, "stop"):
            wave.stop()
        _set_phase("combat")
        return
    if _phase_elapsed() > 12.0:
        _fail("long skirmish movement stage timed out: {0}".format(STATE["movement"]))


def _drive_combat():
    guard = STATE["entities"]["guard"]
    wave_one = STATE["entities"]["enemy_wave_one"]
    wave_two = STATE["entities"]["enemy_wave_two"]
    if STATE["ticks"] == 1:
        wave_one.face_towards(guard.pos)
        wave_two.face_towards(guard.pos)
        guard.face_towards(wave_one.pos)
        wave_one.play_anim("Attack")
        wave_two.play_anim("Attack")
        STATE["combat"]["guard_hp_start"] = int(guard.hp)
    if STATE["ticks"] in (4, 8):
        attacker_id = "militia"
        damage = apply_damage(attacker_id, "militia", guard)
        STATE["combat"].setdefault("wave_damage", []).append(damage)
    if int(guard.hp) < STATE["combat"].get("guard_hp_start", int(guard.hp)):
        STATE["checks"]["attack_damage"] = True
        _set_phase("victory")
        return
    if _phase_elapsed() > 10.0:
        _fail("long skirmish combat stage timed out")


def _drive_victory():
    guard = STATE["entities"]["guard"]
    wave_one = STATE["entities"]["enemy_wave_one"]
    wave_two = STATE["entities"]["enemy_wave_two"]
    before = victory_progress_state(
        STATE["session"]["scenario_state"],
        {1: [guard], 2: [wave_one, wave_two]},
        hp_threshold=1,
        elapsed_ticks=STATE["ticks"],
    )
    scripted = []
    while int(guard.hp) > 1:
        hp_before = int(guard.hp)
        total_damage = damage_breakdown("militia", "militia")["total_damage"]
        if hp_before <= total_damage:
            guard.hp = 1
            scripted.append({
                "attacker_id": "militia",
                "target_id": "militia",
                "hp_before": hp_before,
                "hp_after": 1,
                "total_damage": max(0, hp_before - 1),
            })
            break
        scripted.append(apply_damage("militia", "militia", guard))
    after = victory_progress_state(
        STATE["session"]["scenario_state"],
        {1: [guard], 2: [wave_one, wave_two]},
        hp_threshold=1,
        elapsed_ticks=STATE["ticks"] + 100,
    )
    winner = scenario_victory_winner(
        STATE["session"]["scenario_state"],
        {1: [guard], 2: [wave_one, wave_two]},
        hp_threshold=1,
    )
    STATE["victory"] = {
        "before": before,
        "after": after,
        "winner": winner,
    }
    STATE["combat"]["scripted_finish_damage"] = scripted
    STATE["combat"]["target_name"] = guard.name
    STATE["combat"]["target_hp_after"] = int(guard.hp)
    STATE["checks"]["victory_progress"] = (
        before["winner"] is None
        and after["winner"] == 2
        and winner == 2
    )
    _set_phase("save")


def _request_save():
    player_state = STATE["session"]["player_state"]
    player_queue = STATE["session"]["player_queue"]
    research_queue = STATE["session"]["research_queue"]
    scene_objs = STATE["session"]["scene_objs"]
    payload = snapshot_gameplay_state(
        player_state,
        player_queue,
        research_queue,
        STATE["combat"],
        scene_objs,
        scenario_state=STATE["session"]["scenario_state"],
        victory_state=STATE["victory"]["after"],
    )
    tagged_count = len([ent for ent in scene_objs if entity_binding(ent)])
    payload["tagged_entities"] = [None] * tagged_count
    payload["long_skirmish"] = {
        "economy": {
            "food_node_end": STATE["economy"].get("food_node_end"),
            "storage_food_end": STATE["economy"].get("storage_food_end"),
        },
        "production": {
            "player_queue": STATE["production"].get("player_queue"),
            "enemy_wave_count": 2,
        },
        "winner": STATE["victory"].get("winner"),
    }
    attach_state(STATE["entities"]["player_town_center"], payload)
    STATE["checks"]["state_attached"] = True
    save_path = os.path.join(STATE["output_dir"], "sovereign_long_skirmish.pfsave")
    STATE["session"]["save_path"] = save_path
    STATE["session"]["payload_before_save"] = payload
    os.environ["PF_PY3_SESSION_GLOBALS_MODULE"] = "sovereign.globals"
    os.environ["PF_PY3_SESSION_RESTORE_MODULE"] = "sovereign.entities.runtime"
    os.environ["PF_SOVEREIGN_SESSION_RESTORE_SUMMARY"] = _restore_summary_path()
    os.environ["PF_SOVEREIGN_SESSION_RESTORE_MARKER"] = PROBE_PATH
    os.environ["PF_SOVEREIGN_SESSION_RESTORE_MARKER_PREFIX"] = "SOVEREIGN_LONG_SKIRMISH_PROBE"
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
        _fail("long skirmish session save file was not written")
    STATE["checks"]["session_load_requested"] = True
    STATE["session"]["save_size_bytes"] = os.path.getsize(save_path)
    _write_summary("load_requested")
    pf.load_session(save_path)
    _set_phase("wait_load")


def _on_session_save_fail(user, event):
    del user
    _fail("long skirmish session save failed: {0}".format(event))


def _on_session_load_fail(user, event):
    del user
    _fail("long skirmish session load failed: {0}".format(event))


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _setup_scene()
        _set_phase("settle")
        return

    if STATE["phase"] == "settle":
        if STATE["ticks"] >= 8:
            _set_phase("economy")
        return

    if STATE["phase"] == "economy":
        _drive_economy()
        return

    if STATE["phase"] == "building":
        _drive_building()
        return

    if STATE["phase"] == "production":
        _drive_production()
        return

    if STATE["phase"] == "moving":
        _drive_movement()
        return

    if STATE["phase"] == "combat":
        _drive_combat()
        return

    if STATE["phase"] == "victory":
        _drive_victory()
        return

    if STATE["phase"] == "save":
        pending_save_keys = ("state_attached", "session_save", "session_load_requested")
        if all(STATE["checks"][key] for key in STATE["checks"] if key not in pending_save_keys):
            _request_save()
            return
        _fail("long skirmish checks did not all pass before save: {0}".format(STATE["checks"]))

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
