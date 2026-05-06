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
from sovereign.factory import spawn_minimal_test_scene, validate_registries


PROBE_PATH = "/tmp/pf_sovereign_economy_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_economy_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "output_dir": None,
    "expected_backend": None,
    "phase_started_at": None,
    "phase_log": [],
    "events": {},
    "checks": {
        "registry": False,
        "spawn": False,
        "resource_gather": False,
        "resource_dropoff": False,
        "building_constructed": False,
    },
    "entities": {},
    "resource": {},
    "building": {},
    "dropoff_issued": False,
    "build_issued": False,
    "hold_after_pass_sec": 0.0,
    "capture_after_pass": False,
    "captures": [],
    "pass_marker": None,
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign minimal economy probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-economy-probe")
    parser.add_argument("--expect-backend", default="METAL")
    parser.add_argument("--hold-after-pass-sec", type=float, default=0.0)
    parser.add_argument("--capture-after-pass", action="store_true")
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


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


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    print("SOVEREIGN_ECONOMY_PHASE {0}".format(name))
    sys.stdout.flush()


def _phase_elapsed():
    return time.monotonic() - STATE["phase_started_at"]


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_economy.json")


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
    path = os.path.join(STATE["output_dir"], "sovereign_economy_{0}.png".format(name))
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
    print("SOVEREIGN_ECONOMY_CAPTURE {0} {1} {2}x{3}".format(name, path, width, height))
    sys.stdout.flush()
    return path


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _snapshot_entity(ent):
    payload = {
        "name": getattr(ent, "name", None),
        "position": _ent_xz(ent),
        "selection_radius": getattr(ent, "selection_radius", None),
        "faction_id": getattr(ent, "faction_id", None),
    }
    for attr in ("resource_amount", "completed", "founded", "supplied", "total_carry"):
        if hasattr(ent, attr):
            payload[attr] = getattr(ent, attr)
    return payload


def _write_summary(status, reason=None):
    if not os.path.isdir(STATE["output_dir"]):
        os.makedirs(STATE["output_dir"])
    worker = STATE["entities"].get("worker")
    storage = STATE["entities"].get("storage")
    resource = STATE["entities"].get("resource")
    build_target = STATE["entities"].get("build_target")
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "events": STATE["events"],
        "captures": STATE["captures"],
        "resource": STATE["resource"],
        "building": STATE["building"],
        "entities": {
            "worker": None if worker is None else _snapshot_entity(worker),
            "storage": None if storage is None else _snapshot_entity(storage),
            "resource": None if resource is None else _snapshot_entity(resource),
            "build_target": None if build_target is None else _snapshot_entity(build_target),
        },
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_ECONOMY_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_ECONOMY_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_ECONOMY_PROBE_PASS backend={backend} gather={gather} "
        "dropoff={dropoff} build={build} storage_food={storage_food}"
    ).format(
        backend=pf.get_render_info().get("backend"),
        gather=int(STATE["checks"]["resource_gather"]),
        dropoff=int(STATE["checks"]["resource_dropoff"]),
        build=int(STATE["checks"]["building_constructed"]),
        storage_food=STATE["resource"].get("storage_amount_end"),
    )
    STATE["pass_marker"] = marker
    if STATE["capture_after_pass"] and not STATE["captures"]:
        _capture_visual("economy")
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    if STATE["hold_after_pass_sec"] > 0.0:
        _set_phase("visual_hold")
        return
    os._exit(0)


