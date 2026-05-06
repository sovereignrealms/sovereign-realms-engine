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
from sovereign.scenario import (
    RESOURCE_IDS,
    build_runtime_scene,
    load_scenario,
    save_scenario,
    scenario_player_starting_resources,
    scenario_seeded_choice,
    scenario_setup,
    scenario_summary,
    validate_scenario,
)
from sovereign.systems.combat_rules import apply_damage
from sovereign.systems.skirmish import ScriptedSkirmishAI, scenario_victory_winner


PROBE_PATH = "/tmp/pf_sovereign_editor_scenario_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_editor_scenario_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "scenario_path": None,
    "output_dir": None,
    "expected_backend": None,
    "capture_proof": False,
    "checks": {
        "scenario_valid": False,
        "scenario_exported": False,
        "scenario_reloaded": False,
        "metadata_seed": False,
        "setup_profile": False,
        "seeded_setup": False,
        "export_report": False,
        "runtime_scene": False,
        "two_player_starts": False,
        "diplomacy_war": False,
        "player_resources": False,
        "palette_valid": False,
        "placed_resources": False,
        "placed_objects": False,
        "enemy_trained_wave": False,
        "victory_dispatch": False,
        "conquest_victory": False,
    },
    "captures": [],
    "runtime_summary": {},
    "scenario_export_path": None,
    "entities": {},
    "players": {},
    "ai": {},
    "combat": {},
    "victory": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign editor scenario sidecar probe.")
    parser.add_argument(
        "--scenario",
        default="assets/sovereign/scenarios/two_player_skirmish.json",
    )
    parser.add_argument("--output-dir", default="qa-output/sovereign-editor-scenario")
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
    print("SOVEREIGN_EDITOR_SCENARIO_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_editor_scenario.json")


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
    path = os.path.join(STATE["output_dir"], "sovereign_editor_scenario_{0}.png".format(name))
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
    print("SOVEREIGN_EDITOR_SCENARIO_CAPTURE {0} {1} {2}x{3}".format(name, path, width, height))
    sys.stdout.flush()
    return path


