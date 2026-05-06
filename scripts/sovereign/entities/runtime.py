import weakref

import pf
from sovereign.data.buildings import BUILDINGS
from sovereign.data.units import UNITS
from sovereign.session_state import tag_entity


RESOURCE_IDS = ("food", "wood", "gold", "stone")


class SovereignWorker(pf.BuilderEntity, pf.HarvesterEntity, pf.MovableEntity, pf.GarrisonEntity):
    def __init__(self, path, pfobj, name, unit_id="villager", build_speed=512, **kwargs):
        del kwargs
        definition = UNITS.get(unit_id)
        if definition:
            build_speed = definition.get("build_speed", build_speed)
        pf.BuilderEntity.__init__(self, path, pfobj, name, build_speed=build_speed)
        self.sovereign_unit_id = unit_id
        if definition:
            _configure_worker(self, definition)

    def session_scene_meta(self):
        return {
            "anim": False,
            "static": False,
            "collision": True,
            "class": "SovereignWorker",
            "construct_args": (
                self.pfobj_path.rsplit("/", 1)[0],
                self.pfobj_path.rsplit("/", 1)[1],
                self.name,
                self.sovereign_unit_id,
            ),
        }


class SovereignResourceNode(pf.ResourceEntity):
    def __init__(self, path, pfobj, name, resource_name, resource_amount, **kwargs):
        del kwargs
        pf.ResourceEntity.__init__(
            self,
            path,
            pfobj,
            name,
            resource_name=resource_name,
            resource_amount=resource_amount,
        )
        self.sovereign_resource_id = resource_name
        self.sovereign_resource_amount = int(resource_amount)

    def session_scene_meta(self):
        return {
            "anim": False,
            "static": True,
            "collision": True,
            "class": "SovereignResourceNode",
            "construct_args": (
                self.pfobj_path.rsplit("/", 1)[0],
                self.pfobj_path.rsplit("/", 1)[1],
                self.name,
                self.sovereign_resource_id,
                self.sovereign_resource_amount,
            ),
        }


class SovereignStorageBuilding(pf.StorageSiteEntity):
    def __init__(self, path, pfobj, name, building_id="town_center", **kwargs):
        del path
        del pfobj
        del name
        del kwargs
        self.sovereign_building_id = building_id
        definition = BUILDINGS.get(building_id)
        if definition:
            _configure_storage(self, definition)

    def session_scene_meta(self):
        return {
            "anim": False,
            "static": True,
            "collision": True,
            "class": "SovereignStorageBuilding",
            "construct_args": (
                self.pfobj_path.rsplit("/", 1)[0],
                self.pfobj_path.rsplit("/", 1)[1],
                self.name,
                self.sovereign_building_id,
            ),
        }


class SovereignCombatUnit(pf.AnimEntity, pf.CombatableEntity, pf.MovableEntity):
    def __init__(self, path, pfobj, name, definition, **kwargs):
        del kwargs
        if isinstance(definition, str):
            self.sovereign_unit_id = definition
            definition = UNITS[definition]
        else:
            self.sovereign_unit_id = None
        attack = definition.get("attacks", [{}])[0]
        pf.AnimEntity.__init__(self, path, pfobj, name, idle_clip="Idle")
        self.moving = False
        self.attacking = False
        combat_args = {
            "max_hp": int(definition.get("hp", 1)),
            "base_dmg": int(attack.get("damage", 1)),
            "base_armour": 0.0,
            "attack_range": float(attack.get("range", 0.0)),
        }
        projectile = definition.get("projectile")
        if projectile:
            combat_args["projectile_descriptor"] = projectile["descriptor"]
        pf.CombatableEntity.__init__(
            self,
            path,
            pfobj,
            name,
            **combat_args
        )
        if projectile and projectile.get("fire_descriptor"):
            self.projectile_fire_descriptor = projectile["fire_descriptor"]
        self.register(pf.EVENT_MOTION_START, SovereignCombatUnit._on_motion_start, weakref.ref(self))
        self.register(pf.EVENT_MOTION_END, SovereignCombatUnit._on_motion_end, weakref.ref(self))
        self.register(pf.EVENT_ATTACK_START, SovereignCombatUnit._on_attack_start, weakref.ref(self))
        self.register(pf.EVENT_ATTACK_END, SovereignCombatUnit._on_attack_end, weakref.ref(self))

    def _play_clip(self, clip):
        if self.get_anim() != clip:
            self.play_anim(clip)

    def _on_motion_start(self, event):
        del event
        self.moving = True
        if not self.attacking:
            self._play_clip("Walk")

    def _on_motion_end(self, event):
        del event
        self.moving = False
        if not self.attacking:
            self._play_clip("Idle")

    def _on_attack_start(self, event):
        del event
        self.attacking = True
        self.play_anim("Attack")

    def _on_attack_end(self, event):
        del event
        self.attacking = False
        self.play_anim("Walk" if self.moving else "Idle")

    def session_scene_meta(self):
        unit_id = self.sovereign_unit_id or "militia"
        return {
            "anim": True,
            "idle": "Idle",
            "static": False,
            "collision": True,
            "class": "SovereignCombatUnit",
            "construct_args": (
                self.pfobj_path.rsplit("/", 1)[0],
                self.pfobj_path.rsplit("/", 1)[1],
                self.name,
                unit_id,
            ),
        }


