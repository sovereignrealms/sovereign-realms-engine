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
from sovereign.scenario import build_runtime_scene, load_scenario, scenario_summary
from sovereign.systems.combat_rules import apply_damage


PROBE_PATH = "/tmp/pf_sovereign_ai_large_army_scale_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_large_army_scale_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "units_per_side": 80,
    "settle_ticks": 360,
    "soak_ticks": 300,
    "order_mode": "move",
    "budget_label": "baseline",
    "capture_proof": False,
    "wide_zoom_height": 900.0,
    "sample_budget_every": 30,
    "soft_budget_ms_per_tick": None,
    "hard_budget_ms_per_tick": None,
    "last_tick_at": None,
    "healthbars_visible": False,
    "checks": {
        "runtime_scene": False,
        "army_spawn": False,
        "movement_orders": False,
        "movement_activity": False,
        "animation_activity": False,
        "combat_damage": False,
        "sustained_ticks": False,
    },
    "runtime": {},
    "scale": {},
    "movement": {},
    "combat": {},
    "budget": {
        "phase_durations_sec": {},
        "phase_ticks": {},
        "tick_samples_ms": [],
        "tick_samples_by_phase": {},
        "tick_sample_records": [],
        "warnings": [],
    },
    "captures": [],
    "samples": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run a larger Sovereign AI-vs-player army scale soak.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-large-army-scale")
    parser.add_argument("--expect-backend", default="METAL")
    parser.add_argument("--units-per-side", type=int, default=80)
    parser.add_argument("--settle-ticks", type=int, default=360)
    parser.add_argument("--soak-ticks", type=int, default=300)
    parser.add_argument("--order-mode", choices=("move", "attack-move"), default="move")
    parser.add_argument("--budget-label", default="baseline")
    parser.add_argument("--capture-proof", action="store_true")
    parser.add_argument("--wide-zoom-height", type=float, default=900.0)
    parser.add_argument("--sample-budget-every", type=int, default=30)
    parser.add_argument("--soft-budget-ms-per-tick", type=float, default=None)
    parser.add_argument("--hard-budget-ms-per-tick", type=float, default=None)
    parser.add_argument("--clearpath-stats-path", default=None)
    parser.add_argument("--clearpath-fallback-remove-batch", type=int, default=None)
    parser.add_argument("--clearpath-fallback-batch-min-neighbours", type=int, default=None)
    parser.add_argument("--clearpath-fallback-max-removes", type=int, default=None)
    parser.add_argument("--clearpath-max-constraint-neighbours", type=int, default=None)
    parser.add_argument("--movement-stats-path", default=None)
    parser.add_argument("--movement-seek-clearpath-cadence", type=int, default=None)
    parser.add_argument("--movement-seek-clearpath-min-work-items", type=int, default=None)
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _record_phase_budget():
    started_at = STATE.get("phase_started_at")
    if started_at is None:
        return
    phase = STATE["phase"]
    STATE["budget"]["phase_durations_sec"][phase] = round(time.monotonic() - started_at, 3)
    STATE["budget"]["phase_ticks"][phase] = STATE["ticks"]


def _percentile(values, percentile):
    if not values:
        return None
    ordered = sorted(values)
    idx = int(math.ceil((float(percentile) / 100.0) * len(ordered))) - 1
    idx = max(0, min(len(ordered) - 1, idx))
    return round(ordered[idx], 3)


def _tick_sample_summary(values):
    if not values:
        return {
            "count": 0,
            "p50_ms": None,
            "p95_ms": None,
            "max_ms": None,
        }
    return {
        "count": len(values),
        "p50_ms": _percentile(values, 50),
        "p95_ms": _percentile(values, 95),
        "max_ms": round(max(values), 3),
    }


