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


def _composition_units(counts, side):
    units = []
    for unit_id in sorted(counts):
        if unit_id not in UNITS:
            raise CombatRuleError("unknown_unit", "unknown unit '{0}'".format(unit_id))
        count = int(counts.get(unit_id, 0))
        if count < 0:
            raise CombatRuleError("bad_count", "{0} count for {1} is negative".format(unit_id, side))
        for idx in range(count):
            units.append({
                "uid": "{0}_{1}_{2}".format(side, unit_id, idx + 1),
                "unit_id": unit_id,
                "hp": int(UNITS[unit_id].get("hp", 1)),
                "max_hp": int(UNITS[unit_id].get("hp", 1)),
            })
    return units


def _live_units(units):
    return [unit for unit in units if int(unit["hp"]) > 0]


def _first_live(units):
    for unit in units:
        if int(unit["hp"]) > 0:
            return unit
    return None


def _composition_counts(units):
    counts = {}
    for unit in _live_units(units):
        unit_id = unit["unit_id"]
        counts[unit_id] = counts.get(unit_id, 0) + 1
    return counts


def _total_hp(units):
    return sum(max(0, int(unit["hp"])) for unit in units)


def _strike_round(strikers, targets, side, log, totals):
    for striker in _live_units(strikers):
        target = _first_live(targets)
        if target is None:
            return
        breakdown = damage_breakdown(striker["unit_id"], target["unit_id"])
        before = int(target["hp"])
        after = before - int(breakdown["total_damage"])
        target["hp"] = after
        totals[side] += int(breakdown["total_damage"])
        log.append({
            "side": side,
            "attacker_uid": striker["uid"],
            "attacker_id": striker["unit_id"],
            "target_uid": target["uid"],
            "target_id": target["unit_id"],
            "damage": int(breakdown["total_damage"]),
            "base_damage": int(breakdown["base_damage"]),
            "bonus_damage": int(breakdown["bonus_damage"]),
            "hp_before": before,
            "hp_after": max(0, after),
        })


def composition_duel(attacker_counts, defender_counts, max_rounds=64):
    attackers = _composition_units(attacker_counts, "attacker")
    defenders = _composition_units(defender_counts, "defender")
    if not attackers:
        raise CombatRuleError("empty_attackers", "composition duel needs at least one attacker")
    if not defenders:
        raise CombatRuleError("empty_defenders", "composition duel needs at least one defender")

    rounds = []
    totals = {"attackers": 0, "defenders": 0}
    for round_idx in range(1, int(max_rounds) + 1):
        if not _live_units(attackers) or not _live_units(defenders):
            break
        log = []
        _strike_round(attackers, defenders, "attackers", log, totals)
        if _live_units(defenders):
            _strike_round(defenders, attackers, "defenders", log, totals)
        rounds.append({
            "round": round_idx,
            "events": log,
            "attacker_remaining": _composition_counts(attackers),
            "defender_remaining": _composition_counts(defenders),
            "attacker_hp": _total_hp(attackers),
            "defender_hp": _total_hp(defenders),
        })

    attacker_hp = _total_hp(attackers)
    defender_hp = _total_hp(defenders)
    if attacker_hp > 0 and defender_hp <= 0:
        winner = "attackers"
    elif defender_hp > 0 and attacker_hp <= 0:
        winner = "defenders"
    elif attacker_hp > defender_hp:
        winner = "attackers"
    elif defender_hp > attacker_hp:
        winner = "defenders"
    else:
        winner = "draw"

    return {
        "attacker_counts": dict(attacker_counts),
        "defender_counts": dict(defender_counts),
        "winner": winner,
        "rounds_run": len(rounds),
        "max_rounds": int(max_rounds),
        "initiative": "attackers_first",
        "attacker_remaining": _composition_counts(attackers),
        "defender_remaining": _composition_counts(defenders),
        "attacker_hp": attacker_hp,
        "defender_hp": defender_hp,
        "damage_totals": totals,
        "rounds": rounds,
    }
