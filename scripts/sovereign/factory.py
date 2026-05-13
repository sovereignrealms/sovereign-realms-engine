from __future__ import print_function

from sovereign.data.ages import AGES
from sovereign.data.armor_classes import ARMOR_CLASSES, DAMAGE_BONUSES, DAMAGE_CLASSES
from sovereign.data.buildings import BUILDINGS
from sovereign.data.civilizations import CIVILIZATIONS
from sovereign.data.resources import RESOURCES
from sovereign.data.readability import validate_unit_readability
from sovereign.data.technologies import TECHNOLOGIES
from sovereign.data.units import UNITS


STARTING_UNIT_OFFSETS = [(-8.0, -4.0), (-5.0, -8.0), (-2.0, -4.0)]
STARTING_BUILDING_OFFSETS = [(0.0, 0.0), (10.0, -4.0), (14.0, 6.0)]
RESOURCE_NODE_OFFSETS = {
    "food": (-12.0, 10.0),
    "wood": (-18.0, -2.0),
    "gold": (18.0, 0.0),
    "stone": (14.0, 12.0),
}


def _error(errors, message):
    errors.append(message)


def _check_resource_costs(errors, owner, costs):
    for resource_id in costs:
        if resource_id not in RESOURCES:
            _error(errors, "{0} references unknown resource '{1}'".format(owner, resource_id))


def validate_registries():
    errors = []

    for unit_id, unit in UNITS.items():
        if "asset" not in unit:
            _error(errors, "unit '{0}' is missing an asset".format(unit_id))
        _check_resource_costs(errors, "unit '{0}'".format(unit_id), unit.get("cost", {}))
        for armor_class in unit.get("armor_classes", []):
            if armor_class not in ARMOR_CLASSES:
                _error(errors, "unit '{0}' references unknown armor class '{1}'".format(unit_id, armor_class))
        for attack in unit.get("attacks", []):
            damage_class = attack.get("damage_class")
            if damage_class not in DAMAGE_CLASSES:
                _error(errors, "unit '{0}' references unknown damage class '{1}'".format(unit_id, damage_class))
        projectile = unit.get("projectile")
        if projectile:
            descriptor = projectile.get("descriptor")
            if not descriptor or len(descriptor) < 4:
                _error(errors, "unit '{0}' has invalid projectile descriptor".format(unit_id))
    for error in validate_unit_readability(UNITS)["errors"]:
        _error(errors, error)

    for building_id, building in BUILDINGS.items():
        if "asset" not in building:
            _error(errors, "building '{0}' is missing an asset".format(building_id))
        _check_resource_costs(errors, "building '{0}'".format(building_id), building.get("cost", {}))
        for unit_id in building.get("trains", []):
            if unit_id not in UNITS:
                _error(errors, "building '{0}' trains unknown unit '{1}'".format(building_id, unit_id))
        for tech_id in building.get("researches", []):
            if tech_id not in TECHNOLOGIES:
                _error(errors, "building '{0}' researches unknown tech '{1}'".format(building_id, tech_id))
        for resource_id in building.get("drop_off", []):
            if resource_id not in RESOURCES:
                _error(errors, "building '{0}' drops off unknown resource '{1}'".format(building_id, resource_id))

    for tech_id, tech in TECHNOLOGIES.items():
        _check_resource_costs(errors, "technology '{0}'".format(tech_id), tech.get("cost", {}))
        age_id = tech.get("requires_age")
        if age_id and age_id not in AGES:
            _error(errors, "technology '{0}' requires unknown age '{1}'".format(tech_id, age_id))
        for effect in tech.get("effects", []):
            if effect.get("type") == "set_age" and effect.get("age") not in AGES:
                _error(errors, "technology '{0}' sets unknown age '{1}'".format(tech_id, effect.get("age")))
            elif effect.get("type") == "strategy_tag" and not effect.get("tag"):
                _error(errors, "technology '{0}' has a strategy tag effect without a tag".format(tech_id))
            elif effect.get("type") not in ("set_age", "strategy_tag"):
                _error(errors, "technology '{0}' has unsupported effect '{1}'".format(tech_id, effect.get("type")))

    for damage_class, bonuses in DAMAGE_BONUSES.items():
        if damage_class not in DAMAGE_CLASSES:
            _error(errors, "damage bonus table references unknown damage class '{0}'".format(damage_class))
        for armor_class in bonuses:
            if armor_class not in ARMOR_CLASSES:
                _error(errors, "damage bonus table references unknown armor class '{0}'".format(armor_class))

    for civ_id, civ in CIVILIZATIONS.items():
        if civ.get("starting_age") not in AGES:
            _error(errors, "civilization '{0}' has unknown starting age".format(civ_id))
        for unit_id in civ.get("starting_units", []) + civ.get("available_units", []):
            if unit_id not in UNITS:
                _error(errors, "civilization '{0}' references unknown unit '{1}'".format(civ_id, unit_id))
        for building_id in civ.get("starting_buildings", []) + civ.get("available_buildings", []):
            if building_id not in BUILDINGS:
                _error(errors, "civilization '{0}' references unknown building '{1}'".format(civ_id, building_id))
        for tech_id in civ.get("available_technologies", []):
            if tech_id not in TECHNOLOGIES:
                _error(errors, "civilization '{0}' references unknown technology '{1}'".format(civ_id, tech_id))

    return errors


