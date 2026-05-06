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
from sovereign.systems.production import (
    ProductionError,
    ProductionQueue,
    player_state_from_spawn_result,
    rally_distance,
)


PROBE_PATH = "/tmp/pf_sovereign_production_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_production_probe_error.txt"

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
        "population_gate": False,
        "enqueue": False,
        "cost_deducted": False,
        "unit_spawned": False,
        "population_consumed": False,
        "rally_spawn": False,
    },
    "entities": {},
    "player": {},
    "queue": {},
    "captures": [],
    "capture_proof": False,
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign production/population probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-production-probe")
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
    print("SOVEREIGN_PRODUCTION_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_production.json")


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
    path = os.path.join(STATE["output_dir"], "sovereign_production_{0}.png".format(name))
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
    print("SOVEREIGN_PRODUCTION_CAPTURE {0} {1} {2}x{3}".format(name, path, width, height))
    sys.stdout.flush()
    return path


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _snapshot_entity(ent):
    return {
        "name": getattr(ent, "name", None),
        "position": _ent_xz(ent),
        "faction_id": getattr(ent, "faction_id", None),
        "selection_radius": getattr(ent, "selection_radius", None),
    }


def _write_summary(status, reason=None):
    trained = STATE["entities"].get("trained")
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "player": STATE["player"],
        "queue": STATE["queue"],
        "captures": STATE["captures"],
        "trained": None if trained is None else _snapshot_entity(trained),
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_PRODUCTION_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_PRODUCTION_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_PRODUCTION_PROBE_PASS backend={backend} enqueue={enqueue} "
        "spawn={spawn} pop={pop_used}/{pop_cap} food={food} gold={gold} rally={rally}"
    ).format(
        backend=pf.get_render_info().get("backend"),
        enqueue=int(STATE["checks"]["enqueue"]),
        spawn=int(STATE["checks"]["unit_spawned"]),
        pop_used=STATE["player"]["after"]["population_used"],
        pop_cap=STATE["player"]["after"]["population_cap"],
        food=STATE["player"]["after"]["resources"]["food"],
        gold=STATE["player"]["after"]["resources"]["gold"],
        rally=int(STATE["checks"]["rally_spawn"]),
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


def _complete_building(ent):
    if hasattr(ent, "completed") and not ent.completed:
        ent.mark()
        ent.found(force=True)
        ent.supply()
        ent.complete()


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
        name="sovereign_production_camera",
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
            name="sovereign_production_region",
            position=center,
            dimensions=(72.0, 72.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]
    result = spawn_minimal_test_scene(center=center, faction_id=1, scene_objs=sovereign_globals.scene_objs)
    by_name = {getattr(ent, "name", ""): ent for ent in result["entities"]}
    house = by_name["house"]
    barracks = by_name["barracks"]
    _complete_building(house)
    _complete_building(barracks)
    rally = pf.map_nearest_pathable((82.0, 76.0), radius=3.25)
    barracks.rally_point = rally if rally is not None else (82.0, 76.0)

    player = player_state_from_spawn_result(result, completed_buildings=("house", "barracks"))
    queue = ProductionQueue(
        player,
        "barracks",
        barracks,
        faction_id=1,
        scene_objs=sovereign_globals.scene_objs,
    )
    STATE["entities"] = {
        "house": house,
        "barracks": barracks,
        "trained": None,
    }
    STATE["runtime"] = {
        "player": player,
        "queue": queue,
    }
    STATE["checks"]["spawn"] = len(result["entities"]) == 10
    STATE["player"]["before"] = player.snapshot()
    STATE["queue"]["before"] = queue.snapshot()
    pf.set_unit_selection([barracks])


def _verify_population_gate():
    player = STATE["runtime"]["player"].copy_for_check()
    player.population_used = player.population_cap
    queue = ProductionQueue(player, "barracks", STATE["entities"]["barracks"])
    try:
        queue.enqueue("militia")
    except ProductionError as exc:
        STATE["checks"]["population_gate"] = exc.code == "population_cap"
        return
    _fail("production queue allowed unit beyond population cap")


def _production_phase():
    player = STATE["runtime"]["player"]
    queue = STATE["runtime"]["queue"]
    if STATE["ticks"] == 1:
        _verify_population_gate()
        before = player.snapshot()
        item = queue.enqueue("militia")
        after_enqueue = player.snapshot()
        queue_after_enqueue = queue.snapshot()
        trained = queue.finish_next()
        after = player.snapshot()
        STATE["entities"]["trained"] = trained
        STATE["queue"]["item"] = item
        STATE["queue"]["after_enqueue"] = queue_after_enqueue
        STATE["queue"]["after"] = queue.snapshot()
        STATE["player"]["after_enqueue"] = after_enqueue
        STATE["player"]["after"] = after
        STATE["checks"]["enqueue"] = len(queue.completed) == 1 and len(queue.items) == 0
        STATE["checks"]["cost_deducted"] = (
            after["resources"]["food"] == before["resources"]["food"] - 60
            and after["resources"]["gold"] == before["resources"]["gold"] - 20
        )
        STATE["checks"]["unit_spawned"] = trained in sovereign_globals.scene_objs
        STATE["checks"]["population_consumed"] = (
            after["population_used"] == before["population_used"] + 1
            and after["population_cap"] == before["population_cap"]
        )
        STATE["checks"]["rally_spawn"] = rally_distance(STATE["entities"]["barracks"], trained) <= 3.0
        pf.set_unit_selection([trained])
        _set_phase("done")


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
            _set_phase("production")
        return

    if STATE["phase"] == "production":
        _production_phase()
        return

    if STATE["phase"] == "done":
        if STATE["capture_proof"] and len(STATE["captures"]) < 2:
            _capture_visual("after")
        if all(STATE["checks"].values()):
            _succeed()
        _fail("production checks failed: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    STATE["output_dir"] = args.output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["capture_proof"] = args.capture_proof
    if not os.path.isdir(STATE["output_dir"]):
        os.makedirs(STATE["output_dir"])
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