def _has_capture(name):
    return any(record["name"] == name for record in STATE["captures"])


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "scenario_path": STATE["scenario_path"],
        "scenario_export_path": STATE["scenario_export_path"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "runtime_summary": STATE["runtime_summary"],
        "players": STATE["players"],
        "ai": STATE["ai"],
        "combat": STATE["combat"],
        "victory": STATE["victory"],
        "captures": STATE["captures"],
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_EDITOR_SCENARIO_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_EDITOR_SCENARIO_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend={backend} "
        "export={exported} reload={reloaded} players={players} "
        "objects={objects} train={train} victory={victory}"
    ).format(
        backend=pf.get_render_info().get("backend"),
        exported=int(STATE["checks"]["scenario_exported"]),
        reloaded=int(STATE["checks"]["scenario_reloaded"]),
        players=len(STATE["players"]),
        objects=STATE["runtime_summary"].get("object_count", 0),
        train=int(STATE["checks"]["enemy_trained_wave"]),
        victory=int(STATE["checks"]["conquest_victory"]),
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


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


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _dist(a, b):
    dx = a[0] - b[0]
    dz = a[1] - b[1]
    return math.sqrt(dx * dx + dz * dz)


def _player_start_distance(scenario):
    players = scenario["players"]
    return _dist(players[0]["start"], players[1]["start"])


def _setup_camera(scenario):
    starts = [player["start"] for player in scenario["players"]]
    center = (
        sum(float(start[0]) for start in starts) / len(starts),
        sum(float(start[1]) for start in starts) / len(starts) + 18.0,
    )
    camera = pf.Camera(
        name="sovereign_editor_scenario_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 148.0, center[1]),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_editor_scenario_region",
            position=center,
            dimensions=(128.0, 96.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _setup_render_state():
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)


def _load_export_reload_scenario():
    scenario = load_scenario(STATE["scenario_path"])
    errors = validate_scenario(scenario)
    if errors:
        _fail("scenario validation failed: " + "; ".join(errors))
    STATE["checks"]["scenario_valid"] = True

    sidecar_path = os.path.join(STATE["output_dir"], "editor_two_player_skirmish.sovereign.json")
    save_scenario(scenario, sidecar_path)
    STATE["scenario_export_path"] = sidecar_path
    STATE["checks"]["scenario_exported"] = os.path.exists(sidecar_path)

    reloaded = load_scenario(sidecar_path)
    reload_errors = validate_scenario(reloaded)
    if reload_errors:
        _fail("reloaded scenario validation failed: " + "; ".join(reload_errors))
    STATE["checks"]["scenario_reloaded"] = reloaded == scenario
    if not STATE["checks"]["scenario_reloaded"]:
        _fail("reloaded scenario did not match exported scenario")
    return reloaded


def _setup_scene():
    scenario = _load_export_reload_scenario()
    runtime = build_runtime_scene(scenario, scene_objs=[])
    _setup_render_state()
    _setup_camera(scenario)

    STATE["runtime_summary"] = scenario_summary(runtime)
    placed_resources = scenario.get("placed_resources", [])
    placed_objects = scenario.get("placed_objects", [])
    metadata = scenario.get("metadata", {})
    report = scenario.get("export_report", {})
    report_counts = report.get("counts", {})
    report_validation = report.get("validation", {})
    expected_markers = len(scenario.get("players", [])) + len(placed_resources) + len(placed_objects)
    STATE["checks"]["metadata_seed"] = (
        isinstance(metadata.get("map_seed"), int)
        and metadata.get("map_seed") >= 0
        and isinstance(metadata.get("author_notes", ""), str)
        and scenario.get("victory", {}).get("label") == "Conquest"
    )
    expected_setup = scenario_setup(scenario)
    runtime_setup = STATE["runtime_summary"].get("scenario_state", {}).get("setup", {})
    STATE["checks"]["setup_profile"] = (
        runtime_setup.get("profile") == expected_setup.get("profile")
        and runtime_setup.get("starting_resource_preset") == expected_setup.get("starting_resource_preset")
        and runtime_setup.get("victory_mode") == expected_setup.get("victory_mode")
    )
    seeded_attack_unit = scenario_seeded_choice(scenario, ("militia",), salt=17)
    STATE["checks"]["seeded_setup"] = (
        runtime.get("map_seed") == metadata.get("map_seed")
        and seeded_attack_unit == scenario_seeded_choice(scenario, ("militia",), salt=17)
    )
    STATE["checks"]["export_report"] = (
        report_counts.get("players") == len(scenario.get("players", []))
        and report_counts.get("resource_clusters") == len(placed_resources)
        and report_counts.get("placed_objects") == len(placed_objects)
        and report_counts.get("markers") == expected_markers
        and report_validation.get("status") == "ready"
        and report_validation.get("issue_count") == 0
    )
    STATE["checks"]["runtime_scene"] = (
        len(runtime["players"]) == len(scenario["players"])
        and len(runtime["scene_objs"]) >= 20 + len(placed_resources) + len(placed_objects)
    )
    STATE["checks"]["two_player_starts"] = _player_start_distance(scenario) >= 20.0
    STATE["checks"]["diplomacy_war"] = any(
        row.get("a") == 1 and row.get("b") == 2 and row.get("state") == "war"
        for row in scenario.get("diplomacy", [])
    )
    STATE["checks"]["palette_valid"] = (
        "militia" in scenario["palette"]["units"]
        and "barracks" in scenario["palette"]["buildings"]
        and "food" in scenario["palette"]["resources"]
    )
    if placed_resources:
        placed_resource_ids = set(resource["resource_id"] for resource in placed_resources)
        STATE["checks"]["placed_resources"] = all(
            resource_id in placed_resource_ids
            for resource_id in RESOURCE_IDS
        )
    else:
        STATE["checks"]["placed_resources"] = True
    if placed_objects:
        STATE["checks"]["placed_objects"] = any(
            obj.get("kind") == "unit" and obj.get("owner_player_id") == 1
            for obj in placed_objects
        ) and any(
            obj.get("kind") == "building" and obj.get("owner_player_id") == 2
            for obj in placed_objects
        )
    else:
        STATE["checks"]["placed_objects"] = True

    player_record = runtime["players"][1]
    enemy_record = runtime["players"][2]
    player_state = player_record["state"]
    enemy_state = enemy_record["state"]
    STATE["checks"]["player_resources"] = all(
        player_state.resources[resource_id] == int(amount)
        for resource_id, amount in scenario_player_starting_resources(scenario, player_record["definition"]).items()
    )

    enemy_barracks = _spawned_entity(enemy_record["spawn_result"], "building", "barracks")
    if enemy_barracks is None:
        _fail("enemy barracks was not spawned from scenario")
    try:
        enemy_barracks.rally_point = (108.0, 92.0)
    except AttributeError:
        pass

    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, runtime["scene_objs"], map_seed=runtime["map_seed"])
    wave = ai.train_attack_unit(seeded_attack_unit)
    wave.name = "sovereign_scenario_enemy_wave"
    target = create_entity(_unit_entry("militia", "sovereign_scenario_player_guard"))
    place_entity(target, (104.0, 94.0), faction_id=1, radius=3.25, scale=UNITS["militia"].get("scale"))
    runtime["scene_objs"].append(target)
    player_state.add_unit("militia", target)
    wave.face_towards(target.pos)
    target.face_towards(wave.pos)
    pf.set_unit_selection([wave, target])

    STATE["checks"]["enemy_trained_wave"] = wave in [
        record["entity"] for record in enemy_state.units
    ]
    STATE["entities"] = {
        "enemy_wave": wave,
        "target": target,
        "enemy_barracks": enemy_barracks,
    }
    STATE["players"] = {
        str(player_id): record["state"].snapshot()
        for player_id, record in runtime["players"].items()
    }
    STATE["ai"] = ai.snapshot()
    STATE["combat"] = {
        "target_hp_start": int(target.hp),
        "target_hp_after_data": int(target.hp),
        "seeded_attack_unit": seeded_attack_unit,
        "wave_position": _ent_xz(wave),
        "target_position": _ent_xz(target),
    }


def _finish_conquest_check():
    target = STATE["entities"]["target"]
    wave = STATE["entities"]["enemy_wave"]
    attacker_id = STATE["combat"].get("seeded_attack_unit", "militia")
    damage = apply_damage(attacker_id, "militia", target)
    while int(target.hp) > 1:
        before = int(target.hp)
        damage = apply_damage(attacker_id, "militia", target)
        if int(target.hp) == before:
            target.hp = 1
            break
    winner = scenario_victory_winner(STATE["runtime_summary"]["scenario_state"], {1: [target], 2: [wave]}, hp_threshold=1)
    STATE["combat"]["last_damage"] = damage
    STATE["combat"]["target_hp_after_data"] = int(target.hp)
    STATE["victory"] = {"winner": winner}
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
        _setup_scene()
        _set_phase("settle")
        return

    if STATE["phase"] == "settle":
        if STATE["capture_proof"] and not _has_capture("loaded") and STATE["ticks"] >= 8:
            _capture_visual("loaded")
        if STATE["ticks"] >= 12:
            _finish_conquest_check()
            _set_phase("victory")
        return

    if STATE["phase"] == "victory":
        if STATE["capture_proof"] and not _has_capture("validated") and STATE["ticks"] >= 4:
            _capture_visual("validated")
        if STATE["ticks"] >= 6:
            if all(STATE["checks"].values()):
                _succeed()
                return
            _fail("editor scenario checks did not all pass: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    STATE["scenario_path"] = args.scenario
    STATE["output_dir"] = args.output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["capture_proof"] = args.capture_proof
    if not os.path.isdir(STATE["output_dir"]):
        os.makedirs(STATE["output_dir"])
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
