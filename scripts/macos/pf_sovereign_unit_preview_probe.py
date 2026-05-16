import argparse
import json
import math
import os
import struct
import subprocess
import sys
import time
import zlib

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import rts.globals
import rts.main as demo_main
from sovereign.data.readability import summarize_unit_readability
from sovereign.data.units import UNITS
from sovereign.entities.runtime import create_entity, place_entity


DEFAULT_OUTPUT_DIR = "qa-output/sovereign-unit-preview"
CAPTURE_SETTLE_TICKS = 60
ERROR_PATH = "/tmp/pf_sovereign_unit_preview_probe_error.txt"
PROBE_PATH = "/tmp/pf_sovereign_unit_preview_probe.txt"
POSES = ("Idle", "Walk", "Attack")

STATE = {
    "phase": "init",
    "ticks": 0,
    "output_dir": None,
    "expected_backend": "METAL",
    "window_resolution": None,
    "camera": None,
    "units": {},
    "unit_order": [],
    "scenes": [],
    "scene_index": 0,
    "captures": [],
    "asset_reports": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Capture Sovereign unit art/readability preview proofs.")
    parser.add_argument("--output-dir", default=os.environ.get("PF_SOVEREIGN_UNIT_PREVIEW_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))
    parser.add_argument("--expect-backend", default=os.environ.get("PF_SOVEREIGN_UNIT_PREVIEW_EXPECT_BACKEND", "METAL"))
    parser.add_argument(
        "--unit",
        action="append",
        choices=sorted(UNITS.keys()),
        help="Unit id to preview. Repeat for multiple units. Defaults to all units.",
    )
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    print("SOVEREIGN_UNIT_PREVIEW_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_unit_preview.json")


def _asset_path(unit):
    asset = unit["asset"]
    return os.path.join(pf.get_basedir(), asset["path"], asset["pfobj"])


def _available_animations(unit):
    path = _asset_path(unit)
    out = []
    try:
        with open(path, "r") as infile:
            for line in infile:
                parts = line.strip().split()
                if len(parts) >= 3 and parts[0] == "as":
                    out.append(parts[1])
    except IOError:
        pass
    return out


def _png_size(path):
    with open(path, "rb") as infile:
        header = infile.read(24)
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("not a PNG: {0}".format(path))
    return struct.unpack(">II", header[16:24])


def _paeth(a, b, c):
    p = a + b - c
    pa = abs(p - a)
    pb = abs(p - b)
    pc = abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def _png_luma_rows(path):
    with open(path, "rb") as infile:
        data = infile.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise RuntimeError("not a PNG: {0}".format(path))

    pos = 8
    width = height = bit_depth = color_type = interlace = None
    idat = []
    while pos < len(data):
        length = struct.unpack(">I", data[pos:pos + 4])[0]
        chunk_type = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + length]
        pos += 12 + length
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
        elif chunk_type == b"IDAT":
            idat.append(chunk)
        elif chunk_type == b"IEND":
            break

    if bit_depth != 8 or color_type not in (2, 6) or interlace != 0:
        raise RuntimeError("unsupported PNG format for metrics")

    channels = 3 if color_type == 2 else 4
    stride = width * channels
    raw = zlib.decompress(b"".join(idat))
    rows = []
    prev = [0] * stride
    src = 0
    for _ in range(height):
        filt = raw[src]
        src += 1
        scan = list(raw[src:src + stride])
        src += stride
        recon = [0] * stride
        for i, value in enumerate(scan):
            left = recon[i - channels] if i >= channels else 0
            up = prev[i]
            up_left = prev[i - channels] if i >= channels else 0
            if filt == 0:
                out = value
            elif filt == 1:
                out = value + left
            elif filt == 2:
                out = value + up
            elif filt == 3:
                out = value + ((left + up) >> 1)
            elif filt == 4:
                out = value + _paeth(left, up, up_left)
            else:
                raise RuntimeError("unsupported PNG filter {0}".format(filt))
            recon[i] = out & 0xff
        rows.append([
            int(0.2126 * recon[x] + 0.7152 * recon[x + 1] + 0.0722 * recon[x + 2])
            for x in range(0, stride, channels)
        ])
        prev = recon
    return width, height, rows


def _central_crop_bounds(width, height, ratio):
    crop_w = max(16, int(width * ratio))
    crop_h = max(16, int(height * ratio))
    x0 = max(0, (width - crop_w) // 2)
    y0 = max(0, (height - crop_h) // 2)
    return x0, y0, crop_w, crop_h


def _image_metrics(path, crop_ratio):
    width, height, rows = _png_luma_rows(path)
    x0, y0, crop_w, crop_h = _central_crop_bounds(width, height, crop_ratio)
    values = []
    gradients = []
    for y in range(y0, y0 + crop_h):
        row = rows[y]
        for x in range(x0, x0 + crop_w):
            value = row[x]
            values.append(value)
            if x + 1 < x0 + crop_w and y + 1 < y0 + crop_h:
                gradients.append(abs(row[x + 1] - value) + abs(rows[y + 1][x] - value))

    mean = sum(values) / float(len(values)) if values else 0.0
    variance = sum((value - mean) * (value - mean) for value in values) / float(len(values)) if values else 0.0
    sorted_gradients = sorted(gradients)
    p95_idx = int(0.95 * (len(sorted_gradients) - 1)) if sorted_gradients else 0
    edge_threshold = 18
    return {
        "crop_bounds": [x0, y0, crop_w, crop_h],
        "crop_ratio": crop_ratio,
        "luma_mean": round(mean, 3),
        "luma_stddev": round(math.sqrt(variance), 3),
        "edge_density": round(
            sum(1 for gradient in gradients if gradient >= edge_threshold) / float(len(gradients))
            if gradients else 0.0,
            6,
        ),
        "edge_threshold": edge_threshold,
        "gradient_p95": int(sorted_gradients[p95_idx]) if sorted_gradients else 0,
    }


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


def _height(point):
    value = pf.map_height_at_point(point[0], point[1])
    return 0.0 if value is None else value


def _pathable_near(point, radius=3.25):
    for dx, dz in ((0.0, 0.0), (6.0, 0.0), (-6.0, 0.0), (0.0, 6.0), (0.0, -6.0), (12.0, 0.0), (0.0, 12.0)):
        target = pf.map_nearest_pathable((point[0] + dx, point[1] + dz), radius=radius)
        if target is not None:
            return (float(target[0]), float(target[1]))
    return (float(point[0]), float(point[1]))


def _safe_anim(ent):
    try:
        return ent.get_anim()
    except Exception:
        return None


def _set_unit_pose(unit_id, pose):
    ent = STATE["units"][unit_id]
    target = (ent.pos[0] + 16.0, ent.pos[1], ent.pos[2] - 16.0)
    try:
        ent.face_towards(target)
    except Exception:
        pass
    if pose in STATE["asset_reports"][unit_id]["available_animations"]:
        try:
            ent.play_anim(pose)
        except Exception:
            pass


def _capture(scene):
    unit_id = scene["unit_id"]
    name = scene["name"]
    path = os.path.join(STATE["output_dir"], "unit_preview_{0}_{1}.png".format(unit_id, name))
    _activate_own_window()
    window_id = _capture_window_id()
    ok = False
    if window_id is not None:
        ok = _try_capture(["/usr/sbin/screencapture", "-x", "-o", "-l{0}".format(window_id), path], path)
    if not ok:
        ok = _try_capture(["/usr/sbin/screencapture", "-x", path], path)
    if not ok:
        _fail("screencapture failed for {0}".format(name))

    width, height = _png_size(path)
    crop_ratio = scene["crop_ratio"]
    metrics = _image_metrics(path, crop_ratio)
    crop_path = os.path.join(STATE["output_dir"], "unit_preview_{0}_{1}_crop.png".format(unit_id, name))
    bounds = metrics["crop_bounds"]
    subprocess.run(
        [
            "/usr/bin/sips",
            "-c", str(bounds[3]), str(bounds[2]),
            "--cropOffset", str(bounds[1]), str(bounds[0]),
            path,
            "--out", crop_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=10.0,
    )
    if not os.path.exists(crop_path) or not _png_nonblank(crop_path):
        crop_path = None

    ent = STATE["units"][unit_id]
    record = {
        "unit_id": unit_id,
        "name": name,
        "path": path,
        "crop_path": crop_path,
        "size": [width, height],
        "camera_position": list(STATE["camera"].position),
        "camera_direction": list(STATE["camera"].direction),
        "height": scene["height"],
        "pose": scene.get("pose"),
        "current_anim": _safe_anim(ent),
        "selected_units": len(pf.get_unit_selection()),
        "readability_metrics": metrics,
    }
    STATE["captures"].append(record)
    print(
        "SOVEREIGN_UNIT_PREVIEW_CAPTURE {0} {1} {2}x{3} edge_density={4:.4f} gradient_p95={5}".format(
            name, path, width, height, metrics["edge_density"], metrics["gradient_p95"]
        )
    )
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


def _write_summary(status, reason=None):
    capture_sizes = [record["size"] for record in STATE["captures"]]
    window_resolution = STATE["window_resolution"]
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "window_resolution": window_resolution,
        "retina_scale": _retina_scale(capture_sizes, window_resolution),
        "units": STATE["asset_reports"],
        "captures": STATE["captures"],
        "readability_summary": summarize_unit_readability(
            units=dict((unit_id, UNITS[unit_id]) for unit_id in STATE["unit_order"]),
            basedir=pf.get_basedir(),
        ),
        "contract": {
            "selection_markers": "neutral thin selected rings only",
            "world_team_color": "no broad dynamic world-material tinting",
            "purpose": "preview/intake evidence before production unit assets enter gameplay",
        },
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_UNIT_PREVIEW_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_UNIT_PREVIEW_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    _write_summary("pass")
    marker = "SOVEREIGN_UNIT_PREVIEW_PASS backend={0} units={1} captures={2}".format(
        pf.get_render_info().get("backend"),
        ",".join(STATE["unit_order"]),
        len(STATE["captures"]),
    )
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _hide_demo_ui():
    for vc_name in ("demo_vc", "action_pad_vc"):
        vc = getattr(demo_main, vc_name, None)
        if vc is None:
            continue
        try:
            vc.deactivate()
        except Exception:
            pass


def _stage_units():
    base = (132.0, -198.0)
    spacing = 70.0
    for idx, unit_id in enumerate(STATE["unit_order"]):
        definition = UNITS[unit_id]
        entry = {
            "kind": "unit",
            "id": unit_id,
            "name": "unit_preview_{0}".format(unit_id),
            "definition": definition,
        }
        ent = create_entity(entry)
        point = _pathable_near((base[0] + idx * spacing, base[1]), radius=definition.get("selection_radius", 2.5))
        place_entity(
            ent,
            point,
            faction_id=1,
            radius=definition.get("selection_radius", 2.5),
            scale=definition.get("scale"),
            selectable=True,
        )
        STATE["units"][unit_id] = ent
        rts.globals.scene_objs.append(ent)

        available = _available_animations(definition)
        declared = list(definition.get("animations", []))
        readability = definition.get("readability", {})
        STATE["asset_reports"][unit_id] = {
            "display_name": definition.get("display_name", unit_id),
            "asset_path": _asset_path(definition),
            "declared_animations": declared,
            "available_animations": available,
            "missing_declared_animations": [anim for anim in declared if anim not in available],
            "production_asset_status": (readability.get("production_asset") or {}).get("status"),
            "production_asset_notes": (readability.get("production_asset") or {}).get("notes"),
            "close_view": readability.get("close_view"),
            "far_view": readability.get("far_view"),
            "team_color": readability.get("team_color"),
            "position": [round(float(ent.pos[0]), 3), round(float(ent.pos[1]), 3), round(float(ent.pos[2]), 3)],
        }


def _build_scenes():
    scenes = []
    for unit_id in STATE["unit_order"]:
        ent = STATE["units"][unit_id]
        readability = UNITS[unit_id].get("readability", {})
        close_view = readability.get("close_view") or {}
        preferred = close_view.get("preferred_camera_height") or (72.0, 150.0)
        close_height = float(preferred[0])
        for pose in POSES:
            scenes.append({
                "unit_id": unit_id,
                "name": "close_{0}".format(pose.lower()),
                "pose": pose,
                "height": close_height,
                "pitch": -55.0,
                "yaw": 135.0,
                "crop_ratio": 0.42,
                "selection": True,
                "healthbars": False,
            })
        scenes.append({
            "unit_id": unit_id,
            "name": "wide_silhouette",
            "pose": "Idle",
            "height": 900.0,
            "pitch": -67.0,
            "yaw": 135.0,
            "crop_ratio": 0.54,
            "selection": False,
            "healthbars": False,
        })
        # Keep the unit centered after pathable placement, not the original target.
        STATE["asset_reports"][unit_id]["target"] = [float(ent.pos[0]), float(ent.pos[2])]
    STATE["scenes"] = scenes


def _setup_camera():
    unit = STATE["units"][STATE["unit_order"][0]]
    target = (unit.pos[0], unit.pos[2])
    camera = pf.Camera(
        name="sovereign_unit_preview_camera",
        mode=pf.CAM_MODE_FREE,
        position=(target[0], 100.0, target[1]),
        pitch=-62.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    STATE["camera"] = camera


def _place_camera(scene):
    ent = STATE["units"][scene["unit_id"]]
    target = (float(ent.pos[0]), float(ent.pos[2]))
    camera = STATE["camera"]
    camera.position = (target[0], scene["height"], target[1])
    camera.pitch = scene["pitch"]
    camera.yaw = scene["yaw"]
    camera.center_over_location(target)
    pf.disable_fog_of_war()
    if scene.get("selection"):
        pf.set_unit_selection([ent])
    else:
        pf.set_unit_selection([])
    if scene.get("healthbars"):
        pf.show_healthbars()
    else:
        pf.hide_healthbars()
    _set_unit_pose(scene["unit_id"], scene.get("pose"))


def _start_scene(index):
    if index >= len(STATE["scenes"]):
        _succeed()
    STATE["scene_index"] = index
    scene = STATE["scenes"][index]
    _place_camera(scene)
    _set_phase("{0}_{1}".format(scene["unit_id"], scene["name"]))


def _stage_probe():
    _hide_demo_ui()
    pf.disable_fog_of_war()
    pf.update_faction(1, "Sovereign Blue", (40, 90, 255, 255))
    pf.settings_set("pf.game.healthbar_mode", int(pf.HB_MODE_ALWAYS), persist=False)
    pf.set_minimap_render_all_ents(False)
    pf.set_simstate(pf.G_PAUSED_UI_RUNNING)
    STATE["window_resolution"] = list(pf.get_resolution())
    _stage_units()
    _setup_camera()
    _build_scenes()


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

    scene = STATE["scenes"][STATE["scene_index"]]
    if STATE["ticks"] >= CAPTURE_SETTLE_TICKS:
        _capture(scene)
        _start_scene(STATE["scene_index"] + 1)


def main():
    args = _parse_args()
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["unit_order"] = args.unit or sorted(UNITS.keys())

    demo_main.main()
    pf.register_ui_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
