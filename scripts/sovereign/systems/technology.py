from __future__ import print_function

from sovereign.data.buildings import BUILDINGS
from sovereign.data.civilizations import CIVILIZATIONS
from sovereign.data.technologies import TECHNOLOGIES
from sovereign.systems.production import ProductionError


class TechnologyError(ValueError):
    def __init__(self, code, message):
        ValueError.__init__(self, message)
        self.code = code


def _is_completed(ent):
    return not hasattr(ent, "completed") or bool(ent.completed)


class ResearchQueue(object):
    def __init__(self, player_state, building_id, building_ent):
        self.player_state = player_state
        self.building_id = building_id
        self.building_ent = building_ent
        self.items = []
        self.completed = []

    def _building_definition(self):
        return BUILDINGS[self.building_id]

    def enqueue(self, technology_id):
        building = self._building_definition()
        civilization = CIVILIZATIONS[self.player_state.civilization_id]
        if technology_id not in building.get("researches", []):
            raise TechnologyError("unsupported_technology", "{0} cannot research {1}".format(self.building_id, technology_id))
        if technology_id not in civilization.get("available_technologies", []):
            raise TechnologyError("civilization_locked", "{0} is not available".format(technology_id))
        if not _is_completed(self.building_ent):
            raise TechnologyError("building_incomplete", "{0} is not complete".format(self.building_id))
        if technology_id in self.player_state.researched_technologies:
            raise TechnologyError("already_researched", "{0} is already researched".format(technology_id))

        technology = TECHNOLOGIES[technology_id]
        required_age = technology.get("requires_age")
        if required_age and self.player_state.current_age != required_age:
            raise TechnologyError("required_age", "{0} requires {1}".format(technology_id, required_age))

        try:
            self.player_state.spend(technology.get("cost", {}))
        except ProductionError as exc:
            raise TechnologyError(exc.code, str(exc))

        item = {
            "technology_id": technology_id,
            "remaining_sec": float(technology.get("research_time_sec", 0.0)),
        }
        self.items.append(item)
        return item

    def finish_next(self):
        if not self.items:
            raise TechnologyError("empty_queue", "research queue is empty")
        item = self.items.pop(0)
        technology_id = item["technology_id"]
        technology = TECHNOLOGIES[technology_id]
        for effect in technology.get("effects", []):
            self._apply_effect(technology_id, effect)
        self.player_state.researched_technologies.add(technology_id)
        self.completed.append(item)
        return technology_id

    def _apply_effect(self, technology_id, effect):
        effect_type = effect.get("type")
        if effect_type == "set_age":
            self.player_state.current_age = effect["age"]
            return
        if effect_type == "strategy_tag":
            return
        raise TechnologyError("unsupported_effect", "{0} has unsupported effect {1}".format(technology_id, effect_type))

    def snapshot(self):
        return {
            "building_id": self.building_id,
            "queue_len": len(self.items),
            "completed": len(self.completed),
        }