def require_valid_registries():
    errors = validate_registries()
    if errors:
        raise ValueError("invalid Sovereign registries: " + "; ".join(errors))


def build_minimal_spawn_plan(civilization_id="sovereign_default"):
    require_valid_registries()
    if civilization_id not in CIVILIZATIONS:
        raise ValueError("unknown civilization '{0}'".format(civilization_id))

    civ = CIVILIZATIONS[civilization_id]
    entities = []

    for idx, unit_id in enumerate(civ["starting_units"]):
        offset = STARTING_UNIT_OFFSETS[idx % len(STARTING_UNIT_OFFSETS)]
        entities.append({
            "kind": "unit",
            "id": unit_id,
            "name": "{0}_{1}".format(unit_id, idx + 1),
            "offset": offset,
            "definition": UNITS[unit_id],
        })

    for idx, building_id in enumerate(civ["starting_buildings"]):
        offset = STARTING_BUILDING_OFFSETS[idx % len(STARTING_BUILDING_OFFSETS)]
        entities.append({
            "kind": "building",
            "id": building_id,
            "name": building_id,
            "offset": offset,
            "definition": BUILDINGS[building_id],
        })

    for idx, building_id in enumerate(("house", "barracks")):
        offset = STARTING_BUILDING_OFFSETS[(idx + 1) % len(STARTING_BUILDING_OFFSETS)]
        entities.append({
            "kind": "building",
            "id": building_id,
            "name": building_id,
            "offset": offset,
            "definition": BUILDINGS[building_id],
        })

    for resource_id, offset in RESOURCE_NODE_OFFSETS.items():
        resource = RESOURCES[resource_id]
        entities.append({
            "kind": "resource",
            "id": resource_id,
            "name": "{0}_node".format(resource_id),
            "offset": offset,
            "definition": resource,
        })

    return {
        "civilization_id": civilization_id,
        "civilization": civ,
        "entities": entities,
    }


def spawn_minimal_test_scene(
    center=(64.0, 64.0),
    faction_id=1,
    scene_objs=None,
    civilization_id="sovereign_default",
):
    from sovereign.entities.runtime import place_entity, create_entity

    plan = build_minimal_spawn_plan(civilization_id=civilization_id)
    spawned = []
    for entry in plan["entities"]:
        ent = create_entity(entry)
        offset = entry["offset"]
        point = (center[0] + offset[0], center[1] + offset[1])
        place_entity(
            ent,
            point,
            faction_id=faction_id if entry["kind"] != "resource" else 0,
            radius=entry["definition"].get("selection_radius", 2.5),
            scale=entry["definition"].get("scale"),
            selectable=entry["kind"] != "resource",
        )
        if scene_objs is not None:
            scene_objs.append(ent)
        spawned.append(ent)

    return {
        "plan": plan,
        "entities": spawned,
    }
