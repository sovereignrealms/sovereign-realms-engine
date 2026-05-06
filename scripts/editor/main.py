#
#  This file is part of Permafrost Engine. 
#  Copyright (C) 2018-2023 Eduard Permyakov 
#
#  Permafrost Engine is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Permafrost Engine is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
# 
#  Linking this software statically or dynamically with other modules is making 
#  a combined work based on this software. Thus, the terms and conditions of 
#  the GNU General Public License cover the whole combination. 
#  
#  As a special exception, the copyright holders of Permafrost Engine give 
#  you permission to link Permafrost Engine with independent modules to produce 
#  an executable, regardless of the license terms of these independent 
#  modules, and to copy and distribute the resulting executable under 
#  terms of your choice, provided that you also meet, for each linked 
#  independent module, the terms and conditions of the license of that 
#  module. An independent module is a module which is not derived from 
#  or based on Permafrost Engine. If you modify Permafrost Engine, you may 
#  extend this exception to your version of Permafrost Engine, but you are not 
#  obliged to do so. If you do not wish to do so, delete this exception 
#  statement from your version.
#

import pf
from constants import *
import map
import globals
import mouse_events
import scene

from math import cos, pi
import os
import subprocess
import sys
import time

import view_controllers.terrain_tab_vc as ttvc
import view_controllers.objects_tab_vc as otvc
import view_controllers.diplomacy_tab_vc as dtvc
import view_controllers.menu_vc as mvc
import view_controllers.sovereign_tab_vc as srvc
import common.view_controllers.tab_bar_vc as tbvc
import common.constants as common_constants

import views.tab_bar_window as tbw
import views.terrain_tab_window as ttw
import views.objects_tab_window as otw
import views.diplomacy_tab_window as dtw
import views.menu_window as mw
import views.sovereign_tab_window as srw

editor_probe_ticks = 0
editor_feature_probe_steps_done = set()
editor_workflow_probe_steps_done = set()
editor_workflow_probe_state = {}
editor_visual_probe_steps_done = set()
editor_visual_probe_state = {"captures": []}


def _write_probe_file(path, marker):
    with open(path, "w") as probe_file:
        probe_file.write(marker + "\n")


def _append_probe_trace(path, marker):
    if not path:
        return
    with open(path, "a") as probe_file:
        probe_file.write(marker + "\n")


def _editor_probe_marker():
    render_info = pf.get_render_info()
    return "EDITOR_LAUNCH_READY backend={0} renderer={1}".format(
        render_info.get("backend"),
        render_info.get("renderer"),
    )


def _editor_feature_probe_marker():
    render_info = pf.get_render_info()
    return "EDITOR_FEATURE_AUDIT_READY backend={0} renderer={1} factions={2}".format(
        render_info.get("backend"),
        render_info.get("renderer"),
        len(pf.get_factions_list()),
    )


def _editor_workflow_probe_marker():
    render_info = pf.get_render_info()
    return (
        "EDITOR_WORKFLOW_READY backend={0} renderer={1} saved_map={2} "
        "saved_scene={3} placed_objects={4} saved_objects={5} "
        "sovereign_sidecar={6} sovereign_markers={7}"
    ).format(
        render_info.get("backend"),
        render_info.get("renderer"),
        editor_workflow_probe_state.get("map_path"),
        editor_workflow_probe_state.get("scene_path"),
        editor_workflow_probe_state.get("placed_objects", 0),
        editor_workflow_probe_state.get("saved_objects", 0),
        editor_workflow_probe_state.get("sovereign_sidecar_path"),
        editor_workflow_probe_state.get("sovereign_marker_count", 0),
    )


def _editor_workflow_reload_probe_marker():
    render_info = pf.get_render_info()
    return (
        "EDITOR_WORKFLOW_RELOAD_READY backend={0} renderer={1} loaded_objects={2} "
        "sovereign_sidecar={3} sovereign_markers={4}"
    ).format(
        render_info.get("backend"),
        render_info.get("renderer"),
        len(globals.active_objects_list),
        editor_workflow_probe_state.get("sovereign_sidecar_path"),
        editor_workflow_probe_state.get("sovereign_marker_count", 0),
    )


def _editor_visual_probe_marker():
    render_info = pf.get_render_info()
    return (
        "EDITOR_VISUAL_READY backend={0} renderer={1} captures={2} "
        "placed_objects={3} saved_objects={4}"
    ).format(
        render_info.get("backend"),
        render_info.get("renderer"),
        len(editor_visual_probe_state.get("captures", [])),
        editor_visual_probe_state.get("placed_objects", 0),
        editor_visual_probe_state.get("saved_objects", 0),
    )


def _editor_select_tab(index):
    tab_bar_vc.view.active_idx = index
    tab_bar_vc.view._TabBarWindow__show_active()
    pf.global_event(EVENT_TOP_TAB_SELECTION_CHANGED, index)


def _editor_workflow_probe_apply_sovereign_stress(state):
    player_specs = (
        (1, "Blue Author", [74.0, 84.0], [40, 90, 255, 255], {"food": 520, "wood": 520, "gold": 260, "stone": 180}),
        (2, "Red Author", [136.0, 78.0], [220, 50, 50, 255], {"food": 640, "wood": 640, "gold": 260, "stone": 180}),
        (3, "Green Author", [74.0, 136.0], [50, 180, 70, 255], {"food": 560, "wood": 560, "gold": 220, "stone": 160}),
        (4, "Gold Author", [136.0, 136.0], [220, 180, 45, 255], {"food": 560, "wood": 560, "gold": 220, "stone": 160}),
    )
    state["players"] = [
        {
            "id": player_id,
            "name": name,
            "civilization_id": "sovereign_default",
            "faction_color": list(color),
            "start": list(start),
            "starting_resources": dict(resources),
        }
        for player_id, name, start, color, resources in player_specs
    ]

    cluster_specs = (
        (1, "food", [60.0, 96.0]), (1, "wood", [52.0, 78.0]), (1, "gold", [86.0, 76.0]), (1, "stone", [88.0, 102.0]),
        (2, "food", [150.0, 88.0]), (2, "wood", [156.0, 70.0]), (2, "gold", [122.0, 72.0]), (2, "stone", [124.0, 100.0]),
        (3, "food", [60.0, 150.0]), (3, "wood", [52.0, 126.0]), (3, "gold", [88.0, 124.0]), (3, "stone", [90.0, 154.0]),
        (4, "food", [150.0, 148.0]), (4, "wood", [158.0, 126.0]), (4, "gold", [124.0, 124.0]), (4, "stone", [126.0, 154.0]),
    )
    state["placed_resources"] = [
        {
            "id": "p{0}_{1}_{2}".format(player_id, resource_id, idx + 1),
            "resource_id": resource_id,
            "owner_player_id": 0,
            "point": list(point),
            "amount": 280 + (idx % 4) * 40,
        }
        for idx, (player_id, resource_id, point) in enumerate(cluster_specs)
    ]

    object_specs = (
        (1, "building", "town_center", [78.0, 88.0]), (1, "building", "barracks", [96.0, 94.0]), (1, "unit", "militia", [104.0, 96.0]),
        (2, "building", "town_center", [132.0, 82.0]), (2, "building", "barracks", [150.0, 88.0]), (2, "unit", "archer", [116.0, 86.0]),
        (3, "building", "town_center", [78.0, 132.0]), (3, "building", "house", [96.0, 126.0]), (3, "unit", "villager", [104.0, 132.0]),
        (4, "building", "town_center", [132.0, 132.0]), (4, "building", "barracks", [150.0, 126.0]), (4, "unit", "militia", [116.0, 132.0]),
    )
    state["placed_objects"] = [
        {
            "id": "p{0}_{1}_{2}".format(player_id, object_id, idx + 1),
            "kind": kind,
            "object_id": object_id,
            "owner_player_id": player_id,
            "point": list(point),
        }
        for idx, (player_id, kind, object_id, point) in enumerate(object_specs)
    ]
    state["selected_placement"] = {
        "kind": "unit",
        "player_id": 1,
        "resource_index": 0,
        "object_index": 2,
    }
    state["scenario_id"] = "authoring_stress_scenario"
    state["name"] = "Authoring Stress Scenario"
    state["map_seed"] = 20260506
    state["author_notes"] = "Stress fixture for large authored maps"
    state["victory_mode"] = "conquest"
    state["setup_profile"] = "fast_skirmish"
    state["starting_resource_preset"] = "generous"
    return {
        "players": len(state["players"]),
        "placed_resources": len(state["placed_resources"]),
        "placed_objects": len(state["placed_objects"]),
    }


