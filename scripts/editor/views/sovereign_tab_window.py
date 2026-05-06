import pf
from constants import *

from sovereign.data.buildings import BUILDINGS
from sovereign.data.civilizations import CIVILIZATIONS
from sovereign.data.resources import RESOURCES
from sovereign.data.units import UNITS
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
from sovereign.scenario import DEFAULT_SETUP_PROFILE, SETUP_PROFILES, STARTING_RESOURCE_PRESETS


RESOURCE_IDS = ("food", "wood", "gold", "stone")
PLACEMENT_KINDS = ("player_start", "resource", "unit", "building")
PLACEMENT_LABELS = ("Start", "Resource", "Unit", "Building")
PALETTE_GROUPS = (
    ("unit", "units", "Units"),
    ("building", "buildings", "Buildings"),
    ("resource", "resources", "Resources"),
)
VALIDATION_GROUPS = (
    ("player_start", "Starts"),
    ("resource", "Resources"),
    ("object", "Objects"),
    ("other", "Other"),
)


class SovereignTabWindow(pf.Window):

    def __init__(self):
        vresx, vresy = (1920, 1080)
        super(SovereignTabWindow, self).__init__(
            "SovereignTab",
            (0, UI_TOP_PANE_Y, UI_LEFT_PANE_WIDTH, vresy - UI_TOP_PANE_Y),
            pf.NK_WINDOW_BORDER,
            (vresx, vresy),
            resize_mask=pf.ANCHOR_X_LEFT | pf.ANCHOR_Y_TOP | pf.ANCHOR_Y_BOT,
        )
        self.selected_player_idx = 0
        self.diplomacy_idx = 0
        self.placement_idx = 0
        self.selected_resource_idx = 0
        self.selected_object_idx = 0
        self.palette_filter = ""
        self.palette_show_units = True
        self.palette_show_buildings = True
        self.palette_show_resources = True

    def _select_validation_issue(self, issue_idx):
        selected = select_validation_issue(issue_idx)
        if selected is None:
            return
        if selected["kind"] == "player_start":
            self.selected_player_idx = selected["player_index"]
            self.placement_idx = 0
        elif selected["kind"] == "resource":
            self.selected_resource_idx = selected["resource_index"]
            self.placement_idx = 1
        elif selected["kind"] == "object":
            self.selected_object_idx = selected["object_index"]
            self.placement_idx = 2 if selected.get("placement_kind") == "unit" else 3

    def _ids_preview(self, ids, limit=3):
        shown = list(ids[:limit])
        suffix = "" if len(ids) <= limit else " +{0}".format(len(ids) - limit)
        return ", ".join(shown) + suffix

    def _validation_counts(self, issues):
        counts = {"player_start": 0, "resource": 0, "object": 0, "other": 0}
        for issue in issues:
            key = issue.get("target_kind") or "other"
            counts[key if key in counts else "other"] += 1
        return counts

    def _first_validation_issue_index(self, issues, kind):
        for idx, issue in enumerate(issues):
            key = issue.get("target_kind") or "other"
            if key == kind:
                return idx
        return None

    def _palette_definition(self, kind, item_id):
        if kind == "unit":
            return UNITS.get(item_id, {})
        if kind == "building":
            return BUILDINGS.get(item_id, {})
        return RESOURCES.get(item_id, {})

    def _palette_group_enabled(self, kind):
        if kind == "unit":
            return self.palette_show_units
        if kind == "building":
            return self.palette_show_buildings
        if kind == "resource":
            return self.palette_show_resources
        return True

    def _matches_palette_filter(self, kind, item_id, query):
        if not query:
            return True
        definition = self._palette_definition(kind, item_id)
        search_values = [
            item_id,
            definition.get("display_name", ""),
            definition.get("role", ""),
            definition.get("archetype", ""),
        ]
        asset = definition.get("asset", {})
        if not asset:
            asset = definition.get("node", {}).get("asset", {})
        search_values.extend([
            asset.get("path", ""),
            asset.get("pfobj", ""),
        ])
        return any(query in str(value).lower() for value in search_values)

    def _filtered_palette_entries(self, state):
        query = (self.palette_filter or "").strip().lower()
        entries = []
        for kind, palette_key, label in PALETTE_GROUPS:
            if not self._palette_group_enabled(kind):
                continue
            for item_id in state["palette"].get(palette_key, []):
                if self._matches_palette_filter(kind, item_id, query):
                    definition = self._palette_definition(kind, item_id)
                    entries.append({
                        "kind": kind,
                        "label": label[:-1] if label.endswith("s") else label,
                        "id": item_id,
                        "display_name": definition.get("display_name", item_id),
                    })
        return entries

    def _palette_entry_counts(self, entries):
        counts = {"unit": 0, "building": 0, "resource": 0}
        for entry in entries:
            counts[entry["kind"]] += 1
        return counts

    def _cost_text(self, definition):
        cost = definition.get("cost", {})
        if not cost:
            return "Cost: none"
        parts = [
            "{0} {1}".format(amount, resource_id)
            for resource_id, amount in sorted(cost.items())
        ]
        return "Cost: " + ", ".join(parts)

    def _preset_resource_text(self, preset_id):
        preset = STARTING_RESOURCE_PRESETS[preset_id]
        resources = preset.get("resources", {})
        parts = [
            "{0} {1}".format(int(resources.get(resource_id, 0)), resource_id)
            for resource_id in RESOURCE_IDS
        ]
        return ", ".join(parts)

    def _asset_text(self, definition):
        asset = definition.get("asset", {})
        if not asset:
            node = definition.get("node", {})
            asset = node.get("asset", {})
        if not asset:
            return "Asset: none"
        return "Asset: {0}/{1}".format(asset.get("path", "?"), asset.get("pfobj", "?"))

    def _selected_preview_lines(self, state, obj, resource):
        placement_kind = state["selected_placement"].get("kind")
        if placement_kind == "resource":
            resource_def = {}
            if resource is not None:
                resource_def = RESOURCES.get(resource["resource_id"], {})
            node = resource_def.get("node", {})
            return [
                "Resource: {0}".format(resource_def.get("display_name", resource["resource_id"])),
                "Amount: {0} | Owner: {1}".format(resource["amount"], resource.get("owner_player_id", 0)),
                "Radius: {0}".format(node.get("selection_radius", "?")),
                self._asset_text(resource_def),
            ]

        if placement_kind in ("unit", "building") and obj is not None:
            definitions = UNITS if obj["kind"] == "unit" else BUILDINGS
            definition = definitions.get(obj["object_id"], {})
            lines = [
                "{0}: {1}".format(
                    obj["kind"].capitalize(),
                    definition.get("display_name", obj["object_id"]),
                ),
                "Role: {0} | HP: {1}".format(
                    definition.get("role", definition.get("archetype", "?")),
                    definition.get("hp", "?"),
                ),
                self._cost_text(definition),
            ]
            if obj["kind"] == "unit":
                attack = (definition.get("attacks") or [{}])[0]
                lines.append("Pop: {0} | Range: {1}".format(
                    definition.get("population", "?"),
                    attack.get("range", "?"),
                ))
            else:
                lines.append("Footprint: {0} | Pop+: {1}".format(
                    "x".join(str(value) for value in definition.get("footprint", ["?", "?"])),
                    definition.get("population_provided", 0),
                ))
            lines.append(self._asset_text(definition))
            return lines

        player_id = state["selected_placement"].get("player_id")
        player = None
        for candidate in state["players"]:
            if candidate["id"] == player_id:
                player = candidate
                break
        if player is None:
            player = state["players"][0]
        return [
            "Start: Player {0}".format(player["id"]),
            "Name: {0}".format(player["name"]),
            "Point: [{0:.1f}, {1:.1f}]".format(float(player["start"][0]), float(player["start"][1])),
            "Civilization: {0}".format(player["civilization_id"]),
        ]

    def _selected_preview_group(self, state, obj, resource):
        self.layout_row_static(20, UI_LEFT_PANE_WIDTH - 60, 1)
        for line in self._selected_preview_lines(state, obj, resource)[:5]:
            self.label_colored_wrap(line, (210, 210, 210))

    def _selected_player(self, state):
        players = state["players"]
        if self.selected_player_idx >= len(players):
            self.selected_player_idx = max(0, len(players) - 1)
        return players[self.selected_player_idx]

    def _palette_group(self, state):
        entries = self._filtered_palette_entries(state)
        counts = self._palette_entry_counts(entries)
        self.layout_row_static(20, UI_LEFT_PANE_WIDTH - 60, 1)
        self.label_colored_wrap(
            "Filtered: U {0} | B {1} | R {2}".format(
                counts["unit"],
                counts["building"],
                counts["resource"],
            ),
            (210, 210, 210),
        )
        if not entries:
            self.label_colored_wrap("No palette matches", (210, 210, 210))
            return
        for entry in entries[:5]:
            self.label_colored_wrap(
                "{0}: {1} ({2})".format(entry["label"], entry["display_name"], entry["id"]),
                (210, 210, 210),
            )
        if len(entries) > 5:
            self.label_colored_wrap("+{0} more matched entries".format(len(entries) - 5), (180, 180, 180))

    def _selected_resource(self, state):
        resources = state["placed_resources"]
        if self.selected_resource_idx >= len(resources):
            self.selected_resource_idx = max(0, len(resources) - 1)
        return resources[self.selected_resource_idx]

    def _selected_object(self, state):
        objects = state["placed_objects"]
        if self.selected_object_idx >= len(objects):
            self.selected_object_idx = max(0, len(objects) - 1)
        return objects[self.selected_object_idx]

    def _object_ids_for_kind(self, state, kind):
        if kind == "unit":
            return [unit_id for unit_id in state["palette"]["units"] if unit_id in UNITS]
        return [building_id for building_id in state["palette"]["buildings"] if building_id in BUILDINGS]

    def update(self):
        state = get_editor_authoring_state()
        players = state["players"]

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Sovereign Scenario:", (255, 255, 255))
        self.layout_row_dynamic(28, 1)
        state["name"] = self.edit_string(pf.NK_EDIT_SIMPLE, state.get("name") or "")

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Scenario ID:", (255, 255, 255))
        self.layout_row_dynamic(28, 1)
        state["scenario_id"] = self.edit_string(pf.NK_EDIT_SIMPLE, state.get("scenario_id") or "")

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Map Seed:", (255, 255, 255))
        self.layout_row_dynamic(24, 1)
        state["map_seed"] = self.property_int(
            "Seed",
            0,
            2147483647,
            int(state.get("map_seed", 0)),
            1,
            1.0,
        )

        profile_ids = sorted(SETUP_PROFILES.keys())
        setup_profile = state.get("setup_profile") or DEFAULT_SETUP_PROFILE
        if setup_profile not in profile_ids:
            setup_profile = DEFAULT_SETUP_PROFILE
        profile_idx = profile_ids.index(setup_profile)
        profile_labels = [
            SETUP_PROFILES[profile_id]["label"]
            for profile_id in profile_ids
        ]
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Setup Profile:", (255, 255, 255))
        self.layout_row_dynamic(25, 1)
        profile_idx = self.combo_box(profile_labels, profile_idx, 25, (UI_LEFT_PANE_WIDTH - 30, 150))
        setup_profile = profile_ids[profile_idx]
        state["setup_profile"] = setup_profile

        preset_ids = sorted(STARTING_RESOURCE_PRESETS.keys())
        preset_id = state.get("starting_resource_preset") or SETUP_PROFILES[setup_profile]["starting_resource_preset"]
        if preset_id not in preset_ids:
            preset_id = SETUP_PROFILES[setup_profile]["starting_resource_preset"]
        preset_idx = preset_ids.index(preset_id)
        preset_labels = [
            STARTING_RESOURCE_PRESETS[preset]["label"]
            for preset in preset_ids
        ]
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Resource Preset:", (255, 255, 255))
        self.layout_row_dynamic(25, 1)
        preset_idx = self.combo_box(preset_labels, preset_idx, 25, (UI_LEFT_PANE_WIDTH - 30, 150))
        preset_id = preset_ids[preset_idx]
        state["starting_resource_preset"] = preset_id
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Preset: {0}".format(self._preset_resource_text(preset_id)), (180, 220, 255))

        state["victory_mode"] = "conquest"
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Victory: Conquest", (180, 220, 255))

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Author Notes:", (255, 255, 255))
        self.layout_row_dynamic(28, 1)
        state["author_notes"] = self.edit_string(pf.NK_EDIT_SIMPLE, state.get("author_notes") or "")

        resource_count = len(state["placed_resources"])
        object_count = len(state["placed_objects"])
        unit_count = len([obj for obj in state["placed_objects"] if obj.get("kind") == "unit"])
        building_count = object_count - unit_count
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap(
            "Scenario: {0} players | {1} resources | {2} units | {3} buildings".format(
                len(players),
                resource_count,
                unit_count,
                building_count,
            ),
            (180, 220, 255),
        )

        export_status = state.get("export_status", {})
        export_state = export_status.get("state", "not_saved")
        export_color = (80, 220, 120) if export_state == "saved" else (255, 80, 80) if export_state == "error" else (210, 210, 210)
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Sidecar: {0}".format(export_state.replace("_", " ")), export_color)
        if export_status.get("path"):
            self.layout_row_dynamic(20, 1)
            self.label_colored_wrap(export_status["path"], (180, 180, 180))
        if export_status.get("message"):
            self.layout_row_dynamic(20, 1)
            self.label_colored_wrap(export_status["message"], export_color)

        export_report = state.get("export_report", {})
        report_counts = export_report.get("counts", {})
        report_validation = export_report.get("validation", {})
        if report_counts:
            self.layout_row_dynamic(20, 1)
            self.label_colored_wrap(
                "Report: {0}p | {1} res | {2} obj | {3} markers".format(
                    report_counts.get("players", 0),
                    report_counts.get("resource_clusters", 0),
                    report_counts.get("placed_objects", 0),
                    report_counts.get("markers", 0),
                ),
                (180, 220, 255),
            )
            self.layout_row_dynamic(20, 1)
            self.label_colored_wrap(
                "Validation Report: {0} ({1})".format(
                    report_validation.get("status", "unknown"),
                    report_validation.get("issue_count", 0),
                ),
                (80, 220, 120) if report_validation.get("status") == "ready" else (255, 80, 80),
            )

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Player:", (255, 255, 255))
        self.layout_row_dynamic(25, 1)
        player_labels = [
            "{0}: {1}".format(player["id"], player["name"])
            for player in players
        ]
        self.selected_player_idx = self.combo_box(
            player_labels,
            self.selected_player_idx,
            25,
            (UI_LEFT_PANE_WIDTH - 30, 160),
        )
        player = self._selected_player(state)

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Name:", (255, 255, 255))
        self.layout_row_dynamic(28, 1)
        player["name"] = self.edit_string(pf.NK_EDIT_SIMPLE, player["name"])

        civ_ids = sorted(CIVILIZATIONS.keys())
        civ_idx = civ_ids.index(player["civilization_id"]) if player["civilization_id"] in civ_ids else 0
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Civilization:", (255, 255, 255))
        self.layout_row_dynamic(25, 1)
        civ_idx = self.combo_box(civ_ids, civ_idx, 25, (UI_LEFT_PANE_WIDTH - 30, 140))
        player["civilization_id"] = civ_ids[civ_idx]

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Player Start:", (255, 255, 255))
        self.layout_row_dynamic(26, 1)
        player["start"][0] = self.property_float("X", -4096.0, 4096.0, float(player["start"][0]), 1.0, 0.5)
        self.layout_row_dynamic(26, 1)
        player["start"][1] = self.property_float("Z", -4096.0, 4096.0, float(player["start"][1]), 1.0, 0.5)
        self.layout_row_dynamic(24, 2)

        def on_duplicate_player():
            self.selected_player_idx = duplicate_player(self.selected_player_idx)

        def on_remove_player():
            self.selected_player_idx = remove_player(self.selected_player_idx)

        self.button_label("Duplicate Start", on_duplicate_player)
        self.button_label("Remove Start", on_remove_player)

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Placement Mode:", (255, 255, 255))
        old_placement = self.placement_idx
        placement_kind = state["selected_placement"]["kind"]
        self.placement_idx = PLACEMENT_KINDS.index(placement_kind) if placement_kind in PLACEMENT_KINDS else 0
        self.layout_row_dynamic(20, 2)
        for idx, label in enumerate(PLACEMENT_LABELS):
            if self.option_label(label, self.placement_idx == idx):
                self.placement_idx = idx
        if self.placement_idx != old_placement:
            state["selected_placement"]["kind"] = PLACEMENT_KINDS[self.placement_idx]

        state["selected_placement"]["player_id"] = player["id"]

        resources = state["placed_resources"]
        placement_resource_idx = int(state["selected_placement"].get("resource_index", self.selected_resource_idx))
        if 0 <= placement_resource_idx < len(resources):
            self.selected_resource_idx = placement_resource_idx
        resource_labels = [
            "{0}: {1}".format(idx + 1, resource["resource_id"])
            for idx, resource in enumerate(resources)
        ]
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Resource Cluster:", (255, 255, 255))
        self.layout_row_dynamic(25, 1)
        self.selected_resource_idx = self.combo_box(
            resource_labels,
            self.selected_resource_idx,
            25,
            (UI_LEFT_PANE_WIDTH - 30, 140),
        )
        resource = self._selected_resource(state)
        state["selected_placement"]["resource_index"] = self.selected_resource_idx
        self.layout_row_dynamic(24, 3)

        def on_add_resource():
            self.selected_resource_idx = add_placed_resource(resource["resource_id"], resource.get("owner_player_id", 0), resource["point"])

        def on_duplicate_resource():
            self.selected_resource_idx = duplicate_placed_resource(self.selected_resource_idx)

        def on_remove_resource():
            self.selected_resource_idx = remove_placed_resource(self.selected_resource_idx)

        self.button_label("Add", on_add_resource)
        self.button_label("Duplicate", on_duplicate_resource)
        self.button_label("Remove", on_remove_resource)
        resource = self._selected_resource(state)
        state["selected_placement"]["resource_index"] = self.selected_resource_idx

        owner_ids = [0] + [player_def["id"] for player_def in players]
        owner_labels = ["Neutral"] + [player_def["name"] for player_def in players]
        owner_idx = owner_ids.index(resource.get("owner_player_id", 0)) \
            if resource.get("owner_player_id", 0) in owner_ids else 0
        self.layout_row_dynamic(25, 1)
        owner_idx = self.combo_box(owner_labels, owner_idx, 25, (UI_LEFT_PANE_WIDTH - 30, 140))
        resource["owner_player_id"] = owner_ids[owner_idx]
        self.layout_row_dynamic(24, 1)
        resource["amount"] = self.property_int("Cluster Amount", 1, 5000, int(resource["amount"]), 10, 5.0)
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap(
            "Point: [{0:.1f}, {1:.1f}]".format(float(resource["point"][0]), float(resource["point"][1])),
            (200, 200, 0),
        )

        objects = state["placed_objects"]
        placement_object_idx = int(state["selected_placement"].get("object_index", self.selected_object_idx))
        if 0 <= placement_object_idx < len(objects):
            self.selected_object_idx = placement_object_idx
        object_labels = [
            "{0}: {1}".format(idx + 1, obj["id"])
            for idx, obj in enumerate(objects)
        ]
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Placed Object:", (255, 255, 255))
        self.layout_row_dynamic(25, 1)
        self.selected_object_idx = self.combo_box(
            object_labels,
            self.selected_object_idx,
            25,
            (UI_LEFT_PANE_WIDTH - 30, 140),
        )
        obj = self._selected_object(state)
        state["selected_placement"]["object_index"] = self.selected_object_idx
        if state["selected_placement"]["kind"] in ("unit", "building"):
            obj["kind"] = state["selected_placement"]["kind"]
        self.layout_row_dynamic(24, 3)

        def on_add_object():
            kind = state["selected_placement"]["kind"] if state["selected_placement"]["kind"] in ("unit", "building") else obj["kind"]
            self.selected_object_idx = add_placed_object(kind, obj["object_id"], obj.get("owner_player_id", player["id"]), obj["point"])

        def on_duplicate_object():
            self.selected_object_idx = duplicate_placed_object(self.selected_object_idx)

        def on_remove_object():
            self.selected_object_idx = remove_placed_object(self.selected_object_idx)

        self.button_label("Add", on_add_object)
        self.button_label("Duplicate", on_duplicate_object)
        self.button_label("Remove", on_remove_object)
        obj = self._selected_object(state)
        state["selected_placement"]["object_index"] = self.selected_object_idx
        if state["selected_placement"]["kind"] in ("unit", "building"):
            obj["kind"] = state["selected_placement"]["kind"]

        object_ids = self._object_ids_for_kind(state, obj["kind"])
        if not object_ids:
            object_ids = sorted(UNITS.keys() if obj["kind"] == "unit" else BUILDINGS.keys())
        object_idx = object_ids.index(obj["object_id"]) if obj["object_id"] in object_ids else 0
        self.layout_row_dynamic(25, 1)
        object_idx = self.combo_box(object_ids, object_idx, 25, (UI_LEFT_PANE_WIDTH - 30, 140))
        obj["object_id"] = object_ids[object_idx]

        object_owner_ids = [player_def["id"] for player_def in players]
        object_owner_labels = [player_def["name"] for player_def in players]
        object_owner_idx = object_owner_ids.index(obj.get("owner_player_id", player["id"])) \
            if obj.get("owner_player_id", player["id"]) in object_owner_ids else self.selected_player_idx
        self.layout_row_dynamic(25, 1)
        object_owner_idx = self.combo_box(object_owner_labels, object_owner_idx, 25, (UI_LEFT_PANE_WIDTH - 30, 140))
        obj["owner_player_id"] = object_owner_ids[object_owner_idx]
        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap(
            "Object Point: [{0:.1f}, {1:.1f}]".format(float(obj["point"][0]), float(obj["point"][1])),
            (200, 200, 0),
        )

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Starting Resources:", (255, 255, 255))
        for resource_id in RESOURCE_IDS:
            self.layout_row_dynamic(24, 1)
            amount = int(player["starting_resources"].get(resource_id, 0))
            player["starting_resources"][resource_id] = self.property_int(
                resource_id.capitalize(),
                0,
                5000,
                amount,
                10,
                5.0,
            )

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Diplomacy:", (255, 255, 255))
        old = self.diplomacy_idx
        self.diplomacy_idx = 0 if state.get("diplomacy_state") == "war" else 1
        self.layout_row_dynamic(20, 2)
        if self.option_label("War", self.diplomacy_idx == 0):
            self.diplomacy_idx = 0
        if self.option_label("Peace", self.diplomacy_idx == 1):
            self.diplomacy_idx = 1
        if self.diplomacy_idx != old:
            state["diplomacy_state"] = "war" if self.diplomacy_idx == 0 else "peace"

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Object Palette:", (255, 255, 255))
        self.layout_row_dynamic(28, 1)
        self.palette_filter = self.edit_string(pf.NK_EDIT_SIMPLE, self.palette_filter or "")
        self.layout_row_dynamic(20, 3)
        self.palette_show_units = bool(self.checkbox("Units", int(self.palette_show_units)))
        self.palette_show_buildings = bool(self.checkbox("Buildings", int(self.palette_show_buildings)))
        self.palette_show_resources = bool(self.checkbox("Resources", int(self.palette_show_resources)))
        self.layout_row_static(126, UI_LEFT_PANE_WIDTH - 30, 1)
        self.group("SovereignPalette", pf.NK_WINDOW_BORDER, self._palette_group, (state,))

        self.layout_row_dynamic(20, 1)
        self.label_colored_wrap("Selected Preview:", (255, 255, 255))
        self.layout_row_static(106, UI_LEFT_PANE_WIDTH - 30, 1)
        self.group("SovereignSelectedPreview", pf.NK_WINDOW_BORDER, self._selected_preview_group, (state, obj, resource))

        errors = validate_editor_authoring_state(check_pathing=True)
        issues = state.get("validation_issues", [])
        counts = self._validation_counts(issues)
        self.layout_row_dynamic(20, 1)
        if errors:
            self.label_colored_wrap("Validation: {0} issue(s)".format(len(errors)), (255, 80, 80))
            self.layout_row_dynamic(22, 4)
            for kind, label in VALIDATION_GROUPS:
                count = counts[kind]
                issue_idx = self._first_validation_issue_index(issues, kind)
                if count and issue_idx is not None:
                    def on_select(idx=issue_idx):
                        self._select_validation_issue(idx)

                    self.button_label("{0} {1}".format(label, count), on_select)
                else:
                    self.label_colored_wrap("{0} 0".format(label), (130, 130, 130))
            jumpable = len([issue for issue in issues if issue.get("target_kind")])
            self.layout_row_dynamic(20, 1)
            self.label_colored_wrap(
                "Showing first {0} | Jumpable {1}".format(min(4, len(issues)), jumpable),
                (255, 120, 80),
            )
            for issue_idx, issue in enumerate(issues[:4]):
                message = issue["message"]
                if issue.get("target_kind"):
                    self.layout_row_dynamic(22, 2)

                    def on_select(idx=issue_idx):
                        self._select_validation_issue(idx)

                    self.button_label("Go", on_select)
                    self.label_colored_wrap("#{0} {1}".format(issue_idx + 1, message), (255, 80, 80))
                else:
                    self.layout_row_dynamic(20, 1)
                    self.label_colored_wrap("#{0} {1}".format(issue_idx + 1, message), (255, 80, 80))
            if len(errors) > 4:
                self.layout_row_dynamic(20, 1)
                self.label_colored_wrap("+{0} more".format(len(errors) - 4), (255, 80, 80))
        else:
            self.label_colored_wrap("Validation: ready", (80, 220, 120))
