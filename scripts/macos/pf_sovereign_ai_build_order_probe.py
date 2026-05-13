import argparse
import json
import math
import os
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import sovereign.globals as sovereign_globals
from sovereign.scenario import build_runtime_scene, load_scenario, scenario_summary
from sovereign.session_state import attach_state, entity_binding, snapshot_gameplay_state
from sovereign.systems.combat_rules import apply_damage, damage_breakdown
from sovereign.systems.skirmish import BuildOrderPlanner, ScriptedSkirmishAI, scenario_victory_winner, victory_progress_state
from sovereign.systems.technology import ResearchQueue


PROBE_PATH = "/tmp/pf_sovereign_ai_build_order_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_build_order_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "resource_income": False,
        "house_built": False,
        "trained_wave": False,
        "target_priority": False,
        "attack_wave": False,
        "combat_damage": False,
        "victory_progress": False,
        "state_attached": False,
        "session_save": False,
        "session_load_requested": False,
    },
    "entities": {},
    "runtime": {},
    "ai": {},
    "combat": {},
    "victory": {},
    "session": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign AI build-order continuity probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-build-order")
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
    print("SOVEREIGN_AI_BUILD_ORDER_PHASE {0}".format(name))
    sys.stdout.flush()


def _phase_elapsed():
    return time.monotonic() - STATE["phase_started_at"]


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_build_order.json")