def _ensure_factions():
    if len(pf.get_factions_list()) == 0:
        pf.add_faction("Neutral", (160, 160, 160, 255))
        pf.add_faction("Sovereign", (40, 90, 255, 255))
        pf.add_faction("Opponent", (220, 50, 50, 255))


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

    center = (64.0, 64.0)
    camera = pf.Camera(
        name="sovereign_economy_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 120.0, center[1]),
        pitch=-62.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)

    sovereign_globals.scene_objs = []
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_economy_region",
            position=center,
            dimensions=(72.0, 72.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]
    result = spawn_minimal_test_scene(center=center, faction_id=1, scene_objs=sovereign_globals.scene_objs)
    by_name = {getattr(ent, "name", ""): ent for ent in result["entities"]}

    worker = by_name["villager_1"]
    storage = by_name["town_center"]
    resource = by_name["food_node"]
    build_target = by_name["house"]
    STATE["entities"] = {
        "worker": worker,
        "storage": storage,
        "resource": resource,
        "build_target": build_target,
    }
    STATE["checks"]["spawn"] = len(result["entities"]) == 10
    STATE["resource"] = {
        "resource_amount_start": resource.resource_amount,
        "storage_amount_start": storage.get_curr_amount("food"),
    }
    STATE["building"] = {
        "target_start": _snapshot_entity(build_target),
    }

    worker.register(pf.EVENT_HARVEST_TARGET_ACQUIRED, _on_event("harvest_target"), None)
    worker.register(pf.EVENT_HARVEST_BEGIN, _on_event("harvest_begin"), None)
    worker.register(pf.EVENT_HARVEST_END, _on_event("harvest_end"), None)
    worker.register(pf.EVENT_STORAGE_TARGET_ACQUIRED, _on_event("storage_target"), None)
    worker.register(pf.EVENT_RESOURCE_DROPPED_OFF, _on_event("resource_dropped_off"), None)
    worker.register(pf.EVENT_BUILD_TARGET_ACQUIRED, _on_event("build_target"), None)
    worker.register(pf.EVENT_BUILD_BEGIN, _on_event("build_begin"), None)
    worker.register(pf.EVENT_BUILD_END, _on_event("build_end"), None)
    build_target.register(pf.EVENT_BUILDING_COMPLETED, _on_event("building_completed"), None)


def _drive_harvest():
    worker = STATE["entities"]["worker"]
    worker.notify(pf.EVENT_MOTION_END, None)
    if _event_count("harvest_begin") > 0:
        worker.notify(pf.EVENT_ANIM_CYCLE_FINISHED, None)


def _drive_dropoff():
    STATE["entities"]["worker"].notify(pf.EVENT_MOTION_END, None)


def _resource_phase():
    worker = STATE["entities"]["worker"]
    resource = STATE["entities"]["resource"]
    storage = STATE["entities"]["storage"]
    if STATE["ticks"] == 1:
        worker.gather(resource)

    _drive_harvest()
    if worker.get_curr_carry("food") > 0 or resource.resource_amount < STATE["resource"]["resource_amount_start"]:
        STATE["checks"]["resource_gather"] = True

    if worker.get_curr_carry("food") > 0 and not STATE["dropoff_issued"]:
        worker.drop_off(storage)
        STATE["dropoff_issued"] = True
    _drive_dropoff()

    STATE["resource"].update({
        "resource_amount_end": resource.resource_amount,
        "worker_carry": worker.get_curr_carry("food"),
        "worker_total_carry": worker.total_carry,
        "storage_amount_end": storage.get_curr_amount("food"),
    })

    if storage.get_curr_amount("food") > STATE["resource"]["storage_amount_start"]:
        STATE["checks"]["resource_dropoff"] = True
        _set_phase("building")
        return

    if _phase_elapsed() > 10.0:
        _fail("villager did not gather and drop off food")


def _building_phase():
    worker = STATE["entities"]["worker"]
    build_target = STATE["entities"]["build_target"]
    if STATE["ticks"] == 1 and not STATE["build_issued"]:
        try:
            build_target.mark()
            build_target.found(force=True)
            build_target.supply()
        except Exception as exc:
            _fail("house setup failed: {0}: {1}".format(exc.__class__.__name__, exc))
        worker.build(build_target)
        STATE["build_issued"] = True

    worker.notify(pf.EVENT_MOTION_END, None)
    worker.notify(pf.EVENT_ANIM_CYCLE_FINISHED, None)
    STATE["building"]["target_end"] = _snapshot_entity(build_target)

    if build_target.completed:
        STATE["checks"]["building_constructed"] = True
        _set_phase("done")
        return

    if _phase_elapsed() > 10.0:
        _fail("villager did not complete house placeholder")


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
            _set_phase("resource")
        return

    if STATE["phase"] == "resource":
        _resource_phase()
        return

    if STATE["phase"] == "building":
        _building_phase()
        return

    if STATE["phase"] == "done":
        _succeed()
        return

    if STATE["phase"] == "visual_hold":
        if _phase_elapsed() >= STATE["hold_after_pass_sec"]:
            os._exit(0)


def main():
    args = _parse_args()
    STATE["output_dir"] = args.output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["hold_after_pass_sec"] = max(0.0, args.hold_after_pass_sec)
    STATE["capture_after_pass"] = args.capture_after_pass
    if not os.path.isdir(STATE["output_dir"]):
        os.makedirs(STATE["output_dir"])
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