def _sample_tick_budget():
    now = time.monotonic()
    last = STATE.get("last_tick_at")
    STATE["last_tick_at"] = now
    if last is None:
        return
    sample_every = max(1, int(STATE.get("sample_budget_every") or 1))
    if STATE["ticks"] % sample_every != 0:
        return
    elapsed_ms = round((now - last) * 1000.0, 3)
    STATE["budget"]["tick_samples_ms"].append(elapsed_ms)
    phase = STATE["phase"]
    STATE["budget"]["tick_samples_by_phase"].setdefault(phase, []).append(elapsed_ms)
    STATE["budget"]["tick_sample_records"].append({
        "phase": phase,
        "phase_tick": STATE["ticks"],
        "sample_ms": elapsed_ms,
    })
    hard = STATE.get("hard_budget_ms_per_tick")
    if hard is not None and elapsed_ms > float(hard):
        _fail("hard budget exceeded: phase={0} sample_ms={1} threshold_ms={2}".format(
            phase,
            elapsed_ms,
            hard,
        ))


def _budget_warnings(overall, by_phase):
    warnings = list(STATE["budget"].get("warnings", []))
    soft = STATE.get("soft_budget_ms_per_tick")
    if soft is None:
        return warnings
    threshold = float(soft)
    if overall.get("p95_ms") is not None and overall["p95_ms"] > threshold:
        warnings.append("overall p95 tick budget {0}ms exceeds soft threshold {1}ms".format(
            overall["p95_ms"],
            threshold,
        ))
    for phase, summary in sorted(by_phase.items()):
        if summary.get("p95_ms") is not None and summary["p95_ms"] > threshold:
            warnings.append("{0} p95 tick budget {1}ms exceeds soft threshold {2}ms".format(
                phase,
                summary["p95_ms"],
                threshold,
            ))
    return warnings


def _set_phase(name):
    _record_phase_budget()
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    if STATE.get("output_dir"):
        _write_progress("phase:{0}".format(name))
    print("SOVEREIGN_AI_LARGE_ARMY_SCALE_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_large_army_scale.json")


def _progress_path():
    return os.path.join(STATE["output_dir"], "progress_sovereign_ai_large_army_scale.json")


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


def _capture_proof(name):
    if not STATE.get("capture_proof"):
        return None
    path = os.path.join(STATE["output_dir"], "sovereign_large_army_{0}.png".format(name))
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
    camera = pf.get_active_camera()
    player_units = STATE["scale"].get("player_units", [])
    enemy_units = STATE["scale"].get("enemy_units", [])
    record = {
        "name": name,
        "path": path,
        "size": [width, height],
        "phase": STATE["phase"],
        "ticks": STATE["ticks"],
        "camera_position": list(camera.position),
        "camera_direction": list(camera.direction),
        "selected_units": len(pf.get_unit_selection()),
        "healthbars_visible": bool(STATE.get("healthbars_visible", False)),
        "player_live_count": len([ent for ent in player_units if _is_live(ent)]),
        "enemy_live_count": len([ent for ent in enemy_units if _is_live(ent)]),
        "total_live_count": len([ent for ent in player_units + enemy_units if _is_live(ent)]),
    }
    STATE["captures"].append(record)
    print("SOVEREIGN_AI_LARGE_ARMY_SCALE_CAPTURE {0} {1} {2}x{3}".format(name, path, width, height))
    sys.stdout.flush()
    return record


def _place_wide_zoom_camera():
    camera = pf.get_active_camera()
    target = (106.0, 94.0)
    camera.position = (target[0], float(STATE["wide_zoom_height"]), target[1] + 12.0)
    camera.pitch = -67.0
    camera.yaw = 135.0
    camera.center_over_location(target)


def _ent_xz(ent):
    pos = ent.pos
    return (float(pos[0]), float(pos[2]))


def _dist(a, b):
    dx = float(a[0]) - float(b[0])
    dz = float(a[1]) - float(b[1])
    return math.sqrt(dx * dx + dz * dz)


def _centroid(points):
    if not points:
        return None
    return (
        sum(point[0] for point in points) / float(len(points)),
        sum(point[1] for point in points) / float(len(points)),
    )


def _spread(points, center):
    if not points or center is None:
        return 0.0
    return sum(_dist(point, center) for point in points) / float(len(points))


def _is_live(ent):
    try:
        if bool(ent.zombie):
            return False
    except (AttributeError, RuntimeError):
        pass
    try:
        return int(ent.hp) > 0
    except (AttributeError, RuntimeError):
        return True


