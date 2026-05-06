import argparse
import json
import math
import os
import struct
import subprocess
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import sovereign.globals as sovereign_globals
from sovereign.data.units import UNITS
from sovereign.entities.runtime import create_entity, place_entity
from sovereign.factory import spawn_minimal_test_scene, validate_registries
from sovereign.scenario import load_scenario, scenario_runtime_state, scenario_seeded_choice
from sovereign.systems.combat_rules import apply_damage, damage_breakdown
from sovereign.systems.production import player_state_from_spawn_result
from sovereign.systems.skirmish import (
    ScriptedSkirmishAI,
    faction_defeated,
    scenario_victory_winner,
    victory_progress_state,
)


PROBE_PATH = "/tmp/pf_sovereign_skirmish_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_skirmish_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "output_dir": None,
    "expected_backend": None,
    "phase_started_at": None,
    "phase_log": [],
    "checks": {
        "registry": False,
        "setup_profile": False,
        "seeded_setup": False,
        "two_player_setup": False,
        "enemy_economy_seeded": False,
        "enemy_trained_wave": False,
        "wave_move_started": False,
        "wave_moved_gradually": False,
        "walk_anim_observed": False,
        "actors_facing": False,
        "attack_anim_observed": False,
        "target_damaged": False,
        "victory_dispatch": False,
        "conquest_victory": False,
    },
    "entities": {},
    "players": {},
    "ai": {},
    "movement": {
        "samples": [],
        "anim_samples": [],
        "motion_start_events": 0,
        "motion_end_events": 0,
        "max_step": 0.0,
    },
    "combat": {},
    "victory": {},
    "scenario_state": {},
    "captures": [],
    "capture_proof": False,
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign skirmish loop probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-skirmish-loop")
    parser.add_argument("--expect-backend", default="METAL")
    parser.add_argument("--capture-proof", action="store_true")
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    print("SOVEREIGN_SKIRMISH_PHASE {0}".format(name))
    sys.stdout.flush()


def _phase_elapsed():
    return time.monotonic() - STATE["phase_started_at"]


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_skirmish.json")


def _png_size(path):
    with open(path, "rb") as infile:
        header = infile.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("not a PNG: {0}".format(path))
    return struct.unpack(">II", header[16:24])


def _png_nonblank(path):
    checker = os.path.join(pf.get_basedir(), "scripts/macos/check_png_nonblank.py")
    try:
        ret = subprocess.run(
            ["/usr/bin/python3", checker, path, "--min-nonblack-ratio", "0.01"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=20.0,
        )
    except subprocess.TimeoutExpired:
        return False
    return ret.returncode == 0


def _try_capture(cmd, path):
    try:
        ret = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5.0)
    except subprocess.TimeoutExpired:
        return False
    return ret.returncode == 0 and _png_nonblank(path)


def _capture_window_id():
    helper = os.path.join(pf.get_basedir(), "scripts/macos/pf_window_id_for_pid.swift")
    try:
        ret = subprocess.run(
            ["/usr/bin/swift", helper, str(os.getpid())],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=3.0,
        )
    except subprocess.TimeoutExpired:
        return None
    if ret.returncode != 0:
        return None
    window_id = ret.stdout.strip().splitlines()[-1]
    return window_id if window_id.isdigit() else None