def on_editor_probe_update(user, event):
    del user
    del event

    global editor_probe_ticks
    editor_probe_ticks += 1

    quit_after = int(os.environ.get("PF_EDITOR_LAUNCH_PROBE_QUIT_AFTER", "8"))
    if editor_probe_ticks < quit_after:
        return

    marker = _editor_probe_marker()
    print(marker)
    probe_path = os.environ.get("PF_EDITOR_LAUNCH_PROBE_PATH")
    if probe_path:
        _write_probe_file(probe_path, marker)
    if os.environ.get("PF_EDITOR_LAUNCH_PROBE_AUTOQUIT") == "1":
        sys.stdout.flush()
        os._exit(0)


def _run_editor_feature_probe_step(name):
    marker = "EDITOR_FEATURE_STEP tick={0} name={1}".format(editor_probe_ticks, name)
    print(marker)
    sys.stdout.flush()
    _append_probe_trace(os.environ.get("PF_EDITOR_FEATURE_PROBE_TRACE_PATH"), marker)

    if name == "terrain_tab":
        pf.global_event(EVENT_TOP_TAB_SELECTION_CHANGED, 0)
    elif name == "objects_tab":
        pf.global_event(EVENT_TOP_TAB_SELECTION_CHANGED, 1)
    elif name == "objects_select_mode":
        objects_tab_vc.view.mode = objects_tab_vc.view.OBJECTS_MODE_SELECT
        pf.global_event(EVENT_OBJECTS_TAB_MODE_CHANGED, objects_tab_vc.view.mode)
    elif name == "objects_place_mode":
        objects_tab_vc.view.mode = objects_tab_vc.view.OBJECTS_MODE_PLACE
        pf.global_event(EVENT_OBJECTS_TAB_MODE_CHANGED, objects_tab_vc.view.mode)
    elif name == "diplomacy_tab":
        pf.global_event(EVENT_TOP_TAB_SELECTION_CHANGED, 2)
    elif name == "diplomacy_add_probe_faction":
        pf.global_event(EVENT_DIPLO_FAC_NEW, ("Editor Probe", (128, 64, 255, 255)))
    elif name == "terrain_large_brush":
        pf.global_event(EVENT_TOP_TAB_SELECTION_CHANGED, 0)
        terrain_tab_vc.view.brush_size_idx = 1
        pf.global_event(EVENT_TERRAIN_BRUSH_SIZE_CHANGED, terrain_tab_vc.view.brush_size_idx)
    elif name == "menu_show":
        menu.show()
    elif name == "settings_show":
        pf.global_event(EVENT_MENU_SETTINGS_SHOW, None)
    elif name == "settings_game_tab":
        pf.global_event(common_constants.EVENT_SETTINGS_TAB_SEL_CHANGED, 1)
    elif name == "settings_hide":
        pf.global_event(common_constants.EVENT_SETTINGS_HIDE, None)
    elif name == "perf_show":
        pf.global_event(EVENT_MENU_PERF_SHOW, None)
    elif name == "session_show":
        pf.global_event(EVENT_MENU_SESSION_SHOW, None)
    elif name == "load_cancel":
        pf.global_event(EVENT_MENU_LOAD, None)
        pf.global_event(EVENT_FILE_CHOOSER_CANCEL, None)
    elif name == "save_as_cancel":
        pf.global_event(EVENT_MENU_SAVE_AS, None)
        pf.global_event(EVENT_FILE_CHOOSER_CANCEL, None)

    marker = "EDITOR_FEATURE_STEP_DONE tick={0} name={1}".format(editor_probe_ticks, name)
    print(marker)
    sys.stdout.flush()
    _append_probe_trace(os.environ.get("PF_EDITOR_FEATURE_PROBE_TRACE_PATH"), marker)


def on_editor_feature_probe_update(user, event):
    del user
    del event

    global editor_probe_ticks
    editor_probe_ticks += 1

    steps = (
        (4, "terrain_tab"),
        (10, "objects_tab"),
        (16, "objects_select_mode"),
        (22, "objects_place_mode"),
        (28, "diplomacy_tab"),
        (34, "diplomacy_add_probe_faction"),
        (40, "terrain_large_brush"),
        (46, "menu_show"),
        (52, "settings_show"),
        (58, "settings_game_tab"),
        (64, "settings_hide"),
        (70, "perf_show"),
        (76, "session_show"),
        (82, "load_cancel"),
        (88, "save_as_cancel"),
    )

    for tick, name in steps:
        if editor_probe_ticks >= tick and name not in editor_feature_probe_steps_done:
            _run_editor_feature_probe_step(name)
            editor_feature_probe_steps_done.add(name)

    quit_after = int(os.environ.get("PF_EDITOR_FEATURE_PROBE_QUIT_AFTER", "110"))
    if editor_probe_ticks < quit_after:
        return

    marker = _editor_feature_probe_marker()
    print(marker)
    probe_path = os.environ.get("PF_EDITOR_FEATURE_PROBE_PATH")
    if probe_path:
        _write_probe_file(probe_path, marker)
    if os.environ.get("PF_EDITOR_FEATURE_PROBE_AUTOQUIT") == "1":
        sys.stdout.flush()
        os._exit(0)


