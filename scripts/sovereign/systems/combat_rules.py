from __future__ import print_function

from sovereign.data.armor_classes import DAMAGE_BONUSES
from sovereign.data.units import UNITS


class CombatRuleError(ValueError):
    def __init__(self, code, message):
        ValueError.__init__(self, message)
        self.code = code


def primary_attack(unit_id):
    attacks = UNITS[unit_id].get("attacks", [])
    if not attacks:
        raise CombatRuleError("no_attack", "{0} has no attacks".format(unit_id))
    return attacks[0]


def damage_breakdown(attacker_id, target_id):
    attack = primary_attack(attacker_id)
    damage_class = attack.get("damage_class")
    target_classes = UNITS[target_id].get("armor_classes", [])
    bonuses = DAMAGE_BONUSES.get(damage_class, {})
    bonus_damage = 0
    matched_classes = []
    for armor_class in target_classes:
        value = int(bonuses.get(armor_class, 0))
        if value:
            bonus_damage += value
            matched_classes.append(armor_class)

    base_damage = int(attack.get("damage", 0))
    total_damage = max(1, base_damage + bonus_damage)
    return {
        "attacker_id": attacker_id,
        "target_id": target_id,
        "damage_class": damage_class,
        "target_armor_classes": list(target_classes),
        "matched_bonus_classes": matched_classes,
        "base_damage": base_damage,
        "bonus_damage": bonus_damage,
        "total_damage": total_damage,
    }


def apply_damage(attacker_id, target_id, target_ent):
    breakdown = damage_breakdown(attacker_id, target_id)
    before = int(target_ent.hp)
    after = max(1, before - breakdown["total_damage"])
    target_ent.hp = after
    breakdown["hp_before"] = before
    breakdown["hp_after"] = after
    return breakdown