def _restore_summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_build_order_restore.json")


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
    queue = session.get("queue")
    if queue is not None:
        ret["queue"] = queue.snapshot()
    research_queue = session.get("research_queue")
    if research_queue is not None:
        ret["research_queue"] = research_queue.snapshot()
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
        "runtime": STATE["runtime"],
        "ai": STATE["ai"],
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
    print("SOVEREIGN_AI_BUILD_ORDER_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_BUILD_ORDER_FAIL {0}".format(reason))
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
        sum(float(start[1]) for start in starts) / len(starts) + 16.0,
    )
    camera = pf.Camera(
        name="sovereign_ai_build_order_camera",
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
            name="sovereign_ai_build_order_region",
            position=center,
            dimensions=(132.0, 96.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _face_each_other(a, b):
    try:
        a.face_towards(b.pos)
    except (AttributeError, RuntimeError):
        pass
    try:
        b.face_towards(a.pos)
    except (AttributeError, RuntimeError):
        pass


def _drive_build_order():
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

    player_town_center = _spawned_entity(player_result, "building", "town_center")
    player_villager = _spawned_entity(player_result, "unit", "villager", "villager_1")
    player_barracks = _spawned_entity(player_result, "building", "barracks")
    enemy_town_center = _spawned_entity(enemy_result, "building", "town_center")
    enemy_barracks = _spawned_entity(enemy_result, "building", "barracks")
    guard = _entity_named(scene_objs, "p1_guard")
    if None in (player_town_center, player_villager, player_barracks, enemy_town_center, enemy_barracks, guard):
        _fail("required build-order fixture entity was not spawned")

    enemy_town_center.name = "ai_build_order_enemy_town_center"
    enemy_barracks.name = "ai_build_order_enemy_barracks"
    try:
        enemy_barracks.rally_point = (126.0, 92.0)
    except AttributeError:
        pass

    enemy_state.resources["food"] = 0
    enemy_state.resources["gold"] = 0
    enemy_state.resources["wood"] = max(enemy_state.resources.get("wood", 0), 300)
    enemy_state.population_used = max(enemy_state.population_cap - 1, enemy_state.population_used)

    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=runtime["map_seed"])
    planner = BuildOrderPlanner(
        ai,
        {
            "town_center": [player_town_center],
            "villagers": [player_villager],
            "military": [guard],
            "buildings": [player_barracks],
        },
        attack_wave_size=3,
    )

    decisions = []
    for _idx in range(12):
        decision = planner.step()
        decisions.append(dict(decision))
        if planner.attack_launched:
            break
    if not planner.attack_launched:
        _fail("build-order planner did not launch an attack wave")

    wave = ai.wave_units("militia")
    for ent in wave:
        _face_each_other(ent, guard)
    _face_each_other(guard, wave[0])

    before = victory_progress_state(
        runtime["scenario_state"],
        {1: [guard], 2: wave},
        hp_threshold=1,
        elapsed_ticks=STATE["ticks"],
    )
    STATE["combat"]["target_name"] = guard.name
    STATE["combat"]["target_hp_start"] = int(guard.hp)
    STATE["combat"]["damage_events"] = []
    if wave:
        STATE["combat"]["damage_events"].append(apply_damage("militia", "militia", guard))
    while int(guard.hp) > 1:
        hp_before = int(guard.hp)
        total_damage = damage_breakdown("militia", "militia")["total_damage"]
        if hp_before <= total_damage:
            guard.hp = 1
            STATE["combat"]["damage_events"].append({
                "attacker_id": "militia",
                "target_id": "militia",
                "hp_before": hp_before,
                "hp_after": 1,
                "total_damage": max(0, hp_before - 1),
            })
            break
        STATE["combat"]["damage_events"].append(apply_damage("militia", "militia", guard))
    after = victory_progress_state(
        runtime["scenario_state"],
        {1: [guard], 2: wave},
        hp_threshold=1,
        elapsed_ticks=STATE["ticks"] + 100,
    )
    winner = scenario_victory_winner(
        runtime["scenario_state"],
        {1: [guard], 2: wave},
        hp_threshold=1,
    )
    STATE["combat"]["target_hp_after"] = int(guard.hp)
    STATE["victory"] = {
        "before": before,
        "after": after,
        "winner": winner,
    }

    enemy_state.resources["food"] = max(enemy_state.resources.get("food", 0), 120)
    enemy_state.resources["gold"] = max(enemy_state.resources.get("gold", 0), 40)
    ai.queue.enqueue("militia")
    research_queue = ResearchQueue(enemy_state, "town_center", enemy_town_center)

    STATE["entities"] = {
        "player_town_center": player_town_center,
        "player_villager": player_villager,
        "player_barracks": player_barracks,
        "enemy_town_center": enemy_town_center,
        "enemy_barracks": enemy_barracks,
        "guard": guard,
    }
    for idx, ent in enumerate(wave):
        STATE["entities"]["wave_{0}".format(idx + 1)] = ent
    STATE["runtime"] = scenario_summary(runtime)
    STATE["runtime"]["scene_obj_count_after_build_order"] = len(scene_objs)
    STATE["ai"] = {
        "decisions": decisions,
        "snapshot": ai.snapshot(),
        "planner": planner.snapshot(),
        "target_distance": _dist(_ent_xz(wave[0]), _ent_xz(player_town_center)) if wave else None,
    }
    STATE["session"]["scenario_state"] = runtime["scenario_state"]
    STATE["session"]["enemy_state"] = enemy_state
    STATE["session"]["ai"] = ai
    STATE["session"]["planner"] = planner
    STATE["session"]["queue"] = ai.queue
    STATE["session"]["research_queue"] = research_queue
    STATE["session"]["scene_objs"] = scene_objs
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 24 and len(runtime["players"]) == 2
    STATE["checks"]["resource_income"] = any(
        entry.get("action") == "gather_resources"
        and entry.get("reason") == "build_order_income"
        for entry in planner.history
    )
    STATE["checks"]["house_built"] = any(
        entry.get("action") == "build_house"
        and entry.get("reason") == "build_order"
        for entry in ai.decision_log
    )
    STATE["checks"]["trained_wave"] = ai.unit_count("militia") >= 3
    STATE["checks"]["target_priority"] = any(
        entry.get("action") == "target"
        and entry.get("target_role") == "town_center"
        and entry.get("target_name") == getattr(player_town_center, "name", None)
        for entry in ai.decision_log
    )
    STATE["checks"]["attack_wave"] = any(
        entry.get("action") == "attack"
        and entry.get("reason") == "wave_launched"
        for entry in ai.decision_log
    )
    STATE["checks"]["combat_damage"] = (
        STATE["combat"]["target_hp_after"] < STATE["combat"]["target_hp_start"]
    )
    STATE["checks"]["victory_progress"] = (
        before["winner"] is None
        and after["winner"] == 2
        and winner == 2
    )


def _request_save():
    enemy_state = STATE["session"]["enemy_state"]
    queue = STATE["session"]["queue"]
    research_queue = STATE["session"]["research_queue"]
    scene_objs = STATE["session"]["scene_objs"]
    payload = snapshot_gameplay_state(
        enemy_state,
        queue,
        research_queue,
        STATE["combat"],
        scene_objs,
        scenario_state=STATE["session"]["scenario_state"],
        victory_state=STATE["victory"]["after"],
    )
    tagged_count = len([ent for ent in scene_objs if entity_binding(ent)])
    payload["tagged_entities"] = [None] * tagged_count
    ai = STATE["session"]["ai"]
    planner = STATE["session"]["planner"]
    payload["ai_build_order"] = {
        "unit_id": planner.unit_id,
        "attack_wave_size": planner.attack_wave_size,
        "step_index": planner.step_index,
        "attack_launched": planner.attack_launched,
        "trained_militia": ai.unit_count("militia"),
        "actions": [entry.get("action") for entry in planner.history],
        "target_priority": "town_center",
    }
    attach_state(STATE["entities"]["enemy_town_center"], payload)
    STATE["checks"]["state_attached"] = True
    save_path = os.path.join(STATE["output_dir"], "sovereign_ai_build_order.pfsave")
    STATE["session"]["save_path"] = save_path
    STATE["session"]["payload_before_save"] = payload
    os.environ["PF_PY3_SESSION_GLOBALS_MODULE"] = "sovereign.globals"
    os.environ["PF_PY3_SESSION_RESTORE_MODULE"] = "sovereign.entities.runtime"
    os.environ["PF_SOVEREIGN_SESSION_RESTORE_SUMMARY"] = _restore_summary_path()
    os.environ["PF_SOVEREIGN_SESSION_RESTORE_MARKER"] = PROBE_PATH
    os.environ["PF_SOVEREIGN_SESSION_RESTORE_MARKER_PREFIX"] = "SOVEREIGN_AI_BUILD_ORDER_PROBE"
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
        _fail("AI build-order session save file was not written")
    STATE["checks"]["session_load_requested"] = True
    STATE["session"]["save_size_bytes"] = os.path.getsize(save_path)
    _write_summary("load_requested")
    pf.load_session(save_path)
    _set_phase("wait_load")


def _on_session_save_fail(user, event):
    del user
    _fail("AI build-order session save failed: {0}".format(event))


def _on_session_load_fail(user, event):
    del user
    _fail("AI build-order session load failed: {0}".format(event))


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _drive_build_order()
        _set_phase("save")
        return

    if STATE["phase"] == "save":
        pending_save_keys = ("state_attached", "session_save", "session_load_requested")
        if all(STATE["checks"][key] for key in STATE["checks"] if key not in pending_save_keys):
            _request_save()
            return
        _fail("AI build-order checks did not all pass before save: {0}".format(STATE["checks"]))

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