def _editor_workflow_probe_output_dir():
    output_dir = os.environ.get("PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR")
    if not output_dir:
        output_dir = "visual_parity_captures/2026-04-30-editor-workflow"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    return output_dir


def _editor_workflow_probe_world_pos(chunk_coords, tile_coords):
    global_r = chunk_coords[0] * pf.TILES_PER_CHUNK_HEIGHT + tile_coords[0]
    global_c = chunk_coords[1] * pf.TILES_PER_CHUNK_WIDTH + tile_coords[1]
    x = -(global_c + 0.5) * pf.X_COORDS_PER_TILE
    z = (global_r + 0.5) * pf.Z_COORDS_PER_TILE
    y = pf.map_height_at_point(x, z)
    if y is None:
        y = 0.0
    return (x, y, z)


def _editor_workflow_probe_object_index(animated):
    for idx, meta in enumerate(scene.OBJECTS_LIST):
        if bool(meta["anim"]) == bool(animated):
            return idx
    raise RuntimeError("Editor workflow probe could not find an object with anim={0}".format(animated))


def _editor_workflow_probe_make_object(index, pos):
    obj = objects_tab_vc._ObjectsVC__object_at_index(index)
    obj.pos = pos
    obj.faction_id = pf.get_factions_list()[0]["id"]
    obj.selectable = True
    globals.active_objects_list.append(obj)
    return obj


def _editor_workflow_probe_scene_entity_count(path):
    with open(path, "r") as scene_file:
        for line in scene_file:
            parts = line.split()
            if len(parts) == 2 and parts[0] == "num_entities":
                return int(parts[1])
    raise RuntimeError("Editor workflow probe could not find num_entities in saved scene")


def _editor_visual_probe_output_dir():
    output_dir = os.environ.get("PF_EDITOR_VISUAL_PROBE_OUTPUT_DIR")
    if not output_dir:
        output_dir = "visual_parity_captures/2026-05-01-editor-visual-harness"
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    return output_dir


def _editor_visual_probe_capture_window_id():
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


def _editor_visual_probe_activate_window():
    script = (
        'tell application "System Events"\n'
        '    set capture_process to first process whose unix id is {0}\n'
        '    set frontmost of capture_process to true\n'
        '    if (count of windows of capture_process) is greater than 0 then\n'
        '        perform action "AXRaise" of window 1 of capture_process\n'
        '    end if\n'
        'end tell\n'
    ).format(os.getpid())
    try:
        subprocess.run(["osascript", "-e", script], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=3.0)
    except subprocess.TimeoutExpired:
        pass


