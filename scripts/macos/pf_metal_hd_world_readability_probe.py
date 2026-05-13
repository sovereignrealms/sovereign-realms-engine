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
from rts.units.berzerker import Berzerker
from rts.units.goblin import Goblin
from rts.units.knight import Knight
from rts.units.mage import Mage


PROBE_PATH = "/tmp/pf_metal_hd_world_readability_probe.txt"
ERROR_PATH = "/tmp/pf_metal_hd_world_readability_probe_error.txt"
SPRITE_STATS_PATH = "/tmp/pf_metal_hd_world_readability_sprite_stats.txt"
DEFAULT_OUTPUT_DIR = "visual_parity_captures/hd-world-readability-probe"
CAPTURE_SETTLE_TICKS = 75
METRIC_CROP_RATIOS = {
    "close_character_lod_target": 0.42,
    "close_character_team_readability": 0.42,
    "dense_army_readability": 0.58,
    "dense_forest_building_readability": 0.58,
    "vfx_combat_readability": 0.52,
    "wide_large_map_readability": 0.78,
    "wide_army_marked_readability": 0.78,
}

EXPECTED_SPRITE_SHEETS = set((
    "projectile_trail.png",
    "impact_burst.png",
    "fire_loop.png",
    "smoke_puff.png",
))