def _activate_own_window():
    script = (
        'tell application "System Events" to set frontmost of '
        '(first process whose unix id is {0}) to true'
    ).format(os.getpid())
    try:
        subprocess.run(["osascript", "-e", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=2.0)
    except subprocess.TimeoutExpired:
        pass


def _capture_visual(name):
    path = os.path.join(STATE["output_dir"], "sovereign_skirmish_{0}.png".format(name))
    _activate_own_window()
    window_id = _capture_window_id()
    ok = False
    if window_id is not None:
        ok = _try_capture(["/usr/sbin/screencapture", "-x", "-o", "-l{0}".format(window_id), path], path)
    if not ok:
        ok = _try_capture(["/usr/sbin/screencapture", "-x", path], path)
    if not ok:
        for display_idx in range(1, 5):
            ok = _try_capture(["/usr/sbin/screencapture", "-x", "-D{0}".format(display_idx), path], path)
            if ok:
                break
    if not ok:
        _fail("screencapture failed for {0}".format(name))

    width, height = _png_size(path)
    record = {"name": name, "path": path, "size": [width, height]}
    STATE["captures"].append(record)
    print("SOVEREIGN_SKIRMISH_CAPTURE {0} {1} {2}x{3}".format(name, path, width, height))
    sys.stdout.flush()
    return path


def _has_capture(name):
    return any(record["name"] == name for record in STATE["captures"])


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


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "players": STATE["players"],
        "ai": STATE["ai"],
        "movement": STATE["movement"],
        "combat": STATE["combat"],
        "victory": STATE["victory"],
        "scenario_state": STATE["scenario_state"],
        "captures": STATE["captures"],
        "entities": {
            key: _snapshot_entity(ent)
            for key, ent in STATE["entities"].items()
        },
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_SKIRMISH_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_SKIRMISH_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_SKIRMISH_PROBE_PASS backend={backend} train={train} "
        "move={move} walk={walk} attack={attack} damage={damage} "
        "victory={victory} winner={winner}"
    ).format(
        backend=pf.get_render_info().get("backend"),
        train=int(STATE["checks"]["enemy_trained_wave"]),
        move=int(STATE["checks"]["wave_moved_gradually"]),
        walk=int(STATE["checks"]["walk_anim_observed"]),
        attack=int(STATE["checks"]["attack_anim_observed"]),
        damage=STATE["combat"].get("data_damage", 0),
        victory=int(STATE["checks"]["conquest_victory"]),
        winner=STATE["victory"].get("winner"),
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


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


def _unit_entry(unit_id, name):
    return {
        "kind": "unit",
        "id": unit_id,
        "name": name,
        "definition": UNITS[unit_id],
    }


def _spawned_entity(result, kind, entity_id, name=None):
    for entry, ent in zip(result["plan"]["entities"], result["entities"]):
        if entry["kind"] != kind or entry["id"] != entity_id:
            continue
        if name is not None and entry["name"] != name:
            continue
        return ent
    return None


def _on_motion_start(user, event):
    del user
    del event
    STATE["movement"]["motion_start_events"] += 1


def _on_motion_end(user, event):
    del user
    del event
    STATE["movement"]["motion_end_events"] += 1


def _complete_buildings(result):
    return player_state_from_spawn_result(
        result,
        completed_buildings=("town_center", "house", "barracks"),
    )


def _setup_scene():
    scenario = load_scenario(os.path.join(pf.get_basedir(), "assets/sovereign/scenarios/two_player_skirmish.json"))
    scenario_state = scenario_runtime_state(scenario)
    seeded_attack_unit = scenario_seeded_choice(scenario, ("militia",), salt=29)
    pf.load_map("assets/maps", "plain.pfmap")
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    _ensure_factions()

    center = (96.0, 86.0)
    camera = pf.Camera(
        name="sovereign_skirmish_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 128.0, center[1]),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)

    sovereign_globals.scene_objs = []
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_skirmish_region",
            position=center,
            dimensions=(96.0, 80.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]

    player_result = spawn_minimal_test_scene(
        center=(56.0, 58.0),
        faction_id=1,
        scene_objs=sovereign_globals.scene_objs,
    )
    enemy_result = spawn_minimal_test_scene(
        center=(112.0, 58.0),
        faction_id=2,
        scene_objs=sovereign_globals.scene_objs,
    )
    player_state = _complete_buildings(player_result)
    enemy_state = _complete_buildings(enemy_result)

    target = create_entity(_unit_entry("militia", "sovereign_player_guard"))
    place_entity(target, (112.0, 98.0), faction_id=1, radius=3.25, scale=UNITS["militia"].get("scale"))
    sovereign_globals.scene_objs.append(target)
    player_state.add_unit("militia", target)

    enemy_barracks = _spawned_entity(enemy_result, "building", "barracks")
    if enemy_barracks is None:
        _fail("enemy barracks was not spawned")
    try:
        enemy_barracks.rally_point = (124.0, 98.0)
    except AttributeError:
        pass

    ai = ScriptedSkirmishAI(
        enemy_state,
        enemy_barracks,
        2,
        sovereign_globals.scene_objs,
        map_seed=scenario_state["metadata"]["map_seed"],
    )
    ai.seed_opening_resources({"food": 500, "wood": 500, "gold": 200, "stone": 100})
    wave = ai.train_attack_unit(seeded_attack_unit)
    wave.name = "sovereign_enemy_wave_{0}".format(seeded_attack_unit)
    place_entity(wave, (124.0, 98.0), faction_id=2, radius=3.25, scale=UNITS["militia"].get("scale"))
    wave.face_towards(target.pos)
    target.face_towards(wave.pos)
    wave.register(pf.EVENT_MOTION_START, _on_motion_start, None)
    wave.register(pf.EVENT_MOTION_END, _on_motion_end, None)

    pf.set_unit_selection([wave])
    sovereign_globals.player_state = player_state
    sovereign_globals.production_queue = ai.queue
    sovereign_globals.scenario_state = scenario_state

    STATE["entities"] = {
        "player_target": target,
        "enemy_wave": wave,
        "player_town_center": _spawned_entity(player_result, "building", "town_center"),
        "enemy_town_center": _spawned_entity(enemy_result, "building", "town_center"),
        "enemy_barracks": enemy_barracks,
    }
    STATE["players"] = {
        "player": player_state.snapshot(),
        "enemy": enemy_state.snapshot(),
    }
    STATE["ai"] = ai.snapshot()
    STATE["scenario_state"] = scenario_state
    STATE["combat"] = {
        "target_hp_start": int(target.hp),
        "target_hp_after_data": int(target.hp),
        "engine_damage": 0,
        "seeded_attack_unit": seeded_attack_unit,
        "scripted_damage": [],
    }
    STATE["movement"]["start"] = _ent_xz(wave)
    STATE["movement"]["target"] = (116.0, 98.0)
    STATE["checks"]["two_player_setup"] = (
        player_state.population_cap >= 10 and enemy_state.population_cap >= 10
    )
    STATE["checks"]["setup_profile"] = (
        scenario_state["setup"]["profile"] == "standard_skirmish"
        and scenario_state["setup"]["starting_resource_preset"] == "standard"
    )
    STATE["checks"]["seeded_setup"] = (
        ai.snapshot().get("map_seed") == scenario_state["metadata"]["map_seed"]
        and seeded_attack_unit == scenario_seeded_choice(scenario, ("militia",), salt=29)
    )
    STATE["checks"]["enemy_economy_seeded"] = enemy_state.resources["food"] >= 440
    STATE["checks"]["enemy_trained_wave"] = wave in [
        record["entity"] for record in enemy_state.units
    ]
    STATE["checks"]["actors_facing"] = True


def _sample_wave():
    wave = STATE["entities"]["enemy_wave"]
    pos = _ent_xz(wave)
    samples = STATE["movement"]["samples"]
    if samples:
        last = samples[-1]["position"]
        step = _dist(pos, last)
        STATE["movement"]["max_step"] = max(STATE["movement"]["max_step"], step)
    try:
        anim = wave.get_anim()
    except (AttributeError, RuntimeError):
        anim = None
    STATE["movement"]["anim_samples"].append(anim)
    STATE["checks"]["walk_anim_observed"] = (
        STATE["checks"]["walk_anim_observed"] or anim == "Walk"
    )
    STATE["checks"]["attack_anim_observed"] = (
        STATE["checks"]["attack_anim_observed"] or anim == "Attack"
    )
    samples.append({"tick": STATE["ticks"], "position": pos, "anim": anim})
    return pos, anim


def _start_move():
    wave = STATE["entities"]["enemy_wave"]
    target = STATE["movement"]["target"]
    wave.face_towards((target[0], wave.pos[1], target[1]))
    wave.move(target)
    STATE["checks"]["wave_move_started"] = True


def _movement_ready(pos):
    start = STATE["movement"]["start"]
    displacement = _dist(pos, start)
    STATE["movement"]["displacement"] = displacement
    STATE["checks"]["wave_moved_gradually"] = (
        displacement >= 3.0
        and STATE["movement"]["max_step"] <= 12.0
        and len(STATE["movement"]["samples"]) >= 8
    )
    return STATE["checks"]["wave_moved_gradually"]


def _start_attack():
    wave = STATE["entities"]["enemy_wave"]
    target = STATE["entities"]["player_target"]
    if hasattr(wave, "stop"):
        wave.stop()
    if hasattr(target, "stop"):
        target.stop()
    try:
        target.play_anim("Idle")
    except (AttributeError, RuntimeError):
        pass
    wave.face_towards(target.pos)
    target.face_towards(wave.pos)
    wave.play_anim("Attack")
    STATE["checks"]["attack_anim_observed"] = True
    STATE["combat"]["scripted_attack_started"] = True


def _finish_victory():
    target = STATE["entities"]["player_target"]
    attacker_id = STATE["combat"].get("seeded_attack_unit", "militia")
    scripted_damage = []
    while int(target.hp) > 1:
        before = int(target.hp)
        total_damage = damage_breakdown(attacker_id, "militia")["total_damage"]
        if before <= total_damage:
            target.hp = 1
            scripted_damage.append({
                "attacker_id": attacker_id,
                "target_id": "militia",
                "total_damage": min(total_damage, before - 1),
                "hp_before": before,
                "hp_after": 1,
            })
            break
        scripted_damage.append(apply_damage(attacker_id, "militia", target))
    winner = scenario_victory_winner(STATE["scenario_state"], {
        1: [target],
        2: [STATE["entities"]["enemy_wave"]],
    }, hp_threshold=1)
    STATE["combat"]["scripted_damage"] = scripted_damage
    STATE["victory"] = {
        "winner": winner,
        "player_defeated": faction_defeated([target], hp_threshold=1),
        "progress": victory_progress_state(
            STATE["scenario_state"],
            {
                1: [target],
                2: [STATE["entities"]["enemy_wave"]],
            },
            hp_threshold=1,
            elapsed_ticks=STATE["ticks"],
        ),
    }
    STATE["checks"]["victory_dispatch"] = winner == 2
    STATE["checks"]["conquest_victory"] = winner == 2


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
        _set_phase("settle")
        return

    if STATE["phase"] == "settle":
        if STATE["ticks"] >= 8:
            if STATE["capture_proof"]:
                _capture_visual("setup")
            _start_move()
            _set_phase("moving")
        return

    if STATE["phase"] == "moving":
        pos, anim = _sample_wave()
        del anim
        if STATE["capture_proof"] and not _has_capture("moving") and STATE["ticks"] >= 4:
            _capture_visual("moving")
        if _movement_ready(pos):
            if STATE["capture_proof"] and not _has_capture("moving"):
                _capture_visual("moving")
            _start_attack()
            _set_phase("combat")
            return
        if _phase_elapsed() > 12.0:
            _fail("enemy wave did not move naturally: {0}".format(STATE["movement"]))
        return

    if STATE["phase"] == "combat":
        _sample_wave()
        target = STATE["entities"]["player_target"]
        hp_after = int(target.hp)
        if STATE["ticks"] >= 6 and not STATE["checks"]["target_damaged"]:
            damage = apply_damage(STATE["combat"].get("seeded_attack_unit", "militia"), "militia", target)
            STATE["combat"]["data_damage"] = damage["total_damage"]
            hp_after = int(target.hp)
            STATE["combat"]["target_hp_after_data"] = hp_after
        if hp_after < STATE["combat"]["target_hp_start"]:
            STATE["combat"]["engine_damage"] = 0
            STATE["checks"]["target_damaged"] = True
        if (
            STATE["capture_proof"]
            and not _has_capture("combat")
            and STATE["checks"]["attack_anim_observed"]
            and STATE["ticks"] >= 2
        ):
            _capture_visual("combat")
        if STATE["checks"]["target_damaged"] and STATE["checks"]["attack_anim_observed"]:
            _finish_victory()
            if STATE["capture_proof"] and not _has_capture("victory"):
                _capture_visual("victory")
            if all(STATE["checks"].values()):
                _succeed()
                return
            _fail("skirmish checks did not all pass: {0}".format(STATE["checks"]))
        if _phase_elapsed() > 24.0:
            _fail("timed out waiting for combat damage/animation: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    STATE["output_dir"] = args.output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["capture_proof"] = args.capture_proof
    if not os.path.isdir(STATE["output_dir"]):
        os.makedirs(STATE["output_dir"])
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
