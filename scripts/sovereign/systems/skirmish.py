from __future__ import print_function

import random

from sovereign.data.buildings import BUILDINGS
from sovereign.data.technologies import TECHNOLOGIES
from sovereign.data.units import UNITS
from sovereign.systems.production import ProductionQueue


AI_DIFFICULTY_PROFILES = {
    "standard": {
        "label": "Standard",
        "economy_weight": 1.0,
        "military_weight": 1.0,
        "expansion_min_units": 1,
        "military_target_units": 2,
        "defense_min_units": 1,
        "harass_min_units": 1,
        "personality_id": "balanced",
        "expansion_target_bases": 2,
        "harass_interval_steps": 5,
        "max_harass_waves": 1,
        "harass_target_roles": ["buildings", "villagers", "town_center"],
        "preferred_military_unit": "militia",
        "attack_threshold": 0.45,
        "retreat_threshold": 0.40,
        "map_control_weight": 0.35,
        "army_advantage_weight": 0.10,
        "build_order": ["secure_home", "train_military", "attack"],
        "income_per_step": {"food": 90, "wood": 90, "gold": 55, "stone": 0},
    },
    "booming": {
        "label": "Booming",
        "economy_weight": 1.8,
        "military_weight": 0.7,
        "expansion_min_units": 1,
        "military_target_units": 2,
        "defense_min_units": 1,
        "harass_min_units": 1,
        "personality_id": "booming",
        "expansion_target_bases": 3,
        "harass_interval_steps": 7,
        "max_harass_waves": 1,
        "harass_target_roles": ["buildings", "town_center", "villagers"],
        "preferred_military_unit": "militia",
        "attack_threshold": 0.60,
        "retreat_threshold": 0.50,
        "map_control_weight": 0.25,
        "army_advantage_weight": 0.08,
        "build_order": ["expand", "secure_home", "train_military", "attack"],
        "income_per_step": {"food": 80, "wood": 140, "gold": 50, "stone": 0},
    },
    "hard": {
        "label": "Hard",
        "economy_weight": 1.0,
        "military_weight": 1.7,
        "expansion_min_units": 2,
        "military_target_units": 3,
        "defense_min_units": 1,
        "harass_min_units": 2,
        "personality_id": "pressure",
        "expansion_target_bases": 3,
        "harass_interval_steps": 2,
        "max_harass_waves": 2,
        "harass_target_roles": ["villagers", "buildings", "town_center"],
        "preferred_military_unit": "archer",
        "attack_threshold": 0.50,
        "retreat_threshold": 0.50,
        "map_control_weight": 0.45,
        "army_advantage_weight": 0.15,
        "build_order": ["scout", "secure_home", "expand", "train_counter", "harass", "attack"],
        "income_per_step": {"food": 110, "wood": 90, "gold": 90, "stone": 0},
    },
}


AI_COMPOSITION_PLANS = {
    "standard": {
        "plan_id": "infantry_screen",
        "technology_id": "infantry_drills",
        "unit_targets": {"militia": 3},
        "attack_roster": ["militia"],
        "target_roles": ["buildings", "town_center", "villagers"],
    },
    "booming": {
        "plan_id": "mixed_security",
        "technology_id": "settlement_logistics",
        "unit_targets": {"militia": 2, "archer": 1},
        "attack_roster": ["militia", "archer"],
        "target_roles": ["town_center", "buildings", "villagers"],
    },
    "hard": {
        "plan_id": "archer_pressure",
        "technology_id": "ranger_fletching",
        "unit_targets": {"archer": 3},
        "attack_roster": ["archer"],
        "target_roles": ["villagers", "buildings", "town_center"],
    },
}


def ai_difficulty_profile(profile_id):
    profile_id = profile_id or "standard"
    profile = dict(AI_DIFFICULTY_PROFILES.get(profile_id, AI_DIFFICULTY_PROFILES["standard"]))
    profile["id"] = profile_id if profile_id in AI_DIFFICULTY_PROFILES else "standard"
    profile["income_per_step"] = dict(profile.get("income_per_step", {}))
    profile["build_order"] = list(profile.get("build_order", []))
    profile["harass_target_roles"] = list(profile.get("harass_target_roles", []))
    return profile


def ai_composition_plan(profile_id):
    profile_id = profile_id or "standard"
    plan = dict(AI_COMPOSITION_PLANS.get(profile_id, AI_COMPOSITION_PLANS["standard"]))
    plan["difficulty_id"] = profile_id if profile_id in AI_COMPOSITION_PLANS else "standard"
    plan["unit_targets"] = dict(plan.get("unit_targets", {}))
    plan["attack_roster"] = list(plan.get("attack_roster", []))
    plan["target_roles"] = list(plan.get("target_roles", []))
    return plan


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _distance(a, b):
    dx = a[0] - b[0]
    dz = a[1] - b[1]
    return (dx * dx + dz * dz) ** 0.5


def _is_live_entity(ent):
    try:
        zombie = bool(ent.zombie)
    except (AttributeError, RuntimeError):
        zombie = False
    try:
        hp = int(ent.hp)
    except (AttributeError, RuntimeError):
        hp = 1
    return hp > 0 and not zombie


def _position_to_tuple(point):
    return (float(point[0]), float(point[1]))


def compact_scout_report(report):
    return {
        "scout_name": report.get("scout_name"),
        "observed_count": len(report.get("observed", [])),
        "threat_count": len(report.get("threats", [])),
        "observed": [
            {
                "role": item.get("role"),
                "name": item.get("name"),
                "distance_to_scout": item.get("distance_to_scout"),
            }
            for item in report.get("observed", [])
        ],
        "threats": [
            {
                "role": item.get("role"),
                "name": item.get("name"),
                "distance_to_defended": item.get("distance_to_defended"),
                "defended_name": item.get("defended_name"),
                "severity": item.get("severity"),
            }
            for item in report.get("threats", [])
        ],
    }


class ThreatMemory(object):
    def __init__(self, ttl_steps=8):
        self.ttl_steps = int(ttl_steps)
        self.sightings = {}

    @classmethod
    def from_snapshot(cls, snapshot):
        snapshot = dict(snapshot or {})
        memory = cls(ttl_steps=snapshot.get("ttl_steps", 8))
        for item in snapshot.get("sightings", []):
            entry = dict(item)
            name = entry.get("name")
            if not name:
                continue
            entry.pop("age_steps", None)
            memory.sightings[name] = entry
        return memory

    def remember_report(self, report, step_index):
        step_index = int(step_index)
        threat_names = set(item.get("name") for item in report.get("threats", []))
        for item in report.get("observed", []):
            name = item.get("name")
            if not name:
                continue
            previous = self.sightings.get(name, {})
            previous_count = int(previous.get("seen_count", 0))
            previous_severity = int(previous.get("highest_severity", 0))
            severity = previous_severity
            distance_to_defended = previous.get("distance_to_defended")
            defended_name = previous.get("defended_name")
            for threat in report.get("threats", []):
                if threat.get("name") != name:
                    continue
                severity = max(severity, int(threat.get("severity", 0)))
                distance_to_defended = threat.get("distance_to_defended")
                defended_name = threat.get("defended_name")
            self.sightings[name] = {
                "name": name,
                "role": item.get("role"),
                "position": item.get("position"),
                "first_seen_step": int(previous.get("first_seen_step", step_index)),
                "last_seen_step": step_index,
                "seen_count": previous_count + 1,
                "is_threat": bool(previous.get("is_threat", False) or name in threat_names),
                "highest_severity": severity,
                "distance_to_scout": item.get("distance_to_scout"),
                "distance_to_defended": distance_to_defended,
                "defended_name": defended_name,
            }
        return self.snapshot(step_index)

    def remembered_threats(self, current_step=None, max_age=None):
        current_step = int(current_step if current_step is not None else 0)
        max_age = int(max_age if max_age is not None else self.ttl_steps)
        threats = []
        for item in self.sightings.values():
            if not item.get("is_threat"):
                continue
            if current_step and current_step - int(item.get("last_seen_step", 0)) > max_age:
                continue
            threats.append(dict(item))
        threats.sort(key=lambda item: (
            -int(item.get("highest_severity", 0)),
            -int(item.get("last_seen_step", 0)),
            item.get("name") or "",
        ))
        return threats

    def best_threat(self, current_step=None):
        threats = self.remembered_threats(current_step=current_step)
        if not threats:
            return None
        return threats[0]

    def snapshot(self, current_step=None):
        current_step = int(current_step if current_step is not None else 0)
        sightings = []
        for item in self.sightings.values():
            entry = dict(item)
            if current_step:
                entry["age_steps"] = current_step - int(item.get("last_seen_step", 0))
            sightings.append(entry)
        sightings.sort(key=lambda item: (item.get("role") or "", item.get("name") or ""))
        return {
            "ttl_steps": self.ttl_steps,
            "sighting_count": len(sightings),
            "remembered_threat_count": len(self.remembered_threats(current_step=current_step)),
            "sightings": sightings,
        }


