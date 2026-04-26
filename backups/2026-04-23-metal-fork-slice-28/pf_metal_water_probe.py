import math
import os
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import rts.globals
import rts.main as demo_main


PROBE_PATH = "/tmp/pf_metal_water_probe.txt"
ERROR_PATH = "/tmp/pf_metal_water_probe_error.txt"

STATE = {
    "phase": "init",
    "phase_started_at": None,
    "camera_start": None,
    "water_pos": None,
    "water_height": None,
}


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["phase_started_at"] = time.monotonic()
    print("METAL_WATER_PROBE_PHASE {0}".format(name))
    sys.stdout.flush()


def _phase_elapsed():
    return time.monotonic() - STATE["phase_started_at"]


def _fail(reason):
    _write(ERROR_PATH, str(reason))
    print("METAL_WATER_PROBE_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    water_pos = STATE["water_pos"]
    marker = (
        "METAL_WATER_PROBE_PASS backend={backend} "
        "water_x={water_x:.2f} water_z={water_z:.2f} water_h={water_h:.2f}"
    ).format(
        backend=pf.get_render_info().get("backend"),
        water_x=water_pos[0],
        water_z=water_pos[1],
        water_h=STATE["water_height"],
    )
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    quit_after = os.environ.get("PF_METAL_WATER_PROBE_AUTOQUIT", "1")
    if quit_after == "1":
        os._exit(0)


def _dist_xz(a, b):
    dx = a[0] - b[0]
    dz = a[1] - b[1]
    return math.sqrt(dx * dx + dz * dz)


def _scene_anchor_points():
    points = []
    for ent in list(rts.globals.scene_objs):
        try:
            pos = ent.pos
        except Exception:
            continue
        points.append((pos[0], pos[2]))
        if len(points) >= 64:
            break
    return points


def _find_water_point():
    for anchor in _scene_anchor_points():
        water = pf.map_nearest_pathable_water(anchor)
        if water is None:
            continue
        if not pf.map_pos_over_water(water[0], water[1]):
            continue
        height = pf.map_height_at_point(water[0], water[1])
        if height is None:
            continue
        return water, height
    return None, None


def on_update(user, event):
    del user
    del event

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if backend != "METAL":
            _fail("expected METAL backend, got {0}".format(backend))

        water_pos, water_height = _find_water_point()
        if water_pos is None:
            _fail("could not find water position")

        cam = pf.get_active_camera()
        STATE["camera_start"] = cam.position
        STATE["water_pos"] = water_pos
        STATE["water_height"] = water_height
        cam.center_over_location(water_pos)
        _set_phase("camera")
        return

    if STATE["phase"] == "camera":
        cam = pf.get_active_camera()
        start = STATE["camera_start"]
        curr = cam.position
        if _dist_xz((start[0], start[2]), (curr[0], curr[2])) > 5.0:
            _set_phase("stabilize")
            return
        if _phase_elapsed() > 4.0:
            _fail("camera did not move over water")

    if STATE["phase"] == "stabilize":
        if _phase_elapsed() > 1.0:
            _succeed()


demo_main.main()
pf.register_ui_event_handler(pf.EVENT_UPDATE_START, on_update, None)
