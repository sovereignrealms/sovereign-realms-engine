import json
import os
import struct
import subprocess
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import common.constants as common_constants
import rts.constants as rts_constants
import rts.globals
import rts.main as demo_main


PROBE_PATH = "/tmp/pf_metal_runtime_ui_readability_probe.txt"
ERROR_PATH = "/tmp/pf_metal_runtime_ui_readability_probe_error.txt"
DEFAULT_OUTPUT_DIR = "visual_parity_captures/runtime-ui-readability-probe"
CAPTURE_SETTLE_TICKS = 60

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "output_dir": None,
    "expected_backend": "METAL",
    "captures": [],
    "window_resolution": None,
    "console_only": False,
    "console_ready_printed": False,
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
    STATE["phase_started_at"] = time.monotonic()
    print("RUNTIME_UI_READABILITY_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_runtime_ui_readability.json")


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
        subprocess.run(["osascript", "-e", script], stdout=subprocess.PIPE,
                       stderr=subprocess.PIPE, timeout=2.0)
    except subprocess.TimeoutExpired:
        pass


def _capture(name):
    path = os.path.join(STATE["output_dir"], "metal_runtime_ui_{0}.png".format(name))
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
    print("RUNTIME_UI_READABILITY_CAPTURE {0} {1} {2}x{3}".format(name, path, width, height))
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
        "captures": STATE["captures"],
        "highdpi_capture": highdpi,
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("RUNTIME_UI_READABILITY_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("RUNTIME_UI_READABILITY_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _choose_units():
    units = [
        ent for ent in list(rts.globals.scene_objs)
        if getattr(ent, "faction_id", None) == 1
        and getattr(ent, "selectable", False)
        and hasattr(ent, "pos")
    ]
    if not units:
        _fail("no friendly selectable units found")
    return units[:8]


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _stage_runtime_ui():
    units = _choose_units()
    pf.settings_set("pf.game.healthbar_mode", int(pf.HB_MODE_ALWAYS), persist=False)
    pf.show_healthbars()
    pf.set_unit_selection(units)
    pf.set_minimap_render_all_ents(False)
    pf.set_minimap_size(260)
    pf.set_minimap_position(1640.0, 880.0)
    pf.set_minimap_resize_mask(pf.ANCHOR_X_RIGHT | pf.ANCHOR_Y_BOT)
    pf.get_active_camera().center_over_location(_ent_xz(units[0]))
    pf.set_simstate(pf.G_PAUSED_UI_RUNNING)
    STATE["window_resolution"] = list(pf.get_resolution())


def _draw_probe_labels():
    pf.draw_text(
        "Retina runtime UI probe: HUD, minimap, healthbars, settings, session, console",
        (1080, 120, 1280, 42),
        (255, 255, 255, 255),
        (0, 0, 0, 255),
    )
    pf.draw_text(
        "High-DPI drawables should render text without compositor upscaling blur",
        (1080, 170, 1280, 42),
        (180, 220, 255, 255),
        (0, 0, 0, 255),
    )


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
        "RUNTIME_UI_READABILITY_PASS backend={backend} captures={captures} "
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


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1
    _draw_probe_labels()

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _stage_runtime_ui()
        if STATE["console_only"]:
            pf.show_console()
            _set_phase("console")
            return
        _set_phase("hud")
        return

    if STATE["console_only"] and STATE["phase"] == "console":
        if STATE["ticks"] >= CAPTURE_SETTLE_TICKS and not STATE["console_ready_printed"]:
            STATE["console_ready_printed"] = True
            print("RUNTIME_UI_READABILITY_CONSOLE_READY")
            sys.stdout.flush()
        return

    if STATE["phase"] == "hud" and STATE["ticks"] >= CAPTURE_SETTLE_TICKS:
        _capture("hud")
        pf.global_event(rts_constants.EVENT_SETTINGS_SHOW, None)
        _set_phase("settings")
        return

    if STATE["phase"] == "settings" and STATE["ticks"] >= CAPTURE_SETTLE_TICKS:
        _capture("settings")
        pf.global_event(common_constants.EVENT_SETTINGS_HIDE, None)
        pf.global_event(rts_constants.EVENT_SESSION_SHOW, None)
        _set_phase("session")
        return

    if STATE["phase"] == "session" and STATE["ticks"] >= CAPTURE_SETTLE_TICKS:
        _capture("session")
        pf.show_console()
        _set_phase("console")
        return

    if STATE["phase"] == "console" and STATE["ticks"] >= CAPTURE_SETTLE_TICKS:
        _capture("console")
        _succeed()


def main():
    output_dir = _arg_value(
        "--output-dir",
        os.environ.get("PF_RUNTIME_UI_READABILITY_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
    )
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = _arg_value(
        "--expect-backend",
        os.environ.get("PF_RUNTIME_UI_READABILITY_EXPECT_BACKEND", "METAL"),
    )
    STATE["console_only"] = (
        "--console-only" in sys.argv
        or os.environ.get("PF_RUNTIME_UI_READABILITY_CONSOLE_ONLY") == "1"
    )

    demo_main.main()
    pf.register_ui_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
