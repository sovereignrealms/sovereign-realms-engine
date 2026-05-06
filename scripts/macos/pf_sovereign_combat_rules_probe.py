import argparse
import json
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
from sovereign.factory import validate_registries
from sovereign.systems.combat_rules import apply_damage, damage_breakdown


PROBE_PATH = "/tmp/pf_sovereign_combat_rules_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_combat_rules_probe_error.txt"

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
        "base_damage": False,
        "bonus_damage": False,
        "hp_delta": False,
        "target_alive": False,
    },
    "entities": {},
    "combat": {},
    "captures": [],
    "capture_proof": False,
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign combat-rules probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-combat-rules-probe")
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
    print("SOVEREIGN_COMBAT_RULES_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_combat_rules.json")


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
    path = os.path.join(STATE["output_dir"], "sovereign_combat_rules_{0}.png".format(name))
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
    print("SOVEREIGN_COMBAT_RULES_CAPTURE {0} {1} {2}x{3}".format(name, path, width, height))
    sys.stdout.flush()
    return path


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "combat": STATE["combat"],
        "captures": STATE["captures"],
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_COMBAT_RULES_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_COMBAT_RULES_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_COMBAT_RULES_PROBE_PASS backend={backend} "
        "damage={damage} base={base} bonus={bonus} hp={hp_before}->{hp_after}"
    ).format(
        backend=pf.get_render_info().get("backend"),
        damage=STATE["combat"]["applied"]["total_damage"],
        base=STATE["combat"]["applied"]["base_damage"],
        bonus=STATE["combat"]["applied"]["bonus_damage"],
        hp_before=STATE["combat"]["applied"]["hp_before"],
        hp_after=STATE["combat"]["applied"]["hp_after"],
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _ensure_factions():
    if len(pf.get_factions_list()) == 0:
        pf.add_faction("Neutral", (160, 160, 160, 255))
        pf.add_faction("Sovereign", (40, 90, 255, 255))
        pf.add_faction("Opponent", (220, 50, 50, 255))


def _unit_entry(unit_id, name):
    return {
        "kind": "unit",
        "id": unit_id,
        "name": name,
        "definition": UNITS[unit_id],
    }


def _setup_scene():
    pf.load_map("assets/maps", "plain.pfmap")
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    _ensure_factions()

    center = (72.0, 72.0)
    camera = pf.Camera(
        name="sovereign_combat_rules_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 88.0, center[1]),
        pitch=-58.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)

    sovereign_globals.scene_objs = []
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_combat_rules_region",
            position=center,
            dimensions=(48.0, 48.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]

    attacker = create_entity(_unit_entry("militia", "militia_counter_attacker"))
    target = create_entity(_unit_entry("militia", "militia_counter_target"))
    place_entity(attacker, (70.0, 72.0), faction_id=1, radius=3.25, scale=UNITS["militia"].get("scale"))
    place_entity(target, (76.0, 72.0), faction_id=2, radius=3.25, scale=UNITS["militia"].get("scale"))
    sovereign_globals.scene_objs.extend([attacker, target])
    pf.set_unit_selection([target])
    STATE["entities"] = {
        "attacker": attacker,
        "target": target,
    }
    STATE["checks"]["spawn"] = int(attacker.hp) == 45 and int(target.hp) == 45
    STATE["combat"]["expected"] = damage_breakdown("militia", "militia")


def _apply_combat_rules():
    attacker = STATE["entities"]["attacker"]
    target = STATE["entities"]["target"]
    del attacker
    applied = apply_damage("militia", "militia", target)
    STATE["combat"]["applied"] = applied
    expected = STATE["combat"]["expected"]
    STATE["checks"]["base_damage"] = applied["base_damage"] == 4
    STATE["checks"]["bonus_damage"] = applied["bonus_damage"] == 1 and applied["matched_bonus_classes"] == ["infantry"]
    STATE["checks"]["hp_delta"] = applied["hp_before"] - applied["hp_after"] == expected["total_damage"]
    STATE["checks"]["target_alive"] = int(target.hp) > 0
    pf.set_unit_selection([target])


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
            if STATE["capture_proof"] and not STATE["captures"]:
                _capture_visual("before")
            _set_phase("apply_damage")
        return

    if STATE["phase"] == "apply_damage":
        if STATE["ticks"] == 1:
            _apply_combat_rules()
            _set_phase("done")
        return

    if STATE["phase"] == "done":
        if STATE["capture_proof"] and len(STATE["captures"]) < 2:
            _capture_visual("after")
        if all(STATE["checks"].values()):
            _succeed()
        _fail("combat rule checks failed: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    STATE["output_dir"] = args.output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["capture_proof"] = args.capture_proof
    if not os.path.isdir(STATE["output_dir"]):
        os.makedirs(STATE["output_dir"])
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
