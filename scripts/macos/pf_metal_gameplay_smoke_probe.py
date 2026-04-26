import math
import os
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import rts.globals
import rts.main as demo_main


PROBE_PATH = "/tmp/pf_metal_gameplay_smoke_probe.txt"
ERROR_PATH = "/tmp/pf_metal_gameplay_smoke_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "camera_checked": False,
    "selection_checked": False,
    "move_checked": False,
    "pause_checked": False,
    "attack_checked": False,
    "camera_start": None,
    "move_target": None,
    "move_start_positions": None,
    "selected": None,
    "enemy": None,
    "enemy_hp": None,
    "motion_started": False,
    "attack_started": False,
    "phase_started_at": None,
}


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    print("METAL_GAMEPLAY_SMOKE_PHASE {0}".format(name))
    sys.stdout.flush()


def _phase_elapsed():
    return time.monotonic() - STATE["phase_started_at"]


def _fail(reason):
    _write(ERROR_PATH, str(reason))
    print("METAL_GAMEPLAY_SMOKE_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "METAL_GAMEPLAY_SMOKE_PASS "
        "backend={backend} camera={camera} selection={selection} "
        "move={move} pause={pause} attack={attack}"
    ).format(
        backend=pf.get_render_info().get("backend"),
        camera=int(STATE["camera_checked"]),
        selection=int(STATE["selection_checked"]),
        move=int(STATE["move_checked"]),
        pause=int(STATE["pause_checked"]),
        attack=int(STATE["attack_checked"]),
    )
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _dist_xz(a, b):
    dx = a[0] - b[0]
    dz = a[1] - b[1]
    return math.sqrt(dx * dx + dz * dz)


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _choose_units():
    scene = list(rts.globals.scene_objs)

    friendlies = [
        ent for ent in scene
        if getattr(ent, "faction_id", None) == 1
        and hasattr(ent, "move")
        and hasattr(ent, "attack")
        and getattr(ent, "selectable", False)
    ]
    if len(friendlies) < 3:
        _fail("not enough friendly movable combat units for smoke probe")

    anchor = friendlies[0]
    enemies = [
        ent for ent in scene
        if getattr(ent, "faction_id", None) not in (None, 1)
        and hasattr(ent, "hp")
        and hasattr(ent, "attack_range")
        and getattr(ent, "selectable", False)
        and getattr(ent, "hp", 0) > 0
    ]
    if not enemies:
        _fail("no enemy combat target found for smoke probe")

    enemy = min(enemies, key=lambda ent: _dist_xz(_ent_xz(ent), _ent_xz(anchor)))
    selected = friendlies[:4]
    print(
        "METAL_GAMEPLAY_SMOKE_TARGETS selected={0} enemy={1}".format(
            ",".join("{0}:{1}".format(ent.name, _ent_xz(ent)) for ent in selected),
            "{0}:{1}".format(enemy.name, _ent_xz(enemy)),
        )
    )
    sys.stdout.flush()
    return selected, enemy


def on_motion_start(user, event):
    del user
    del event
    STATE["motion_started"] = True


def on_attack_start(user, event):
    del user
    del event
    STATE["attack_started"] = True


def _register_entity_probes(selected):
    for ent in selected:
        ent.register(pf.EVENT_MOTION_START, on_motion_start, None)
        ent.register(pf.EVENT_ATTACK_START, on_attack_start, None)


def _issue_move(selected, enemy):
    sx, sz = _ent_xz(selected[0])
    ex, ez = _ent_xz(enemy)
    midpoint = ((sx + ex) * 0.5, (sz + ez) * 0.5)

    target = pf.map_nearest_pathable(midpoint, radius=selected[0].selection_radius)
    if target is None:
        target = pf.map_nearest_pathable((sx + 12.0, sz + 12.0), radius=selected[0].selection_radius)
    if target is None:
        _fail("could not find move target")

    STATE["move_target"] = target
    STATE["move_start_positions"] = [_ent_xz(ent) for ent in selected]
    for ent in selected:
        ent.move(target)


