import argparse
import json
import math
import os
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import sovereign.globals as sovereign_globals
from sovereign.data.units import UNITS
from sovereign.entities.runtime import create_entity, place_entity
from sovereign.scenario import build_runtime_scene, load_scenario, scenario_summary
from sovereign.systems.skirmish import MultiFrontArmyPlanner, ScriptedSkirmishAI


PROBE_PATH = "/tmp/pf_sovereign_ai_multi_front_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_multi_front_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "split_assignments": False,
        "defense_front": False,
        "harass_front": False,
        "attack_front": False,
        "disjoint_fronts": False,
        "defense_motion": False,
        "harass_motion": False,
        "attack_motion": False,
    },
    "runtime": {},
    "ai": {},
    "movement": {},
    "entities": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign AI multi-front control probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-multi-front")
    parser.add_argument("--expect-backend", default="METAL")
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    print("SOVEREIGN_AI_MULTI_FRONT_PHASE {0}".format(name))
    sys.stdout.flush()


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _dist(a, b):
    dx = a[0] - b[0]
    dz = a[1] - b[1]
    return math.sqrt(dx * dx + dz * dz)


def _snapshot_entity(ent):
    payload = {
        "name": getattr(ent, "name", None),
        "position": _ent_xz(ent),
        "faction_id": getattr(ent, "faction_id", None),
    }
    try:
        payload["hp"] = int(ent.hp)
    except (AttributeError, RuntimeError):
        payload["hp"] = None
    try:
        payload["anim"] = ent.get_anim()
    except (AttributeError, RuntimeError):
        payload["anim"] = None
    return payload


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_multi_front.json")


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "runtime": STATE["runtime"],
        "ai": STATE["ai"],
        "movement": STATE["movement"],
        "entities": {
            key: _snapshot_entity(ent)
            for key, ent in STATE["entities"].items()
        },
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_AI_MULTI_FRONT_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_MULTI_FRONT_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_MULTI_FRONT_PROBE_PASS runtime={runtime} split={split} "
        "defense={defense} harass={harass} attack={attack} disjoint={disjoint} "
        "defense_motion={defense_motion} harass_motion={harass_motion} attack_motion={attack_motion}"
    ).format(
        runtime=int(STATE["checks"]["runtime_scene"]),
        split=int(STATE["checks"]["split_assignments"]),
        defense=int(STATE["checks"]["defense_front"]),
        harass=int(STATE["checks"]["harass_front"]),
        attack=int(STATE["checks"]["attack_front"]),
        disjoint=int(STATE["checks"]["disjoint_fronts"]),
        defense_motion=int(STATE["checks"]["defense_motion"]),
        harass_motion=int(STATE["checks"]["harass_motion"]),
        attack_motion=int(STATE["checks"]["attack_motion"]),
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _spawned_entity(result, kind, entity_id, name=None):
    for entry, ent in zip(result["plan"]["entities"], result["entities"]):
        if entry["kind"] != kind or entry["id"] != entity_id:
            continue
        if name is not None and entry["name"] != name:
            continue
        return ent
    return None


def _entity_named(scene_objs, name):
    for ent in scene_objs:
        if getattr(ent, "name", None) == name:
            return ent
    return None


def _setup_render_state():
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    center = (124.0, 86.0)
    camera = pf.Camera(
        name="sovereign_ai_multi_front_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 132.0, center[1] + 10.0),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_multi_front_region",
            position=center,
            dimensions=(128.0, 96.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _create_unit(scene_objs, player_state, unit_id, name, point, faction_id):
    definition = UNITS[unit_id]
    ent = create_entity({
        "kind": "unit",
        "id": unit_id,
        "name": name,
        "definition": definition,
    })
    place_entity(
        ent,
        point,
        faction_id=faction_id,
        radius=definition.get("selection_radius", 2.5),
        scale=definition.get("scale"),
    )
    scene_objs.append(ent)
    if player_state is not None:
        player_state.add_unit(unit_id, ent)
    return ent


def _front_units(scene_objs, assignment):
    return [
        _entity_named(scene_objs, name)
        for name in assignment.get("unit_names", [])
        if _entity_named(scene_objs, name) is not None
    ]


def _run_multi_front():
    scenario = load_scenario(os.path.join(pf.get_basedir(), "assets/sovereign/scenarios/two_player_skirmish.json"))
    scene_objs = []
    sovereign_globals.scene_objs = scene_objs
    runtime = build_runtime_scene(scenario, scene_objs=scene_objs)
    _setup_render_state()

    player_record = runtime["players"][1]
    enemy_record = runtime["players"][2]
    player_result = player_record["spawn_result"]
    enemy_result = enemy_record["spawn_result"]
    enemy_state = enemy_record["state"]

    player_town_center = _spawned_entity(player_result, "building", "town_center")
    player_villager = _spawned_entity(player_result, "unit", "villager", "villager_1")
    player_barracks = _spawned_entity(player_result, "building", "barracks")
    enemy_town_center = _spawned_entity(enemy_result, "building", "town_center")
    enemy_barracks = _spawned_entity(enemy_result, "building", "barracks")
    if None in (player_town_center, player_villager, player_barracks, enemy_town_center, enemy_barracks):
        _fail("required multi-front fixture entity was not spawned")

    enemy_town_center.name = "ai_multi_front_enemy_town_center"
    enemy_barracks.name = "ai_multi_front_enemy_barracks"
    place_entity(
        player_barracks,
        (132.0, 116.0),
        faction_id=1,
        radius=4.0,
        scale=None,
    )

    pressure = _create_unit(
        scene_objs,
        None,
        "militia",
        "player_multi_front_pressure",
        (122.0, 88.0),
        1,
    )
    forward_villager = _create_unit(
        scene_objs,
        None,
        "villager",
        "player_multi_front_forward_worker",
        (94.0, 78.0),
        1,
    )
    defender = _create_unit(
        scene_objs,
        enemy_state,
        "militia",
        "ai_multi_front_defender",
        (146.0, 92.0),
        2,
    )
    archers = []
    for idx in range(4):
        archers.append(_create_unit(
            scene_objs,
            enemy_state,
            "archer",
            "ai_multi_front_archer_{0}".format(idx + 1),
            (144.0 + idx * 2.5, 98.0 + idx * 1.5),
            2,
        ))

    try:
        pressure.face_towards(defender.pos)
        forward_villager.face_towards(enemy_barracks.pos)
        defender.face_towards(pressure.pos)
        for ent in archers:
            ent.face_towards(forward_villager.pos)
    except (AttributeError, RuntimeError):
        pass

    enemy_state.population_cap = max(enemy_state.population_cap, enemy_state.population_used + 8)
    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=runtime["map_seed"])
    target_groups = {
        "town_center": [player_town_center],
        "villagers": [forward_villager, player_villager],
        "military": [pressure],
        "buildings": [player_barracks],
    }
    planner = MultiFrontArmyPlanner(
        ai,
        target_groups,
        defended_assets=[enemy_barracks, enemy_town_center],
        difficulty_id="hard",
        min_defenders=1,
        min_harassers=2,
        min_attackers=2,
        threat_radius=56.0,
    )

    decisions = []
    for _idx in range(6):
        decisions.append(dict(planner.step()))
        if planner.defense_launched and planner.harass_launched and planner.attack_launched:
            break
    if not (planner.defense_launched and planner.harass_launched and planner.attack_launched):
        _fail("multi-front planner did not launch all fronts: {0}".format(decisions))

    snapshot = planner.snapshot()
    STATE["runtime"] = scenario_summary(runtime)
    STATE["runtime"]["scene_obj_count_after_multi_front"] = len(scene_objs)
    STATE["ai"] = {
        "decisions": decisions,
        "planner": snapshot,
        "snapshot": ai.snapshot(),
    }
    STATE["entities"] = {
        "player_town_center": player_town_center,
        "player_villager": player_villager,
        "player_barracks": player_barracks,
        "forward_villager": forward_villager,
        "pressure": pressure,
        "enemy_town_center": enemy_town_center,
        "enemy_barracks": enemy_barracks,
        "defender": defender,
    }
    for idx, ent in enumerate(archers):
        STATE["entities"]["archer_{0}".format(idx + 1)] = ent

    assignments = snapshot["front_assignments"]
    for front_id, assignment in assignments.items():
        units = _front_units(scene_objs, assignment)
        STATE["movement"][front_id] = {
            "target": assignment.get("target_position"),
            "unit_names": assignment.get("unit_names", []),
            "before": [_ent_xz(ent) for ent in units],
        }

    assigned_names = []
    for assignment in assignments.values():
        assigned_names.extend(assignment.get("unit_names", []))
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 20 and len(runtime["players"]) == 2
    STATE["checks"]["split_assignments"] = sorted(assignments.keys()) == ["attack", "defense", "harass"]
    STATE["checks"]["defense_front"] = (
        assignments["defense"]["target_role"] == "military"
        and len(assignments["defense"]["unit_names"]) == 1
    )
    STATE["checks"]["harass_front"] = (
        assignments["harass"]["target_role"] == "villagers"
        and len(assignments["harass"]["unit_names"]) == 2
    )
    STATE["checks"]["attack_front"] = (
        assignments["attack"]["target_role"] == "buildings"
        and len(assignments["attack"]["unit_names"]) == 2
    )
    STATE["checks"]["disjoint_fronts"] = len(assigned_names) == len(set(assigned_names)) == 5


def _sample_motion():
    for front_id, movement in STATE["movement"].items():
        target = movement["target"]
        units = [
            _entity_named(sovereign_globals.scene_objs, name)
            for name in movement["unit_names"]
        ]
        units = [ent for ent in units if ent is not None]
        after = [_ent_xz(ent) for ent in units]
        improvements = []
        for idx, pos in enumerate(after):
            start = movement["before"][idx] if idx < len(movement["before"]) else pos
            improvements.append(round(_dist(start, target) - _dist(pos, target), 3))
        movement["after"] = after
        movement["distance_improvements"] = improvements
    STATE["checks"]["defense_motion"] = any(value > 0.25 for value in STATE["movement"]["defense"]["distance_improvements"])
    STATE["checks"]["harass_motion"] = any(value > 0.25 for value in STATE["movement"]["harass"]["distance_improvements"])
    STATE["checks"]["attack_motion"] = any(value > 0.1 for value in STATE["movement"]["attack"]["distance_improvements"])


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _run_multi_front()
        _set_phase("settle")
        return

    if STATE["phase"] == "settle" and STATE["ticks"] >= 120:
        _sample_motion()
        if all(STATE["checks"].values()):
            _succeed()
            return
        _fail("multi-front checks did not all pass: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["phase_started_at"] = time.monotonic()
    for path in (PROBE_PATH, ERROR_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
