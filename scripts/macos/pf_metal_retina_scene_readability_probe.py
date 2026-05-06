import json
import math
import os
import struct
import subprocess
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import rts.globals
import rts.main as demo_main


PROBE_PATH = "/tmp/pf_metal_retina_scene_readability_probe.txt"
ERROR_PATH = "/tmp/pf_metal_retina_scene_readability_probe_error.txt"
DEFAULT_OUTPUT_DIR = "visual_parity_captures/retina-scene-readability-probe"
CAPTURE_SETTLE_TICKS = 70

SCENES = (
    {
        "name": "close_characters",
        "target": "friendly_cluster",
        "height": 92.0,
        "pitch": -58.0,
        "yaw": 135.0,
        "select_units": True,
    },
    {
        "name": "close_world_props",
        "target": "rocks_and_terrain",
        "height": 135.0,
        "pitch": -62.0,
        "yaw": 135.0,
        "select_units": False,
    },
    {
        "name": "wide_overview",
        "target": "battlefield_overview",
        "height": 640.0,
        "pitch": -65.0,
        "yaw": 135.0,
        "select_units": True,
        "fog_of_war": True,
    },
    {
        "name": "wide_world_revealed",
        "target": "full_world_overview",
        "height": 820.0,
        "pitch": -67.0,
        "yaw": 135.0,
        "select_units": False,
        "fog_of_war": False,
    },
)

STATE = {
    "phase": "init",
    "ticks": 0,
    "output_dir": None,
    "expected_backend": "METAL",
    "window_resolution": None,
    "captures": [],
    "camera": None,
    "scene_index": 0,
    "friendly_units": [],
    "targets": {},
}


def _arg_value(name, default=None):
    if name not in sys.argv:
        return default
    idx = sys.argv.index(name)
    if idx + 1 >= len(sys.argv):
        return default
    return sys.argv[idx + 1]


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    print("RETINA_SCENE_READABILITY_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_retina_scene_readability.json")


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
            ["/usr/bin/python3", checker, path, "--min-nonblack-ratio", "0.02"],
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
        subprocess.run(
            ["osascript", "-e", script],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=2.0,
        )
    except subprocess.TimeoutExpired:
        pass
    time.sleep(0.2)


def _capture(scene):
    path = os.path.join(
        STATE["output_dir"],
        "metal_retina_scene_{0}.png".format(scene["name"]),
    )
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
        _fail("screencapture failed for {0}".format(scene["name"]))

    width, height = _png_size(path)
    target = STATE["targets"][scene["target"]]
    camera = STATE["camera"]
    record = {
        "name": scene["name"],
        "path": path,
        "size": [width, height],
        "target": [target[0], target[1]],
        "camera_position": list(camera.position),
        "camera_direction": list(camera.direction),
        "height": scene["height"],
        "pitch": scene["pitch"],
        "yaw": scene["yaw"],
        "selected_units": len(pf.get_unit_selection()),
    }
    STATE["captures"].append(record)
    print("RETINA_SCENE_READABILITY_CAPTURE {0} {1} {2}x{3}".format(scene["name"], path, width, height))
    sys.stdout.flush()
    return path