class SovereignBuildable(pf.BuildableEntity):
    def __init__(self, path, pfobj, name, required_resources=None, pathable=True, **kwargs):
        del kwargs
        self.sovereign_building_id = None
        if isinstance(required_resources, str):
            self.sovereign_building_id = required_resources
            required_resources = BUILDINGS[required_resources].get("cost", {})
        if required_resources is None:
            required_resources = {}
        pf.BuildableEntity.__init__(
            self,
            path,
            pfobj,
            name,
            required_resources=required_resources,
            pathable=pathable,
        )

    def session_scene_meta(self):
        building_id = self.sovereign_building_id or "house"
        return {
            "anim": False,
            "static": True,
            "collision": True,
            "class": "SovereignBuildable",
            "construct_args": (
                self.pfobj_path.rsplit("/", 1)[0],
                self.pfobj_path.rsplit("/", 1)[1],
                self.name,
                building_id,
            ),
        }


def _asset(definition):
    asset = definition.get("asset")
    if not asset:
        raise ValueError("definition is missing asset")
    return asset["path"], asset["pfobj"]


def _configure_worker(ent, definition):
    ent.speed = float(definition.get("speed", 20.0))
    ent.garrison_capacity = 1
    for resource_id, amount in definition.get("carry_capacity", {}).items():
        ent.set_max_carry(resource_id, int(amount))
        ent.set_do_not_transport(resource_id, False)
    for resource_id, speed in definition.get("gather_speed", {}).items():
        ent.set_gather_speed(resource_id, float(speed))


def _configure_storage(ent, definition):
    for resource_id in definition.get("drop_off", RESOURCE_IDS):
        ent.set_capacity(resource_id, 1000)
        ent.set_desired(resource_id, 1000)
        ent.set_curr_amount(resource_id, 0)


def create_entity(entry):
    definition = entry["definition"]
    path, pfobj = _asset(definition.get("node", definition))
    name = entry["name"]
    ent = None

    if entry["kind"] == "unit" and definition.get("archetype") == "worker":
        ent = SovereignWorker(path, pfobj, name, entry["id"], build_speed=definition.get("build_speed", 512))

    elif entry["kind"] == "unit" and definition.get("archetype") == "combat_unit":
        ent = SovereignCombatUnit(path, pfobj, name, entry["id"])
        ent.speed = float(definition.get("speed", 20.0))

    elif entry["kind"] == "building" and definition.get("archetype") == "storage_building":
        ent = SovereignStorageBuilding(path, pfobj, name, entry["id"])

    elif entry["kind"] == "building":
        ent = SovereignBuildable(path, pfobj, name, required_resources=entry["id"])

    elif entry["kind"] == "resource":
        node = definition["node"]
        ent = SovereignResourceNode(
            path,
            pfobj,
            name,
            resource_name=entry["id"],
            resource_amount=node.get("amount", 300),
        )

    if ent is None:
        raise ValueError("unsupported Sovereign spawn entry: {0}".format(entry))
    return tag_entity(ent, entry["kind"], entry["id"])


def restore_runtime_after_session_load(scene_objs=None, scene_regions=None, scene_cameras=None):
    from sovereign.session_state import restore_runtime_after_session_load as restore
    return restore(scene_objs, scene_regions, scene_cameras)


def place_entity(ent, point, faction_id=1, radius=2.5, scale=None, selectable=True):
    target = pf.map_nearest_pathable(point, radius=radius)
    if target is None:
        target = point
    height = pf.map_height_at_point(target[0], target[1])
    if height is None:
        height = 0.0
    ent.pos = (float(target[0]), float(height), float(target[1]))
    ent.faction_id = faction_id
    ent.selection_radius = float(radius)
    try:
        ent.selectable = selectable
    except AttributeError:
        pass
    if scale is not None:
        ent.scale = tuple(scale)
    return ent
