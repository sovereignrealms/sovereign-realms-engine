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
from sovereign.factory import validate_registries


PROBE_PATH = "/tmp/pf_sovereign_projectile_vfx_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_projectile_vfx_probe_error.txt"
RENDER_STATS_PATH = "/tmp/pf_sovereign_projectile_vfx_render_stats.txt"
PROJECTILE_STATS_PATH = "/tmp/pf_sovereign_projectile_vfx_projectile_stats.txt"

EXPECTED_RENDER_SHEETS = set((
    "projectile_trail.png",
    "impact_burst.png",
    "fire_loop.png",
    "smoke_puff.png",
))

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
        "projectile_descriptor": False,
        "attack_started": False,
        "target_damaged": False,
        "trail_emitted": False,
        "impact_emitted": False,
        "projectile_spawn_near_attacker": False,
        "projectile_impact_near_target": False,
        "projectile_direction_targetward": False,
        "actors_facing": False,
        "fire_rendered": False,
        "smoke_rendered": False,
    },
    "entities": {},
    "combat": {},
    "alignment": {},
    "captures": [],
    "capture_proof": False,
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign projectile/VFX probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-projectile-vfx-probe")
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
    print("SOVEREIGN_PROJECTILE_VFX_PHASE {0}".format(name))
    sys.stdout.flush()


def _phase_elapsed():
    return time.monotonic() - STATE["phase_started_at"]


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_projectile_vfx.json")


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
    path = os.path.join(STATE["output_dir"], "sovereign_projectile_vfx_{0}.png".format(name))
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
    print("SOVEREIGN_PROJECTILE_VFX_CAPTURE {0} {1} {2}x{3}".format(name, path, width, height))
    sys.stdout.flush()
    return path


def _read_sheet_stats(path):
    sheets = {}
    if not os.path.exists(path):
        return sheets
    with open(path, "r") as infile:
        for line in infile:
            fields = line.strip().split()
            sheet = None
            for field in fields:
                if field.startswith("sheet="):
                    sheet = field.split("=", 1)[1]
                    break
            if sheet:
                sheets[sheet] = sheets.get(sheet, 0) + 1
    return sheets


def _read_projectile_events():
    events = []
    if not os.path.exists(PROJECTILE_STATS_PATH):
        return events
    with open(PROJECTILE_STATS_PATH, "r") as infile:
        for line in infile:
            row = {}
            for field in line.strip().split():
                if "=" in field:
                    key, value = field.split("=", 1)
                    row[key] = value
            if row:
                events.append(row)
    return events


def _parse_vec3(value):
    if not value:
        return None
    parts = value.split(",")
    if len(parts) != 3:
        return None
    try:
        return tuple(float(part) for part in parts)
    except ValueError:
        return None


def _dist_xz(a, b):
    return math.sqrt((a[0] - b[0]) ** 2 + (a[2] - b[2]) ** 2)


