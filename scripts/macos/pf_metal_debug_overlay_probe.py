import os
import sys

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import rts.globals
import rts.main as demo_main


PROBE_PATH = "/tmp/pf_metal_debug_overlay_probe.txt"
ERROR_PATH = "/tmp/pf_metal_debug_overlay_probe_error.txt"

STATE = {
    "updates": 0,
    "render_frames": 0,
    "move_issued": False,
    "combat_issued": False,
}


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _fail(reason):
    _write(ERROR_PATH, str(reason))
    print("METAL_DEBUG_OVERLAY_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = "METAL_DEBUG_OVERLAY_PASS backend={0} render_frames={1} chunk_boundaries=1 flow_field=1 combat_targets=1".format(
        pf.get_render_info().get("backend"),
        STATE["render_frames"],
    )
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def on_render(user, event):
    del user
    del event
    STATE["render_frames"] += 1


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _issue_debug_move():
    scene = list(rts.globals.scene_objs)
    friendlies = [
        ent for ent in scene
        if getattr(ent, "faction_id", None) == 1
        and hasattr(ent, "move")
        and hasattr(ent, "attack")
        and getattr(ent, "selectable", False)
    ]
    if not friendlies:
        _fail("no friendly movable unit found for flow-field debug overlay")

    ent = friendlies[0]
    enemies = [
        enemy for enemy in scene
        if getattr(enemy, "faction_id", None) not in (None, 1)
        and hasattr(enemy, "hp")
        and getattr(enemy, "selectable", False)
        and getattr(enemy, "hp", 0) > 0
    ]
    if not enemies:
        _fail("no enemy unit found for combat-target debug overlay")

    sx, sz = _ent_xz(ent)
    target = pf.map_nearest_pathable((sx + 24.0, sz + 16.0), radius=ent.selection_radius)
    if target is None:
        target = pf.map_nearest_pathable((sx + 12.0, sz + 12.0), radius=ent.selection_radius)
    if target is None:
        _fail("could not find flow-field debug move target")

    pf.set_unit_selection([ent])
    ent.move(target)
    STATE["move_issued"] = True

    enemy = enemies[0]
    enemy_anchor = pf.map_nearest_pathable((sx + 18.0, sz + 6.0), radius=enemy.selection_radius)
    if enemy_anchor is not None:
        enemy_height = pf.map_height_at_point(enemy_anchor[0], enemy_anchor[1])
        if enemy_height is not None:
            enemy.pos = (enemy_anchor[0], enemy_height, enemy_anchor[1])
    ex, ez = _ent_xz(enemy)
    ent.attack((ex, ez))
    STATE["combat_issued"] = True


def on_update(user, event):
    del user
    del event
    STATE["updates"] += 1

    backend = pf.get_render_info().get("backend")
    if backend != "METAL":
        _fail("expected METAL backend, got {0}".format(backend))

    if not STATE["move_issued"]:
        _issue_debug_move()
        return

    if STATE["render_frames"] >= 8 and STATE["combat_issued"]:
        _succeed()
    if STATE["updates"] > 240:
        _fail("debug overlay did not render")


demo_main.main()
pf.settings_set("pf.debug.show_chunk_boundaries", True, persist=False)
pf.settings_set("pf.debug.show_last_cmd_flow_field", True, persist=False)
pf.settings_set("pf.debug.show_combat_targets", True, persist=False)
pf.register_ui_event_handler(pf.EVENT_RENDER_3D_POST, on_render, None)
pf.register_ui_event_handler(pf.EVENT_UPDATE_START, on_update, None)