class ScriptedSkirmishAI(object):
    def __init__(self, player_state, barracks_ent, faction_id, scene_objs=None, map_seed=0):
        self.player_state = player_state
        self.barracks_ent = barracks_ent
        self.faction_id = faction_id
        self.map_seed = int(map_seed)
        self.rng = random.Random(self.map_seed + int(faction_id) * 9973)
        self.decision_log = []
        self.scene_objs = scene_objs
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

    def gather_resources(self, income, reason="scripted_income"):
        income = dict(income)
        for resource_id, amount in income.items():
            self.player_state.resources[resource_id] = (
                self.player_state.resources.get(resource_id, 0) + int(amount)
            )
        return self._record_decision("gather_resources", reason, income=income)

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

    def live_unit_count(self, unit_id=None):
        count = 0
        for record in self.player_state.units:
            if unit_id is not None and record.get("id") != unit_id:
                continue
            if _is_live_entity(record.get("entity")):
                count += 1
        return count

    def available_population(self):
        return self.player_state.population_cap - self.player_state.population_used

    def building_count(self, building_id=None):
        count = 0
        for record in self.player_state.buildings:
            if building_id is None or record.get("id") == building_id:
                count += 1
        return count

    def can_train_unit(self, unit_id="militia"):
        unit = UNITS[unit_id]
        return (
            self.player_state.can_afford(unit.get("cost", {}))
            and self.player_state.has_population_space(unit_id)
        )

    def can_build_building(self, building_id):
        return self.player_state.can_afford(BUILDINGS[building_id].get("cost", {}))

    def build_complete_building(self, building_id, point, name=None, reason="build_order"):
        if not self.can_build_building(building_id):
            return None, self._record_decision(
                "gather_resources",
                "building_cannot_afford",
                building_id=building_id,
            )

        from sovereign.entities.runtime import create_entity, place_entity

        definition = BUILDINGS[building_id]
        self.player_state.spend(definition.get("cost", {}))
        entry = {
            "kind": "building",
            "id": building_id,
            "name": name or "{0}_{1}".format(building_id, self.building_count(building_id) + 1),
            "definition": definition,
        }
        ent = create_entity(entry)
        place_entity(
            ent,
            point,
            faction_id=self.faction_id,
            radius=definition.get("selection_radius", 2.5),
            scale=definition.get("scale"),
        )
        if hasattr(ent, "mark"):
            ent.mark()
        if hasattr(ent, "found"):
            ent.found(force=True)
        if hasattr(ent, "supply"):
            ent.supply()
        if hasattr(ent, "complete"):
            ent.complete()
        if self.scene_objs is not None:
            self.scene_objs.append(ent)
        self.player_state.add_building(building_id, ent)
        return ent, self._record_decision(
            "build_house" if building_id == "house" else "build_building",
            reason,
            building_id=building_id,
            entity_name=getattr(ent, "name", None),
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

    def train_for_build_order(self, unit_id="militia", target_count=3):
        if self.unit_count(unit_id) >= int(target_count):
            return None, self._record_decision(
                "wait_training",
                "target_count_met",
                unit_id=unit_id,
                target_count=int(target_count),
            )
        ent, decision = self.train_from_decision(unit_id, min_attack_units=int(target_count) + 1)
        return ent, decision

    def choose_attack_unit(self, roster=("militia",)):
        roster = list(roster)
        if not roster:
            return "militia"
        return roster[self.rng.randrange(len(roster))]

    def train_attack_wave(self, roster=("militia",)):
        return self.train_attack_unit(self.choose_attack_unit(roster))

    def wave_units(self, unit_id="militia"):
        return [
            record["entity"]
            for record in self.player_state.units
            if record.get("id") == unit_id and _is_live_entity(record.get("entity"))
        ]

    def roster_units(self, unit_ids=("militia", "archer")):
        unit_ids = set(unit_ids)
        return [
            record["entity"]
            for record in self.player_state.units
            if record.get("id") in unit_ids and _is_live_entity(record.get("entity"))
        ]

    def record_unit_loss(self, ent, reason="attrition_loss"):
        for idx, record in enumerate(list(self.player_state.units)):
            if record.get("entity") is not ent:
                continue
            unit_id = record.get("id")
            del self.player_state.units[idx]
            self.player_state.population_used = max(
                0,
                self.player_state.population_used - int(UNITS[unit_id].get("population", 0)),
            )
            return self._record_decision(
                "unit_lost",
                reason,
                unit_id=unit_id,
                entity_name=getattr(ent, "name", None),
            )
        return self._record_decision(
            "unit_lost",
            "unknown_unit",
            entity_name=getattr(ent, "name", None),
        )

    def choose_priority_target(self, target_groups):
        priority = ("town_center", "villagers", "military", "buildings")
        for role in priority:
            for ent in target_groups.get(role, []):
                if _is_live_entity(ent):
                    return ent, self._record_decision(
                        "target",
                        "priority",
                        target_role=role,
                        target_name=getattr(ent, "name", None),
                    )
        return None, self._record_decision("wait_attack", "no_target")

    def scout_report(self, target_groups, scout_ent=None, defended_assets=None, sight_radius=96.0, threat_radius=44.0):
        scout_ent = scout_ent or self.barracks_ent
        scout_pos = _ent_xz(scout_ent)
        defended_assets = list(defended_assets or [self.barracks_ent])
        role_weight = {
            "military": 4,
            "villagers": 2,
            "buildings": 2,
            "town_center": 1,
        }
        observed = []
        threats = []
        for role, ents in target_groups.items():
            for ent in ents:
                if not _is_live_entity(ent):
                    continue
                ent_pos = _ent_xz(ent)
                distance_to_scout = _distance(scout_pos, ent_pos)
                nearest_asset = None
                nearest_distance = None
                for asset in defended_assets:
                    dist = _distance(ent_pos, _ent_xz(asset))
                    if nearest_distance is None or dist < nearest_distance:
                        nearest_distance = dist
                        nearest_asset = asset
                if distance_to_scout <= float(sight_radius):
                    observed.append({
                        "role": role,
                        "entity": ent,
                        "name": getattr(ent, "name", None),
                        "position": ent_pos,
                        "distance_to_scout": round(distance_to_scout, 3),
                    })
                if nearest_distance is not None and nearest_distance <= float(threat_radius):
                    severity = role_weight.get(role, 1) * 1000 - int(nearest_distance)
                    threats.append({
                        "role": role,
                        "entity": ent,
                        "name": getattr(ent, "name", None),
                        "position": ent_pos,
                        "defended_asset": nearest_asset,
                        "defended_name": getattr(nearest_asset, "name", None),
                        "distance_to_defended": round(nearest_distance, 3),
                        "severity": severity,
                    })
        threats.sort(key=lambda item: (-item["severity"], item["distance_to_defended"], item["name"] or ""))
        report = {
            "scout_name": getattr(scout_ent, "name", None),
            "observed": observed,
            "threats": threats,
            "defended_assets": [getattr(ent, "name", None) for ent in defended_assets],
        }
        self._record_decision(
            "scout",
            "threats_detected" if threats else "no_threat",
            observed_count=len(observed),
            threat_count=len(threats),
            closest_threat_name=threats[0]["name"] if threats else None,
        )
        return report

    def launch_defense_to_position(
        self,
        point,
        target_name=None,
        defended_name=None,
        unit_id="militia",
        min_units=2,
        reason="memory_threat_response",
    ):
        units = self.wave_units(unit_id)
        if len(units) < int(min_units):
            return False, self._record_decision(
                "wait_defense",
                "not_enough_units",
                unit_id=unit_id,
                ready_units=len(units),
                min_units=int(min_units),
                target_name=target_name,
            )
        target_xz = (float(point[0]), float(point[1]))
        for ent in units:
            try:
                ent.face_towards((target_xz[0], ent.pos[1], target_xz[1]))
            except (AttributeError, RuntimeError):
                pass
            try:
                ent.move(target_xz)
            except (AttributeError, RuntimeError):
                pass
        return True, self._record_decision(
            "defend",
            reason,
            unit_id=unit_id,
            response_count=len(units),
            target_name=target_name,
            target_position=target_xz,
            defended_name=defended_name,
        )

    def regroup_units(self, units, point, reason="regroup"):
        target_xz = (float(point[0]), float(point[1]))
        units = list(units)
        for ent in units:
            try:
                ent.face_towards((target_xz[0], ent.pos[1], target_xz[1]))
            except (AttributeError, RuntimeError):
                pass
            try:
                ent.move(target_xz)
            except (AttributeError, RuntimeError):
                pass
        return self._record_decision(
            "retreat_regroup",
            reason,
            regroup_position=target_xz,
            regroup_count=len(units),
        )

    def launch_defense_response(self, target, defended_asset=None, unit_id="militia", min_units=2):
        point = _ent_xz(target)
        distance_to_defended = None
        if defended_asset is not None:
            distance_to_defended = round(_distance(point, _ent_xz(defended_asset)), 3)
        launched, decision = self.launch_defense_to_position(
            point,
            target_name=getattr(target, "name", None),
            defended_name=getattr(defended_asset, "name", None),
            unit_id=unit_id,
            min_units=min_units,
            reason="threat_response",
        )
        decision["distance_to_defended"] = distance_to_defended
        return launched, decision

    def launch_attack_wave(self, target, unit_id="militia", min_units=3):
        units = self.wave_units(unit_id)
        if len(units) < int(min_units):
            return False, self._record_decision(
                "wait_attack",
                "not_enough_units",
                unit_id=unit_id,
                ready_units=len(units),
                min_units=int(min_units),
            )
        target_xz = _ent_xz(target)
        for ent in units:
            try:
                ent.face_towards(target.pos)
            except (AttributeError, RuntimeError):
                pass
            try:
                ent.move(target_xz)
            except (AttributeError, RuntimeError):
                pass
        return True, self._record_decision(
            "attack",
            "wave_launched",
            unit_id=unit_id,
            wave_count=len(units),
            target_name=getattr(target, "name", None),
            target_position=target_xz,
        )

    def launch_roster_attack(self, target, unit_ids=("militia", "archer"), min_units=2, reason="counterattack"):
        units = self.roster_units(unit_ids)
        if len(units) < int(min_units):
            return False, self._record_decision(
                "wait_attack",
                "not_enough_roster_units",
                unit_ids=list(unit_ids),
                ready_units=len(units),
                min_units=int(min_units),
            )
        target_xz = _ent_xz(target)
        for ent in units:
            try:
                ent.face_towards(target.pos)
            except (AttributeError, RuntimeError):
                pass
            try:
                ent.move(target_xz)
            except (AttributeError, RuntimeError):
                pass
        return True, self._record_decision(
            "counterattack",
            reason,
            unit_ids=list(unit_ids),
            wave_count=len(units),
            target_name=getattr(target, "name", None),
            target_position=target_xz,
        )

    def select_live_units(self, unit_id, count, exclude=None):
        excluded = set(exclude or [])
        units = []
        for record in self.player_state.units:
            if record.get("id") != unit_id:
                continue
            ent = record.get("entity")
            if id(ent) in excluded or not _is_live_entity(ent):
                continue
            units.append(ent)
            if len(units) >= int(count):
                break
        return units

    def launch_units_to_position(self, units, point, action="front_move", reason="multi_front", front_id=None, target_name=None):
        target_xz = (float(point[0]), float(point[1]))
        units = list(units)
        for ent in units:
            try:
                ent.face_towards((target_xz[0], ent.pos[1], target_xz[1]))
            except (AttributeError, RuntimeError):
                pass
            try:
                ent.move(target_xz)
            except (AttributeError, RuntimeError):
                pass
        return self._record_decision(
            action,
            reason,
            front_id=front_id,
            unit_names=[getattr(ent, "name", None) for ent in units],
            unit_count=len(units),
            target_name=target_name,
            target_position=target_xz,
        )

    def launch_units_to_target(self, units, target, action="front_attack", reason="multi_front", front_id=None):
        return self.launch_units_to_position(
            units,
            _ent_xz(target),
            action=action,
            reason=reason,
            front_id=front_id,
            target_name=getattr(target, "name", None),
        )

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


class BuildOrderPlanner(object):
    def __init__(
        self,
        ai,
        target_groups,
        unit_id="militia",
        attack_wave_size=3,
        income_per_step=None,
        house_points=None,
    ):
        self.ai = ai
        self.target_groups = target_groups
        self.unit_id = unit_id
        self.attack_wave_size = int(attack_wave_size)
        self.income_per_step = dict(income_per_step or {
            "food": 90,
            "wood": 60,
            "gold": 35,
            "stone": 0,
        })
        base = _ent_xz(ai.barracks_ent)
        self.house_points = list(house_points or [
            (base[0] + 8.0, base[1] - 8.0),
            (base[0] + 12.0, base[1] - 10.0),
            (base[0] + 16.0, base[1] - 12.0),
        ])
        self.step_index = 0
        self.attack_launched = False
        self.history = []

    def _next_house_point(self):
        idx = min(self.ai.building_count("house"), len(self.house_points) - 1)
        return self.house_points[idx]

    def _missing_training_resources(self):
        unit = UNITS[self.unit_id]
        missing = {}
        for resource_id, amount in unit.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def step(self):
        self.step_index += 1

        if self.attack_launched:
            decision = self.ai._record_decision("wait_attack", "attack_already_launched")
            self.history.append(decision)
            return decision

        if self.ai.unit_count(self.unit_id) < self.attack_wave_size:
            missing = self._missing_training_resources()
            if missing:
                decision = self.ai.gather_resources(self.income_per_step, "build_order_income")
                decision["missing_before_income"] = missing
                self.history.append(decision)
                return decision

            if self.ai.available_population() <= 1:
                house, decision = self.ai.build_complete_building(
                    "house",
                    self._next_house_point(),
                    name="ai_build_order_house_{0}".format(self.ai.building_count("house") + 1),
                )
                if house is None:
                    decision = self.ai.gather_resources({"wood": 50}, "house_income")
                self.history.append(decision)
                return decision

            ent, decision = self.ai.train_for_build_order(self.unit_id, self.attack_wave_size)
            if ent is not None:
                ent.name = "ai_build_order_{0}_{1}".format(self.unit_id, self.ai.unit_count(self.unit_id))
            self.history.append(decision)
            return decision

        target, decision = self.ai.choose_priority_target(self.target_groups)
        self.history.append(decision)
        if target is None:
            return decision
        launched, attack = self.ai.launch_attack_wave(target, self.unit_id, self.attack_wave_size)
        self.attack_launched = bool(launched)
        self.history.append(attack)
        return attack

    def snapshot(self):
        return {
            "unit_id": self.unit_id,
            "attack_wave_size": self.attack_wave_size,
            "step_index": self.step_index,
            "attack_launched": self.attack_launched,
            "history": list(self.history),
        }


class TacticalResponsePlanner(object):
    def __init__(
        self,
        ai,
        scout_ent=None,
        defended_assets=None,
        unit_id="militia",
        min_defenders=2,
        sight_radius=96.0,
        threat_radius=44.0,
        income_per_step=None,
        house_points=None,
    ):
        self.ai = ai
        self.scout_ent = scout_ent or ai.barracks_ent
        self.defended_assets = list(defended_assets or [ai.barracks_ent])
        self.unit_id = unit_id
        self.min_defenders = int(min_defenders)
        self.sight_radius = float(sight_radius)
        self.threat_radius = float(threat_radius)
        self.income_per_step = dict(income_per_step or {
            "food": 90,
            "wood": 60,
            "gold": 35,
            "stone": 0,
        })
        base = _ent_xz(ai.barracks_ent)
        self.house_points = list(house_points or [
            (base[0] + 8.0, base[1] - 8.0),
            (base[0] + 12.0, base[1] - 10.0),
        ])
        self.step_index = 0
        self.defense_launched = False
        self.last_report = None
        self.history = []

    def _next_house_point(self):
        idx = min(self.ai.building_count("house"), len(self.house_points) - 1)
        return self.house_points[idx]

    def _missing_training_resources(self):
        unit = UNITS[self.unit_id]
        missing = {}
        for resource_id, amount in unit.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def step(self, target_groups):
        self.step_index += 1
        report = self.ai.scout_report(
            target_groups,
            scout_ent=self.scout_ent,
            defended_assets=self.defended_assets,
            sight_radius=self.sight_radius,
            threat_radius=self.threat_radius,
        )
        self.last_report = report
        threats = report["threats"]
        if not threats:
            decision = self.ai._record_decision(
                "scout_patrol",
                "no_threat",
                scout_name=getattr(self.scout_ent, "name", None),
            )
            self.history.append(decision)
            return decision

        threat = threats[0]
        if self.ai.unit_count(self.unit_id) < self.min_defenders:
            missing = self._missing_training_resources()
            if missing:
                decision = self.ai.gather_resources(self.income_per_step, "threat_response_income")
                decision["missing_before_income"] = missing
                decision["threat_name"] = threat["name"]
                self.history.append(decision)
                return decision

            if self.ai.available_population() <= 1:
                house, decision = self.ai.build_complete_building(
                    "house",
                    self._next_house_point(),
                    name="ai_threat_house_{0}".format(self.ai.building_count("house") + 1),
                )
                if house is None:
                    decision = self.ai.gather_resources({"wood": 50}, "threat_house_income")
                decision["threat_name"] = threat["name"]
                self.history.append(decision)
                return decision

            ent, decision = self.ai.train_for_build_order(self.unit_id, self.min_defenders)
            if ent is not None:
                ent.name = "ai_threat_{0}_{1}".format(self.unit_id, self.ai.unit_count(self.unit_id))
            decision["threat_name"] = threat["name"]
            self.history.append(decision)
            return decision

        launched, decision = self.ai.launch_defense_response(
            threat["entity"],
            defended_asset=threat.get("defended_asset"),
            unit_id=self.unit_id,
            min_units=self.min_defenders,
        )
        self.defense_launched = bool(launched)
        self.history.append(decision)
        return decision

    def snapshot(self):
        return {
            "unit_id": self.unit_id,
            "min_defenders": self.min_defenders,
            "step_index": self.step_index,
            "defense_launched": self.defense_launched,
            "last_report": compact_scout_report(self.last_report or {}),
            "history": list(self.history),
        }


class ScoutingRoutePlanner(object):
    def __init__(
        self,
        ai,
        scout_ent,
        route_points,
        target_groups,
        defended_assets=None,
        memory=None,
        sight_radius=96.0,
        threat_radius=44.0,
    ):
        self.ai = ai
        self.scout_ent = scout_ent
        self.route_points = list(route_points)
        self.target_groups = target_groups
        self.defended_assets = list(defended_assets or [ai.barracks_ent])
        self.memory = memory or ThreatMemory()
        self.sight_radius = float(sight_radius)
        self.threat_radius = float(threat_radius)
        self.route_index = 0
        self.step_index = 0
        self.history = []
        self.last_report = None

    def _next_waypoint(self):
        if not self.route_points:
            return _ent_xz(self.scout_ent)
        return self.route_points[self.route_index % len(self.route_points)]

    def step(self, target_groups=None):
        self.step_index += 1
        target_groups = target_groups if target_groups is not None else self.target_groups
        waypoint = self._next_waypoint()
        try:
            self.scout_ent.face_towards((float(waypoint[0]), self.scout_ent.pos[1], float(waypoint[1])))
        except (AttributeError, RuntimeError):
            pass
        try:
            self.scout_ent.move((float(waypoint[0]), float(waypoint[1])))
        except (AttributeError, RuntimeError):
            pass

        report = self.ai.scout_report(
            target_groups,
            scout_ent=self.scout_ent,
            defended_assets=self.defended_assets,
            sight_radius=self.sight_radius,
            threat_radius=self.threat_radius,
        )
        self.memory.remember_report(report, self.step_index)
        decision = self.ai._record_decision(
            "scout_route",
            "waypoint",
            scout_name=getattr(self.scout_ent, "name", None),
            waypoint=(float(waypoint[0]), float(waypoint[1])),
            route_index=self.route_index,
            memory_threat_count=self.memory.snapshot(self.step_index)["remembered_threat_count"],
        )
        self.history.append(decision)
        self.last_report = report
        self.route_index += 1
        return report

    def snapshot(self):
        return {
            "route_index": self.route_index,
            "step_index": self.step_index,
            "route_points": [(float(point[0]), float(point[1])) for point in self.route_points],
            "last_report": compact_scout_report(self.last_report or {}),
            "memory": self.memory.snapshot(self.step_index),
            "history": list(self.history),
        }


class MemoryResponsePlanner(object):
    def __init__(
        self,
        ai,
        memory,
        unit_id="militia",
        min_defenders=2,
        income_per_step=None,
        house_points=None,
        regroup_point=None,
        retreat_when_outnumbered=True,
    ):
        self.ai = ai
        self.memory = memory
        self.unit_id = unit_id
        self.min_defenders = int(min_defenders)
        self.income_per_step = dict(income_per_step or {
            "food": 90,
            "wood": 60,
            "gold": 35,
            "stone": 0,
        })
        base = _ent_xz(ai.barracks_ent)
        self.house_points = list(house_points or [
            (base[0] + 8.0, base[1] - 8.0),
            (base[0] + 12.0, base[1] - 10.0),
        ])
        self.step_index = 0
        self.response_launched = False
        self.regroup_point = regroup_point or _ent_xz(ai.barracks_ent)
        self.retreat_when_outnumbered = bool(retreat_when_outnumbered)
        self.regroup_done = False
        self.history = []

    def _next_house_point(self):
        idx = min(self.ai.building_count("house"), len(self.house_points) - 1)
        return self.house_points[idx]

    def _missing_training_resources(self):
        unit = UNITS[self.unit_id]
        missing = {}
        for resource_id, amount in unit.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def step(self):
        self.step_index += 1
        threat = self.memory.best_threat(current_step=self.step_index)
        if threat is None:
            decision = self.ai._record_decision(
                "scout_patrol",
                "no_memory_threat",
            )
            self.history.append(decision)
            return decision

        if self.ai.unit_count(self.unit_id) < self.min_defenders:
            existing = self.ai.wave_units(self.unit_id)
            if self.retreat_when_outnumbered and existing and not self.regroup_done:
                decision = self.ai.regroup_units(existing, self.regroup_point, reason="memory_outnumbered")
                decision["remembered_threat_name"] = threat.get("name")
                self.regroup_done = True
                self.history.append(decision)
                return decision

            missing = self._missing_training_resources()
            if missing:
                decision = self.ai.gather_resources(self.income_per_step, "memory_response_income")
                decision["missing_before_income"] = missing
                decision["remembered_threat_name"] = threat.get("name")
                self.history.append(decision)
                return decision

            if self.ai.available_population() <= 1:
                house, decision = self.ai.build_complete_building(
                    "house",
                    self._next_house_point(),
                    name="ai_memory_house_{0}".format(self.ai.building_count("house") + 1),
                )
                if house is None:
                    decision = self.ai.gather_resources({"wood": 50}, "memory_house_income")
                decision["remembered_threat_name"] = threat.get("name")
                self.history.append(decision)
                return decision

            ent, decision = self.ai.train_for_build_order(self.unit_id, self.min_defenders)
            if ent is not None:
                ent.name = "ai_memory_{0}_{1}".format(self.unit_id, self.ai.unit_count(self.unit_id))
            decision["remembered_threat_name"] = threat.get("name")
            self.history.append(decision)
            return decision

        launched, decision = self.ai.launch_defense_to_position(
            threat["position"],
            target_name=threat.get("name"),
            defended_name=threat.get("defended_name"),
            unit_id=self.unit_id,
            min_units=self.min_defenders,
            reason="memory_threat_response",
        )
        self.response_launched = bool(launched)
        decision["remembered_threat_role"] = threat.get("role")
        decision["remembered_threat_seen_count"] = threat.get("seen_count")
        self.history.append(decision)
        return decision

    def snapshot(self):
        return {
            "unit_id": self.unit_id,
            "min_defenders": self.min_defenders,
            "step_index": self.step_index,
            "response_launched": self.response_launched,
            "regroup_done": self.regroup_done,
            "regroup_point": (float(self.regroup_point[0]), float(self.regroup_point[1])),
            "memory": self.memory.snapshot(self.step_index),
            "history": list(self.history),
        }


class AdaptiveMemoryStrategyPlanner(object):
    def __init__(
        self,
        ai,
        memory,
        scout_planner=None,
        counterattack_targets=None,
        preferred_units=None,
        min_response_units=2,
        counterattack_units=2,
        scout_interval=2,
        income_per_step=None,
        house_points=None,
        regroup_point=None,
    ):
        self.ai = ai
        self.memory = memory
        self.scout_planner = scout_planner
        self.counterattack_targets = counterattack_targets or {}
        self.preferred_units = dict(preferred_units or {
            "military": "archer",
            "villagers": "militia",
            "buildings": "militia",
            "town_center": "militia",
        })
        self.min_response_units = int(min_response_units)
        self.counterattack_units = int(counterattack_units)
        self.scout_interval = max(1, int(scout_interval))
        self.income_per_step = dict(income_per_step or {
            "food": 90,
            "wood": 80,
            "gold": 80,
            "stone": 0,
        })
        base = _ent_xz(ai.barracks_ent)
        self.house_points = list(house_points or [
            (base[0] + 8.0, base[1] - 8.0),
            (base[0] + 12.0, base[1] - 10.0),
        ])
        self.regroup_point = regroup_point or _ent_xz(ai.barracks_ent)
        self.step_index = 0
        self.regroup_done = False
        self.response_launched = False
        self.counterattack_launched = False
        self.preferred_unit_history = []
        self.history = []
        self.scout_history = []

    def _next_house_point(self):
        idx = min(self.ai.building_count("house"), len(self.house_points) - 1)
        return self.house_points[idx]

    def _priority_target(self):
        target, decision = self.ai.choose_priority_target(self.counterattack_targets)
        self.history.append(decision)
        return target

    def _preferred_unit_for_threat(self, threat):
        role = threat.get("role") or "military"
        unit_id = self.preferred_units.get(role, "militia")
        self.preferred_unit_history.append({
            "step": self.step_index,
            "role": role,
            "unit_id": unit_id,
            "threat_name": threat.get("name"),
        })
        return unit_id

    def _missing_training_resources(self, unit_id):
        unit = UNITS[unit_id]
        missing = {}
        for resource_id, amount in unit.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def _schedule_scout(self):
        if self.scout_planner is None:
            return None
        if (self.step_index - 1) % self.scout_interval != 0:
            return None
        report = self.scout_planner.step()
        decision = self.ai._record_decision(
            "scout_schedule",
            "adaptive_memory_strategy",
            scout_step=self.scout_planner.step_index,
            threat_count=len(report.get("threats", [])),
            route_index=self.scout_planner.route_index,
        )
        self.scout_history.append(decision)
        self.history.append(decision)
        return report

    def step(self):
        self.step_index += 1
        self._schedule_scout()
        threat = self.memory.best_threat(current_step=self.step_index)
        if threat is None:
            decision = self.ai._record_decision("scout_patrol", "adaptive_no_memory")
            self.history.append(decision)
            return decision

        preferred_unit = self._preferred_unit_for_threat(threat)
        existing = self.ai.roster_units(("militia", "archer"))
        if len(existing) < self.min_response_units and existing and not self.regroup_done:
            decision = self.ai.regroup_units(existing, self.regroup_point, reason="adaptive_memory_outnumbered")
            decision["remembered_threat_name"] = threat.get("name")
            decision["preferred_unit_id"] = preferred_unit
            self.regroup_done = True
            self.history.append(decision)
            return decision

        if self.ai.unit_count(preferred_unit) < self.min_response_units:
            missing = self._missing_training_resources(preferred_unit)
            if missing:
                decision = self.ai.gather_resources(self.income_per_step, "adaptive_build_order_income")
                decision["missing_before_income"] = missing
                decision["remembered_threat_name"] = threat.get("name")
                decision["preferred_unit_id"] = preferred_unit
                self.history.append(decision)
                return decision

            if self.ai.available_population() <= 1:
                house, decision = self.ai.build_complete_building(
                    "house",
                    self._next_house_point(),
                    name="ai_adaptive_house_{0}".format(self.ai.building_count("house") + 1),
                )
                if house is None:
                    decision = self.ai.gather_resources({"wood": 50}, "adaptive_house_income")
                decision["remembered_threat_name"] = threat.get("name")
                decision["preferred_unit_id"] = preferred_unit
                self.history.append(decision)
                return decision

            ent, decision = self.ai.train_for_build_order(preferred_unit, self.min_response_units)
            if ent is not None:
                ent.name = "ai_adaptive_{0}_{1}".format(preferred_unit, self.ai.unit_count(preferred_unit))
            decision["remembered_threat_name"] = threat.get("name")
            decision["preferred_unit_id"] = preferred_unit
            self.history.append(decision)
            return decision

        if not self.response_launched:
            launched, decision = self.ai.launch_defense_to_position(
                threat["position"],
                target_name=threat.get("name"),
                defended_name=threat.get("defended_name"),
                unit_id=preferred_unit,
                min_units=self.min_response_units,
                reason="adaptive_memory_response",
            )
            self.response_launched = bool(launched)
            decision["preferred_unit_id"] = preferred_unit
            self.history.append(decision)
            return decision

        if not self.counterattack_launched and len(existing) >= self.counterattack_units:
            target = self._priority_target()
            if target is not None:
                launched, decision = self.ai.launch_roster_attack(
                    target,
                    unit_ids=("militia", preferred_unit),
                    min_units=self.counterattack_units,
                    reason="adaptive_counterattack",
                )
                self.counterattack_launched = bool(launched)
                decision["preferred_unit_id"] = preferred_unit
                decision["remembered_threat_name"] = threat.get("name")
                self.history.append(decision)
                return decision

        decision = self.ai._record_decision(
            "hold_position",
            "adaptive_response_complete",
            preferred_unit_id=preferred_unit,
            remembered_threat_name=threat.get("name"),
        )
        self.history.append(decision)
        return decision

    def snapshot(self):
        return {
            "step_index": self.step_index,
            "min_response_units": self.min_response_units,
            "counterattack_units": self.counterattack_units,
            "regroup_done": self.regroup_done,
            "response_launched": self.response_launched,
            "counterattack_launched": self.counterattack_launched,
            "regroup_point": _position_to_tuple(self.regroup_point),
            "preferred_unit_history": list(self.preferred_unit_history),
            "scout_history": list(self.scout_history),
            "memory": self.memory.snapshot(self.step_index),
            "history": list(self.history),
        }


class MapControlEvaluator(object):
    def __init__(self, control_points, friendly_assets=None, radius=24.0):
        self.control_points = [self._normalise_point(idx, item) for idx, item in enumerate(control_points)]
        self.friendly_assets = list(friendly_assets or [])
        self.radius = float(radius)

    def _normalise_point(self, idx, item):
        if isinstance(item, dict):
            position = item.get("position") or item.get("point")
            return {
                "name": item.get("name") or "control_{0}".format(idx + 1),
                "position": _position_to_tuple(position),
                "weight": float(item.get("weight", 1.0)),
            }
        return {
            "name": "control_{0}".format(idx + 1),
            "position": _position_to_tuple(item),
            "weight": 1.0,
        }

    def _positions(self, entities):
        positions = []
        for ent in entities:
            if ent is None or not _is_live_entity(ent):
                continue
            positions.append(_ent_xz(ent))
        return positions

    def _enemy_entities(self, target_groups):
        entities = []
        for group in (target_groups or {}).values():
            entities.extend(group)
        return entities

    def _nearest_distance(self, point, positions):
        best = None
        for pos in positions:
            dist = _distance(point, pos)
            if best is None or dist < best:
                best = dist
        return best

    def evaluate(self, friendly_entities=None, target_groups=None):
        friendly_positions = self._positions(list(self.friendly_assets) + list(friendly_entities or []))
        enemy_positions = self._positions(self._enemy_entities(target_groups))
        details = []
        counts = {
            "controlled": 0,
            "contested": 0,
            "enemy": 0,
            "neutral": 0,
        }
        weighted_score = 0.0
        total_weight = 0.0

        for point in self.control_points:
            position = point["position"]
            weight = float(point["weight"])
            total_weight += weight
            friendly_dist = self._nearest_distance(position, friendly_positions)
            enemy_dist = self._nearest_distance(position, enemy_positions)
            friendly_near = friendly_dist is not None and friendly_dist <= self.radius
            enemy_near = enemy_dist is not None and enemy_dist <= self.radius
            if friendly_near and enemy_near:
                owner = "contested"
                contribution = 0.5
            elif friendly_near:
                owner = "controlled"
                contribution = 1.0
            elif enemy_near:
                owner = "enemy"
                contribution = 0.0
            else:
                owner = "neutral"
                contribution = 0.25
            counts[owner] += 1
            weighted_score += weight * contribution
            details.append({
                "name": point["name"],
                "position": position,
                "weight": weight,
                "owner": owner,
                "friendly_distance": round(friendly_dist, 3) if friendly_dist is not None else None,
                "enemy_distance": round(enemy_dist, 3) if enemy_dist is not None else None,
            })

        score = weighted_score / total_weight if total_weight > 0.0 else 0.0
        summary = {
            "radius": self.radius,
            "score": round(score, 3),
            "controlled_count": counts["controlled"],
            "contested_count": counts["contested"],
            "enemy_count": counts["enemy"],
            "neutral_count": counts["neutral"],
            "total_points": len(self.control_points),
            "details": details,
        }
        return summary


class MapControlStrategyPlanner(object):
    def __init__(
        self,
        ai,
        target_groups,
        control_points,
        difficulty_id="standard",
        memory=None,
        regroup_point=None,
        house_points=None,
        map_control_radius=24.0,
    ):
        self.ai = ai
        self.target_groups = target_groups or {}
        self.profile = ai_difficulty_profile(difficulty_id)
        self.memory = memory
        self.evaluator = MapControlEvaluator(
            control_points,
            friendly_assets=[ai.barracks_ent],
            radius=map_control_radius,
        )
        base = _ent_xz(ai.barracks_ent)
        self.regroup_point = regroup_point or (base[0] - 8.0, base[1] - 6.0)
        self.house_points = list(house_points or [
            (base[0] + 8.0, base[1] - 8.0),
            (base[0] + 12.0, base[1] - 10.0),
        ])
        self.step_index = 0
        self.regroup_done = False
        self.attack_launched = False
        self.last_map_control = None
        self.last_timing = None
        self.history = []

    def _army_units(self):
        return self.ai.roster_units(("militia", "archer"))

    def _army_count(self):
        return len(self._army_units())

    def _enemy_military_count(self):
        count = 0
        for ent in self.target_groups.get("military", []):
            if _is_live_entity(ent):
                count += 1
        return count

    def _next_house_point(self):
        idx = min(self.ai.building_count("house"), len(self.house_points) - 1)
        return self.house_points[idx]

    def _preferred_unit(self):
        threat = self.memory.best_threat(current_step=max(1, self.step_index)) if self.memory is not None else None
        if threat is None:
            return self.profile["preferred_military_unit"]
        if threat.get("role") == "military":
            return "archer"
        return self.profile["preferred_military_unit"]

    def _missing_training_resources(self, unit_id):
        unit = UNITS[unit_id]
        missing = {}
        for resource_id, amount in unit.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def _timing(self, summary):
        army_count = self._army_count()
        enemy_military_count = self._enemy_military_count()
        army_advantage = army_count - enemy_military_count
        map_score = float(summary.get("score", 0.0))
        attack_score = (
            map_score * float(self.profile["map_control_weight"])
            + max(0, army_advantage) * float(self.profile["army_advantage_weight"])
            + army_count * 0.03
        )
        retreat_recommended = (
            army_count > 0
            and not self.regroup_done
            and (
                map_score < float(self.profile["retreat_threshold"])
                or army_advantage < 0
            )
        )
        attack_recommended = (
            army_count >= int(self.profile["military_target_units"])
            and attack_score >= float(self.profile["attack_threshold"])
        )
        timing = {
            "army_count": army_count,
            "enemy_military_count": enemy_military_count,
            "army_advantage": army_advantage,
            "attack_score": round(attack_score, 3),
            "attack_threshold": float(self.profile["attack_threshold"]),
            "retreat_threshold": float(self.profile["retreat_threshold"]),
            "attack_recommended": attack_recommended,
            "retreat_recommended": retreat_recommended and not attack_recommended,
            "build_order": list(self.profile.get("build_order", [])),
        }
        self.last_timing = timing
        return timing

    def _record_with_context(self, decision, summary, timing, preferred_unit):
        decision["difficulty_id"] = self.profile["id"]
        decision["preferred_unit_id"] = preferred_unit
        decision["map_control"] = summary
        decision["timing"] = timing
        self.history.append(decision)
        return decision

    def step(self):
        self.step_index += 1
        preferred_unit = self._preferred_unit()
        summary = self.evaluator.evaluate(self._army_units(), self.target_groups)
        timing = self._timing(summary)
        self.last_map_control = summary

        if timing["retreat_recommended"]:
            decision = self.ai.regroup_units(
                self._army_units(),
                self.regroup_point,
                reason="map_control_retreat",
            )
            self.regroup_done = True
            return self._record_with_context(decision, summary, timing, preferred_unit)

        if self.ai.unit_count(preferred_unit) < int(self.profile["military_target_units"]):
            missing = self._missing_training_resources(preferred_unit)
            if missing:
                decision = self.ai.gather_resources(self.profile["income_per_step"], "map_control_military_income")
                decision["missing_before_income"] = missing
                return self._record_with_context(decision, summary, timing, preferred_unit)

            if self.ai.available_population() <= 1:
                house, decision = self.ai.build_complete_building(
                    "house",
                    self._next_house_point(),
                    name="ai_map_control_house_{0}".format(self.ai.building_count("house") + 1),
                    reason="map_control_population",
                )
                if house is None:
                    decision = self.ai.gather_resources({"wood": 50}, "map_control_house_income")
                return self._record_with_context(decision, summary, timing, preferred_unit)

            ent, decision = self.ai.train_for_build_order(
                preferred_unit,
                int(self.profile["military_target_units"]),
            )
            if ent is not None:
                ent.name = "ai_map_control_{0}_{1}".format(preferred_unit, self.ai.unit_count(preferred_unit))
            return self._record_with_context(decision, summary, timing, preferred_unit)

        if timing["attack_recommended"] and not self.attack_launched:
            target, target_decision = self.ai.choose_priority_target(self.target_groups)
            self.history.append(target_decision)
            if target is not None:
                launched, decision = self.ai.launch_roster_attack(
                    target,
                    unit_ids=("militia", preferred_unit),
                    min_units=int(self.profile["military_target_units"]),
                    reason="map_control_attack",
                )
                self.attack_launched = bool(launched)
                return self._record_with_context(decision, summary, timing, preferred_unit)

        decision = self.ai._record_decision(
            "hold_position",
            "map_control_wait",
            army_count=timing["army_count"],
            attack_score=timing["attack_score"],
        )
        return self._record_with_context(decision, summary, timing, preferred_unit)

    def snapshot(self):
        return {
            "difficulty_id": self.profile["id"],
            "profile": dict(self.profile),
            "step_index": self.step_index,
            "regroup_done": self.regroup_done,
            "attack_launched": self.attack_launched,
            "regroup_point": _position_to_tuple(self.regroup_point),
            "last_map_control": dict(self.last_map_control or {}),
            "last_timing": dict(self.last_timing or {}),
            "history": list(self.history),
        }


class BranchingStrategyPlanner(object):
    def __init__(
        self,
        ai,
        target_groups,
        defended_assets=None,
        difficulty_id="standard",
        expansion_points=None,
        target_bases=None,
        expansion_building_id="town_center",
        defense_unit_id="militia",
        harass_unit_id=None,
        harassment_target_roles=None,
        house_points=None,
        sight_radius=96.0,
        threat_radius=44.0,
    ):
        self.ai = ai
        self.target_groups = target_groups or {}
        self.defended_assets = list(defended_assets or [ai.barracks_ent])
        self.profile = ai_difficulty_profile(difficulty_id)
        self.expansion_points = list(expansion_points or [])
        self.target_bases = int(target_bases if target_bases is not None else self.profile["expansion_target_bases"])
        self.expansion_building_id = expansion_building_id
        self.defense_unit_id = defense_unit_id
        self.harass_unit_id = harass_unit_id or self.profile["preferred_military_unit"]
        self.harassment_target_roles = tuple(harassment_target_roles or self.profile["harass_target_roles"])
        self.harass_interval_steps = int(self.profile["harass_interval_steps"])
        self.max_harass_waves = int(self.profile["max_harass_waves"])
        self.sight_radius = float(sight_radius)
        self.threat_radius = float(threat_radius)
        base = _ent_xz(ai.barracks_ent)
        self.house_points = list(house_points or [
            (base[0] + 8.0, base[1] - 8.0),
            (base[0] + 12.0, base[1] - 10.0),
            (base[0] + 16.0, base[1] - 12.0),
        ])
        self.step_index = 0
        self.defense_launched = False
        self.harass_launched = False
        self.harass_wave_count = 0
        self.last_harass_step = None
        self.harass_launch_history = []
        self.last_report = None
        self.history = []

    def _base_count(self):
        return self.ai.building_count(self.expansion_building_id)

    def _army_count(self):
        return self.ai.unit_count("militia") + self.ai.unit_count("archer")

    def _next_house_point(self):
        idx = min(self.ai.building_count("house"), len(self.house_points) - 1)
        return self.house_points[idx]

    def _next_expansion_point(self):
        if not self.expansion_points:
            base = _ent_xz(self.ai.barracks_ent)
            return (base[0] + 20.0 + 8.0 * max(0, self._base_count() - 1), base[1] + 14.0)
        idx = min(max(0, self._base_count() - 1), len(self.expansion_points) - 1)
        return self.expansion_points[idx]

    def _missing_training_resources(self, unit_id):
        unit = UNITS[unit_id]
        missing = {}
        for resource_id, amount in unit.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def _record(self, decision, branch, report=None):
        decision["strategy_branch"] = branch
        decision["difficulty_id"] = self.profile["id"]
        decision["base_count"] = self._base_count()
        decision["army_count"] = self._army_count()
        if report is not None:
            decision["scout_report"] = {
                "observed_count": len(report.get("observed", [])),
                "threat_count": len(report.get("threats", [])),
                "closest_threat_name": report.get("threats", [{}])[0].get("name") if report.get("threats") else None,
            }
        self.history.append(decision)
        return decision

    def _train_to_count(self, unit_id, target_count, branch, report=None):
        missing = self._missing_training_resources(unit_id)
        if missing:
            decision = self.ai.gather_resources(self.profile["income_per_step"], "{0}_income".format(branch))
            decision["missing_before_income"] = missing
            decision["preferred_unit_id"] = unit_id
            return self._record(decision, branch, report)

        if self.ai.available_population() <= 1:
            house, decision = self.ai.build_complete_building(
                "house",
                self._next_house_point(),
                name="ai_branching_house_{0}".format(self.ai.building_count("house") + 1),
                reason="{0}_population".format(branch),
            )
            if house is None:
                decision = self.ai.gather_resources({"wood": 50}, "{0}_house_income".format(branch))
            decision["preferred_unit_id"] = unit_id
            return self._record(decision, branch, report)

        ent, decision = self.ai.train_for_build_order(unit_id, target_count)
        if ent is not None:
            ent.name = "ai_branching_{0}_{1}".format(unit_id, self.ai.unit_count(unit_id))
        decision["preferred_unit_id"] = unit_id
        return self._record(decision, branch, report)

    def _harass_target(self):
        for role in self.harassment_target_roles:
            for ent in self.target_groups.get(role, []):
                if _is_live_entity(ent):
                    return role, ent
        return None, None

    def _harass_ready(self):
        if self.harass_wave_count >= self.max_harass_waves:
            return False
        if self.last_harass_step is None:
            return True
        return self.step_index - int(self.last_harass_step) >= self.harass_interval_steps

    def _restore_from_snapshot(self, snapshot):
        snapshot = dict(snapshot or {})
        self.step_index = int(snapshot.get("step_index", self.step_index))
        self.defense_launched = bool(snapshot.get("defense_launched", self.defense_launched))
        self.harass_launched = bool(snapshot.get("harass_launched", self.harass_launched))
        self.harass_wave_count = int(snapshot.get("harass_wave_count", self.harass_wave_count))
        self.last_harass_step = snapshot.get("last_harass_step", self.last_harass_step)
        self.harass_launch_history = list(snapshot.get("harass_launch_history", self.harass_launch_history))
        self.history = list(snapshot.get("history", self.history))
        return self

    @classmethod
    def from_snapshot(cls, snapshot, ai, target_groups, defended_assets=None, expansion_points=None):
        snapshot = dict(snapshot or {})
        planner = cls(
            ai,
            target_groups,
            defended_assets=defended_assets,
            difficulty_id=snapshot.get("difficulty_id", "standard"),
            expansion_points=expansion_points,
            target_bases=snapshot.get("target_bases"),
            expansion_building_id=snapshot.get("expansion_building_id", "town_center"),
            defense_unit_id=snapshot.get("defense_unit_id", "militia"),
            harass_unit_id=snapshot.get("harass_unit_id", "archer"),
            harassment_target_roles=snapshot.get("harassment_target_roles"),
            house_points=snapshot.get("house_points"),
            sight_radius=snapshot.get("sight_radius", 96.0),
            threat_radius=snapshot.get("threat_radius", 44.0),
        )
        return planner._restore_from_snapshot(snapshot)

    def step(self):
        self.step_index += 1
        report = self.ai.scout_report(
            self.target_groups,
            scout_ent=self.ai.barracks_ent,
            defended_assets=self.defended_assets,
            sight_radius=self.sight_radius,
            threat_radius=self.threat_radius,
        )
        self.last_report = report
        threats = report.get("threats", [])
        if threats and not self.defense_launched:
            min_defenders = int(self.profile["defense_min_units"])
            if self.ai.unit_count(self.defense_unit_id) < min_defenders:
                return self._train_to_count(self.defense_unit_id, min_defenders, "branching_defense", report)
            threat = threats[0]
            launched, decision = self.ai.launch_defense_to_position(
                threat["position"],
                target_name=threat.get("name"),
                defended_name=threat.get("defended_name"),
                unit_id=self.defense_unit_id,
                min_units=min_defenders,
                reason="branching_defense",
            )
            self.defense_launched = bool(launched)
            decision["target_role"] = threat.get("role")
            return self._record(decision, "branching_defense", report)

        if self._base_count() < self.target_bases and self._army_count() >= int(self.profile["expansion_min_units"]):
            building = BUILDINGS[self.expansion_building_id]
            if not self.ai.player_state.can_afford(building.get("cost", {})):
                decision = self.ai.gather_resources(self.profile["income_per_step"], "branching_expansion_income")
                decision["expansion_target_bases"] = self.target_bases
                return self._record(decision, "branching_expansion", report)
            ent, decision = self.ai.build_complete_building(
                self.expansion_building_id,
                self._next_expansion_point(),
                name="ai_branching_expansion_{0}".format(self._base_count() + 1),
                reason="branching_expansion",
            )
            decision["expansion_target_bases"] = self.target_bases
            decision["expansion_position"] = _ent_xz(ent) if ent is not None else None
            return self._record(decision, "branching_expansion", report)

        min_harassers = int(self.profile["harass_min_units"])
        if self.ai.unit_count(self.harass_unit_id) < min_harassers:
            return self._train_to_count(self.harass_unit_id, min_harassers, "branching_harass", report)

        if self._harass_ready():
            target_role, target = self._harass_target()
            if target is not None:
                launched, decision = self.ai.launch_roster_attack(
                    target,
                    unit_ids=(self.harass_unit_id,),
                    min_units=min_harassers,
                    reason="branching_harass",
                )
                if launched:
                    self.harass_launched = True
                    self.harass_wave_count += 1
                    self.last_harass_step = self.step_index
                    self.harass_launch_history.append({
                        "step": self.step_index,
                        "target_role": target_role,
                        "target_name": getattr(target, "name", None),
                    })
                decision["target_role"] = target_role
                decision["harass_wave_count"] = self.harass_wave_count
                decision["harass_interval_steps"] = self.harass_interval_steps
                return self._record(decision, "branching_harass", report)

        decision = self.ai._record_decision(
            "hold_position",
            "branching_harass_cooldown" if self.harass_wave_count < self.max_harass_waves else "branching_strategy_complete",
            target_bases=self.target_bases,
            harass_wave_count=self.harass_wave_count,
            max_harass_waves=self.max_harass_waves,
            last_harass_step=self.last_harass_step,
            harass_interval_steps=self.harass_interval_steps,
        )
        return self._record(decision, "branching_hold", report)

    def snapshot(self):
        return {
            "difficulty_id": self.profile["id"],
            "profile": dict(self.profile),
            "step_index": self.step_index,
            "target_bases": self.target_bases,
            "expansion_building_id": self.expansion_building_id,
            "defense_unit_id": self.defense_unit_id,
            "harass_unit_id": self.harass_unit_id,
            "harassment_target_roles": list(self.harassment_target_roles),
            "harass_interval_steps": self.harass_interval_steps,
            "max_harass_waves": self.max_harass_waves,
            "harass_wave_count": self.harass_wave_count,
            "last_harass_step": self.last_harass_step,
            "harass_launch_history": list(self.harass_launch_history),
            "house_points": [_position_to_tuple(point) for point in self.house_points],
            "sight_radius": self.sight_radius,
            "threat_radius": self.threat_radius,
            "base_count": self._base_count(),
            "army_count": self._army_count(),
            "defense_launched": self.defense_launched,
            "harass_launched": self.harass_launched,
            "last_report": compact_scout_report(self.last_report or {}),
            "history": list(self.history),
        }


class MultiFrontArmyPlanner(object):
    def __init__(
        self,
        ai,
        target_groups,
        defended_assets=None,
        difficulty_id="hard",
        defense_unit_id="militia",
        harass_unit_id="archer",
        attack_unit_id="archer",
        min_defenders=None,
        min_harassers=None,
        min_attackers=2,
        harass_target_roles=None,
        attack_target_roles=None,
        sight_radius=96.0,
        threat_radius=44.0,
    ):
        self.ai = ai
        self.target_groups = target_groups or {}
        self.defended_assets = list(defended_assets or [ai.barracks_ent])
        self.profile = ai_difficulty_profile(difficulty_id)
        self.defense_unit_id = defense_unit_id
        self.harass_unit_id = harass_unit_id
        self.attack_unit_id = attack_unit_id
        self.min_defenders = int(min_defenders if min_defenders is not None else self.profile["defense_min_units"])
        self.min_harassers = int(min_harassers if min_harassers is not None else self.profile["harass_min_units"])
        self.min_attackers = int(min_attackers)
        self.harass_target_roles = tuple(harass_target_roles or ("villagers",))
        self.attack_target_roles = tuple(attack_target_roles or ("buildings", "town_center"))
        self.sight_radius = float(sight_radius)
        self.threat_radius = float(threat_radius)
        self.step_index = 0
        self.defense_launched = False
        self.harass_launched = False
        self.attack_launched = False
        self.front_assignments = {}
        self.front_history = []
        self.history = []
        self.last_report = None

    def _assigned_ids(self):
        ids = set()
        for names in self.front_assignments.values():
            for ent_id in names.get("entity_ids", []):
                ids.add(ent_id)
        return ids

    def _record_front(self, front_id, units, target, target_role, decision):
        assignment = {
            "front_id": front_id,
            "unit_names": [getattr(ent, "name", None) for ent in units],
            "entity_ids": [id(ent) for ent in units],
            "target_name": getattr(target, "name", None) if target is not None else decision.get("target_name"),
            "target_role": target_role,
            "target_position": decision.get("target_position"),
            "step": self.step_index,
        }
        self.front_assignments[front_id] = assignment
        self.front_history.append(assignment)
        decision["front_id"] = front_id
        decision["target_role"] = target_role
        decision["multi_front_assignments"] = {
            key: list(value.get("unit_names", []))
            for key, value in self.front_assignments.items()
        }
        self.history.append(decision)
        return decision

    def _target_for_roles(self, roles):
        for role in roles:
            for ent in self.target_groups.get(role, []):
                if _is_live_entity(ent):
                    return role, ent
        return None, None

    def _launch_front(self, front_id, unit_id, count, target, target_role, reason):
        units = self.ai.select_live_units(unit_id, count, exclude=self._assigned_ids())
        if len(units) < int(count):
            decision = self.ai._record_decision(
                "wait_front",
                "not_enough_units",
                front_id=front_id,
                unit_id=unit_id,
                ready_units=len(units),
                min_units=int(count),
            )
            self.history.append(decision)
            return False, decision
        decision = self.ai.launch_units_to_target(
            units,
            target,
            action="front_attack" if front_id != "defense" else "front_defend",
            reason=reason,
            front_id=front_id,
        )
        self._record_front(front_id, units, target, target_role, decision)
        return True, decision

    def step(self):
        self.step_index += 1
        report = self.ai.scout_report(
            self.target_groups,
            scout_ent=self.ai.barracks_ent,
            defended_assets=self.defended_assets,
            sight_radius=self.sight_radius,
            threat_radius=self.threat_radius,
        )
        self.last_report = report

        if not self.defense_launched and report.get("threats"):
            threat = report["threats"][0]
            launched, decision = self._launch_front(
                "defense",
                self.defense_unit_id,
                self.min_defenders,
                threat["entity"],
                threat.get("role"),
                "multi_front_defense",
            )
            self.defense_launched = bool(launched)
            return decision

        if not self.harass_launched:
            target_role, target = self._target_for_roles(self.harass_target_roles)
            if target is not None:
                launched, decision = self._launch_front(
                    "harass",
                    self.harass_unit_id,
                    self.min_harassers,
                    target,
                    target_role,
                    "multi_front_harass",
                )
                self.harass_launched = bool(launched)
                return decision

        if not self.attack_launched:
            target_role, target = self._target_for_roles(self.attack_target_roles)
            if target is not None:
                launched, decision = self._launch_front(
                    "attack",
                    self.attack_unit_id,
                    self.min_attackers,
                    target,
                    target_role,
                    "multi_front_attack",
                )
                self.attack_launched = bool(launched)
                return decision

        decision = self.ai._record_decision(
            "hold_position",
            "multi_front_complete" if self.attack_launched else "multi_front_wait",
            fronts=list(sorted(self.front_assignments.keys())),
        )
        self.history.append(decision)
        return decision

    def snapshot(self):
        return {
            "difficulty_id": self.profile["id"],
            "step_index": self.step_index,
            "defense_launched": self.defense_launched,
            "harass_launched": self.harass_launched,
            "attack_launched": self.attack_launched,
            "front_assignments": dict(self.front_assignments),
            "front_history": list(self.front_history),
            "last_report": compact_scout_report(self.last_report or {}),
            "history": list(self.history),
        }


class MatchLengthBuildOrderPlanner(object):
    def __init__(
        self,
        ai,
        target_groups,
        defended_assets=None,
        difficulty_id="standard",
        expansion_points=None,
        target_bases=None,
        attack_unit_id=None,
        economy_opening_steps=None,
        house_points=None,
        threat_radius=44.0,
    ):
        self.ai = ai
        self.target_groups = target_groups or {}
        self.defended_assets = list(defended_assets or [ai.barracks_ent])
        self.profile = ai_difficulty_profile(difficulty_id)
        self.expansion_points = list(expansion_points or [])
        self.target_bases = int(target_bases if target_bases is not None else self.profile["expansion_target_bases"])
        self.attack_unit_id = attack_unit_id or self.profile["preferred_military_unit"]
        self.economy_opening_steps = int(
            economy_opening_steps
            if economy_opening_steps is not None
            else max(2, min(6, int(round(3.0 + self.profile["economy_weight"] - self.profile["military_weight"]))))
        )
        base = _ent_xz(ai.barracks_ent)
        self.house_points = list(house_points or [
            (base[0] + 8.0, base[1] - 8.0),
            (base[0] + 12.0, base[1] - 10.0),
            (base[0] + 16.0, base[1] - 12.0),
        ])
        self.threat_radius = float(threat_radius)
        self.step_index = 0
        self.defense_launched = False
        self.attack_launched = False
        self.transition_step = None
        self.expansion_step = None
        self.attack_step = None
        self.defense_step = None
        self.phase_history = []
        self.history = []
        self.last_report = None

    def _base_count(self):
        return self.ai.building_count("town_center")

    def _army_count(self):
        return self.ai.unit_count("militia") + self.ai.unit_count("archer")

    def _target_army_count(self):
        return int(self.profile["military_target_units"])

    def _next_house_point(self):
        idx = min(self.ai.building_count("house"), len(self.house_points) - 1)
        return self.house_points[idx]

    def _next_expansion_point(self):
        if not self.expansion_points:
            base = _ent_xz(self.ai.barracks_ent)
            return (base[0] + 20.0 + 8.0 * max(0, self._base_count() - 1), base[1] + 14.0)
        idx = min(max(0, self._base_count() - 1), len(self.expansion_points) - 1)
        return self.expansion_points[idx]

    def _missing_training_resources(self, unit_id):
        unit = UNITS[unit_id]
        missing = {}
        for resource_id, amount in unit.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def _record(self, decision, phase, report=None):
        decision["match_phase"] = phase
        decision["difficulty_id"] = self.profile["id"]
        decision["economy_opening_steps"] = self.economy_opening_steps
        decision["transition_step"] = self.transition_step
        decision["base_count"] = self._base_count()
        decision["army_count"] = self._army_count()
        if report is not None:
            decision["scout_report"] = {
                "observed_count": len(report.get("observed", [])),
                "threat_count": len(report.get("threats", [])),
                "closest_threat_name": report.get("threats", [{}])[0].get("name") if report.get("threats") else None,
            }
        self.phase_history.append(phase)
        self.history.append(decision)
        return decision

    def _mark_transition(self):
        if self.transition_step is None:
            self.transition_step = self.step_index

    def _train_to_count(self, unit_id, target_count, phase, report=None):
        self._mark_transition()
        missing = self._missing_training_resources(unit_id)
        if missing:
            decision = self.ai.gather_resources(self.profile["income_per_step"], "{0}_income".format(phase))
            decision["missing_before_income"] = missing
            decision["preferred_unit_id"] = unit_id
            return self._record(decision, phase, report)

        if self.ai.available_population() <= 1:
            house, decision = self.ai.build_complete_building(
                "house",
                self._next_house_point(),
                name="ai_match_house_{0}".format(self.ai.building_count("house") + 1),
                reason="{0}_population".format(phase),
            )
            if house is None:
                decision = self.ai.gather_resources({"wood": 50}, "{0}_house_income".format(phase))
            decision["preferred_unit_id"] = unit_id
            return self._record(decision, phase, report)

        ent, decision = self.ai.train_for_build_order(unit_id, target_count)
        if ent is not None:
            ent.name = "ai_match_{0}_{1}".format(unit_id, self.ai.unit_count(unit_id))
        decision["preferred_unit_id"] = unit_id
        return self._record(decision, phase, report)

    def _attack_target(self):
        for role in self.profile["harass_target_roles"]:
            for ent in self.target_groups.get(role, []):
                if _is_live_entity(ent):
                    return role, ent
        return None, None

    def step(self):
        self.step_index += 1
        report = self.ai.scout_report(
            self.target_groups,
            scout_ent=self.ai.barracks_ent,
            defended_assets=self.defended_assets,
            sight_radius=96.0,
            threat_radius=self.threat_radius,
        )
        self.last_report = report
        threats = report.get("threats", [])

        if threats and not self.defense_launched:
            self._mark_transition()
            min_defenders = int(self.profile["defense_min_units"])
            if self.ai.unit_count("militia") < min_defenders:
                return self._train_to_count("militia", min_defenders, "defense_reaction", report)
            threat = threats[0]
            launched, decision = self.ai.launch_defense_to_position(
                threat["position"],
                target_name=threat.get("name"),
                defended_name=threat.get("defended_name"),
                unit_id="militia",
                min_units=min_defenders,
                reason="match_defense_reaction",
            )
            self.defense_launched = bool(launched)
            self.defense_step = self.step_index if launched else self.defense_step
            decision["target_role"] = threat.get("role")
            return self._record(decision, "defense_reaction", report)

        if self.step_index <= self.economy_opening_steps:
            decision = self.ai.gather_resources(self.profile["income_per_step"], "match_opening_economy")
            return self._record(decision, "opening_economy", report)

        if self._base_count() < self.target_bases and self._army_count() >= int(self.profile["expansion_min_units"]):
            building = BUILDINGS["town_center"]
            if not self.ai.player_state.can_afford(building.get("cost", {})):
                decision = self.ai.gather_resources(self.profile["income_per_step"], "match_expansion_income")
                decision["expansion_target_bases"] = self.target_bases
                return self._record(decision, "expansion_timing", report)
            ent, decision = self.ai.build_complete_building(
                "town_center",
                self._next_expansion_point(),
                name="ai_match_expansion_{0}".format(self._base_count() + 1),
                reason="match_expansion",
            )
            self.expansion_step = self.step_index if self.expansion_step is None else self.expansion_step
            decision["expansion_target_bases"] = self.target_bases
            decision["expansion_position"] = _ent_xz(ent) if ent is not None else None
            return self._record(decision, "expansion_timing", report)

        if self.ai.unit_count(self.attack_unit_id) < self._target_army_count():
            return self._train_to_count(self.attack_unit_id, self._target_army_count(), "military_transition", report)

        if not self.attack_launched:
            self._mark_transition()
            target_role, target = self._attack_target()
            if target is not None:
                launched, decision = self.ai.launch_roster_attack(
                    target,
                    unit_ids=(self.attack_unit_id,),
                    min_units=self._target_army_count(),
                    reason="match_attack_timing",
                )
                self.attack_launched = bool(launched)
                self.attack_step = self.step_index if launched else self.attack_step
                decision["target_role"] = target_role
                return self._record(decision, "attack_timing", report)

        decision = self.ai._record_decision(
            "hold_position",
            "match_plan_complete" if self.attack_launched else "match_no_target",
            target_bases=self.target_bases,
            transition_step=self.transition_step,
            attack_step=self.attack_step,
        )
        return self._record(decision, "match_hold", report)

    def snapshot(self):
        return {
            "difficulty_id": self.profile["id"],
            "profile": dict(self.profile),
            "step_index": self.step_index,
            "economy_opening_steps": self.economy_opening_steps,
            "target_bases": self.target_bases,
            "attack_unit_id": self.attack_unit_id,
            "target_army_count": self._target_army_count(),
            "transition_step": self.transition_step,
            "expansion_step": self.expansion_step,
            "attack_step": self.attack_step,
            "defense_step": self.defense_step,
            "defense_launched": self.defense_launched,
            "attack_launched": self.attack_launched,
            "base_count": self._base_count(),
            "army_count": self._army_count(),
            "attack_unit_count": self.ai.unit_count(self.attack_unit_id),
            "phase_history": list(self.phase_history),
            "last_report": compact_scout_report(self.last_report or {}),
            "history": list(self.history),
        }


class AttritionRecoveryPlanner(object):
    def __init__(
        self,
        ai,
        target_groups,
        defended_assets=None,
        difficulty_id="hard",
        expansion_points=None,
        target_bases=None,
        attack_unit_id=None,
        defense_unit_id="militia",
        target_army_count=None,
        regroup_point=None,
        house_points=None,
        research_queue=None,
        pressure_technology_id=None,
        tech_failure_threshold=2,
        sight_radius=96.0,
        threat_radius=44.0,
    ):
        self.ai = ai
        self.target_groups = target_groups or {}
        self.defended_assets = list(defended_assets or [ai.barracks_ent])
        self.profile = ai_difficulty_profile(difficulty_id)
        self.expansion_points = list(expansion_points or [])
        self.target_bases = int(target_bases if target_bases is not None else self.profile["expansion_target_bases"])
        self.attack_unit_id = attack_unit_id or self.profile["preferred_military_unit"]
        self.defense_unit_id = defense_unit_id
        self.target_army_count = int(target_army_count if target_army_count is not None else self.profile["military_target_units"])
        self.research_queue = research_queue
        self.pressure_technology_id = pressure_technology_id or ai_composition_plan(self.profile["id"])["technology_id"]
        self.tech_failure_threshold = int(tech_failure_threshold)
        base = _ent_xz(ai.barracks_ent)
        self.regroup_point = regroup_point or (base[0] + 6.0, base[1] - 8.0)
        self.house_points = list(house_points or [
            (base[0] + 8.0, base[1] - 8.0),
            (base[0] + 12.0, base[1] - 10.0),
            (base[0] + 16.0, base[1] - 12.0),
        ])
        self.sight_radius = float(sight_radius)
        self.threat_radius = float(threat_radius)
        self.step_index = 0
        self.initial_attack_launched = False
        self.initial_attack_step = None
        self.attack_failed = False
        self.regroup_done = False
        self.pressure_defense_launched = False
        self.pressure_defense_step = None
        self.relaunch_launched = False
        self.relaunch_step = None
        self.awaiting_rebuild = False
        self.failed_wave_count = 0
        self.successful_wave_count = 0
        self.relaunch_count = 0
        self.wave_launch_history = []
        self.attack_outcome_history = []
        self.recovery_training_count = 0
        self.post_success_expansion_done = False
        self.pressure_tech_researched = self.pressure_technology_id in self.ai.player_state.researched_technologies
        self.pressure_tech_step = None
        self.pressure_tech_history = []
        self.phase_history = []
        self.score_history = []
        self.history = []
        self.last_report = None

    def _base_count(self):
        return self.ai.building_count("town_center")

    def _army_count(self):
        return self.ai.live_unit_count("militia") + self.ai.live_unit_count("archer")

    def _live_attack_count(self):
        return self.ai.live_unit_count(self.attack_unit_id)

    def _active_target_army_count(self):
        return self.target_army_count + (1 if self.failed_wave_count >= 2 else 0)

    def _next_house_point(self):
        idx = min(self.ai.building_count("house"), len(self.house_points) - 1)
        return self.house_points[idx]

    def _next_expansion_point(self):
        if not self.expansion_points:
            base = _ent_xz(self.ai.barracks_ent)
            return (base[0] + 20.0 + 8.0 * max(0, self._base_count() - 1), base[1] + 14.0)
        idx = min(max(0, self._base_count() - 1), len(self.expansion_points) - 1)
        return self.expansion_points[idx]

    def _missing_training_resources(self, unit_id):
        unit = UNITS[unit_id]
        missing = {}
        for resource_id, amount in unit.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def _missing_research_resources(self, technology_id):
        technology = TECHNOLOGIES[technology_id]
        missing = {}
        for resource_id, amount in technology.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def _pressure_tech_due(self):
        return (
            self.research_queue is not None
            and self.pressure_technology_id
            and self.failed_wave_count >= self.tech_failure_threshold
            and self.pressure_technology_id not in self.ai.player_state.researched_technologies
        )

    def _scores(self, report):
        pressure = len(report.get("threats", [])) > 0
        failure = self.awaiting_rebuild or (
            self.initial_attack_launched
            and not self.successful_wave_count
            and self._live_attack_count() < self._active_target_army_count()
        )
        economy_need = 1.0 if self._base_count() < self.target_bases else 0.2
        military_need = 1.0 if self._live_attack_count() < self._active_target_army_count() else 0.35
        if pressure:
            economy_need *= 0.35
            military_need += 0.65
        if failure:
            economy_need *= 0.35
            military_need += 0.75
        scores = {
            "economy": round(float(self.profile["economy_weight"]) * economy_need, 3),
            "military": round(float(self.profile["military_weight"]) * military_need, 3),
            "live_pressure": pressure,
            "attack_failure": failure,
            "base_count": self._base_count(),
            "army_count": self._army_count(),
            "live_attack_count": self._live_attack_count(),
            "target_army_count": self._active_target_army_count(),
            "failed_wave_count": self.failed_wave_count,
            "successful_wave_count": self.successful_wave_count,
            "pressure_technology_id": self.pressure_technology_id,
            "pressure_tech_researched": self.pressure_technology_id in self.ai.player_state.researched_technologies,
        }
        self.score_history.append(scores)
        return scores

    def _record(self, decision, phase, report, scores):
        decision["attrition_phase"] = phase
        decision["difficulty_id"] = self.profile["id"]
        decision["attack_unit_id"] = self.attack_unit_id
        decision["target_army_count"] = self._active_target_army_count()
        decision["live_attack_count"] = self._live_attack_count()
        decision["army_count"] = self._army_count()
        decision["base_count"] = self._base_count()
        decision["failed_wave_count"] = self.failed_wave_count
        decision["successful_wave_count"] = self.successful_wave_count
        decision["pressure_technology_id"] = self.pressure_technology_id
        decision["pressure_tech_researched"] = self.pressure_technology_id in self.ai.player_state.researched_technologies
        decision["scores"] = dict(scores)
        decision["scout_report"] = {
            "observed_count": len(report.get("observed", [])),
            "threat_count": len(report.get("threats", [])),
            "closest_threat_name": report.get("threats", [{}])[0].get("name") if report.get("threats") else None,
        }
        self.phase_history.append(phase)
        self.history.append(decision)
        return decision

    def _train_live_to_count(self, unit_id, target_count, phase, report, scores):
        if self.ai.live_unit_count(unit_id) >= int(target_count):
            decision = self.ai._record_decision(
                "wait_training",
                "{0}_target_met".format(phase),
                unit_id=unit_id,
                live_units=self.ai.live_unit_count(unit_id),
                target_count=int(target_count),
            )
            return self._record(decision, phase, report, scores)

        missing = self._missing_training_resources(unit_id)
        if missing:
            decision = self.ai.gather_resources(self.profile["income_per_step"], "{0}_income".format(phase))
            decision["missing_before_income"] = missing
            decision["preferred_unit_id"] = unit_id
            return self._record(decision, phase, report, scores)

        if self.ai.available_population() <= 1:
            house, decision = self.ai.build_complete_building(
                "house",
                self._next_house_point(),
                name="ai_attrition_house_{0}".format(self.ai.building_count("house") + 1),
                reason="{0}_population".format(phase),
            )
            if house is None:
                decision = self.ai.gather_resources({"wood": 50}, "{0}_house_income".format(phase))
            decision["preferred_unit_id"] = unit_id
            return self._record(decision, phase, report, scores)

        self.ai.queue.enqueue(unit_id)
        ent = self.ai.queue.finish_next()
        if ent is not None:
            ent.name = "ai_attrition_{0}_{1}".format(unit_id, self.ai.unit_count(unit_id))
        self.recovery_training_count += 1
        decision = self.ai._record_decision(
            "train",
            phase,
            unit_id=unit_id,
            entity_name=getattr(ent, "name", None),
            live_units=self.ai.live_unit_count(unit_id),
            target_count=int(target_count),
        )
        return self._record(decision, phase, report, scores)

    def _research_pressure_technology(self, report, scores):
        technology_id = self.pressure_technology_id
        missing = self._missing_research_resources(technology_id)
        if missing:
            decision = self.ai.gather_resources(self.profile["income_per_step"], "pressure_tech_income")
            decision["technology_id"] = technology_id
            decision["missing_before_income"] = missing
            return self._record(decision, "pressure_tech", report, scores)

        self.research_queue.enqueue(technology_id)
        completed = self.research_queue.finish_next()
        self.pressure_tech_researched = True
        self.pressure_tech_step = self.step_index
        self.pressure_tech_history.append({
            "step": self.step_index,
            "technology_id": completed,
            "failed_wave_count": self.failed_wave_count,
            "live_attack_count": self._live_attack_count(),
        })
        decision = self.ai._record_decision(
            "research",
            "pressure_tech",
            technology_id=completed,
            failed_wave_count=self.failed_wave_count,
            live_attack_count=self._live_attack_count(),
        )
        return self._record(decision, "pressure_tech", report, scores)

    def _attack_target(self):
        for role in self.profile["harass_target_roles"]:
            for ent in self.target_groups.get(role, []):
                if _is_live_entity(ent):
                    return role, ent
        return None, None

    def _mark_failure(self, reason, target_name=None):
        if not self.awaiting_rebuild:
            self.failed_wave_count += 1
            self.regroup_done = False
            self.attack_outcome_history.append({
                "step": self.step_index,
                "outcome": "failed",
                "reason": reason,
                "target_name": target_name,
                "failed_wave_count": self.failed_wave_count,
                "live_attack_count": self._live_attack_count(),
                "target_army_count": self._active_target_army_count(),
            })
        self.attack_failed = True
        self.awaiting_rebuild = True
        self.relaunch_launched = False

    def record_attack_outcome(self, outcome, reason="scripted_outcome", target_name=None):
        outcome = str(outcome)
        if outcome == "failed":
            self._mark_failure(reason, target_name=target_name)
        elif outcome == "success":
            self.successful_wave_count += 1
            self.awaiting_rebuild = False
            self.attack_failed = False
            self.attack_outcome_history.append({
                "step": self.step_index,
                "outcome": "success",
                "reason": reason,
                "target_name": target_name,
                "successful_wave_count": self.successful_wave_count,
                "live_attack_count": self._live_attack_count(),
                "target_army_count": self._active_target_army_count(),
            })
        return self.ai._record_decision(
            "attack_outcome",
            reason,
            outcome=outcome,
            target_name=target_name,
            failed_wave_count=self.failed_wave_count,
            successful_wave_count=self.successful_wave_count,
            live_attack_count=self._live_attack_count(),
            target_army_count=self._active_target_army_count(),
        )

    def step(self):
        self.step_index += 1
        report = self.ai.scout_report(
            self.target_groups,
            scout_ent=self.ai.barracks_ent,
            defended_assets=self.defended_assets,
            sight_radius=self.sight_radius,
            threat_radius=self.threat_radius,
        )
        self.last_report = report
        scores = self._scores(report)
        threats = report.get("threats", [])

        if threats and not self.pressure_defense_launched:
            min_defenders = int(self.profile["defense_min_units"])
            if self.ai.live_unit_count(self.defense_unit_id) < min_defenders:
                return self._train_live_to_count(self.defense_unit_id, min_defenders, "live_pressure_defense", report, scores)
            threat = threats[0]
            launched, decision = self.ai.launch_defense_to_position(
                threat["position"],
                target_name=threat.get("name"),
                defended_name=threat.get("defended_name"),
                unit_id=self.defense_unit_id,
                min_units=min_defenders,
                reason="live_pressure_defense",
            )
            self.pressure_defense_launched = bool(launched)
            self.pressure_defense_step = self.step_index if launched else self.pressure_defense_step
            decision["target_role"] = threat.get("role")
            return self._record(decision, "live_pressure_defense", report, scores)

        if (
            self.initial_attack_launched
            and not self.successful_wave_count
            and self._live_attack_count() < self._active_target_army_count()
        ):
            self._mark_failure("detected_failed_attack")
            live_roster = self.ai.roster_units(("militia", "archer"))
            if live_roster and not self.regroup_done:
                decision = self.ai.regroup_units(live_roster, self.regroup_point, reason="failed_attack_regroup")
                self.regroup_done = True
                return self._record(decision, "failed_attack_regroup", report, scores)
            if self._pressure_tech_due():
                return self._research_pressure_technology(report, scores)
            return self._train_live_to_count(
                self.attack_unit_id,
                self._active_target_army_count(),
                "attrition_rebuild",
                report,
                scores,
            )

        if self.attack_failed and self.awaiting_rebuild and self._pressure_tech_due():
            return self._research_pressure_technology(report, scores)

        if self.attack_failed and self.awaiting_rebuild and self._live_attack_count() >= self._active_target_army_count():
            target_role, target = self._attack_target()
            if target is not None:
                launched, decision = self.ai.launch_roster_attack(
                    target,
                    unit_ids=(self.attack_unit_id,),
                    min_units=self._active_target_army_count(),
                    reason="attrition_relaunch",
                )
                self.relaunch_launched = bool(launched)
                self.relaunch_step = self.step_index if launched else self.relaunch_step
                if launched:
                    self.relaunch_count += 1
                    self.awaiting_rebuild = False
                    self.wave_launch_history.append({
                        "step": self.step_index,
                        "kind": "relaunch",
                        "target_role": target_role,
                        "target_name": getattr(target, "name", None),
                        "target_army_count": self._active_target_army_count(),
                    })
                decision["target_role"] = target_role
                return self._record(decision, "attrition_relaunch", report, scores)

        if not self.initial_attack_launched:
            if self._live_attack_count() < self._active_target_army_count():
                return self._train_live_to_count(
                    self.attack_unit_id,
                    self._active_target_army_count(),
                    "initial_military_transition",
                    report,
                    scores,
                )
            target_role, target = self._attack_target()
            if target is not None:
                launched, decision = self.ai.launch_roster_attack(
                    target,
                    unit_ids=(self.attack_unit_id,),
                    min_units=self._active_target_army_count(),
                    reason="attrition_initial_attack",
                )
                self.initial_attack_launched = bool(launched)
                self.initial_attack_step = self.step_index if launched else self.initial_attack_step
                if launched:
                    self.wave_launch_history.append({
                        "step": self.step_index,
                        "kind": "initial",
                        "target_role": target_role,
                        "target_name": getattr(target, "name", None),
                        "target_army_count": self._active_target_army_count(),
                    })
                decision["target_role"] = target_role
                return self._record(decision, "initial_attack", report, scores)

        if self.successful_wave_count and scores["economy"] > scores["military"] and self._base_count() < self.target_bases:
            building = BUILDINGS["town_center"]
            if not self.ai.player_state.can_afford(building.get("cost", {})):
                decision = self.ai.gather_resources(self.profile["income_per_step"], "post_success_expansion_income")
                return self._record(decision, "post_success_expansion", report, scores)
            ent, decision = self.ai.build_complete_building(
                "town_center",
                self._next_expansion_point(),
                name="ai_attrition_expansion_{0}".format(self._base_count() + 1),
                reason="post_success_expansion",
            )
            self.post_success_expansion_done = ent is not None
            decision["expansion_position"] = _ent_xz(ent) if ent is not None else None
            return self._record(decision, "post_success_expansion", report, scores)

        decision = self.ai._record_decision(
            "hold_position",
            "attrition_plan_complete" if self.relaunch_launched else "attrition_wait",
            attack_failed=self.attack_failed,
            relaunch_launched=self.relaunch_launched,
        )
        return self._record(decision, "attrition_hold", report, scores)

    def snapshot(self):
        return {
            "difficulty_id": self.profile["id"],
            "profile": dict(self.profile),
            "step_index": self.step_index,
            "target_bases": self.target_bases,
            "attack_unit_id": self.attack_unit_id,
            "defense_unit_id": self.defense_unit_id,
            "target_army_count": self.target_army_count,
            "regroup_point": _position_to_tuple(self.regroup_point),
            "initial_attack_launched": self.initial_attack_launched,
            "initial_attack_step": self.initial_attack_step,
            "attack_failed": self.attack_failed,
            "regroup_done": self.regroup_done,
            "pressure_defense_launched": self.pressure_defense_launched,
            "pressure_defense_step": self.pressure_defense_step,
            "relaunch_launched": self.relaunch_launched,
            "relaunch_step": self.relaunch_step,
            "awaiting_rebuild": self.awaiting_rebuild,
            "failed_wave_count": self.failed_wave_count,
            "successful_wave_count": self.successful_wave_count,
            "relaunch_count": self.relaunch_count,
            "pressure_technology_id": self.pressure_technology_id,
            "tech_failure_threshold": self.tech_failure_threshold,
            "pressure_tech_researched": self.pressure_technology_id in self.ai.player_state.researched_technologies,
            "pressure_tech_step": self.pressure_tech_step,
            "pressure_tech_history": list(self.pressure_tech_history),
            "researched_technologies": sorted(self.ai.player_state.researched_technologies),
            "wave_launch_history": list(self.wave_launch_history),
            "attack_outcome_history": list(self.attack_outcome_history),
            "recovery_training_count": self.recovery_training_count,
            "active_target_army_count": self._active_target_army_count(),
            "post_success_expansion_done": self.post_success_expansion_done,
            "live_attack_count": self._live_attack_count(),
            "base_count": self._base_count(),
            "army_count": self._army_count(),
            "phase_history": list(self.phase_history),
            "score_history": list(self.score_history),
            "last_report": compact_scout_report(self.last_report or {}),
            "history": list(self.history),
        }


class StrategicMacroPlanner(object):
    def __init__(
        self,
        ai,
        target_groups=None,
        memory=None,
        difficulty_id="standard",
        expansion_points=None,
        target_bases=2,
        expansion_building_id="town_center",
        military_unit_by_role=None,
        house_points=None,
    ):
        self.ai = ai
        self.target_groups = target_groups or {}
        self.memory = memory
        self.profile = ai_difficulty_profile(difficulty_id)
        self.expansion_points = list(expansion_points or [])
        self.target_bases = int(target_bases)
        self.expansion_building_id = expansion_building_id
        self.military_unit_by_role = dict(military_unit_by_role or {
            "military": self.profile["preferred_military_unit"],
            "villagers": "militia",
            "buildings": "militia",
            "town_center": "militia",
        })
        base = _ent_xz(ai.barracks_ent)
        self.house_points = list(house_points or [
            (base[0] + 8.0, base[1] - 8.0),
            (base[0] + 12.0, base[1] - 10.0),
        ])
        self.step_index = 0
        self.expansion_built = False
        self.military_ready = False
        self.last_scores = {}
        self.history = []

    def _army_count(self):
        return self.ai.unit_count("militia") + self.ai.unit_count("archer")

    def _base_count(self):
        return self.ai.building_count(self.expansion_building_id)

    def _next_house_point(self):
        idx = min(self.ai.building_count("house"), len(self.house_points) - 1)
        return self.house_points[idx]

    def _next_expansion_point(self):
        if not self.expansion_points:
            base = _ent_xz(self.ai.barracks_ent)
            return (base[0] + 20.0, base[1] + 14.0)
        idx = min(max(0, self._base_count() - 1), len(self.expansion_points) - 1)
        return self.expansion_points[idx]

    def _remembered_threat(self):
        if self.memory is None:
            return None
        return self.memory.best_threat(current_step=max(1, self.step_index))

    def _preferred_unit(self, threat):
        if threat is None:
            return self.profile["preferred_military_unit"]
        return self.military_unit_by_role.get(threat.get("role"), self.profile["preferred_military_unit"])

    def _missing_training_resources(self, unit_id):
        unit = UNITS[unit_id]
        missing = {}
        for resource_id, amount in unit.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def _strategy_scores(self, threat):
        expansion_open = self._base_count() < self.target_bases
        army_count = self._army_count()
        enough_screen = army_count >= int(self.profile["expansion_min_units"])
        economy_need = 1.0 if expansion_open and enough_screen else 0.0
        if expansion_open and not enough_screen:
            economy_need = 0.35
        military_need = 1.0 if army_count < int(self.profile["military_target_units"]) else 0.25
        if threat is not None:
            military_need += 0.75
        scores = {
            "economy": round(float(self.profile["economy_weight"]) * economy_need, 3),
            "military": round(float(self.profile["military_weight"]) * military_need, 3),
            "expansion_open": expansion_open,
            "army_count": army_count,
            "base_count": self._base_count(),
            "threat_name": threat.get("name") if threat else None,
            "threat_role": threat.get("role") if threat else None,
        }
        self.last_scores = scores
        return scores

    def step(self):
        self.step_index += 1
        threat = self._remembered_threat()
        scores = self._strategy_scores(threat)
        preferred_unit = self._preferred_unit(threat)

        if scores["economy"] > scores["military"] and scores["expansion_open"]:
            building = BUILDINGS[self.expansion_building_id]
            if not self.ai.player_state.can_afford(building.get("cost", {})):
                decision = self.ai.gather_resources(self.profile["income_per_step"], "strategic_expansion_income")
                decision["scores"] = scores
                decision["difficulty_id"] = self.profile["id"]
                self.history.append(decision)
                return decision

            ent, decision = self.ai.build_complete_building(
                self.expansion_building_id,
                self._next_expansion_point(),
                name="ai_expansion_{0}_{1}".format(self.expansion_building_id, self._base_count() + 1),
                reason="strategic_expansion",
            )
            self.expansion_built = ent is not None
            decision["scores"] = scores
            decision["difficulty_id"] = self.profile["id"]
            decision["strategy"] = "economy"
            self.history.append(decision)
            return decision

        if self.ai.unit_count(preferred_unit) < int(self.profile["military_target_units"]):
            missing = self._missing_training_resources(preferred_unit)
            if missing:
                decision = self.ai.gather_resources(self.profile["income_per_step"], "strategic_military_income")
                decision["missing_before_income"] = missing
                decision["preferred_unit_id"] = preferred_unit
                decision["scores"] = scores
                decision["difficulty_id"] = self.profile["id"]
                self.history.append(decision)
                return decision

            if self.ai.available_population() <= 1:
                house, decision = self.ai.build_complete_building(
                    "house",
                    self._next_house_point(),
                    name="ai_strategy_house_{0}".format(self.ai.building_count("house") + 1),
                    reason="strategic_population",
                )
                if house is None:
                    decision = self.ai.gather_resources({"wood": 50}, "strategic_house_income")
                decision["preferred_unit_id"] = preferred_unit
                decision["scores"] = scores
                decision["difficulty_id"] = self.profile["id"]
                self.history.append(decision)
                return decision

            ent, decision = self.ai.train_for_build_order(preferred_unit, int(self.profile["military_target_units"]))
            if ent is not None:
                ent.name = "ai_strategy_{0}_{1}".format(preferred_unit, self.ai.unit_count(preferred_unit))
            decision["preferred_unit_id"] = preferred_unit
            decision["scores"] = scores
            decision["difficulty_id"] = self.profile["id"]
            decision["strategy"] = "military"
            self.history.append(decision)
            return decision

        self.military_ready = True
        target, target_decision = self.ai.choose_priority_target(self.target_groups)
        self.history.append(target_decision)
        if target is None:
            decision = self.ai._record_decision(
                "hold_position",
                "strategic_no_target",
                preferred_unit_id=preferred_unit,
                difficulty_id=self.profile["id"],
            )
            self.history.append(decision)
            return decision
        launched, decision = self.ai.launch_roster_attack(
            target,
            unit_ids=("militia", preferred_unit),
            min_units=int(self.profile["military_target_units"]),
            reason="strategic_attack",
        )
        decision["preferred_unit_id"] = preferred_unit
        decision["scores"] = scores
        decision["difficulty_id"] = self.profile["id"]
        decision["strategy"] = "military"
        self.history.append(decision)
        return decision

    def snapshot(self):
        return {
            "difficulty_id": self.profile["id"],
            "profile": dict(self.profile),
            "step_index": self.step_index,
            "target_bases": self.target_bases,
            "expansion_building_id": self.expansion_building_id,
            "expansion_built": self.expansion_built,
            "military_ready": self.military_ready,
            "last_scores": dict(self.last_scores),
            "history": list(self.history),
        }


class CompositionStrategyPlanner(object):
    def __init__(
        self,
        ai,
        research_queue,
        target_groups,
        difficulty_id="standard",
        house_points=None,
    ):
        self.ai = ai
        self.research_queue = research_queue
        self.target_groups = target_groups or {}
        self.profile = ai_difficulty_profile(difficulty_id)
        self.plan = ai_composition_plan(difficulty_id)
        base = _ent_xz(ai.barracks_ent)
        self.house_points = list(house_points or [
            (base[0] + 8.0, base[1] - 8.0),
            (base[0] + 12.0, base[1] - 10.0),
            (base[0] + 16.0, base[1] - 12.0),
        ])
        self.step_index = 0
        self.attack_launched = False
        self.last_target_role = None
        self.history = []

    def _unit_counts(self):
        return {
            unit_id: self.ai.unit_count(unit_id)
            for unit_id in self.plan["unit_targets"]
        }

    def _army_count(self):
        return self.ai.unit_count("militia") + self.ai.unit_count("archer")

    def _next_house_point(self):
        idx = min(self.ai.building_count("house"), len(self.house_points) - 1)
        return self.house_points[idx]

    def _record(self, decision, branch):
        decision["strategy_branch"] = branch
        decision["difficulty_id"] = self.profile["id"]
        decision["composition_plan_id"] = self.plan["plan_id"]
        decision["technology_id"] = self.plan["technology_id"]
        decision["unit_targets"] = dict(self.plan["unit_targets"])
        decision["unit_counts"] = self._unit_counts()
        self.history.append(decision)
        return decision

    def _missing_research_resources(self):
        technology = TECHNOLOGIES[self.plan["technology_id"]]
        missing = {}
        for resource_id, amount in technology.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def _missing_training_resources(self, unit_id):
        unit = UNITS[unit_id]
        missing = {}
        for resource_id, amount in unit.get("cost", {}).items():
            deficit = int(amount) - self.ai.player_state.resources.get(resource_id, 0)
            if deficit > 0:
                missing[resource_id] = deficit
        return missing

    def _next_unit_gap(self):
        for unit_id, target_count in self.plan["unit_targets"].items():
            if self.ai.unit_count(unit_id) < int(target_count):
                return unit_id, int(target_count)
        return None, 0

    def _attack_target(self):
        for role in self.plan["target_roles"]:
            for ent in self.target_groups.get(role, []):
                if _is_live_entity(ent):
                    return role, ent
        return None, None

    def _target_army_size(self):
        return sum(int(value) for value in self.plan["unit_targets"].values())

    def step(self):
        self.step_index += 1
        technology_id = self.plan["technology_id"]

        if technology_id not in self.ai.player_state.researched_technologies:
            missing = self._missing_research_resources()
            if missing:
                decision = self.ai.gather_resources(self.profile["income_per_step"], "composition_research_income")
                decision["missing_before_income"] = missing
                return self._record(decision, "composition_research")

            self.research_queue.enqueue(technology_id)
            completed = self.research_queue.finish_next()
            decision = self.ai._record_decision(
                "research",
                "composition_tech",
                technology_id=completed,
                research_building_id=self.research_queue.building_id,
            )
            return self._record(decision, "composition_research")

        unit_id, target_count = self._next_unit_gap()
        if unit_id is not None:
            missing = self._missing_training_resources(unit_id)
            if missing:
                decision = self.ai.gather_resources(self.profile["income_per_step"], "composition_training_income")
                decision["missing_before_income"] = missing
                decision["preferred_unit_id"] = unit_id
                return self._record(decision, "composition_training")

            if self.ai.available_population() <= 1:
                house, decision = self.ai.build_complete_building(
                    "house",
                    self._next_house_point(),
                    name="ai_composition_house_{0}".format(self.ai.building_count("house") + 1),
                    reason="composition_population",
                )
                if house is None:
                    decision = self.ai.gather_resources({"wood": 50}, "composition_house_income")
                decision["preferred_unit_id"] = unit_id
                return self._record(decision, "composition_training")

            ent, decision = self.ai.train_for_build_order(unit_id, target_count)
            if ent is not None:
                ent.name = "ai_composition_{0}_{1}".format(unit_id, self.ai.unit_count(unit_id))
            decision["preferred_unit_id"] = unit_id
            return self._record(decision, "composition_training")

        target_role, target = self._attack_target()
        if target is None:
            decision = self.ai._record_decision(
                "hold_position",
                "composition_no_target",
                attack_roster=list(self.plan["attack_roster"]),
            )
            return self._record(decision, "composition_hold")

        launched, decision = self.ai.launch_roster_attack(
            target,
            unit_ids=tuple(self.plan["attack_roster"]),
            min_units=self._target_army_size(),
            reason="composition_attack",
        )
        self.attack_launched = bool(launched)
        self.last_target_role = target_role
        decision["target_role"] = target_role
        decision["attack_roster"] = list(self.plan["attack_roster"])
        return self._record(decision, "composition_attack")

    def snapshot(self):
        return {
            "difficulty_id": self.profile["id"],
            "profile": dict(self.profile),
            "composition_plan": dict(self.plan),
            "step_index": self.step_index,
            "attack_launched": self.attack_launched,
            "last_target_role": self.last_target_role,
            "unit_counts": self._unit_counts(),
            "army_count": self._army_count(),
            "researched_technologies": sorted(self.ai.player_state.researched_technologies),
            "history": list(self.history),
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