def _dot_xz(a, b):
    alen = math.sqrt(a[0] * a[0] + a[1] * a[1])
    blen = math.sqrt(b[0] * b[0] + b[1] * b[1])
    if alen <= 1.0e-5 or blen <= 1.0e-5:
        return 0.0
    return (a[0] * b[0] + a[1] * b[1]) / (alen * blen)


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _snapshot_entity(ent):
    return {
        "name": getattr(ent, "name", None),
        "uid": getattr(ent, "uid", None),
        "position": _ent_xz(ent),
        "faction_id": getattr(ent, "faction_id", None),
        "hp": getattr(ent, "hp", None) if hasattr(ent, "hp") else None,
    }


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "combat": STATE["combat"],
        "alignment": STATE["alignment"],
        "entities": {
            key: _snapshot_entity(value)
            for key, value in STATE["entities"].items()
        },
        "render_sprite_sheets": _read_sheet_stats(RENDER_STATS_PATH),
        "projectile_sprite_events": _read_projectile_events(),
        "captures": STATE["captures"],
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_PROJECTILE_VFX_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_PROJECTILE_VFX_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_PROJECTILE_VFX_PROBE_PASS backend={backend} damage={damage} "
        "hp={hp_before}->{hp_after} trail={trail} impact={impact} fire={fire} smoke={smoke} "
        "spawn_dist={spawn_dist:.2f} impact_dist={impact_dist:.2f} dir_dot={dir_dot:.2f}"
    ).format(
        backend=pf.get_render_info().get("backend"),
        damage=STATE["combat"]["hp_before"] - STATE["combat"]["hp_after"],
        hp_before=STATE["combat"]["hp_before"],
        hp_after=STATE["combat"]["hp_after"],
        trail=int(STATE["checks"]["trail_emitted"]),
        impact=int(STATE["checks"]["impact_emitted"]),
        fire=int(STATE["checks"]["fire_rendered"]),
        smoke=int(STATE["checks"]["smoke_rendered"]),
        spawn_dist=STATE["alignment"]["spawn_to_attacker_xz"],
        impact_dist=STATE["alignment"]["impact_to_target_xz"],
        dir_dot=STATE["alignment"]["projectile_target_dot_xz"],
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _ensure_factions():
    while len(pf.get_factions_list()) < 3:
        idx = len(pf.get_factions_list())
        if idx == 0:
            pf.add_faction("Neutral", (160, 160, 160, 255))
        elif idx == 1:
            pf.add_faction("Sovereign", (40, 90, 255, 255))
        else:
            pf.add_faction("Opponent", (220, 50, 50, 255))
    pf.set_diplomacy_state(1, 2, pf.DIPLOMACY_STATE_WAR)


def _unit_entry(unit_id, name):
    return {
        "kind": "unit",
        "id": unit_id,
        "name": name,
        "definition": UNITS[unit_id],
    }


def _require_effect_assets():
    sprites_dir = os.path.join(pf.get_basedir(), "assets", "sprites")
    missing = [
        name for name in EXPECTED_RENDER_SHEETS
        if not os.path.exists(os.path.join(sprites_dir, name))
    ]
    if missing:
        _fail("missing sprite asset(s): {0}".format(",".join(sorted(missing))))


def _spawn_fire_smoke_fixture(target):
    x, z = _ent_xz(target)
    height = pf.map_height_at_point(x, z)
    if height is None:
        height = target.pos[1]
    pf.spawn_sprite_animated(
        ("fire_loop.png", 1, 4, 4),
        (11.0, 18.0),
        (x + 7.0, height + 11.0, z + 5.0),
        8,
        12,
    )
    pf.spawn_sprite_animated(
        ("smoke_puff.png", 1, 4, 4),
        (15.0, 15.0),
        (x + 9.0, height + 17.0, z + 6.0),
        7,
        12,
    )


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
    _require_effect_assets()

    center = (72.0, 72.0)
    camera = pf.Camera(
        name="sovereign_projectile_vfx_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 92.0, center[1]),
        pitch=-58.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)

    sovereign_globals.scene_objs = []
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_projectile_vfx_region",
            position=center,
            dimensions=(56.0, 56.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]

    archer = create_entity(_unit_entry("archer", "sovereign_archer_projectile"))
    target = create_entity(_unit_entry("militia", "sovereign_projectile_target"))
    place_entity(archer, (58.0, 72.0), faction_id=1, radius=3.0, scale=UNITS["archer"].get("scale"))
    place_entity(target, (82.0, 72.0), faction_id=2, radius=3.25, scale=UNITS["militia"].get("scale"))
    archer.face_towards(target.pos)
    target.face_towards(archer.pos)
    sovereign_globals.scene_objs.extend([archer, target])
    _spawn_fire_smoke_fixture(target)
    pf.set_unit_selection([target])
    STATE["entities"] = {
        "archer": archer,
        "target": target,
    }
    STATE["checks"]["spawn"] = int(archer.hp) == 35 and int(target.hp) == 45
    STATE["checks"]["projectile_descriptor"] = bool(UNITS["archer"].get("projectile"))
    STATE["checks"]["actors_facing"] = True
    STATE["combat"]["hp_before"] = int(target.hp)


def _issue_attack():
    archer = STATE["entities"]["archer"]
    target = STATE["entities"]["target"]
    if hasattr(archer, "attack_entity"):
        archer.attack_entity(target)
    else:
        archer.attack(_ent_xz(target))
    STATE["checks"]["attack_started"] = True


def _update_alignment(events):
    archer = STATE["entities"]["archer"]
    target = STATE["entities"]["target"]
    parent_uid = str(getattr(archer, "uid", ""))
    spawn_event = None
    impact_event = None
    for event in events:
        if event.get("parent") != parent_uid:
            continue
        if event.get("event") == "spawn" and spawn_event is None:
            spawn_event = event
        elif event.get("event") in ("impact_hit", "impact_oob") and impact_event is None:
            impact_event = event

    spawn_pos = _parse_vec3(spawn_event.get("pos")) if spawn_event else None
    impact_pos = _parse_vec3(impact_event.get("pos")) if impact_event else None
    archer_pos = archer.pos
    target_pos = target.pos

    if spawn_pos:
        spawn_dist = _dist_xz(spawn_pos, archer_pos)
        STATE["alignment"]["spawn_to_attacker_xz"] = spawn_dist
        STATE["alignment"]["spawn_pos"] = spawn_pos
        STATE["checks"]["projectile_spawn_near_attacker"] = spawn_dist <= 9.0

    if impact_pos:
        impact_dist = _dist_xz(impact_pos, target_pos)
        STATE["alignment"]["impact_to_target_xz"] = impact_dist
        STATE["alignment"]["impact_pos"] = impact_pos
        STATE["checks"]["projectile_impact_near_target"] = impact_dist <= 10.0

    if spawn_pos and impact_pos:
        projectile_dir = (impact_pos[0] - spawn_pos[0], impact_pos[2] - spawn_pos[2])
        target_dir = (target_pos[0] - archer_pos[0], target_pos[2] - archer_pos[2])
        dot = _dot_xz(projectile_dir, target_dir)
        STATE["alignment"]["projectile_target_dot_xz"] = dot
        STATE["checks"]["projectile_direction_targetward"] = dot >= 0.80


def _effects_ready(events=None):
    target = STATE["entities"]["target"]
    hp_after = int(target.hp)
    if hp_after < STATE["combat"]["hp_before"]:
        STATE["combat"]["hp_after"] = hp_after
        STATE["checks"]["target_damaged"] = True

    render_sheets = _read_sheet_stats(RENDER_STATS_PATH)
    STATE["checks"]["fire_rendered"] = render_sheets.get("fire_loop.png", 0) > 0
    STATE["checks"]["smoke_rendered"] = render_sheets.get("smoke_puff.png", 0) > 0

    if events is None:
        events = _read_projectile_events()
    _update_alignment(events)
    parent_uid = str(getattr(STATE["entities"]["archer"], "uid", ""))
    STATE["checks"]["trail_emitted"] = any(
        event.get("event") == "trail"
        and event.get("sheet") == "projectile_trail.png"
        and event.get("parent") == parent_uid
        for event in events
    )
    STATE["checks"]["impact_emitted"] = any(
        event.get("event") in ("impact_hit", "impact_oob")
        and event.get("sheet") == "impact_burst.png"
        and event.get("parent") == parent_uid
        for event in events
    )
    return all(STATE["checks"].values())


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
            _issue_attack()
            _set_phase("combat")
        return

    if STATE["phase"] == "combat":
        events = _read_projectile_events()
        if STATE["capture_proof"] and len(STATE["captures"]) == 1 and any(
            event.get("event") == "trail"
            and event.get("parent") == str(getattr(STATE["entities"]["archer"], "uid", ""))
            for event in events
        ):
            _capture_visual("mid")
        if _effects_ready(events):
            if STATE["capture_proof"] and len(STATE["captures"]) < 3:
                _capture_visual("after")
            _succeed()
            return
        if _phase_elapsed() > 24.0:
            if "hp_after" not in STATE["combat"]:
                STATE["combat"]["hp_after"] = int(STATE["entities"]["target"].hp)
            _fail("timed out waiting for projectile/VFX checks: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    STATE["output_dir"] = args.output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["capture_proof"] = args.capture_proof
    if not os.path.isdir(STATE["output_dir"]):
        os.makedirs(STATE["output_dir"])
    os.environ["PF_METAL_SPRITE_STATS_PATH"] = RENDER_STATS_PATH
    os.environ["PF_PROJECTILE_SPRITE_STATS_PATH"] = PROJECTILE_STATS_PATH
    for path in (RENDER_STATS_PATH, PROJECTILE_STATS_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