def _write_summary(status, reason=None):
    capture_sizes = [record["size"] for record in STATE["captures"]]
    window_resolution = STATE["window_resolution"]
    highdpi = False
    if window_resolution and capture_sizes:
        highdpi = any(
            size[0] > int(window_resolution[0]) or size[1] > int(window_resolution[1])
            for size in capture_sizes
        )
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "window_resolution": window_resolution,
        "highdpi_capture": highdpi,
        "retina_scale": _retina_scale(capture_sizes, window_resolution),
        "targets": STATE["targets"],
        "friendly_unit_count": len(STATE["friendly_units"]),
        "captures": STATE["captures"],
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("RETINA_SCENE_READABILITY_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _retina_scale(capture_sizes, window_resolution):
    if not window_resolution or not capture_sizes:
        return None
    width = float(window_resolution[0])
    height = float(window_resolution[1])
    if width <= 0.0 or height <= 0.0:
        return None
    first = capture_sizes[0]
    return [first[0] / width, first[1] / height]


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("RETINA_SCENE_READABILITY_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    _write_summary("pass")
    highdpi = 0
    if STATE["window_resolution"]:
        for record in STATE["captures"]:
            size = record["size"]
            if size[0] > int(STATE["window_resolution"][0]) or size[1] > int(STATE["window_resolution"][1]):
                highdpi = 1
                break
    marker = (
        "RETINA_SCENE_READABILITY_PASS backend={backend} captures={captures} "
        "highdpi={highdpi} window={winw}x{winh}"
    ).format(
        backend=pf.get_render_info().get("backend"),
        captures=len(STATE["captures"]),
        highdpi=highdpi,
        winw=int(STATE["window_resolution"][0]) if STATE["window_resolution"] else 0,
        winh=int(STATE["window_resolution"][1]) if STATE["window_resolution"] else 0,
    )
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _ent_xz(ent):
    pos = ent.pos
    return (float(pos[0]), float(pos[2]))


def _distance(a, b):
    return math.sqrt((a[0] - b[0]) * (a[0] - b[0]) + (a[1] - b[1]) * (a[1] - b[1]))


def _average(points):
    if not points:
        _fail("cannot average empty point list")
    return (
        sum(point[0] for point in points) / float(len(points)),
        sum(point[1] for point in points) / float(len(points)),
    )


def _choose_friendly_units():
    units = [
        ent for ent in list(rts.globals.scene_objs)
        if getattr(ent, "faction_id", None) == 1
        and getattr(ent, "selectable", False)
        and hasattr(ent, "pos")
    ]
    if not units:
        _fail("no friendly selectable units found")
    return units


def _compute_targets(units):
    close_points = [_ent_xz(ent) for ent in units[:14]]
    cluster = _average(close_points)
    world_anchor = (52.0, -12.0)
    overview_anchor = _average([cluster, (0.0, -180.0), world_anchor])
    return {
        "friendly_cluster": cluster,
        "rocks_and_terrain": world_anchor,
        "battlefield_overview": overview_anchor,
        "full_world_overview": (0.0, -175.0),
    }


def _hide_probe_ui():
    for vc_name in ("demo_vc", "action_pad_vc"):
        vc = getattr(demo_main, vc_name, None)
        if vc is None:
            continue
        try:
            vc.deactivate()
        except Exception:
            pass


def _setup_camera():
    target = STATE["targets"]["friendly_cluster"]
    camera = pf.Camera(
        name="retina_scene_readability_camera",
        mode=pf.CAM_MODE_FREE,
        position=(target[0], 120.0, target[1]),
        pitch=-62.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    STATE["camera"] = camera


def _place_camera(scene):
    target = STATE["targets"][scene["target"]]
    camera = STATE["camera"]
    camera.position = (target[0], scene["height"], target[1])
    camera.pitch = scene["pitch"]
    camera.yaw = scene["yaw"]
    camera.center_over_location(target)
    if scene.get("fog_of_war", True):
        pf.enable_fog_of_war()
    else:
        pf.disable_fog_of_war()
    if scene["select_units"]:
        selection = STATE["friendly_units"][:14]
        pf.set_unit_selection(selection)
        pf.show_healthbars()
    else:
        pf.set_unit_selection([])
        pf.hide_healthbars()


def _start_scene(index):
    if index >= len(SCENES):
        _succeed()
    STATE["scene_index"] = index
    scene = SCENES[index]
    _place_camera(scene)
    _set_phase(scene["name"])


def _stage_probe():
    units = _choose_friendly_units()
    STATE["friendly_units"] = units
    STATE["targets"] = _compute_targets(units)
    _hide_probe_ui()
    pf.settings_set("pf.game.healthbar_mode", int(pf.HB_MODE_ALWAYS), persist=False)
    pf.set_minimap_render_all_ents(False)
    pf.set_simstate(pf.G_PAUSED_UI_RUNNING)
    STATE["window_resolution"] = list(pf.get_resolution())
    _setup_camera()


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _stage_probe()
        _start_scene(0)
        return

    scene = SCENES[STATE["scene_index"]]
    if STATE["ticks"] >= CAPTURE_SETTLE_TICKS:
        _capture(scene)
        _start_scene(STATE["scene_index"] + 1)


def main():
    output_dir = _arg_value(
        "--output-dir",
        os.environ.get("PF_RETINA_SCENE_READABILITY_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
    )
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = _arg_value(
        "--expect-backend",
        os.environ.get("PF_RETINA_SCENE_READABILITY_EXPECT_BACKEND", "METAL"),
    )

    demo_main.main()
    pf.register_ui_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
