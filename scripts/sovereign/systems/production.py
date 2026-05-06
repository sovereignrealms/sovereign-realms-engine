from __future__ import print_function

import math

from sovereign.data.buildings import BUILDINGS
from sovereign.data.civilizations import CIVILIZATIONS
from sovereign.data.resources import RESOURCES
from sovereign.data.units import UNITS


class ProductionError(ValueError):
    def __init__(self, code, message):
        ValueError.__init__(self, message)
        self.code = code


def _starting_resources():
    resources = {}
    for resource_id, definition in RESOURCES.items():
        if resource_id == "population":
            continue
        resources[resource_id] = int(definition.get("starting_amount", 0))
    return resources


def _is_completed(ent):
    return not hasattr(ent, "completed") or bool(ent.completed)


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _distance(a, b):
    dx = a[0] - b[0]
    dz = a[1] - b[1]
    return math.sqrt(dx * dx + dz * dz)


class SovereignPlayerState(object):
    def __init__(
        self,
        civilization_id="sovereign_default",
        resources=None,
        current_age=None,
        researched_technologies=None,
    ):
        self.civilization_id = civilization_id
        self.resources = dict(_starting_resources() if resources is None else resources)
        self.current_age = current_age or CIVILIZATIONS[civilization_id].get("starting_age", "founding")
        self.researched_technologies = set(researched_technologies or [])
        self.population_used = 0
        self.population_cap = 0
        self.units = []
        self.buildings = []

    def copy_for_check(self):
        other = SovereignPlayerState(
            self.civilization_id,
            self.resources,
            self.current_age,
            self.researched_technologies,
        )
        other.population_used = self.population_used
        other.population_cap = self.population_cap
        other.units = list(self.units)
        other.buildings = list(self.buildings)
        return other

    def add_unit(self, unit_id, ent):
        definition = UNITS[unit_id]
        self.population_used += int(definition.get("population", 0))
        self.units.append({"id": unit_id, "entity": ent})

    def add_building(self, building_id, ent):
        definition = BUILDINGS[building_id]
        if _is_completed(ent):
            self.population_cap += int(definition.get("population_provided", 0))
        self.buildings.append({"id": building_id, "entity": ent})

    def can_afford(self, cost):
        for resource_id, amount in cost.items():
            if self.resources.get(resource_id, 0) < int(amount):
                return False
        return True

    def spend(self, cost):
        if not self.can_afford(cost):
            raise ProductionError("resources", "insufficient resources")
        for resource_id, amount in cost.items():
            self.resources[resource_id] = self.resources.get(resource_id, 0) - int(amount)

    def has_population_space(self, unit_id):
        required = int(UNITS[unit_id].get("population", 0))
        return self.population_used + required <= self.population_cap

    def snapshot(self):
        return {
            "civilization_id": self.civilization_id,
            "current_age": self.current_age,
            "researched_technologies": sorted(self.researched_technologies),
            "resources": dict(self.resources),
            "population_used": self.population_used,
            "population_cap": self.population_cap,
            "unit_count": len(self.units),
            "building_count": len(self.buildings),
        }


def player_state_from_spawn_result(result, completed_buildings=None, civilization_id="sovereign_default"):
    completed_buildings = set(completed_buildings or [])
    state = SovereignPlayerState(civilization_id)
    for entry, ent in zip(result["plan"]["entities"], result["entities"]):
        if entry["kind"] == "unit":
            state.add_unit(entry["id"], ent)
        elif entry["kind"] == "building":
            if entry["id"] in completed_buildings and hasattr(ent, "completed") and not ent.completed:
                ent.mark()
                ent.found(force=True)
                ent.supply()
                ent.complete()
            state.add_building(entry["id"], ent)
    return state


class ProductionQueue(object):
    def __init__(self, player_state, building_id, building_ent, faction_id=1, scene_objs=None):
        self.player_state = player_state
        self.building_id = building_id
        self.building_ent = building_ent
        self.faction_id = faction_id
        self.scene_objs = scene_objs
        self.items = []
        self.completed = []

    def _building_definition(self):
        return BUILDINGS[self.building_id]

    def enqueue(self, unit_id):
        building = self._building_definition()
        if unit_id not in building.get("trains", []):
            raise ProductionError("unsupported_unit", "{0} cannot train {1}".format(self.building_id, unit_id))
        if hasattr(self.building_ent, "completed") and not self.building_ent.completed:
            raise ProductionError("building_incomplete", "{0} is not complete".format(self.building_id))
        if not self.player_state.has_population_space(unit_id):
            raise ProductionError("population_cap", "population cap reached")

        unit = UNITS[unit_id]
        self.player_state.spend(unit.get("cost", {}))
        item = {
            "unit_id": unit_id,
            "remaining_sec": float(unit.get("train_time_sec", 0.0)),
            "name": "{0}_trained_{1}".format(unit_id, len(self.completed) + len(self.items) + 1),
        }
        self.items.append(item)
        return item

    def finish_next(self):
        from sovereign.entities.runtime import create_entity, place_entity

        if not self.items:
            raise ProductionError("empty_queue", "production queue is empty")
        item = self.items.pop(0)
        unit_id = item["unit_id"]
        definition = UNITS[unit_id]
        entry = {
            "kind": "unit",
            "id": unit_id,
            "name": item["name"],
            "definition": definition,
        }
        ent = create_entity(entry)
        point = self._spawn_point()
        place_entity(
            ent,
            point,
            faction_id=self.faction_id,
            radius=definition.get("selection_radius", 2.5),
            scale=definition.get("scale"),
            selectable=True,
        )
        if self.scene_objs is not None:
            self.scene_objs.append(ent)
        self.player_state.add_unit(unit_id, ent)
        self.completed.append({"item": item, "entity": ent})
        return ent

    def _spawn_point(self):
        fallback = _ent_xz(self.building_ent)
        try:
            rally = self.building_ent.rally_point
        except AttributeError:
            rally = None
        if not rally:
            return (fallback[0] + 7.0, fallback[1] + 7.0)
        return (float(rally[0]), float(rally[1]))

    def snapshot(self):
        return {
            "building_id": self.building_id,
            "queue_len": len(self.items),
            "completed": len(self.completed),
            "building_position": _ent_xz(self.building_ent),
            "rally_point": self._spawn_point(),
        }


def rally_distance(building_ent, trained_ent):
    try:
        rally = building_ent.rally_point
    except AttributeError:
        rally = _ent_xz(building_ent)
    return _distance((float(rally[0]), float(rally[1])), _ent_xz(trained_ent))
