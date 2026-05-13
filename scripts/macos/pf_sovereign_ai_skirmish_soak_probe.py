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
from sovereign.systems.combat_rules import apply_damage
from sovereign.systems.production import ProductionQueue
from sovereign.systems.skirmish import (
    AttritionRecoveryPlanner,
    MultiFrontArmyPlanner,
    ScriptedSkirmishAI,
    scenario_victory_winner,
    victory_progress_state,
)
from sovereign.systems.technology import ResearchQueue


PROBE_PATH = "/tmp/pf_sovereign_ai_skirmish_soak_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_skirmish_soak_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "soak_ticks": 300,
    "checks": {
        "runtime_scene": False,
        "economy_growth": False,
        "player_wave_ready": False,
        "enemy_roster_ready": False,
        "multi_front_split": False,
        "multi_front_motion": False,
        "attrition_recovery": False,
        "pressure_tech": False,
        "relaunch_after_pressure": False,
        "combat_damage": False,
        "victory_progress": False,
        "sustained_ticks": False,
    },
    "runtime": {},
    "economy": {},
    "production": {},
    "multi_front": {},
    "movement": {},
    "attrition": {},
    "combat": {},
    "victory": {},
    "entities": {},
    "session": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run a longer Sovereign AI-vs-player skirmish soak.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-skirmish-soak")
    parser.add_argument("--expect-backend", default="METAL")
    parser.add_argument("--soak-ticks", type=int, default=300)
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    print("SOVEREIGN_AI_SKIRMISH_SOAK_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_skirmish_soak.json")


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


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "runtime": STATE["runtime"],
        "economy": STATE["economy"],
        "production": STATE["production"],
        "multi_front": STATE["multi_front"],
        "movement": STATE["movement"],
        "attrition": STATE["attrition"],
        "combat": STATE["combat"],
        "victory": STATE["victory"],
        "session": {
            "player_state": STATE["session"]["player_state"].snapshot() if STATE["session"].get("player_state") else None,
            "enemy_state": STATE["session"]["enemy_state"].snapshot() if STATE["session"].get("enemy_state") else None,
            "ai": STATE["session"]["ai"].snapshot() if STATE["session"].get("ai") else None,
        },
        "entities": {
            key: _snapshot_entity(ent)
            for key, ent in STATE["entities"].items()
        },
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_AI_SKIRMISH_SOAK_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_SKIRMISH_SOAK_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_SKIRMISH_SOAK_PROBE_PASS runtime={runtime} economy={economy} "
        "player={player} enemy={enemy} fronts={fronts} motion={motion} "
        "attrition={attrition} tech={tech} relaunch={relaunch} damage={damage} "
        "victory={victory} soak={soak}"
    ).format(
        runtime=int(STATE["checks"]["runtime_scene"]),
        economy=int(STATE["checks"]["economy_growth"]),
        player=int(STATE["checks"]["player_wave_ready"]),
        enemy=int(STATE["checks"]["enemy_roster_ready"]),
        fronts=int(STATE["checks"]["multi_front_split"]),
        motion=int(STATE["checks"]["multi_front_motion"]),
        attrition=int(STATE["checks"]["attrition_recovery"]),
        tech=int(STATE["checks"]["pressure_tech"]),
        relaunch=int(STATE["checks"]["relaunch_after_pressure"]),
        damage=int(STATE["checks"]["combat_damage"]),
        victory=int(STATE["checks"]["victory_progress"]),
        soak=int(STATE["checks"]["sustained_ticks"]),
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


def _kill_unit(ai, ent, reason):
    try:
        getattr(ent, "del")()
    except (AttributeError, RuntimeError):
        try:
            ent.hp = 1
        except (AttributeError, RuntimeError):
            pass
    return ai.record_unit_loss(ent, reason=reason)


def _setup_render_state():
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    center = (124.0, 90.0)
    camera = pf.Camera(
        name="sovereign_ai_skirmish_soak_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 142.0, center[1] + 8.0),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_skirmish_soak_region",
            position=center,
            dimensions=(144.0, 112.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _front_units(scene_objs, assignment):
    units = []
    for name in assignment.get("unit_names", []):
        ent = _entity_named(scene_objs, name)
        if ent is not None:
            units.append(ent)
    return units


def _improvements(front_id):
    movement = STATE["movement"][front_id]
    target = movement["target"]
    units = [
        _entity_named(sovereign_globals.scene_objs, name)
        for name in movement["unit_names"]
    ]
    units = [ent for ent in units if ent is not None]
    after = [_ent_xz(ent) for ent in units]
    improvements = []
    travel = []
    for idx, pos in enumerate(after):
        start = movement["before"][idx] if idx < len(movement["before"]) else pos
        improvements.append(round(_dist(start, target) - _dist(pos, target), 3))
        travel.append(round(_dist(start, pos), 3))
    movement["after"] = after
    movement["distance_improvements"] = improvements
    movement["travel_distances"] = travel
    return improvements


def _setup_scene():
    scenario = load_scenario(os.path.join(pf.get_basedir(), "assets/sovereign/scenarios/two_player_skirmish.json"))
    scene_objs = []
    sovereign_globals.scene_objs = scene_objs
    runtime = build_runtime_scene(scenario, scene_objs=scene_objs)
    _setup_render_state()

    player_record = runtime["players"][1]
    enemy_record = runtime["players"][2]
    player_result = player_record["spawn_result"]
    enemy_result = enemy_record["spawn_result"]
    player_state = player_record["state"]
    enemy_state = enemy_record["state"]

    player_town_center = _spawned_entity(player_result, "building", "town_center")
    player_villager = _spawned_entity(player_result, "unit", "villager", "villager_1")
    player_barracks = _spawned_entity(player_result, "building", "barracks")
    enemy_town_center = _spawned_entity(enemy_result, "building", "town_center")
    enemy_barracks = _spawned_entity(enemy_result, "building", "barracks")
    if None in (player_town_center, player_villager, player_barracks, enemy_town_center, enemy_barracks):
        _fail("required skirmish soak fixture entity was not spawned")

    enemy_town_center.name = "ai_soak_enemy_town_center"
    enemy_barracks.name = "ai_soak_enemy_barracks"
    place_entity(player_barracks, (132.0, 116.0), faction_id=1, radius=4.0, scale=None)
    player_barracks.rally_point = (112.0, 126.0)
    enemy_barracks.rally_point = (138.0, 92.0)

    pressure = _create_unit(scene_objs, None, "militia", "player_soak_pressure", (122.0, 88.0), 1)
    forward_villager = _create_unit(scene_objs, None, "villager", "player_soak_forward_worker", (94.0, 78.0), 1)
    player_guard = _create_unit(scene_objs, player_state, "militia", "player_soak_guard", (108.0, 92.0), 1)
    defender = _create_unit(scene_objs, enemy_state, "militia", "ai_soak_defender", (146.0, 92.0), 2)
    archers = []
    for idx in range(6):
        archers.append(_create_unit(
            scene_objs,
            enemy_state,
            "archer",
            "ai_soak_archer_{0}".format(idx + 1),
            (144.0 + idx * 2.3, 98.0 + idx * 1.2),
            2,
        ))

    player_state.resources["food"] = max(player_state.resources.get("food", 0), 420)
    player_state.resources["gold"] = max(player_state.resources.get("gold", 0), 160)
    player_state.population_cap = max(player_state.population_cap, player_state.population_used + 8)
    enemy_state.resources["food"] = 900
    enemy_state.resources["wood"] = 900
    enemy_state.resources["gold"] = 900
    enemy_state.resources["stone"] = 200
    enemy_state.population_cap = max(enemy_state.population_cap, enemy_state.population_used + 12)

    player_queue = ProductionQueue(player_state, "barracks", player_barracks, faction_id=1, scene_objs=scene_objs)
    player_queue.enqueue("militia")
    trained_one = player_queue.finish_next()
    player_queue.enqueue("militia")
    trained_two = player_queue.finish_next()
    trained_one.name = "player_soak_trained_1"
    trained_two.name = "player_soak_trained_2"
    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=runtime["map_seed"])
    research_queue = ResearchQueue(enemy_state, "barracks", enemy_barracks)

    try:
        pressure.face_towards(defender.pos)
        forward_villager.face_towards(enemy_barracks.pos)
        player_guard.face_towards(archers[0].pos)
        for ent in [defender] + archers:
            ent.face_towards(forward_villager.pos)
    except (AttributeError, RuntimeError):
        pass

    STATE["runtime"] = scenario_summary(runtime)
    STATE["runtime"]["scene_obj_count_after_setup"] = len(scene_objs)
    STATE["session"].update({
        "scene_objs": scene_objs,
        "scenario_state": runtime["scenario_state"],
        "player_state": player_state,
        "enemy_state": enemy_state,
        "player_queue": player_queue,
        "research_queue": research_queue,
        "ai": ai,
    })
    STATE["entities"] = {
        "player_town_center": player_town_center,
        "player_villager": player_villager,
        "player_barracks": player_barracks,
        "forward_villager": forward_villager,
        "pressure": pressure,
        "player_guard": player_guard,
        "player_trained_1": trained_one,
        "player_trained_2": trained_two,
        "enemy_town_center": enemy_town_center,
        "enemy_barracks": enemy_barracks,
        "defender": defender,
    }
    for idx, ent in enumerate(archers):
        STATE["entities"]["archer_{0}".format(idx + 1)] = ent

    STATE["economy"] = {
        "enemy_resources_start": dict(enemy_state.resources),
        "player_resources_after_queue": dict(player_state.resources),
    }
    ai.gather_resources({"food": 120, "wood": 120, "gold": 80, "stone": 0}, "soak_enemy_economy_tick")
    player_state.resources["food"] += 80
    player_state.resources["wood"] += 80
    STATE["economy"]["enemy_resources_after_income"] = dict(enemy_state.resources)
    STATE["economy"]["player_resources_after_income"] = dict(player_state.resources)
    STATE["production"] = {
        "player_queue": player_queue.snapshot(),
        "player_state": player_state.snapshot(),
        "enemy_state": enemy_state.snapshot(),
    }
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 26 and len(runtime["players"]) == 2
    STATE["checks"]["economy_growth"] = (
        enemy_state.resources["food"] > STATE["economy"]["enemy_resources_start"]["food"]
        and player_state.resources["wood"] > STATE["economy"]["player_resources_after_queue"]["wood"]
    )
    STATE["checks"]["player_wave_ready"] = trained_one is not None and trained_two is not None and player_state.population_used >= 5
    STATE["checks"]["enemy_roster_ready"] = ai.live_unit_count("archer") >= 6 and ai.live_unit_count("militia") >= 1


def _launch_multi_front():
    ai = STATE["session"]["ai"]
    enemy_barracks = STATE["entities"]["enemy_barracks"]
    enemy_town_center = STATE["entities"]["enemy_town_center"]
    target_groups = {
        "town_center": [STATE["entities"]["player_town_center"]],
        "villagers": [STATE["entities"]["forward_villager"], STATE["entities"]["player_villager"]],
        "military": [STATE["entities"]["pressure"]],
        "buildings": [STATE["entities"]["player_barracks"]],
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
    snapshot = planner.snapshot()
    assignments = snapshot["front_assignments"]
    STATE["multi_front"] = {
        "decisions": decisions,
        "planner": snapshot,
    }
    for front_id, assignment in assignments.items():
        units = _front_units(sovereign_globals.scene_objs, assignment)
        STATE["movement"][front_id] = {
            "target": assignment.get("target_position"),
            "unit_names": assignment.get("unit_names", []),
            "before": [_ent_xz(ent) for ent in units],
        }
    assigned_names = []
    for assignment in assignments.values():
        assigned_names.extend(assignment.get("unit_names", []))
    STATE["checks"]["multi_front_split"] = (
        sorted(assignments.keys()) == ["attack", "defense", "harass"]
        and len(assigned_names) == len(set(assigned_names)) == 5
        and assignments["defense"]["target_role"] == "military"
        and assignments["harass"]["target_role"] == "villagers"
        and assignments["attack"]["target_role"] == "buildings"
    )


def _sample_multi_front_motion():
    defense = _improvements("defense")
    harass = _improvements("harass")
    attack = _improvements("attack")
    checks = {
        "defense": any(value > 0.25 for value in defense),
        "harass": (
            any(value > 0.10 for value in harass)
            or any(value > 0.25 for value in STATE["movement"]["harass"].get("travel_distances", []))
        ),
        "attack": (
            any(value > 0.10 for value in attack)
            or any(value > 0.25 for value in STATE["movement"]["attack"].get("travel_distances", []))
        ),
    }
    STATE["multi_front"]["motion_checks"] = checks
    STATE["checks"]["multi_front_motion"] = all(checks.values())


def _run_attrition_recovery():
    ai = STATE["session"]["ai"]
    target_groups = {
        "town_center": [STATE["entities"]["player_town_center"]],
        "villagers": [STATE["entities"]["forward_villager"], STATE["entities"]["player_villager"]],
        "military": [STATE["entities"]["pressure"], STATE["entities"]["player_guard"]],
        "buildings": [STATE["entities"]["player_barracks"]],
    }
    planner = AttritionRecoveryPlanner(
        ai,
        target_groups,
        defended_assets=[STATE["entities"]["enemy_barracks"], STATE["entities"]["enemy_town_center"]],
        difficulty_id="hard",
        attack_unit_id="archer",
        target_army_count=3,
        research_queue=STATE["session"]["research_queue"],
        pressure_technology_id="ranger_fletching",
        tech_failure_threshold=2,
        threat_radius=1.0,
    )
    decisions = []
    for _idx in range(4):
        decisions.append(dict(planner.step()))
        if planner.initial_attack_launched:
            break
    if not planner.initial_attack_launched:
        _fail("skirmish soak attrition planner did not launch initial attack")

    first_losses = []
    for ent in ai.wave_units("archer")[:2]:
        first_losses.append(_kill_unit(ai, ent, "soak_first_failed_push"))
    first_outcome = planner.record_attack_outcome(
        "failed",
        reason="soak_first_failed_push",
        target_name=getattr(STATE["entities"]["forward_villager"], "name", None),
    )
    for _idx in range(12):
        decisions.append(dict(planner.step()))
        if planner.relaunch_count >= 1:
            break

    second_losses = []
    for ent in ai.wave_units("archer")[:2]:
        second_losses.append(_kill_unit(ai, ent, "soak_second_failed_push"))
    outcome = planner.record_attack_outcome(
        "failed",
        reason="soak_second_failed_push",
        target_name=getattr(STATE["entities"]["forward_villager"], "name", None),
    )
    for _idx in range(18):
        decisions.append(dict(planner.step()))
        if planner.relaunch_count >= 2 and planner.pressure_tech_researched:
            break

    snapshot = planner.snapshot()
    relaunch_steps = [
        item.get("step")
        for item in snapshot["wave_launch_history"]
        if item.get("kind") == "relaunch"
    ]
    phase_counts = {}
    for phase in snapshot["phase_history"]:
        phase_counts[phase] = phase_counts.get(phase, 0) + 1
    STATE["attrition"] = {
        "decisions": decisions,
        "first_losses": first_losses,
        "first_outcome": first_outcome,
        "second_losses": second_losses,
        "second_outcome": outcome,
        "planner": snapshot,
        "phase_counts": phase_counts,
    }
    STATE["checks"]["attrition_recovery"] = (
        snapshot["failed_wave_count"] >= 2
        and snapshot["relaunch_count"] >= 2
        and snapshot["recovery_training_count"] >= 1
    )
    STATE["checks"]["pressure_tech"] = (
        snapshot["pressure_tech_researched"]
        and "ranger_fletching" in snapshot["researched_technologies"]
        and phase_counts.get("pressure_tech", 0) >= 1
    )
    STATE["checks"]["relaunch_after_pressure"] = (
        len(relaunch_steps) >= 2
        and snapshot["pressure_tech_step"] is not None
        and relaunch_steps[0] < snapshot["pressure_tech_step"] < relaunch_steps[-1]
    )


def _run_combat_and_victory():
    guard = STATE["entities"]["player_guard"]
    archers = [
        ent for key, ent in STATE["entities"].items()
        if key.startswith("archer_")
    ]
    STATE["combat"]["guard_hp_start"] = int(guard.hp)
    damage_events = []
    for ent in archers[:3]:
        try:
            ent.face_towards(guard.pos)
            ent.play_anim("Attack")
        except (AttributeError, RuntimeError):
            pass
        damage_events.append(apply_damage("archer", "militia", guard))
    STATE["combat"]["damage_events"] = damage_events
    STATE["combat"]["guard_hp_after_damage"] = int(guard.hp)
    STATE["checks"]["combat_damage"] = int(guard.hp) < STATE["combat"]["guard_hp_start"]

    before = victory_progress_state(
        STATE["session"]["scenario_state"],
        {1: [guard], 2: archers},
        hp_threshold=1,
        elapsed_ticks=STATE["ticks"],
    )
    guard.hp = 1
    after = victory_progress_state(
        STATE["session"]["scenario_state"],
        {1: [guard], 2: archers},
        hp_threshold=1,
        elapsed_ticks=STATE["ticks"] + STATE["soak_ticks"],
    )
    winner = scenario_victory_winner(
        STATE["session"]["scenario_state"],
        {1: [guard], 2: archers},
        hp_threshold=1,
    )
    STATE["victory"] = {
        "before": before,
        "after": after,
        "winner": winner,
    }
    STATE["checks"]["victory_progress"] = before["winner"] is None and after["winner"] == 2 and winner == 2


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _setup_scene()
        _launch_multi_front()
        _set_phase("front_settle")
        return

    if STATE["phase"] == "front_settle" and STATE["ticks"] >= 300:
        _sample_multi_front_motion()
        if not (STATE["checks"]["multi_front_split"] and STATE["checks"]["multi_front_motion"]):
            _fail("multi-front soak setup failed: {0}".format(STATE["checks"]))
        _run_attrition_recovery()
        _run_combat_and_victory()
        _set_phase("sustained_soak")
        return

    if STATE["phase"] == "sustained_soak":
        if STATE["ticks"] % 60 == 0:
            STATE["session"]["ai"].gather_resources(
                {"food": 30, "wood": 30, "gold": 20, "stone": 0},
                "soak_sustained_income",
            )
        if STATE["ticks"] >= STATE["soak_ticks"]:
            STATE["checks"]["sustained_ticks"] = True
            if all(STATE["checks"].values()):
                _succeed()
                return
            _fail("skirmish soak checks did not all pass: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["soak_ticks"] = int(args.soak_ticks)
    STATE["phase_started_at"] = time.monotonic()
    for path in (PROBE_PATH, ERROR_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
