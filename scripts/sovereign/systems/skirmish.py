from __future__ import print_function

import random

from sovereign.data.units import UNITS
from sovereign.systems.production import ProductionQueue


class ScriptedSkirmishAI(object):
    def __init__(self, player_state, barracks_ent, faction_id, scene_objs=None, map_seed=0):
        self.player_state = player_state
        self.barracks_ent = barracks_ent
        self.faction_id = faction_id
        self.map_seed = int(map_seed)
        self.rng = random.Random(self.map_seed + int(faction_id) * 9973)
        self.decision_log = []
        self.queue = ProductionQueue(
            player_state,
            "barracks",
            barracks_ent,
            faction_id=faction_id,
            scene_objs=scene_objs,
        )

    def _record_decision(self, action, reason, **details):
        entry = {
            "action": action,
            "reason": reason,
            "resources": dict(self.player_state.resources),
            "population_used": self.player_state.population_used,
            "population_cap": self.player_state.population_cap,
            "queue_len": len(self.queue.items),
        }
        entry.update(details)
        self.decision_log.append(entry)
        return entry

    def seed_opening_resources(self, resources):
        for resource_id, amount in resources.items():
            self.player_state.resources[resource_id] = int(amount)
        return self._record_decision("seed_resources", "opening", seeded=dict(resources))

    def unit_count(self, unit_id=None):
        count = 0
        for record in self.player_state.units:
            if unit_id is None or record.get("id") == unit_id:
                count += 1
        return count

    def available_population(self):
        return self.player_state.population_cap - self.player_state.population_used

    def can_train_unit(self, unit_id="militia"):
        unit = UNITS[unit_id]
        return (
            self.player_state.can_afford(unit.get("cost", {}))
            and self.player_state.has_population_space(unit_id)
        )

    def attack_wave_ready(self, unit_id="militia", min_units=2):
        return self.unit_count(unit_id) >= int(min_units)

    def choose_next_action(self, unit_id="militia", min_attack_units=2):
        if self.attack_wave_ready(unit_id, min_attack_units):
            return self._record_decision(
                "attack",
                "wave_ready",
                unit_id=unit_id,
                ready_units=self.unit_count(unit_id),
                min_attack_units=int(min_attack_units),
            )
        if self.queue.items:
            return self._record_decision("wait_training", "queue_active", unit_id=unit_id)
        if not self.player_state.has_population_space(unit_id):
            return self._record_decision("build_house", "population_blocked", unit_id=unit_id)
        unit = UNITS[unit_id]
        if not self.player_state.can_afford(unit.get("cost", {})):
            return self._record_decision("gather_resources", "cannot_afford", unit_id=unit_id)
        return self._record_decision("train", "ready", unit_id=unit_id)

    def train_from_decision(self, unit_id="militia", min_attack_units=2):
        decision = self.choose_next_action(unit_id, min_attack_units)
        if decision["action"] != "train":
            return None, decision
        self.queue.enqueue(unit_id)
        ent = self.queue.finish_next()
        self._record_decision("trained", "queue_completed", unit_id=unit_id, entity_name=getattr(ent, "name", None))
        return ent, decision

    def train_attack_unit(self, unit_id="militia"):
        self.queue.enqueue(unit_id)
        ent = self.queue.finish_next()
        self._record_decision("trained", "direct_train", unit_id=unit_id, entity_name=getattr(ent, "name", None))
        return ent

    def choose_attack_unit(self, roster=("militia",)):
        roster = list(roster)
        if not roster:
            return "militia"
        return roster[self.rng.randrange(len(roster))]

    def train_attack_wave(self, roster=("militia",)):
        return self.train_attack_unit(self.choose_attack_unit(roster))

    def snapshot(self):
        return {
            "faction_id": self.faction_id,
            "map_seed": self.map_seed,
            "resources": dict(self.player_state.resources),
            "population_used": self.player_state.population_used,
            "population_cap": self.player_state.population_cap,
            "queue": self.queue.snapshot(),
            "unit_counts": {
                "militia": self.unit_count("militia"),
                "archer": self.unit_count("archer"),
            },
            "decision_log": list(self.decision_log),
        }


def faction_defeated(entities, hp_threshold=0):
    if not entities:
        return True
    for ent in entities:
        try:
            zombie = bool(ent.zombie)
        except (AttributeError, RuntimeError):
            zombie = False
        try:
            hp = int(ent.hp)
        except (AttributeError, RuntimeError):
            hp = 1
        if hp > hp_threshold and not zombie:
            return False
    return True


def conquest_winner(faction_targets, hp_threshold=0):
    alive = [
        faction_id for faction_id, entities in faction_targets.items()
        if not faction_defeated(entities, hp_threshold=hp_threshold)
    ]
    if len(alive) == 1:
        return alive[0]
    return None


def victory_winner(victory_mode, faction_targets, hp_threshold=0):
    if victory_mode == "conquest":
        return conquest_winner(faction_targets, hp_threshold=hp_threshold)
    raise ValueError("unsupported Sovereign victory mode '{0}'".format(victory_mode))


def scenario_victory_winner(scenario_state, faction_targets, hp_threshold=0):
    victory = scenario_state.get("victory", {})
    return victory_winner(victory.get("mode", "conquest"), faction_targets, hp_threshold=hp_threshold)


def victory_progress_state(scenario_state, faction_targets, hp_threshold=0, elapsed_ticks=0):
    alive = []
    defeated = []
    for faction_id, entities in faction_targets.items():
        if faction_defeated(entities, hp_threshold=hp_threshold):
            defeated.append(faction_id)
        else:
            alive.append(faction_id)
    winner = scenario_victory_winner(scenario_state, faction_targets, hp_threshold=hp_threshold)
    victory = scenario_state.get("victory", {})
    return {
        "mode": victory.get("mode", "conquest"),
        "label": victory.get("label", "Conquest"),
        "winner": winner,
        "alive_factions": sorted(alive),
        "defeated_factions": sorted(defeated),
        "elapsed_ticks": int(elapsed_ticks),
    }