def _editor_visual_probe_capture(name):
    external_dir = os.environ.get("PF_EDITOR_VISUAL_PROBE_EXTERNAL_CAPTURE_DIR")
    if external_dir:
        if not os.path.isdir(external_dir):
            os.makedirs(external_dir)
        _editor_visual_probe_activate_window()
        window_id = _editor_visual_probe_capture_window_id()
        path = os.path.join(external_dir, "editor_{0}.png".format(name))
        ready_path = os.path.join(external_dir, "{0}.ready".format(name))
        with open(ready_path, "w") as ready_file:
            ready_file.write("{0}\n{1}\n".format(window_id or "", path))
        editor_visual_probe_state["external_pending"] = {
            "name": name,
            "path": path,
            "done": os.path.join(external_dir, "{0}.done".format(name)),
        }
        return path

    output_dir = _editor_visual_probe_output_dir()
    path = os.path.join(output_dir, "editor_{0}.png".format(name))
    ret = 1
    last_error = ""
    window_id = None
    for _ in range(5):
        _editor_visual_probe_activate_window()
        window_id = _editor_visual_probe_capture_window_id()
        if window_id is None:
            last_error = "no window id"
            time.sleep(0.15)
            continue
        try:
            capture = subprocess.run(
                ["screencapture", "-x", "-o", "-l{0}".format(window_id), path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                timeout=3.0,
            )
            ret = capture.returncode
            last_error = capture.stderr.strip()
            if ret == 0:
                break
        except subprocess.TimeoutExpired:
            last_error = "timeout"
            ret = 1
        time.sleep(0.15)
    if ret != 0:
        window_error = last_error
        for _ in range(3):
            _editor_visual_probe_activate_window()
            try:
                capture = subprocess.run(
                    ["screencapture", "-x", path],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    universal_newlines=True,
                    timeout=3.0,
                )
                ret = capture.returncode
                last_error = capture.stderr.strip()
                if ret == 0:
                    print("EDITOR_VISUAL_CAPTURE_FALLBACK window_id={0} stderr={1}".format(window_id, window_error))
                    sys.stdout.flush()
                    break
            except subprocess.TimeoutExpired:
                last_error = "timeout"
                ret = 1
            time.sleep(0.15)
    if ret != 0:
        print("EDITOR_VISUAL_CAPTURE_FAIL window_id={0} stderr={1}".format(window_id, last_error))
        sys.stdout.flush()
        raise RuntimeError("Editor visual probe could not capture {0}".format(name))
    editor_visual_probe_state["captures"].append(path)
    return path


def _run_editor_visual_probe_step(name):
    marker = "EDITOR_VISUAL_STEP tick={0} name={1}".format(editor_probe_ticks, name)
    print(marker)
    sys.stdout.flush()
    _append_probe_trace(os.environ.get("PF_EDITOR_VISUAL_PROBE_TRACE_PATH"), marker)

    if name == "setup_world":
        _editor_select_tab(0)
        terrain_tab_vc.view.brush_size_idx = 1
        terrain_tab_vc.view.selected_mat_idx = 3
        terrain_tab_vc.view.brush_type_idx = 0
        terrain_tab_vc.view.blend_textures = False
        terrain_tab_vc.view.blend_normals = False

        for row in range(2, 7):
            for col in range(2, 7):
                globals.active_map.update_tile_mat(
                    ((1, 1), (row, col)),
                    globals.active_map.materials[3],
                    pf.BLEND_MODE_NOBLEND,
                    0,
                )
        globals.active_map.update_tile(
            ((1, 1), (7, 4)),
            -1,
            pf.TILETYPE_FLAT,
            globals.active_map.materials[1],
            0,
            pf.BLEND_MODE_NOBLEND,
            0,
        )

        animated_idx = _editor_workflow_probe_object_index(True)
        static_idx = _editor_workflow_probe_object_index(False)
        animated = _editor_workflow_probe_make_object(
            animated_idx,
            _editor_workflow_probe_world_pos((1, 1), (3, 4)),
        )
        _editor_workflow_probe_make_object(
            static_idx,
            _editor_workflow_probe_world_pos((1, 1), (5, 4)),
        )
        animated.select()
        editor_visual_probe_state["placed_objects"] = len(globals.active_objects_list)
        editor_visual_probe_state["target"] = _editor_workflow_probe_world_pos((1, 1), (4, 4))
        pf.get_active_camera().center_over_location((
            editor_visual_probe_state["target"][0],
            editor_visual_probe_state["target"][2],
        ))
    elif name == "select_terrain":
        _editor_select_tab(0)
    elif name == "capture_terrain":
        _editor_visual_probe_capture("terrain")
    elif name == "select_objects":
        _editor_select_tab(1)
        objects_tab_vc.view.mode = objects_tab_vc.view.OBJECTS_MODE_SELECT
        pf.global_event(EVENT_OBJECTS_TAB_MODE_CHANGED, objects_tab_vc.view.mode)
    elif name == "capture_objects":
        _editor_visual_probe_capture("objects")
    elif name == "save_as_show":
        pf.global_event(EVENT_MENU_SAVE_AS, None)
    elif name == "save_as_confirm":
        output_dir = _editor_visual_probe_output_dir()
        map_path = os.path.join(output_dir, "editor_visual_probe.pfmap")
        scene_path = os.path.join(output_dir, "editor_visual_probe.pfscene")
        editor_visual_probe_state["map_path"] = map_path
        editor_visual_probe_state["scene_path"] = scene_path
        editor_visual_probe_state["save_confirm_tick"] = editor_probe_ticks
        pf.global_event(EVENT_FILE_CHOOSER_OKAY, (map_path, scene_path))
    elif name == "validate_saved_files":
        map_path = editor_visual_probe_state["map_path"]
        scene_path = editor_visual_probe_state["scene_path"]
        saved_map = map.Map.from_filepath(map_path)
        if saved_map is None:
            raise RuntimeError("Editor visual probe failed to parse saved map")
        tile = saved_map.tile_at_coords((1, 1), (4, 4))
        if tile.top_mat_idx != 3:
            raise RuntimeError("Editor visual probe saved wrong visible terrain material")
        saved_objects = _editor_workflow_probe_scene_entity_count(scene_path)
        if saved_objects < editor_visual_probe_state["placed_objects"]:
            raise RuntimeError("Editor visual probe saved too few objects")
        editor_visual_probe_state["saved_objects"] = saved_objects

    marker = "EDITOR_VISUAL_STEP_DONE tick={0} name={1}".format(editor_probe_ticks, name)
    print(marker)
    sys.stdout.flush()
    _append_probe_trace(os.environ.get("PF_EDITOR_VISUAL_PROBE_TRACE_PATH"), marker)


def on_editor_visual_probe_update(user, event):
    del user
    del event

    global editor_probe_ticks
    editor_probe_ticks += 1

    pending = editor_visual_probe_state.get("external_pending")
    if pending is not None:
        if not os.path.exists(pending["done"]):
            quit_after = int(os.environ.get("PF_EDITOR_VISUAL_PROBE_QUIT_AFTER", "300"))
            if editor_probe_ticks >= quit_after:
                raise RuntimeError("Editor visual probe timed out waiting for {0} capture".format(pending["name"]))
            return
        editor_visual_probe_state["captures"].append(pending["path"])
        del editor_visual_probe_state["external_pending"]

    steps = (
        (6, "setup_world"),
        (14, "select_terrain"),
        (20, "capture_terrain"),
        (28, "select_objects"),
        (34, "capture_objects"),
        (42, "save_as_show"),
        (48, "save_as_confirm"),
        (62, "validate_saved_files"),
    )

    for tick, name in steps:
        if editor_probe_ticks >= tick and name not in editor_visual_probe_steps_done:
            if name == "validate_saved_files":
                save_tick = editor_visual_probe_state.get("save_confirm_tick")
                if save_tick is not None and editor_probe_ticks - save_tick < 24:
                    return
            _run_editor_visual_probe_step(name)
            editor_visual_probe_steps_done.add(name)
            break

    all_done = all(name in editor_visual_probe_steps_done for _, name in steps)
    quit_after = int(os.environ.get("PF_EDITOR_VISUAL_PROBE_QUIT_AFTER", "300"))
    if not all_done:
        if editor_probe_ticks >= quit_after:
            raise RuntimeError("Editor visual probe timed out before completing all steps")
        return
    if editor_visual_probe_state.get("external_pending") is not None:
        if editor_probe_ticks >= quit_after:
            raise RuntimeError("Editor visual probe timed out waiting for final capture")
        return

    marker = _editor_visual_probe_marker()
    print(marker)
    probe_path = os.environ.get("PF_EDITOR_VISUAL_PROBE_PATH")
    if probe_path:
        _write_probe_file(probe_path, marker)
    if os.environ.get("PF_EDITOR_VISUAL_PROBE_AUTOQUIT") == "1":
        sys.stdout.flush()
        os._exit(0)


def _run_editor_workflow_probe_step(name):
    marker = "EDITOR_WORKFLOW_STEP tick={0} name={1}".format(editor_probe_ticks, name)
    print(marker)
    sys.stdout.flush()
    _append_probe_trace(os.environ.get("PF_EDITOR_WORKFLOW_PROBE_TRACE_PATH"), marker)

    if name == "mutate":
        tile_coords = ((1, 1), (2, 3))
        globals.active_map.update_tile_mat(
            tile_coords,
            globals.active_map.materials[3],
            pf.BLEND_MODE_NOBLEND,
            0,
        )
        globals.active_map.update_tile(
            ((1, 1), (3, 3)),
            2,
            pf.TILETYPE_FLAT,
            globals.active_map.materials[1],
            0,
            pf.BLEND_MODE_NOBLEND,
            0,
        )

        animated_idx = _editor_workflow_probe_object_index(True)
        static_idx = _editor_workflow_probe_object_index(False)
        _editor_workflow_probe_make_object(animated_idx, _editor_workflow_probe_world_pos((1, 1), (2, 5)))
        _editor_workflow_probe_make_object(static_idx, _editor_workflow_probe_world_pos((1, 1), (5, 5)))
        editor_workflow_probe_state["placed_objects"] = len(globals.active_objects_list)
        editor_workflow_probe_state["mutated_tile"] = tile_coords
    elif name == "save_as_show":
        pf.global_event(EVENT_MENU_SAVE_AS, None)
    elif name == "sovereign_authoring":
        from sovereign.editor_scenario import (
            add_placed_object,
            add_placed_resource,
            duplicate_placed_object,
            duplicate_placed_resource,
            duplicate_player,
            get_editor_authoring_state,
            remove_placed_object,
            remove_placed_resource,
            remove_player,
            select_validation_issue,
            validate_editor_authoring_state,
        )

        def issue_index_containing(fragment):
            for idx, issue in enumerate(state.get("validation_issues", [])):
                if fragment in issue["message"]:
                    return idx
            raise RuntimeError("Editor workflow probe could not find validation issue '{0}'".format(fragment))

        _editor_select_tab(3)
        state = get_editor_authoring_state()
        temp_player_idx = duplicate_player(0)
        remove_player(temp_player_idx)
        temp_resource_idx = duplicate_placed_resource(0)
        remove_placed_resource(temp_resource_idx)
        temp_object_idx = duplicate_placed_object(0)
        remove_placed_object(temp_object_idx)
        state["scenario_id"] = "authoring_probe_scenario"
        state["name"] = "Authoring Probe Scenario"
        state["map_seed"] = 424242
        state["author_notes"] = "Editor workflow probe metadata"
        state["victory_mode"] = "conquest"
        state["setup_profile"] = "fast_skirmish"
        state["starting_resource_preset"] = "generous"
        state["players"][0]["name"] = "Blue Author"
        state["players"][0]["start"] = [72.0, 82.0]
        state["players"][0]["starting_resources"]["food"] = 310
        state["players"][0]["starting_resources"]["wood"] = 333
        state["players"][1]["name"] = "Red Author"
        state["players"][1]["start"] = [132.0, 76.0]
        state["players"][1]["starting_resources"]["food"] = 640
        state["players"][1]["starting_resources"]["wood"] = 640
        state["diplomacy_state"] = "war"
        state["selected_placement"]["kind"] = "player_start"
        state["selected_placement"]["player_id"] = 1
        sovereign_tab_vc._apply_point((74.0, 84.0))
        state["selected_placement"]["player_id"] = 2
        sovereign_tab_vc._apply_point((136.0, 78.0))
        state["selected_placement"]["kind"] = "resource"
        state["selected_placement"]["resource_index"] = 0
        state["placed_resources"][0]["owner_player_id"] = 1
        state["placed_resources"][0]["amount"] = 420
        sovereign_tab_vc._apply_point((66.0, 96.0))
        state["selected_placement"]["resource_index"] = 1
        state["placed_resources"][1]["owner_player_id"] = 2
        state["placed_resources"][1]["amount"] = 510
        sovereign_tab_vc._apply_point((146.0, 74.0))
        extra_resource_idx = add_placed_resource("food", 1, [70.0, 100.0])
        state["placed_resources"][extra_resource_idx]["id"] = "p1_extra_food"
        state["placed_resources"][extra_resource_idx]["amount"] = 260
        sovereign_tab_vc._apply_point((70.0, 100.0))
        state["selected_placement"]["kind"] = "unit"
        state["selected_placement"]["object_index"] = 0
        state["placed_objects"][0]["kind"] = "unit"
        state["placed_objects"][0]["object_id"] = "militia"
        state["placed_objects"][0]["owner_player_id"] = 1
        sovereign_tab_vc._apply_point((101.0, 94.0))
        state["selected_placement"]["kind"] = "building"
        state["selected_placement"]["object_index"] = 1
        state["placed_objects"][1]["kind"] = "building"
        state["placed_objects"][1]["object_id"] = "barracks"
        state["placed_objects"][1]["owner_player_id"] = 2
        sovereign_tab_vc._apply_point((152.0, 88.0))
        extra_object_idx = add_placed_object("unit", "archer", 1, [108.0, 98.0])
        state["placed_objects"][extra_object_idx]["id"] = "p1_forward_archer"
        sovereign_tab_vc._apply_point((108.0, 98.0))
        selected_final_object_idx = extra_object_idx
        stress_counts = None
        if os.environ.get("PF_EDITOR_SOVEREIGN_AUTHORING_STRESS_PROBE") == "1":
            stress_counts = _editor_workflow_probe_apply_sovereign_stress(state)
            selected_final_object_idx = state["selected_placement"]["object_index"]
            sovereign_tab_vc._sync_markers()

        sovereign_view = sovereign_tab_vc.view
        sovereign_view.palette_filter = "arch"
        sovereign_view.palette_show_units = True
        sovereign_view.palette_show_buildings = False
        sovereign_view.palette_show_resources = False
        filtered = sovereign_view._filtered_palette_entries(state)
        if len(filtered) != 1 or filtered[0]["kind"] != "unit" or filtered[0]["id"] != "archer":
            raise RuntimeError("Editor workflow probe palette unit filter/fold failed")
        sovereign_view.palette_filter = "town"
        sovereign_view.palette_show_units = False
        sovereign_view.palette_show_buildings = True
        sovereign_view.palette_show_resources = False
        filtered = sovereign_view._filtered_palette_entries(state)
        if len(filtered) != 1 or filtered[0]["kind"] != "building" or filtered[0]["id"] != "town_center":
            raise RuntimeError("Editor workflow probe palette building filter/fold failed")
        sovereign_view.palette_filter = ""
        sovereign_view.palette_show_units = True
        sovereign_view.palette_show_buildings = True
        sovereign_view.palette_show_resources = True

        saved_amount = state["placed_resources"][0]["amount"]
        state["placed_resources"][0]["amount"] = 0
        validate_editor_authoring_state(check_pathing=False)
        if sovereign_view._first_validation_issue_index(state.get("validation_issues", []), "resource") is None:
            raise RuntimeError("Editor workflow probe validation resource summary failed")
        select_validation_issue(issue_index_containing("placed resource 0"))
        if state["selected_placement"]["kind"] != "resource" \
        or state["selected_placement"]["resource_index"] != 0:
            raise RuntimeError("Editor workflow probe validation did not select resource issue")
        state["placed_resources"][0]["amount"] = saved_amount

        saved_owner = state["placed_objects"][0]["owner_player_id"]
        state["placed_objects"][0]["owner_player_id"] = 999
        validate_editor_authoring_state(check_pathing=False)
        if sovereign_view._first_validation_issue_index(state.get("validation_issues", []), "object") is None:
            raise RuntimeError("Editor workflow probe validation object summary failed")
        select_validation_issue(issue_index_containing("placed object 0"))
        expected_object_kind = state["placed_objects"][0]["kind"]
        if state["selected_placement"]["kind"] != expected_object_kind \
        or state["selected_placement"]["object_index"] != 0:
            raise RuntimeError("Editor workflow probe validation did not select object issue")
        state["placed_objects"][0]["owner_player_id"] = saved_owner

        saved_start = list(state["players"][0]["start"])
        state["players"][0]["start"] = list(state["players"][1]["start"])
        validate_editor_authoring_state(check_pathing=False)
        if sovereign_view._first_validation_issue_index(state.get("validation_issues", []), "player_start") is None:
            raise RuntimeError("Editor workflow probe validation start summary failed")
        select_validation_issue(issue_index_containing("player starts 1"))
        if state["selected_placement"]["kind"] != "player_start" \
        or state["selected_placement"]["player_id"] != 1:
            raise RuntimeError("Editor workflow probe validation did not select player-start issue")
        state["players"][0]["start"] = saved_start
        state["selected_placement"]["kind"] = state["placed_objects"][selected_final_object_idx]["kind"]
        state["selected_placement"]["object_index"] = selected_final_object_idx
        validate_editor_authoring_state(check_pathing=False)
        issue_counts = {
            "player_start": 0,
            "resource": 0,
            "object": 0,
            "other": 0,
        }
        for issue in state.get("validation_issues", []):
            key = issue.get("target_kind") or "other"
            issue_counts[key if key in issue_counts else "other"] += 1
        if any(issue_counts.values()):
            raise RuntimeError("Editor workflow probe expected clean Sovereign validation after restore")
        export_report = state.get("export_report", {})
        report_counts = dict(export_report.get("counts", {}))
        report_validation = dict(export_report.get("validation", {}))
        marker_count = sovereign_tab_vc._marker_count()
        active_markers = [
            region.name
            for region in globals.scene_regions
            if region.name.endswith("_ACTIVE")
        ]
        if len(active_markers) != 1:
            raise RuntimeError("Editor workflow probe expected one active Sovereign marker")
        editor_workflow_probe_state["sovereign_authoring_expected"] = {
            "scenario_id": state["scenario_id"],
            "name": state["name"],
            "map_seed": state["map_seed"],
            "author_notes": state["author_notes"],
            "victory_mode": state["victory_mode"],
            "setup_profile": state["setup_profile"],
            "starting_resource_preset": state["starting_resource_preset"],
            "p1_start": list(state["players"][0]["start"]),
            "p1_food": state["players"][0]["starting_resources"]["food"],
            "p2_start": list(state["players"][1]["start"]),
            "p2_food": state["players"][1]["starting_resources"]["food"],
            "placed_resources": [
                dict(resource)
                for resource in state["placed_resources"]
            ],
            "placed_objects": [
                dict(obj)
                for obj in state["placed_objects"]
            ],
            "marker_count": marker_count,
            "active_marker": active_markers[0],
            "palette_scaling": True,
            "stress_counts": stress_counts,
            "validation_scaling": True,
            "validation_navigation": True,
            "export_report_counts": report_counts,
            "export_report_validation": report_validation,
        }
    elif name == "save_as_confirm":
        output_dir = _editor_workflow_probe_output_dir()
        map_path = os.path.join(output_dir, "editor_workflow_probe.pfmap")
        scene_path = os.path.join(output_dir, "editor_workflow_probe.pfscene")
        editor_workflow_probe_state["map_path"] = map_path
        editor_workflow_probe_state["scene_path"] = scene_path
        pf.global_event(EVENT_FILE_CHOOSER_OKAY, (map_path, scene_path))
    elif name == "validate_saved_files":
        map_path = editor_workflow_probe_state["map_path"]
        scene_path = editor_workflow_probe_state["scene_path"]
        saved_map = map.Map.from_filepath(map_path)
        if saved_map is None:
            raise RuntimeError("Editor workflow probe failed to parse saved map")
        tile = saved_map.tile_at_coords(*editor_workflow_probe_state["mutated_tile"])
        if tile.top_mat_idx != 3:
            raise RuntimeError("Editor workflow probe saved wrong terrain material index")
        saved_objects = _editor_workflow_probe_scene_entity_count(scene_path)
        if saved_objects < editor_workflow_probe_state["placed_objects"]:
            raise RuntimeError("Editor workflow probe saved too few objects")
        editor_workflow_probe_state["saved_objects"] = saved_objects
        if os.environ.get("PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT") == "1":
            from sovereign.editor_scenario import get_editor_authoring_state, scenario_path_for_map
            from sovereign.scenario import load_scenario, validate_scenario
            sidecar_path = scenario_path_for_map(map_path)
            if not os.path.exists(sidecar_path):
                raise RuntimeError("Editor workflow probe did not save Sovereign sidecar")
            scenario_errors = validate_scenario(load_scenario(sidecar_path))
            if scenario_errors:
                raise RuntimeError(
                    "Editor workflow probe saved invalid Sovereign sidecar: {0}".format(
                        "; ".join(scenario_errors)
                    )
                )
            scenario_doc = load_scenario(sidecar_path)
            expected = editor_workflow_probe_state.get("sovereign_authoring_expected")
            if expected:
                if scenario_doc["id"] != expected["scenario_id"]:
                    raise RuntimeError("Editor workflow probe saved wrong Sovereign scenario id")
                if scenario_doc["name"] != expected["name"]:
                    raise RuntimeError("Editor workflow probe saved wrong Sovereign scenario name")
                if scenario_doc.get("metadata", {}).get("map_seed") != expected["map_seed"]:
                    raise RuntimeError("Editor workflow probe saved wrong Sovereign map seed")
                if scenario_doc.get("metadata", {}).get("author_notes") != expected["author_notes"]:
                    raise RuntimeError("Editor workflow probe saved wrong Sovereign author notes")
                if scenario_doc.get("victory", {}).get("mode") != expected["victory_mode"]:
                    raise RuntimeError("Editor workflow probe saved wrong Sovereign victory mode")
                if scenario_doc.get("victory", {}).get("label") != "Conquest":
                    raise RuntimeError("Editor workflow probe saved wrong Sovereign victory label")
                if scenario_doc.get("setup", {}).get("profile") != expected["setup_profile"]:
                    raise RuntimeError("Editor workflow probe saved wrong Sovereign setup profile")
                if scenario_doc.get("setup", {}).get("starting_resource_preset") != expected["starting_resource_preset"]:
                    raise RuntimeError("Editor workflow probe saved wrong Sovereign resource preset")
                if scenario_doc.get("setup", {}).get("victory_mode") != expected["victory_mode"]:
                    raise RuntimeError("Editor workflow probe saved wrong Sovereign setup victory mode")
                if scenario_doc["players"][0]["start"] != expected["p1_start"]:
                    raise RuntimeError("Editor workflow probe saved wrong player 1 start")
                if scenario_doc["players"][0]["starting_resources"]["food"] != expected["p1_food"]:
                    raise RuntimeError("Editor workflow probe saved wrong player 1 food")
                if scenario_doc["players"][1]["start"] != expected["p2_start"]:
                    raise RuntimeError("Editor workflow probe saved wrong player 2 start")
                if scenario_doc["players"][1]["starting_resources"]["food"] != expected["p2_food"]:
                    raise RuntimeError("Editor workflow probe saved wrong player 2 food")
                if scenario_doc.get("placed_resources") != expected["placed_resources"]:
                    raise RuntimeError("Editor workflow probe saved wrong placed resource metadata")
                if scenario_doc.get("placed_objects") != expected["placed_objects"]:
                    raise RuntimeError("Editor workflow probe saved wrong placed object metadata")
                if expected["marker_count"] != (
                    len(scenario_doc["players"])
                    + len(scenario_doc.get("placed_resources", []))
                    + len(scenario_doc.get("placed_objects", []))
                ):
                    raise RuntimeError("Editor workflow probe built wrong Sovereign marker count")
                if not expected.get("validation_navigation"):
                    raise RuntimeError("Editor workflow probe did not validate Sovereign issue navigation")
                if not expected.get("palette_scaling") or not expected.get("validation_scaling"):
                    raise RuntimeError("Editor workflow probe did not validate palette/summary scaling")
                stress_counts = expected.get("stress_counts")
                if stress_counts:
                    if len(scenario_doc.get("players", [])) != stress_counts["players"]:
                        raise RuntimeError("Editor workflow probe saved wrong stress player count")
                    if len(scenario_doc.get("placed_resources", [])) != stress_counts["placed_resources"]:
                        raise RuntimeError("Editor workflow probe saved wrong stress resource count")
                    if len(scenario_doc.get("placed_objects", [])) != stress_counts["placed_objects"]:
                        raise RuntimeError("Editor workflow probe saved wrong stress object count")
                report = scenario_doc.get("export_report", {})
                report_counts = report.get("counts", {})
                report_validation = report.get("validation", {})
                report_setup = report.get("setup", {})
                expected_markers = (
                    len(scenario_doc["players"])
                    + len(scenario_doc.get("placed_resources", []))
                    + len(scenario_doc.get("placed_objects", []))
                )
                if report_setup.get("profile") != expected["setup_profile"]:
                    raise RuntimeError("Editor workflow probe saved wrong report setup profile")
                if report_setup.get("starting_resource_preset") != expected["starting_resource_preset"]:
                    raise RuntimeError("Editor workflow probe saved wrong report resource preset")
                if report_counts.get("players") != len(scenario_doc["players"]):
                    raise RuntimeError("Editor workflow probe saved wrong report player count")
                if report_counts.get("resource_clusters") != len(scenario_doc.get("placed_resources", [])):
                    raise RuntimeError("Editor workflow probe saved wrong report resource count")
                if report_counts.get("placed_objects") != len(scenario_doc.get("placed_objects", [])):
                    raise RuntimeError("Editor workflow probe saved wrong report object count")
                if report_counts.get("markers") != expected_markers:
                    raise RuntimeError("Editor workflow probe saved wrong report marker count")
                if report_validation.get("status") != "ready" or report_validation.get("issue_count") != 0:
                    raise RuntimeError("Editor workflow probe saved wrong report validation status")
                if not expected.get("active_marker", "").endswith("_ACTIVE"):
                    raise RuntimeError("Editor workflow probe did not mark active Sovereign marker")
                editor_workflow_probe_state["sovereign_marker_count"] = expected["marker_count"]
                export_status = get_editor_authoring_state().get("export_status", {})
                if export_status.get("state") != "saved":
                    raise RuntimeError("Editor workflow probe did not record Sovereign export success")
                if export_status.get("path") != sidecar_path:
                    raise RuntimeError("Editor workflow probe saved wrong Sovereign export path")
                if "resource cluster" not in export_status.get("message", ""):
                    raise RuntimeError("Editor workflow probe saved weak Sovereign export message")
                if "seed" not in export_status.get("message", "") or "marker" not in export_status.get("message", ""):
                    raise RuntimeError("Editor workflow probe saved weak Sovereign report message")
            editor_workflow_probe_state["sovereign_sidecar_path"] = sidecar_path

    marker = "EDITOR_WORKFLOW_STEP_DONE tick={0} name={1}".format(editor_probe_ticks, name)
    print(marker)
    sys.stdout.flush()
    _append_probe_trace(os.environ.get("PF_EDITOR_WORKFLOW_PROBE_TRACE_PATH"), marker)


def on_editor_workflow_probe_update(user, event):
    del user
    del event

    global editor_probe_ticks
    editor_probe_ticks += 1

    if os.environ.get("PF_EDITOR_WORKFLOW_PROBE_RELOAD_ONLY") == "1":
        expected = int(os.environ.get("PF_EDITOR_WORKFLOW_PROBE_EXPECT_OBJECTS", "0"))
        if expected and len(globals.active_objects_list) < expected:
            raise RuntimeError("Editor workflow reload probe loaded too few objects")

        if os.environ.get("PF_EDITOR_SOVEREIGN_AUTHORING_RELOAD_PROBE") == "1" \
        and not editor_workflow_probe_state.get("sovereign_reload_checked"):
            from sovereign.editor_scenario import get_editor_authoring_state, scenario_path_for_map
            from sovereign.scenario import load_scenario

            if sovereign_tab_vc is None:
                raise RuntimeError("Editor workflow reload probe expected Sovereign tab")
            map_path = editor_workflow_probe_state.get("loaded_map_path")
            sidecar_path = scenario_path_for_map(map_path)
            state = get_editor_authoring_state()
            status = state.get("export_status", {})
            if status.get("state") != "loaded":
                raise RuntimeError("Editor workflow reload probe did not import Sovereign sidecar")
            if status.get("path") != sidecar_path:
                raise RuntimeError("Editor workflow reload probe imported wrong Sovereign sidecar")

            scenario_doc = load_scenario(sidecar_path)
            if state.get("scenario_id") != scenario_doc.get("id"):
                raise RuntimeError("Editor workflow reload probe imported wrong scenario id")
            if state.get("name") != scenario_doc.get("name"):
                raise RuntimeError("Editor workflow reload probe imported wrong scenario name")
            if state.get("map_seed") != scenario_doc.get("metadata", {}).get("map_seed"):
                raise RuntimeError("Editor workflow reload probe imported wrong map seed")
            if state.get("author_notes") != scenario_doc.get("metadata", {}).get("author_notes"):
                raise RuntimeError("Editor workflow reload probe imported wrong author notes")
            if state.get("victory_mode") != scenario_doc.get("victory", {}).get("mode"):
                raise RuntimeError("Editor workflow reload probe imported wrong victory mode")
            if state.get("setup_profile") != scenario_doc.get("setup", {}).get("profile"):
                raise RuntimeError("Editor workflow reload probe imported wrong setup profile")
            if state.get("starting_resource_preset") != scenario_doc.get("setup", {}).get("starting_resource_preset"):
                raise RuntimeError("Editor workflow reload probe imported wrong resource preset")
            if state.get("players") != scenario_doc.get("players"):
                raise RuntimeError("Editor workflow reload probe imported wrong player metadata")
            if state.get("palette") != scenario_doc.get("palette"):
                raise RuntimeError("Editor workflow reload probe imported wrong palette metadata")
            if state.get("placed_resources") != scenario_doc.get("placed_resources"):
                raise RuntimeError("Editor workflow reload probe imported wrong resource metadata")
            if state.get("placed_objects") != scenario_doc.get("placed_objects"):
                raise RuntimeError("Editor workflow reload probe imported wrong object metadata")
            if state.get("export_report", {}).get("counts") != scenario_doc.get("export_report", {}).get("counts"):
                raise RuntimeError("Editor workflow reload probe imported wrong export report counts")

            _editor_select_tab(3)
            marker_count = sovereign_tab_vc._marker_count()
            expected_markers = (
                len(scenario_doc.get("players", []))
                + len(scenario_doc.get("placed_resources", []))
                + len(scenario_doc.get("placed_objects", []))
            )
            if marker_count != expected_markers:
                raise RuntimeError("Editor workflow reload probe built wrong imported marker count")
            editor_workflow_probe_state["sovereign_sidecar_path"] = sidecar_path
            editor_workflow_probe_state["sovereign_marker_count"] = marker_count
            editor_workflow_probe_state["sovereign_reload_checked"] = True

        quit_after = int(os.environ.get("PF_EDITOR_WORKFLOW_PROBE_QUIT_AFTER", "12"))
        if editor_probe_ticks < quit_after:
            return

        marker = _editor_workflow_reload_probe_marker()
        print(marker)
        probe_path = os.environ.get("PF_EDITOR_WORKFLOW_PROBE_PATH")
        if probe_path:
            _write_probe_file(probe_path, marker)
        if os.environ.get("PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT") == "1":
            sys.stdout.flush()
            os._exit(0)
        return

    steps = [(6, "mutate")]
    if os.environ.get("PF_EDITOR_SOVEREIGN_AUTHORING_PROBE") == "1":
        steps.append((10, "sovereign_authoring"))
    steps.extend((
        (12, "save_as_show"),
        (18, "save_as_confirm"),
        (30, "validate_saved_files"),
    ))

    for tick, name in steps:
        if editor_probe_ticks >= tick and name not in editor_workflow_probe_steps_done:
            _run_editor_workflow_probe_step(name)
            editor_workflow_probe_steps_done.add(name)

    quit_after = int(os.environ.get("PF_EDITOR_WORKFLOW_PROBE_QUIT_AFTER", "45"))
    if editor_probe_ticks < quit_after:
        return

    marker = _editor_workflow_probe_marker()
    print(marker)
    probe_path = os.environ.get("PF_EDITOR_WORKFLOW_PROBE_PATH")
    if probe_path:
        _write_probe_file(probe_path, marker)
    if os.environ.get("PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT") == "1":
        sys.stdout.flush()
        os._exit(0)


def install_editor_probe():
    if os.environ.get("PF_EDITOR_VISUAL_PROBE") == "1":
        pf.register_event_handler(pf.EVENT_UPDATE_START, on_editor_visual_probe_update, None)
    elif os.environ.get("PF_EDITOR_WORKFLOW_PROBE") == "1":
        pf.register_event_handler(pf.EVENT_UPDATE_START, on_editor_workflow_probe_update, None)
    elif os.environ.get("PF_EDITOR_FEATURE_PROBE") == "1":
        pf.register_event_handler(pf.EVENT_UPDATE_START, on_editor_feature_probe_update, None)
    elif os.environ.get("PF_EDITOR_LAUNCH_PROBE") == "1":
        pf.register_event_handler(pf.EVENT_UPDATE_START, on_editor_probe_update, None)

############################################################
# Global settings                                          #
############################################################

pf.set_ambient_light_color((1.0, 1.0, 1.0))
pf.set_emit_light_color((1.0, 1.0, 1.0))
pf.set_emit_light_pos((1664.0, 1024.0, 384.0))

pf.set_active_font("OptimusPrinceps.ttf")
pf.disable_unit_selection()
pf.disable_fog_of_war()

mouse_events.install()

############################################################
# Setup Map, Scene                                         #
############################################################

editor_loaded_map_path = None
if len(sys.argv) > 1:
    map_path = sys.argv[1]
    if os.path.isabs(map_path):
        pf.load_map(os.path.dirname(map_path), os.path.basename(map_path), update_navgrid=False)
        globals.active_map = map.Map.from_filepath(map_path)
        editor_loaded_map_path = map_path
    else:
        pf.load_map(pf.get_basedir(), map_path, update_navgrid=False)
        globals.active_map = map.Map.from_filepath(pf.get_basedir() + "/" + map_path)
        editor_loaded_map_path = map_path
else:
    pf.load_map_string(globals.active_map.pfmap_str(), update_navgrid=False)

if os.environ.get("PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT") == "1" and editor_loaded_map_path:
    from sovereign.editor_scenario import load_editor_scenario
    imported_authoring = load_editor_scenario(editor_loaded_map_path)
    if imported_authoring is not None:
        print("EDITOR_SOVEREIGN_SCENARIO_LOADED {0}".format(imported_authoring["export_status"]["path"]))
        sys.stdout.flush()

editor_workflow_probe_state["loaded_map_path"] = editor_loaded_map_path

if len(sys.argv) > 2:
    loaded_scene = pf.load_scene(sys.argv[2], update_navgrid=False)
    globals.active_objects_list = loaded_scene[0]
    globals.scene_filename = sys.argv[2]
    for obj in globals.active_objects_list:
        obj.selectable = True
else:
    pf.add_faction(DEFAULT_FACTION_NAME, DEFAULT_FACTION_COLOR)

############################################################
# Setup UI                                                 #
############################################################

minimap_pos = pf.get_minimap_position()
pf.set_minimap_position(UI_LEFT_PANE_WIDTH + minimap_pos[0], minimap_pos[1])

terrain_tab_vc = ttvc.TerrainTabVC(ttw.TerrainTabWindow())
objects_tab_vc = otvc.ObjectsVC(otw.ObjectsTabWindow())
diplo_tab_vc = dtvc.DiplomacyVC(dtw.DiplomacyTabWindow())
sovereign_tab_vc = None

tab_bar_vc = tbvc.TabBarVC(tbw.TabBarWindow(), EVENT_TOP_TAB_SELECTION_CHANGED)
tab_bar_vc.push_child("Terrain", terrain_tab_vc)
tab_bar_vc.push_child("Objects", objects_tab_vc)
tab_bar_vc.push_child("Diplomacy", diplo_tab_vc)
if os.environ.get("PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT") == "1":
    sovereign_tab_vc = srvc.SovereignTabVC(srw.SovereignTabWindow())
    tab_bar_vc.push_child("Sovereign", sovereign_tab_vc)
tab_bar_vc.activate()
tab_bar_vc.view.show()

menu = mw.Menu()
menuvc = mvc.MenuVC(menu)
menuvc.activate()

mb = mw.MenuButtonWindow(menu)
mb.show()

install_editor_probe()
