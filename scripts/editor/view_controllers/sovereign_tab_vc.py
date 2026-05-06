import pf

import common.view_controllers.view_controller as vc
import globals as editor_globals
import mouse_events
from sovereign.editor_scenario import get_editor_authoring_state


class SovereignTabVC(vc.ViewController):

    def __init__(self, view):
        self.view = view
        self._marker_signature = None

    def _apply_point(self, point):
        state = get_editor_authoring_state()
        placement = state["selected_placement"]
        xz = [round(float(point[0]), 2), round(float(point[1]), 2)]
        if placement["kind"] == "player_start":
            player_id = placement["player_id"]
            for player in state["players"]:
                if player["id"] == player_id:
                    player["start"] = xz
                    self._sync_markers()
                    return
            raise RuntimeError("unknown Sovereign player id {0}".format(player_id))

        if placement["kind"] == "resource":
            resource_idx = int(placement["resource_index"])
            state["placed_resources"][resource_idx]["point"] = xz
            self._sync_markers()
            return

        object_idx = int(placement["object_index"])
        state["placed_objects"][object_idx]["point"] = xz
        self._sync_markers()

    def _selected_marker_key(self, state):
        placement = state["selected_placement"]
        if placement.get("kind") == "player_start":
            return ("start", placement.get("player_id"))
        if placement.get("kind") == "resource":
            return ("resource", int(placement.get("resource_index", -1)))
        if placement.get("kind") in ("unit", "building"):
            return ("object", int(placement.get("object_index", -1)))
        return None

    def _marker_signature_for_state(self, state):
        signature = [("selected", self._selected_marker_key(state))]
        for player in state["players"]:
            signature.append(("start", player["id"], tuple(player["start"])))
        for idx, resource in enumerate(state["placed_resources"]):
            signature.append((
                "resource",
                idx,
                resource["id"],
                resource["resource_id"],
                tuple(resource["point"]),
            ))
        for idx, obj in enumerate(state["placed_objects"]):
            signature.append((
                "object",
                idx,
                obj["id"],
                obj["kind"],
                obj["object_id"],
                obj["owner_player_id"],
                tuple(obj["point"]),
            ))
        return tuple(signature)

    def _marker_region(self, name, point, radius, active=False):
        region = pf.Region(
            type=pf.REGION_CIRCLE,
            name="{0}_ACTIVE".format(name) if active else name,
            position=(float(point[0]), float(point[1])),
            radius=radius + 1.2 if active else radius,
        )
        region.shown = True
        return region

    def _sync_markers(self):
        state = get_editor_authoring_state()
        signature = self._marker_signature_for_state(state)
        if signature == self._marker_signature:
            return

        editor_globals.scene_regions = []
        markers = []
        selected_marker = self._selected_marker_key(state)
        for player in state["players"]:
            markers.append(self._marker_region(
                "SR_Start_P{0}".format(player["id"]),
                player["start"],
                4.0,
                active=selected_marker == ("start", player["id"]),
            ))
        for idx, resource in enumerate(state["placed_resources"]):
            markers.append(self._marker_region(
                "SR_Res_{0}_{1}".format(idx + 1, resource["resource_id"]),
                resource["point"],
                2.8,
                active=selected_marker == ("resource", idx),
            ))
        for idx, obj in enumerate(state["placed_objects"]):
            markers.append(self._marker_region(
                "SR_{0}_{1}_{2}".format(obj["kind"].capitalize(), idx + 1, obj["object_id"]),
                obj["point"],
                3.2,
                active=selected_marker == ("object", idx),
            ))
        editor_globals.scene_regions = markers
        self._marker_signature = signature

    def _clear_markers(self):
        editor_globals.scene_regions = []
        self._marker_signature = None

    def _marker_count(self):
        self._sync_markers()
        return len(editor_globals.scene_regions)

    def __on_click(self, event):
        if event[0] != pf.SDL_BUTTON_LEFT:
            return
        if not mouse_events.mouse_over_map:
            return
        pos = pf.map_pos_under_cursor()
        if pos is None:
            return
        self._apply_point((pos[0], pos[2]))

    def __on_update(self, event):
        del event
        self._sync_markers()

    def activate(self):
        pf.register_event_handler(pf.SDL_MOUSEBUTTONDOWN, SovereignTabVC.__on_click, self)
        pf.register_event_handler(pf.EVENT_UPDATE_START, SovereignTabVC.__on_update, self)
        self._sync_markers()

    def deactivate(self):
        pf.unregister_event_handler(pf.SDL_MOUSEBUTTONDOWN, SovereignTabVC.__on_click)
        pf.unregister_event_handler(pf.EVENT_UPDATE_START, SovereignTabVC.__on_update)
        self._clear_markers()