def _issue_attack(selected, enemy):
    sx, sz = _ent_xz(selected[0])
    enemy_anchor = pf.map_nearest_pathable(
        (sx + 18.0, sz + 6.0),
        radius=enemy.selection_radius,
    )
    if enemy_anchor is not None:
        enemy_height = pf.map_height_at_point(enemy_anchor[0], enemy_anchor[1])
        if enemy_height is not None:
            enemy.pos = (enemy_anchor[0], enemy_height, enemy_anchor[1])

    ex, ez = _ent_xz(enemy)
    offsets = [(-10.0, -8.0), (-10.0, 8.0), (8.0, -10.0), (8.0, 10.0)]
    staged_count = 0

    for ent, (dx, dz) in zip(selected, offsets):
        staged = pf.map_nearest_pathable((ex + dx, ez + dz), radius=ent.selection_radius)
        if staged is None:
            continue
        height = pf.map_height_at_point(staged[0], staged[1])
        if height is None:
            continue
        ent.pos = (staged[0], height, staged[1])
        staged_count += 1

    if staged_count == 0:
        _fail("could not stage attackers near combat target")

    STATE["enemy_hp"] = enemy.hp
    for ent in selected:
        ent.attack((ex, ez))


def on_update(user, event):
    del user
    del event

    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if backend != "METAL":
            _fail("expected METAL backend, got {0}".format(backend))

        selected, enemy = _choose_units()
        STATE["selected"] = selected
        STATE["enemy"] = enemy
        _register_entity_probes(selected)

        cam = pf.get_active_camera()
        STATE["camera_start"] = cam.position
        cam.center_over_location(_ent_xz(selected[0]))
        _set_phase("camera")
        return

    if STATE["phase"] == "camera":
        cam = pf.get_active_camera()
        start = STATE["camera_start"]
        curr = cam.position
        if _dist_xz((start[0], start[2]), (curr[0], curr[2])) > 5.0:
            STATE["camera_checked"] = True
            pf.set_unit_selection(STATE["selected"])
            _set_phase("selection")
            return
        if _phase_elapsed() > 3.0:
            _fail("camera did not move")

    if STATE["phase"] == "selection":
        if len(pf.get_unit_selection()) == len(STATE["selected"]):
            STATE["selection_checked"] = True
            _issue_move(STATE["selected"], STATE["enemy"])
            _set_phase("move")
            return
        if _phase_elapsed() > 2.0:
            _fail("selection did not apply")

    if STATE["phase"] == "move":
        moved = STATE["motion_started"]
        if moved:
            STATE["move_checked"] = True
            pf.set_simstate(pf.G_PAUSED_UI_RUNNING)
            _set_phase("pause")
            return
        if _phase_elapsed() > 8.0:
            _fail("move order did not change unit positions")

    if STATE["phase"] == "pause":
        if pf.get_simstate() == pf.G_PAUSED_UI_RUNNING:
            STATE["pause_checked"] = True
            pf.set_simstate(pf.G_RUNNING)
            _set_phase("resume")
            return
        if _phase_elapsed() > 2.0:
            _fail("pause did not apply")

    if STATE["phase"] == "resume":
        if pf.get_simstate() == pf.G_RUNNING:
            pf.get_active_camera().center_over_location(_ent_xz(STATE["enemy"]))
            _issue_attack(STATE["selected"], STATE["enemy"])
            _set_phase("attack")
            return
        if _phase_elapsed() > 2.0:
            _fail("resume did not apply")

    if STATE["phase"] == "attack":
        try:
            current_hp = STATE["enemy"].hp
        except Exception:
            STATE["attack_checked"] = True
            _succeed()
            return

        if STATE["attack_started"] or current_hp < STATE["enemy_hp"]:
            STATE["attack_checked"] = True
            _succeed()
            return
        if _phase_elapsed() > 20.0:
            _fail("attack did not start or reduce target hp")

demo_main.main()
pf.register_ui_event_handler(pf.EVENT_UPDATE_START, on_update, None)