SCENES = (
    {
        "name": "close_character_lod_target",
        "target": "character_cluster",
        "height": 72.0,
        "pitch": -55.0,
        "yaw": 135.0,
        "fog_of_war": False,
        "selection": "heroes",
        "healthbars": False,
    },
    {
        "name": "close_character_team_readability",
        "target": "character_cluster",
        "height": 72.0,
        "pitch": -55.0,
        "yaw": 135.0,
        "fog_of_war": False,
        "selection": "heroes",
        "healthbars": True,
    },
    {
        "name": "dense_army_readability",
        "target": "army_cluster",
        "height": 210.0,
        "pitch": -62.0,
        "yaw": 135.0,
        "fog_of_war": False,
        "selection": "army",
        "healthbars": True,
    },
    {
        "name": "dense_forest_building_readability",
        "target": "forest_cluster",
        "height": 260.0,
        "pitch": -64.0,
        "yaw": 135.0,
        "fog_of_war": False,
        "selection": None,
        "healthbars": False,
    },
    {
        "name": "vfx_combat_readability",
        "target": "vfx_cluster",
        "height": 150.0,
        "pitch": -60.0,
        "yaw": 135.0,
        "fog_of_war": False,
        "selection": "combat",
        "healthbars": True,
        "spawn_vfx": True,
    },
    {
        "name": "wide_large_map_readability",
        "target": "wide_world",
        "height": 900.0,
        "pitch": -67.0,
        "yaw": 135.0,
        "fog_of_war": False,
        "selection": None,
        "healthbars": False,
    },
    {
        "name": "wide_army_marked_readability",
        "target": "wide_world",
        "height": 900.0,
        "pitch": -67.0,
        "yaw": 135.0,
        "fog_of_war": False,
        "selection": "friendly_army",
        "healthbars": False,
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
    "targets": {},
    "entities": [],
    "heroes": [],
    "army": [],
    "combat": [],
    "vfx_spawned": False,
    "sprite_stats": {},
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
    print("HD_WORLD_READABILITY_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_hd_world_readability.json")


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
        raise RuntimeError(
            "unsupported PNG format for metrics: bit_depth={0} color_type={1} interlace={2}".format(
                bit_depth, color_type, interlace))

    channels = 3 if color_type == 2 else 4
    bpp = channels
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
            left = recon[i - bpp] if i >= bpp else 0
            up = prev[i]
            up_left = prev[i - bpp] if i >= bpp else 0
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
                gx = abs(row[x + 1] - value)
                gy = abs(rows[y + 1][x] - value)
                gradients.append(gx + gy)

    mean = sum(values) / float(len(values)) if values else 0.0
    variance = sum((value - mean) * (value - mean) for value in values) / float(len(values)) if values else 0.0
    sorted_gradients = sorted(gradients)
    p95_idx = int(0.95 * (len(sorted_gradients) - 1)) if sorted_gradients else 0
    edge_threshold = 18
    edge_density = (
        sum(1 for gradient in gradients if gradient >= edge_threshold) / float(len(gradients))
        if gradients else 0.0
    )
    return {
        "crop_bounds": [x0, y0, crop_w, crop_h],
        "crop_ratio": crop_ratio,
        "luma_mean": round(mean, 3),
        "luma_stddev": round(math.sqrt(variance), 3),
        "edge_density": round(edge_density, 6),
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


def _capture(scene):
    path = os.path.join(STATE["output_dir"], "metal_hd_world_{0}.png".format(scene["name"]))
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
    camera = STATE["camera"]
    target = STATE["targets"][scene["target"]]
    crop_ratio = METRIC_CROP_RATIOS.get(scene["name"], 0.5)
    metrics = _image_metrics(path, crop_ratio)
    crop_path = os.path.join(
        STATE["output_dir"], "metal_hd_world_{0}_crop.png".format(scene["name"]))
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

    record = {
        "name": scene["name"],
        "path": path,
        "crop_path": crop_path,
        "size": [width, height],
        "target": [target[0], target[1]],
        "camera_position": list(camera.position),
        "camera_direction": list(camera.direction),
        "height": scene["height"],
        "pitch": scene["pitch"],
        "yaw": scene["yaw"],
        "selected_units": len(pf.get_unit_selection()),
        "fog_of_war": bool(scene.get("fog_of_war", False)),
        "readability_metrics": metrics,
    }
    STATE["captures"].append(record)
    print(
        "HD_WORLD_READABILITY_CAPTURE {0} {1} {2}x{3} edge_density={4:.4f} gradient_p95={5}".format(
            scene["name"], path, width, height, metrics["edge_density"], metrics["gradient_p95"]))
    sys.stdout.flush()
    return path


def _retina_scale(capture_sizes, window_resolution):
    if not window_resolution or not capture_sizes:
        return None
    width = float(window_resolution[0])
    height = float(window_resolution[1])
    if width <= 0.0 or height <= 0.0:
        return None
    first = capture_sizes[0]
    return [first[0] / width, first[1] / height]


def _read_sprite_stats():
    sheets = {}
    if not os.path.exists(SPRITE_STATS_PATH):
        return sheets
    with open(SPRITE_STATS_PATH, "r") as infile:
        for line in infile:
            for field in line.strip().split():
                if field.startswith("sheet="):
                    sheet = field.split("=", 1)[1]
                    sheets[sheet] = sheets.get(sheet, 0) + 1
                    break
    return sheets


def _capture_by_name(name):
    for record in STATE["captures"]:
        if record["name"] == name:
            return record
    return None


def _metric_delta(before_name, after_name):
    before = _capture_by_name(before_name)
    after = _capture_by_name(after_name)
    if before is None or after is None:
        return None
    before_metrics = before["readability_metrics"]
    after_metrics = after["readability_metrics"]
    fields = ("edge_density", "gradient_p95", "luma_stddev")
    deltas = {}
    for field in fields:
        deltas[field] = round(after_metrics[field] - before_metrics[field], 6)
    return {
        "before": before_name,
        "after": after_name,
        "selected_units_before": before["selected_units"],
        "selected_units_after": after["selected_units"],
        "metric_deltas": deltas,
    }


def _write_summary(status, reason=None):
    capture_sizes = [record["size"] for record in STATE["captures"]]
    window_resolution = STATE["window_resolution"]
    highdpi = False
    if window_resolution and capture_sizes:
        highdpi = any(
            size[0] > int(window_resolution[0]) or size[1] > int(window_resolution[1])
            for size in capture_sizes
        )
    STATE["sprite_stats"] = _read_sprite_stats()
    rule_deltas = []
    for before_name, after_name in (
        ("close_character_lod_target", "close_character_team_readability"),
        ("wide_large_map_readability", "wide_army_marked_readability"),
    ):
        delta = _metric_delta(before_name, after_name)
        if delta is not None:
            rule_deltas.append(delta)
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "window_resolution": window_resolution,
        "highdpi_capture": highdpi,
        "retina_scale": _retina_scale(capture_sizes, window_resolution),
        "targets": STATE["targets"],
        "staged_counts": {
            "entities": len(STATE["entities"]),
            "heroes": len(STATE["heroes"]),
            "army": len(STATE["army"]),
            "combat": len(STATE["combat"]),
        },
        "sprite_stats": STATE["sprite_stats"],
        "captures": STATE["captures"],
        "readability_contract": {
            "close_zoom": "center-crop detail metrics and crop image for character-level visual review",
            "wide_zoom": "large center-crop detail metrics and crop image for army/map readability review",
            "selection_markers": "player-owned selected units use a saturated blue marker and wider ring for close/wide readability",
            "retina": "capture dimensions must exceed logical window resolution on high-DPI displays",
            "note": "metrics are evidence gates for regression tracking, not proof of final HD/4K art quality",
        },
        "readability_rule_deltas": rule_deltas,
        "current_limitations": [
            "stock low-poly character meshes are readable but not HD/4K close-zoom quality",
            "team color is currently proven through selection/readability markers, not final unit material masks",
            "wide views show repeated terrain texture patterns and sparse biome variation",
            "dense vegetation/building readability needs asset density, LOD, and silhouette rules",
            "VFX fixture sheets prove the rendering path but are not final production-quality effects",
        ],
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("HD_WORLD_READABILITY_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("HD_WORLD_READABILITY_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    stats = _read_sprite_stats()
    missing = sorted(EXPECTED_SPRITE_SHEETS - set(stats.keys()))
    if missing:
        _fail("missing rendered VFX sheet(s): {0}".format(",".join(missing)))
    _write_summary("pass")
    highdpi = 0
    if STATE["window_resolution"]:
        for record in STATE["captures"]:
            size = record["size"]
            if size[0] > int(STATE["window_resolution"][0]) or size[1] > int(STATE["window_resolution"][1]):
                highdpi = 1
                break
    marker = (
        "HD_WORLD_READABILITY_PASS backend={backend} captures={captures} "
        "highdpi={highdpi} staged={staged} sprite_sheets={sheets}"
    ).format(
        backend=pf.get_render_info().get("backend"),
        captures=len(STATE["captures"]),
        highdpi=highdpi,
        staged=len(STATE["entities"]),
        sheets=",".join(sorted(stats.keys())),
    )
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _height(point):
    value = pf.map_height_at_point(point[0], point[1])
    return 0.0 if value is None else value


def _pathable_near(point, radius=3.25):
    offsets = (
        (0.0, 0.0), (4.0, 0.0), (-4.0, 0.0), (0.0, 4.0), (0.0, -4.0),
        (8.0, 8.0), (8.0, -8.0), (-8.0, 8.0), (-8.0, -8.0),
        (14.0, 0.0), (-14.0, 0.0), (0.0, 14.0), (0.0, -14.0),
    )
    for dx, dz in offsets:
        target = pf.map_nearest_pathable((point[0] + dx, point[1] + dz), radius=radius)
        if target is not None:
            return (float(target[0]), float(target[1]))
    return (float(point[0]), float(point[1]))


def _place(ent, point, radius=2.5, scale=None, selectable=False, faction_id=1):
    ent.pos = (float(point[0]), float(_height(point)), float(point[1]))
    ent.faction_id = faction_id
    ent.selection_radius = float(radius)
    try:
        ent.selectable = selectable
    except AttributeError:
        pass
    if scale is not None:
        ent.scale = scale
    STATE["entities"].append(ent)
    rts.globals.scene_objs.append(ent)
    return ent


def _grid(center, rows, cols, spacing):
    points = []
    x0 = center[0] - ((cols - 1) * spacing * 0.5)
    z0 = center[1] - ((rows - 1) * spacing * 0.5)
    for row in range(rows):
        for col in range(cols):
            points.append((x0 + col * spacing, z0 + row * spacing))
    return points


def _make_unit(kind, name, point, faction_id):
    if kind == "knight":
        ent = Knight("assets/models/knight", "knight.pfobj", name)
        return _place(ent, point, radius=3.25, scale=(0.8, 0.8, 0.8), selectable=True, faction_id=faction_id)
    if kind == "mage":
        ent = Mage("assets/models/mage", "mage.pfobj", name)
        return _place(ent, point, radius=4.25, scale=(0.6, 0.6, 0.6), selectable=True, faction_id=faction_id)
    if kind == "goblin":
        ent = Goblin("assets/models/goblin", "goblin.pfobj", name)
        return _place(ent, point, radius=3.0, scale=(0.9, 0.9, 0.9), selectable=True, faction_id=faction_id)
    ent = Berzerker("assets/models/berzerker", "berzerker.pfobj", name)
    return _place(ent, point, radius=3.0, scale=(0.8, 0.8, 0.8), selectable=True, faction_id=faction_id)


def _make_prop(path, pfobj, name, point, scale=(1.0, 1.0, 1.0), radius=3.0):
    ent = pf.Entity(path, pfobj, name)
    return _place(ent, point, radius=radius, scale=scale, selectable=False, faction_id=0)


def _stage_characters():
    center = STATE["targets"]["character_cluster"]
    kinds = ("knight", "knight", "mage", "goblin", "berzerker", "knight")
    offsets = ((-8.0, -3.0), (-4.0, 4.0), (0.0, 0.0), (4.0, 4.0), (8.0, -3.0), (12.0, 4.0))
    for idx, (kind, offset) in enumerate(zip(kinds, offsets)):
        point = _pathable_near((center[0] + offset[0], center[1] + offset[1]))
        STATE["heroes"].append(_make_unit(kind, "hd_probe_hero_{0}_{1}".format(kind, idx), point, 1))


def _stage_army():
    center = STATE["targets"]["army_cluster"]
    friendly_points = _grid((center[0] - 22.0, center[1] + 4.0), 4, 6, 6.0)
    enemy_points = _grid((center[0] + 24.0, center[1] - 2.0), 4, 6, 6.0)
    for idx, point in enumerate(friendly_points):
        kind = ("knight", "knight", "mage", "berzerker")[idx % 4]
        STATE["army"].append(_make_unit(kind, "hd_probe_friendly_{0}".format(idx), _pathable_near(point), 1))
    for idx, point in enumerate(enemy_points):
        kind = ("goblin", "berzerker", "goblin", "knight")[idx % 4]
        STATE["army"].append(_make_unit(kind, "hd_probe_enemy_{0}".format(idx), _pathable_near(point), 2))


def _stage_forest_and_buildings():
    center = STATE["targets"]["forest_cluster"]
    tree_specs = (
        ("assets/models/tree_basic", "tree_basic.pfobj", (3.0, 3.0, 3.0)),
        ("assets/models/oak_tree", "oak_tree.pfobj", (2.4, 2.4, 2.4)),
        ("assets/models/pine_tree", "pine_tree.pfobj", (3.0, 3.0, 3.0)),
        ("assets/models/large_tree", "large_tree.pfobj", (1.6, 1.6, 1.6)),
        ("assets/models/shrub", "shrub.pfobj", (2.0, 2.0, 2.0)),
        ("assets/models/bushes", "bush_1.pfobj", (2.5, 2.5, 2.5)),
    )
    for idx, point in enumerate(_grid((center[0] - 18.0, center[1] - 2.0), 5, 6, 9.0)):
        path, pfobj, scale = tree_specs[idx % len(tree_specs)]
        _make_prop(path, pfobj, "hd_probe_forest_{0}".format(idx), point, scale=scale, radius=3.0)

    prop_specs = (
        ("assets/models/tower", "tower.pfobj", (0.9, 0.9, 0.9)),
        ("assets/models/mage_tower", "mage_tower.pfobj", (0.9, 0.9, 0.9)),
        ("assets/models/war_banner", "war_banner.pfobj", (1.8, 1.8, 1.8)),
        ("assets/models/props", "wood_fence_1.pfobj", (2.0, 2.0, 2.0)),
        ("assets/models/props", "wood_fence_2.pfobj", (2.0, 2.0, 2.0)),
        ("assets/models/varied_rocks", "rock_3.pfobj", (3.0, 3.0, 3.0)),
    )
    for idx, point in enumerate(_grid((center[0] + 28.0, center[1] + 4.0), 2, 5, 11.0)):
        path, pfobj, scale = prop_specs[idx % len(prop_specs)]
        _make_prop(path, pfobj, "hd_probe_building_prop_{0}".format(idx), point, scale=scale, radius=3.0)


def _stage_combat_units():
    center = STATE["targets"]["vfx_cluster"]
    for idx, point in enumerate(_grid((center[0] - 12.0, center[1] + 2.0), 2, 3, 7.0)):
        STATE["combat"].append(_make_unit("mage", "hd_probe_combat_mage_{0}".format(idx), _pathable_near(point), 1))
    for idx, point in enumerate(_grid((center[0] + 14.0, center[1] - 2.0), 2, 4, 7.0)):
        STATE["combat"].append(_make_unit("goblin", "hd_probe_combat_goblin_{0}".format(idx), _pathable_near(point), 2))


def _spawn_vfx():
    if STATE["vfx_spawned"]:
        return
    center = STATE["targets"]["vfx_cluster"]
    height = _height(center)
    for idx, xoff in enumerate((-18.0, -10.0, -2.0, 6.0, 14.0)):
        pf.spawn_sprite_animated(
            ("projectile_trail.png", 1, 4, 4),
            (18.0, 6.0),
            (center[0] + xoff, height + 9.0 + (idx % 2) * 2.0, center[1] - 10.0 + idx * 4.0),
            12,
            90,
        )
    for idx, offset in enumerate(((4.0, -6.0), (12.0, 2.0), (20.0, 8.0))):
        pf.spawn_sprite_animated(
            ("impact_burst.png", 1, 4, 4),
            (13.0, 13.0),
            (center[0] + offset[0], height + 9.0, center[1] + offset[1]),
            10,
            90,
        )
    for idx, offset in enumerate(((10.0, -12.0), (22.0, 4.0), (4.0, 12.0))):
        pf.spawn_sprite_animated(
            ("fire_loop.png", 1, 4, 4),
            (11.0, 18.0),
            (center[0] + offset[0], height + 11.0, center[1] + offset[1]),
            8,
            120,
        )
    for idx, offset in enumerate(((14.0, -10.0), (26.0, 6.0), (8.0, 14.0))):
        pf.spawn_sprite_animated(
            ("smoke_puff.png", 1, 4, 4),
            (15.0, 15.0),
            (center[0] + offset[0], height + 17.0, center[1] + offset[1]),
            7,
            120,
        )
    STATE["vfx_spawned"] = True


def _hide_probe_ui():
    for vc_name in ("demo_vc", "action_pad_vc"):
        vc = getattr(demo_main, vc_name, None)
        if vc is None:
            continue
        try:
            vc.deactivate()
        except Exception:
            pass


def _setup_targets():
    STATE["targets"] = {
        "character_cluster": (56.0, -84.0),
        "army_cluster": (28.0, -126.0),
        "forest_cluster": (-116.0, -294.0),
        "vfx_cluster": (72.0, -92.0),
        "wide_world": (0.0, -175.0),
    }


def _setup_camera():
    target = STATE["targets"]["character_cluster"]
    camera = pf.Camera(
        name="hd_world_readability_camera",
        mode=pf.CAM_MODE_FREE,
        position=(target[0], 100.0, target[1]),
        pitch=-62.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    STATE["camera"] = camera


def _selection_for(scene):
    key = scene.get("selection")
    if key is None:
        return []
    if key == "heroes":
        return STATE["heroes"]
    if key == "army":
        return STATE["army"][:36]
    if key == "friendly_army":
        return [ent for ent in STATE["army"] if getattr(ent, "faction_id", None) == 1]
    if key == "combat":
        return STATE["combat"]
    return []


def _place_camera(scene):
    target = STATE["targets"][scene["target"]]
    camera = STATE["camera"]
    camera.position = (target[0], scene["height"], target[1])
    camera.pitch = scene["pitch"]
    camera.yaw = scene["yaw"]
    camera.center_over_location(target)
    if scene.get("fog_of_war", False):
        pf.enable_fog_of_war()
    else:
        pf.disable_fog_of_war()
    selection = _selection_for(scene)
    pf.set_unit_selection(selection)
    if scene.get("healthbars", False):
        pf.show_healthbars()
    else:
        pf.hide_healthbars()
    if scene.get("spawn_vfx", False):
        _spawn_vfx()


def _start_scene(index):
    if index >= len(SCENES):
        _succeed()
    STATE["scene_index"] = index
    scene = SCENES[index]
    _place_camera(scene)
    _set_phase(scene["name"])


def _stage_probe():
    _setup_targets()
    _hide_probe_ui()
    pf.disable_fog_of_war()
    pf.update_faction(1, "Sovereign Blue", (40, 90, 255, 255))
    pf.update_faction(2, "Sovereign Red", (220, 50, 50, 255))
    pf.settings_set("pf.game.healthbar_mode", int(pf.HB_MODE_ALWAYS), persist=False)
    pf.set_minimap_render_all_ents(False)
    pf.set_minimap_size(260)
    pf.set_simstate(pf.G_PAUSED_UI_RUNNING)
    STATE["window_resolution"] = list(pf.get_resolution())
    _setup_camera()
    _stage_characters()
    _stage_army()
    _stage_forest_and_buildings()
    _stage_combat_units()


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
        os.environ.get("PF_HD_WORLD_READABILITY_OUTPUT_DIR", DEFAULT_OUTPUT_DIR),
    )
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = _arg_value(
        "--expect-backend",
        os.environ.get("PF_HD_WORLD_READABILITY_EXPECT_BACKEND", "METAL"),
    )
    os.environ["PF_METAL_SPRITE_STATS_PATH"] = SPRITE_STATS_PATH
    try:
        os.unlink(SPRITE_STATS_PATH)
    except OSError:
        pass

    demo_main.main()
    pf.register_ui_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