def _snapshot_unit(ent):
    payload = {
        "name": getattr(ent, "name", None),
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


def _compact_counts():
    player_units = STATE["scale"].get("player_units", [])
    enemy_units = STATE["scale"].get("enemy_units", [])
    payload = {
        "phase": STATE["phase"],
        "ticks": STATE["ticks"],
        "phase_log": list(STATE["phase_log"]),
        "order_mode": STATE["order_mode"],
        "budget": _budget_snapshot(),
        "checks": dict(STATE["checks"]),
        "player_count": len(player_units),
        "enemy_count": len(enemy_units),
        "player_live_count": len([ent for ent in player_units if _is_live(ent)]),
        "enemy_live_count": len([ent for ent in enemy_units if _is_live(ent)]),
        "elapsed_wall_sec": round(
            time.monotonic() - STATE["scale"].get("started_wall_time", time.monotonic()),
            3,
        ),
    }
    if STATE["movement"]:
        payload["movement"] = {
            key: STATE["movement"].get(key)
            for key in (
                "moved_count",
                "average_travel",
                "max_travel",
                "active_animation_count",
                "animation_counts",
                "order_error_count",
            )
            if key in STATE["movement"]
        }
    if STATE["combat"]:
        payload["combat"] = {
            key: STATE["combat"].get(key)
            for key in (
                "target_name",
                "target_hp_start",
                "target_hp_after_sample_damage",
                "engine_damaged_unit_count",
                "player_live_count",
                "enemy_live_count",
            )
            if key in STATE["combat"]
        }
    return payload


def _budget_snapshot():
    elapsed = round(
        time.monotonic() - STATE["scale"].get("started_wall_time", time.monotonic()),
        3,
    )
    total_units = int(STATE["scale"].get("total_units", 0))
    requested_ticks = int(STATE["settle_ticks"] + STATE["soak_ticks"])
    completed_ticks = int(sum(STATE["budget"].get("phase_ticks", {}).values()))
    if STATE["phase"] in ("engage_settle", "sustained_soak"):
        completed_ticks += int(STATE["ticks"])
    wall_ms_per_requested_tick = None
    sim_ticks_per_wall_sec = None
    if elapsed > 0.0:
        wall_ms_per_requested_tick = round((elapsed * 1000.0) / max(1, requested_ticks), 3)
        sim_ticks_per_wall_sec = round(float(completed_ticks) / elapsed, 3)
    wall_sec_per_100_units = None
    if total_units > 0:
        wall_sec_per_100_units = round(elapsed / (float(total_units) / 100.0), 3)
    tick_samples = list(STATE["budget"].get("tick_samples_ms", []))
    tick_summary = _tick_sample_summary(tick_samples)
    phase_tick_summary = {
        phase: _tick_sample_summary(values)
        for phase, values in STATE["budget"].get("tick_samples_by_phase", {}).items()
    }
    warnings = _budget_warnings(tick_summary, phase_tick_summary)
    return {
        "label": STATE["budget_label"],
        "elapsed_wall_sec": elapsed,
        "requested_ticks": requested_ticks,
        "completed_ticks": completed_ticks,
        "wall_ms_per_requested_tick": wall_ms_per_requested_tick,
        "sim_ticks_per_wall_sec": sim_ticks_per_wall_sec,
        "wall_sec_per_100_units": wall_sec_per_100_units,
        "sample_budget_every": STATE["sample_budget_every"],
        "soft_budget_ms_per_tick": STATE["soft_budget_ms_per_tick"],
        "hard_budget_ms_per_tick": STATE["hard_budget_ms_per_tick"],
        "tick_sample_summary": tick_summary,
        "phase_tick_sample_summary": phase_tick_summary,
        "tick_sample_records": list(STATE["budget"].get("tick_sample_records", [])),
        "warnings": warnings,
        "phase_durations_sec": dict(STATE["budget"].get("phase_durations_sec", {})),
        "phase_ticks": dict(STATE["budget"].get("phase_ticks", {})),
    }


def _write_progress(note):
    payload = _compact_counts()
    payload["note"] = note
    with open(_progress_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")


def _flush_clearpath_stats():
    path = os.environ.get("PF_CLEARPATH_STATS_PATH")
    if not path:
        return None

    payload = {"path": path}
    try:
        writer = getattr(pf, "debug_write_clearpath_stats", None)
        if writer:
            writer()
        else:
            payload["error"] = "pf.debug_write_clearpath_stats unavailable"
    except Exception as exc:
        payload["error"] = str(exc)

    if os.path.exists(path):
        try:
            with open(path) as infile:
                payload["stats"] = json.load(infile)
        except Exception as exc:
            payload["load_error"] = str(exc)
    return payload


def _flush_movement_stats():
    path = os.environ.get("PF_MOVEMENT_STATS_PATH")
    if not path:
        return None

    payload = {"path": path}
    try:
        writer = getattr(pf, "debug_write_movement_stats", None)
        if writer:
            writer()
        else:
            payload["error"] = "pf.debug_write_movement_stats unavailable"
    except Exception as exc:
        payload["error"] = str(exc)

    if os.path.exists(path):
        try:
            with open(path) as infile:
                payload["stats"] = json.load(infile)
        except Exception as exc:
            payload["load_error"] = str(exc)
    return payload


def _write_summary(status, reason=None):
    _record_phase_budget()
    clearpath_stats = _flush_clearpath_stats()
    movement_stats = _flush_movement_stats()
    player_units = STATE["scale"].get("player_units", [])
    enemy_units = STATE["scale"].get("enemy_units", [])
    movement = dict(STATE["movement"])
    before = dict(movement.get("before", {}))
    if before:
        movement["before_sample_count"] = len(before)
        movement["before"] = {
            key: before[key]
            for key in sorted(before.keys())[:12]
        }
    payload = {
        "status": status,
        "reason": reason,
        "failure_class": _failure_class(reason) if status == "fail" else None,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "runtime": STATE["runtime"],
        "scale": {
            key: value
            for key, value in STATE["scale"].items()
            if key not in ("player_units", "enemy_units")
        },
        "movement": movement,
        "combat": STATE["combat"],
        "order_mode": STATE["order_mode"],
        "budget": _budget_snapshot(),
        "captures": STATE["captures"],
        "capture_proof": bool(STATE["capture_proof"]),
        "wide_zoom_height": STATE["wide_zoom_height"],
        "samples": {
            "player": [_snapshot_unit(ent) for ent in player_units[:8]],
            "enemy": [_snapshot_unit(ent) for ent in enemy_units[:8]],
        },
    }
    if clearpath_stats:
        payload["clearpath_stats"] = clearpath_stats
    if movement_stats:
        payload["movement_stats"] = movement_stats
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    _write_progress(status)
    print("SOVEREIGN_AI_LARGE_ARMY_SCALE_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _failure_class(reason):
    text = str(reason or "").lower()
    if STATE["phase"] == "init" or not STATE["checks"].get("runtime_scene"):
        return "spawn_setup"
    if "movement" in text or not STATE["checks"].get("movement_orders"):
        return "movement_orders"
    if "projectile" in text or "velocity" in text or "assert" in text:
        return "projectile_combat"
    if "animation" in text or not STATE["checks"].get("animation_activity"):
        return "animation_rendering"
    if "budget" in text:
        return "wall_clock_budget"
    if "screencapture" in text or "capture" in text:
        return "capture_io"
    if not STATE["checks"].get("combat_damage"):
        return "projectile_combat"
    return "unknown"


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_LARGE_ARMY_SCALE_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime={runtime} spawn={spawn} "
        "orders={orders} motion={motion} anim={anim} combat={combat} sustain={sustain} "
        "units_per_side={units_per_side} total_units={total_units}"
    ).format(
        runtime=int(STATE["checks"]["runtime_scene"]),
        spawn=int(STATE["checks"]["army_spawn"]),
        orders=int(STATE["checks"]["movement_orders"]),
        motion=int(STATE["checks"]["movement_activity"]),
        anim=int(STATE["checks"]["animation_activity"]),
        combat=int(STATE["checks"]["combat_damage"]),
        sustain=int(STATE["checks"]["sustained_ticks"]),
        units_per_side=int(STATE["units_per_side"]),
        total_units=int(STATE["scale"].get("total_units", 0)),
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _setup_render_state():
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    try:
        pf.hide_healthbars()
        STATE["healthbars_visible"] = False
    except AttributeError:
        STATE["healthbars_visible"] = False
    center = (106.0, 94.0)
    camera = pf.Camera(
        name="sovereign_ai_large_army_scale_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 168.0, center[1] + 12.0),
        pitch=-62.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_large_army_scale_region",
            position=center,
            dimensions=(160.0, 128.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _formation_point(anchor, idx, cols, spacing, x_sign=1.0, z_sign=1.0):
    row = idx // cols
    col = idx % cols
    return (
        float(anchor[0]) + float(x_sign) * float(col) * spacing,
        float(anchor[1]) + float(z_sign) * float(row) * spacing,
    )


def _unit_id_for(idx):
    if idx % 4 == 0:
        return "archer"
    return "militia"


def _create_unit(scene_objs, player_state, unit_id, name, point, faction_id):
    definition = UNITS[unit_id]
    ent = create_entity({
        "kind": "unit",
        "id": unit_id,
        "name": name,
        "definition": definition,
    })
    place_entity(
        ent,
        point,
        faction_id=faction_id,
        radius=definition.get("selection_radius", 2.5),
        scale=definition.get("scale"),
    )
    scene_objs.append(ent)
    player_state.add_unit(unit_id, ent)
    return ent


def _create_army(scene_objs, player_state, prefix, faction_id, anchor, x_sign, z_sign):
    units = []
    count = int(STATE["units_per_side"])
    cols = max(8, int(math.ceil(math.sqrt(count) * 1.25)))
    spacing = 2.8
    for idx in range(count):
        unit_id = _unit_id_for(idx)
        point = _formation_point(anchor, idx, cols, spacing, x_sign=x_sign, z_sign=z_sign)
        units.append(_create_unit(
            scene_objs,
            player_state,
            unit_id,
            "{0}_{1}_{2}".format(prefix, unit_id, idx + 1),
            point,
            faction_id,
        ))
    return units


def _army_snapshot(units):
    return {
        "count": len(units),
        "live_count": len([ent for ent in units if _is_live(ent)]),
        "archers": len([ent for ent in units if "archer" in getattr(ent, "name", "")]),
        "militia": len([ent for ent in units if "militia" in getattr(ent, "name", "")]),
        "sample_positions": [_ent_xz(ent) for ent in units[:8]],
    }


def _setup_scene():
    scenario = load_scenario(os.path.join(pf.get_basedir(), "assets/sovereign/scenarios/two_player_skirmish.json"))
    scene_objs = []
    sovereign_globals.scene_objs = scene_objs
    runtime = build_runtime_scene(scenario, scene_objs=scene_objs)
    _setup_render_state()

    player_state = runtime["players"][1]["state"]
    enemy_state = runtime["players"][2]["state"]
    player_state.population_cap = max(player_state.population_cap, STATE["units_per_side"] + 24)
    enemy_state.population_cap = max(enemy_state.population_cap, STATE["units_per_side"] + 24)
    player_state.resources.update({"food": 5000, "wood": 5000, "gold": 5000, "stone": 1000})
    enemy_state.resources.update({"food": 5000, "wood": 5000, "gold": 5000, "stone": 1000})

    player_units = _create_army(scene_objs, player_state, "player_scale", 1, (58.0, 72.0), 1.0, 1.0)
    enemy_units = _create_army(scene_objs, enemy_state, "enemy_scale", 2, (154.0, 118.0), -1.0, -1.0)
    STATE["scale"].update({
        "runtime_scene_obj_count": len(scene_objs),
        "player_units": player_units,
        "enemy_units": enemy_units,
        "player_army": _army_snapshot(player_units),
        "enemy_army": _army_snapshot(enemy_units),
        "total_units": len(player_units) + len(enemy_units),
        "player_state": player_state.snapshot(),
        "enemy_state": enemy_state.snapshot(),
    })
    STATE["runtime"] = scenario_summary(runtime)
    STATE["checks"]["runtime_scene"] = len(runtime["players"]) == 2 and len(scene_objs) >= STATE["units_per_side"] * 2
    STATE["checks"]["army_spawn"] = len(player_units) == STATE["units_per_side"] and len(enemy_units) == STATE["units_per_side"]
    _write_progress("scene_setup")
    _capture_proof("before_orders")


def _issue_movement_orders():
    player_units = STATE["scale"]["player_units"]
    enemy_units = STATE["scale"]["enemy_units"]
    errors = []
    before = {}
    for ent in player_units + enemy_units:
        before[getattr(ent, "name", str(id(ent)))] = _ent_xz(ent)

    player_cols = max(8, int(math.ceil(math.sqrt(len(player_units)) * 1.25)))
    enemy_cols = max(8, int(math.ceil(math.sqrt(len(enemy_units)) * 1.25)))
    for idx, ent in enumerate(player_units):
        row = idx // player_cols
        target_xz = (118.0 + float(idx % player_cols) * 0.8, 104.0 + float(row) * 0.35)
        try:
            ent.face_towards((target_xz[0], ent.pos[1], target_xz[1]))
            if STATE["order_mode"] == "attack-move":
                ent.attack(target_xz)
            else:
                ent.move(target_xz)
        except (AttributeError, RuntimeError) as exc:
            errors.append("{0}: {1}".format(getattr(ent, "name", "player"), exc))
    for idx, ent in enumerate(enemy_units):
        row = idx // enemy_cols
        target_xz = (94.0 - float(idx % enemy_cols) * 0.8, 86.0 - float(row) * 0.35)
        try:
            ent.face_towards((target_xz[0], ent.pos[1], target_xz[1]))
            if STATE["order_mode"] == "attack-move":
                ent.attack(target_xz)
            else:
                ent.move(target_xz)
        except (AttributeError, RuntimeError) as exc:
            errors.append("{0}: {1}".format(getattr(ent, "name", "enemy"), exc))

    STATE["movement"]["before"] = before
    STATE["movement"]["order_errors"] = errors[:12]
    STATE["movement"]["order_error_count"] = len(errors)
    STATE["checks"]["movement_orders"] = len(errors) == 0
    _write_progress("movement_orders")


def _hold_all_units():
    held = 0
    errors = []
    for ent in STATE["scale"].get("player_units", []) + STATE["scale"].get("enemy_units", []):
        if not _is_live(ent):
            continue
        try:
            ent.hold_position()
            held += 1
        except (AttributeError, RuntimeError) as exc:
            errors.append("{0}: {1}".format(getattr(ent, "name", "unit"), exc))
    STATE["movement"]["hold_count"] = held
    STATE["movement"]["hold_error_count"] = len(errors)
    STATE["movement"]["hold_errors"] = errors[:12]
    _write_progress("hold_after_sample")


def _sample_motion_and_combat():
    player_units = STATE["scale"]["player_units"]
    enemy_units = STATE["scale"]["enemy_units"]
    before = STATE["movement"]["before"]
    travel = []
    travel_by_name = {}
    anim_counts = {}
    idle_live = 0
    for ent in player_units + enemy_units:
        name = getattr(ent, "name", str(id(ent)))
        pos = _ent_xz(ent)
        curr_travel = _dist(before.get(name, pos), pos)
        travel.append(curr_travel)
        travel_by_name[name] = curr_travel
        try:
            anim = ent.get_anim()
        except (AttributeError, RuntimeError):
            anim = None
        anim_counts[anim] = anim_counts.get(anim, 0) + 1
        if _is_live(ent) and curr_travel <= 0.25 and anim in (None, "Idle"):
            idle_live += 1

    player_start = [before.get(getattr(ent, "name", str(id(ent))), _ent_xz(ent)) for ent in player_units]
    enemy_start = [before.get(getattr(ent, "name", str(id(ent))), _ent_xz(ent)) for ent in enemy_units]
    player_live = [ent for ent in player_units if _is_live(ent)]
    enemy_live = [ent for ent in enemy_units if _is_live(ent)]
    player_now = [_ent_xz(ent) for ent in player_live]
    enemy_now = [_ent_xz(ent) for ent in enemy_live]
    player_start_center = _centroid(player_start)
    enemy_start_center = _centroid(enemy_start)
    player_center = _centroid(player_now)
    enemy_center = _centroid(enemy_now)
    start_separation = _dist(player_start_center, enemy_start_center)
    end_separation = _dist(player_center, enemy_center) if player_center and enemy_center else None

    moved = [value for value in travel if value > 0.25]
    average_travel = sum(travel) / float(len(travel)) if travel else 0.0
    active_anims = anim_counts.get("Walk", 0) + anim_counts.get("Attack", 0)
    STATE["movement"].update({
        "moved_count": len(moved),
        "average_travel": round(average_travel, 3),
        "max_travel": round(max(travel) if travel else 0.0, 3),
        "active_animation_count": active_anims,
        "animation_counts": anim_counts,
        "idle_live_count": idle_live,
        "flow": {
            "player_start_centroid": [round(value, 3) for value in player_start_center],
            "enemy_start_centroid": [round(value, 3) for value in enemy_start_center],
            "player_centroid": [round(value, 3) for value in player_center] if player_center else None,
            "enemy_centroid": [round(value, 3) for value in enemy_center] if enemy_center else None,
            "start_center_separation": round(start_separation, 3),
            "end_center_separation": round(end_separation, 3) if end_separation is not None else None,
            "center_closing_distance": round(start_separation - end_separation, 3) if end_separation is not None else None,
            "player_spread": round(_spread(player_now, player_center), 3),
            "enemy_spread": round(_spread(enemy_now, enemy_center), 3),
            "idle_live_count": idle_live,
        },
    })
    STATE["checks"]["movement_activity"] = (
        len(moved) >= int(STATE["units_per_side"] * 0.50)
        and average_travel > 0.20
    )
    STATE["checks"]["animation_activity"] = active_anims >= int(STATE["units_per_side"] * 0.25)

    target = next((ent for ent in player_units if _is_live(ent)), None)
    attackers = [ent for ent in enemy_units if _is_live(ent)][:8]
    if target is None or not attackers:
        _fail("large army scale probe lost all representative combat units")

    start_hp = int(target.hp)
    events = []
    for attacker in attackers:
        try:
            attacker.face_towards(target.pos)
            attacker.play_anim("Attack")
        except (AttributeError, RuntimeError):
            pass
        unit_id = "archer" if "archer" in getattr(attacker, "name", "") else "militia"
        events.append(apply_damage(unit_id, "militia", target))
    end_hp = int(target.hp)
    engine_damaged = 0
    for ent in player_units + enemy_units:
        try:
            if int(ent.hp) < int(ent.max_hp):
                engine_damaged += 1
        except (AttributeError, RuntimeError):
            pass
    STATE["combat"] = {
        "target_name": getattr(target, "name", None),
        "target_hp_start": start_hp,
        "target_hp_after_sample_damage": end_hp,
        "sample_damage_events": events,
        "engine_damaged_unit_count": engine_damaged,
        "player_live_count": len([ent for ent in player_units if _is_live(ent)]),
        "enemy_live_count": len([ent for ent in enemy_units if _is_live(ent)]),
    }
    STATE["checks"]["combat_damage"] = end_hp < start_hp or engine_damaged > 0
    _write_progress("movement_and_combat_sample")
    _capture_proof("engage_sample")
    _hold_all_units()
    _set_phase("sustained_soak")


def _finish_soak():
    player_units = STATE["scale"]["player_units"]
    enemy_units = STATE["scale"]["enemy_units"]
    STATE["checks"]["sustained_ticks"] = True
    STATE["scale"]["player_army_after_soak"] = _army_snapshot(player_units)
    STATE["scale"]["enemy_army_after_soak"] = _army_snapshot(enemy_units)
    STATE["scale"]["elapsed_wall_sec"] = round(time.monotonic() - STATE["scale"]["started_wall_time"], 3)
    _capture_proof("sustained_soak")
    _place_wide_zoom_camera()
    _capture_proof("wide_zoom")
    _write_progress("finish_soak")
    if all(STATE["checks"].values()):
        _succeed()
        return
    _fail("large army scale checks did not all pass: {0}".format(STATE["checks"]))


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1
    _sample_tick_budget()

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        STATE["scale"]["started_wall_time"] = time.monotonic()
        _setup_scene()
        _issue_movement_orders()
        _set_phase("engage_settle")
        return

    if STATE["phase"] == "engage_settle" and STATE["ticks"] >= STATE["settle_ticks"]:
        _sample_motion_and_combat()
        return

    if STATE["phase"] == "sustained_soak" and STATE["ticks"] >= STATE["soak_ticks"]:
        _finish_soak()
        return

    if STATE["phase"] == "sustained_soak" and STATE["ticks"] % 30 == 0:
        _write_progress("sustained_tick")


def main():
    args = _parse_args()
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["units_per_side"] = max(32, int(args.units_per_side))
    STATE["settle_ticks"] = max(120, int(args.settle_ticks))
    STATE["soak_ticks"] = max(120, int(args.soak_ticks))
    STATE["order_mode"] = args.order_mode
    STATE["budget_label"] = args.budget_label
    STATE["capture_proof"] = bool(args.capture_proof)
    STATE["wide_zoom_height"] = max(300.0, float(args.wide_zoom_height))
    STATE["sample_budget_every"] = max(1, int(args.sample_budget_every))
    STATE["soft_budget_ms_per_tick"] = args.soft_budget_ms_per_tick
    STATE["hard_budget_ms_per_tick"] = args.hard_budget_ms_per_tick
    STATE["phase_started_at"] = time.monotonic()
    STATE["last_tick_at"] = None
    if args.clearpath_stats_path:
        stats_path = args.clearpath_stats_path
        if not os.path.isabs(stats_path):
            stats_path = os.path.join(pf.get_basedir(), stats_path)
        stats_dir = os.path.dirname(stats_path)
        if stats_dir and not os.path.isdir(stats_dir):
            os.makedirs(stats_dir)
        os.environ["PF_CLEARPATH_STATS_PATH"] = stats_path
    if args.clearpath_fallback_remove_batch is not None:
        os.environ["PF_CLEARPATH_FALLBACK_REMOVE_BATCH"] = str(
            max(1, int(args.clearpath_fallback_remove_batch)))
    if args.clearpath_fallback_batch_min_neighbours is not None:
        os.environ["PF_CLEARPATH_FALLBACK_BATCH_MIN_NEIGHBOURS"] = str(
            max(0, int(args.clearpath_fallback_batch_min_neighbours)))
    if args.clearpath_fallback_max_removes is not None:
        os.environ["PF_CLEARPATH_FALLBACK_MAX_REMOVES"] = str(
            max(0, int(args.clearpath_fallback_max_removes)))
    if args.clearpath_max_constraint_neighbours is not None:
        os.environ["PF_CLEARPATH_MAX_CONSTRAINT_NEIGHBOURS"] = str(
            max(0, int(args.clearpath_max_constraint_neighbours)))
    if args.movement_stats_path:
        stats_path = args.movement_stats_path
        if not os.path.isabs(stats_path):
            stats_path = os.path.join(pf.get_basedir(), stats_path)
        stats_dir = os.path.dirname(stats_path)
        if stats_dir and not os.path.isdir(stats_dir):
            os.makedirs(stats_dir)
        os.environ["PF_MOVEMENT_STATS_PATH"] = stats_path
    if args.movement_seek_clearpath_cadence is not None:
        os.environ["PF_MOVEMENT_SEEK_CLEARPATH_CADENCE"] = str(
            max(1, int(args.movement_seek_clearpath_cadence)))
    if args.movement_seek_clearpath_min_work_items is not None:
        os.environ["PF_MOVEMENT_SEEK_CLEARPATH_MIN_WORK_ITEMS"] = str(
            max(0, int(args.movement_seek_clearpath_min_work_items)))
    for path in (PROBE_PATH, ERROR_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
