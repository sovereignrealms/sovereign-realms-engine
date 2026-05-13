import argparse
import json
import os
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import sovereign.globals as sovereign_globals
from sovereign.data.units import UNITS
from sovereign.entities.runtime import create_entity, place_entity
from sovereign.factory import spawn_minimal_test_scene
from sovereign.systems.production import player_state_from_spawn_result
from sovereign.systems.skirmish import AttritionRecoveryPlanner, ScriptedSkirmishAI
from sovereign.systems.technology import ResearchQueue


PROBE_PATH = "/tmp/pf_sovereign_ai_attrition_recovery_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_attrition_recovery_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "initial_attack": False,
        "live_pressure": False,
        "failed_attack": False,
        "regroup": False,
        "recovery_training": False,
        "relaunch": False,
        "second_failure": False,
        "second_rebuild": False,
        "second_relaunch": False,
        "pressure_tech": False,
        "success_outcome": False,
        "post_success_economy": False,
        "transition_pressure": False,
    },
    "runtime": {},
    "attrition": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run Sovereign AI attrition recovery checks.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-attrition-recovery")
    parser.add_argument("--expect-backend", default="METAL")
    parser.add_argument("--steps", type=int, default=12)
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    print("SOVEREIGN_AI_ATTRITION_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_attrition_recovery.json")


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "runtime": STATE["runtime"],
        "attrition": STATE["attrition"],
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_AI_ATTRITION_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_ATTRITION_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_ATTRITION_RECOVERY_PROBE_PASS runtime={runtime} "
        "initial={initial} pressure={pressure} failed={failed} regroup={regroup} "
        "recovery={recovery} relaunch={relaunch} second_failed={second_failed} "
        "second_rebuild={second_rebuild} second_relaunch={second_relaunch} tech={tech} "
        "success={success} economy={economy} transition={transition}"
    ).format(
        runtime=int(STATE["checks"]["runtime_scene"]),
        initial=int(STATE["checks"]["initial_attack"]),
        pressure=int(STATE["checks"]["live_pressure"]),
        failed=int(STATE["checks"]["failed_attack"]),
        regroup=int(STATE["checks"]["regroup"]),
        recovery=int(STATE["checks"]["recovery_training"]),
        relaunch=int(STATE["checks"]["relaunch"]),
        second_failed=int(STATE["checks"]["second_failure"]),
        second_rebuild=int(STATE["checks"]["second_rebuild"]),
        second_relaunch=int(STATE["checks"]["second_relaunch"]),
        tech=int(STATE["checks"]["pressure_tech"]),
        success=int(STATE["checks"]["success_outcome"]),
        economy=int(STATE["checks"]["post_success_economy"]),
        transition=int(STATE["checks"]["transition_pressure"]),
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _ensure_factions():
    if len(pf.get_factions_list()) == 0:
        pf.add_faction("Neutral", (160, 160, 160, 255))
        pf.add_faction("Sovereign", (40, 90, 255, 255))
        pf.add_faction("Opponent", (220, 50, 50, 255))


def _setup_world():
    pf.load_map("assets/maps", "plain.pfmap")
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    _ensure_factions()
    center = (110.0, 104.0)
    camera = pf.Camera(
        name="sovereign_ai_attrition_recovery_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 150.0, center[1] + 18.0),
        pitch=-62.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_attrition_recovery_region",
            position=center,
            dimensions=(128.0, 112.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _spawned_entity(result, kind, entity_id, name=None):
    for entry, ent in zip(result["plan"]["entities"], result["entities"]):
        if entry["kind"] != kind or entry["id"] != entity_id:
            continue
        if name is not None and entry["name"] != name:
            continue
        return ent
    return None


def _rename_spawned(result, prefix):
    for ent in result["entities"]:
        ent.name = "{0}_{1}".format(prefix, ent.name)


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


def _kill_unit(ent):
    try:
        getattr(ent, "del")()
        return
    except (AttributeError, RuntimeError):
        pass
    try:
        ent.hp = 1
    except (AttributeError, RuntimeError):
        pass
    try:
        ent.play_anim("Die")
    except (AttributeError, RuntimeError):
        pass


def _live_scores(scores):
    return [
        item for item in scores
        if item.get("live_pressure") and item.get("military", 0.0) > item.get("economy", 0.0)
    ]


def _script_losses(ai, units, reason):
    decisions = []
    for ent in list(units):
        _kill_unit(ent)
        decisions.append(ai.record_unit_loss(ent, reason=reason))
    return decisions


def _run_probe(steps):
    _setup_world()
    scene_objs = []
    sovereign_globals.scene_objs = scene_objs
    player_result = spawn_minimal_test_scene(center=(66.0, 76.0), faction_id=1, scene_objs=scene_objs)
    enemy_result = spawn_minimal_test_scene(center=(116.0, 92.0), faction_id=2, scene_objs=scene_objs)
    _rename_spawned(player_result, "player_attrition")
    _rename_spawned(enemy_result, "ai_attrition")
    enemy_state = player_state_from_spawn_result(
        enemy_result,
        completed_buildings=("town_center", "house", "barracks"),
    )

    player_town_center = _spawned_entity(player_result, "building", "town_center")
    player_villager = _spawned_entity(player_result, "unit", "villager", "villager_1")
    player_barracks = _spawned_entity(player_result, "building", "barracks")
    enemy_town_center = _spawned_entity(enemy_result, "building", "town_center")
    enemy_barracks = _spawned_entity(enemy_result, "building", "barracks")
    if None in (player_town_center, player_villager, player_barracks, enemy_town_center, enemy_barracks):
        _fail("required attrition fixture entity was not spawned")

    enemy_town_center.name = "ai_attrition_enemy_town_center"
    enemy_barracks.name = "ai_attrition_enemy_barracks"
    try:
        enemy_barracks.rally_point = (enemy_barracks.pos[0] - 8.0, enemy_barracks.pos[2] + 6.0)
    except (AttributeError, RuntimeError):
        pass

    archers = []
    for idx in range(3):
        archers.append(_create_unit(
            scene_objs,
            enemy_state,
            "archer",
            "ai_attrition_opening_archer_{0}".format(idx + 1),
            (enemy_barracks.pos[0] - 8.0 + idx * 3.0, enemy_barracks.pos[2] + 10.0),
            2,
        ))
    defender = _create_unit(
        scene_objs,
        enemy_state,
        "militia",
        "ai_attrition_home_guard",
        (enemy_barracks.pos[0] + 8.0, enemy_barracks.pos[2] + 8.0),
        2,
    )
    pressure = _create_unit(
        scene_objs,
        None,
        "militia",
        "player_attrition_live_pressure",
        (player_barracks.pos[0] + 6.0, player_barracks.pos[2] + 8.0),
        1,
    )
    try:
        for ent in archers:
            ent.face_towards(player_villager.pos)
        defender.face_towards(pressure.pos)
        pressure.face_towards(enemy_barracks.pos)
    except (AttributeError, RuntimeError):
        pass

    enemy_state.resources["food"] = 0
    enemy_state.resources["wood"] = 0
    enemy_state.resources["gold"] = 0
    enemy_state.resources["stone"] = 0
    enemy_state.population_cap = max(enemy_state.population_cap, enemy_state.population_used + 8)

    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=9090)
    research_queue = ResearchQueue(enemy_state, "barracks", enemy_barracks)
    target_groups = {
        "town_center": [player_town_center],
        "villagers": [player_villager],
        "military": [pressure],
        "buildings": [player_barracks],
    }
    planner = AttritionRecoveryPlanner(
        ai,
        target_groups,
        defended_assets=[enemy_barracks, enemy_town_center],
        difficulty_id="hard",
        expansion_points=[(148.0, 118.0), (160.0, 126.0)],
        target_bases=3,
        attack_unit_id="archer",
        target_army_count=3,
        research_queue=research_queue,
        pressure_technology_id="ranger_fletching",
        tech_failure_threshold=2,
        threat_radius=30.0,
    )

    decisions = []
    initial = dict(planner.step())
    decisions.append(initial)
    if not planner.initial_attack_launched:
        _fail("attrition planner did not launch initial attack: {0}".format(initial))

    casualty_decisions = _script_losses(ai, archers[:2], "scripted_failed_attack")
    outcome_decisions = []
    place_entity(
        pressure,
        (enemy_barracks.pos[0] + 4.0, enemy_barracks.pos[2] + 5.0),
        faction_id=1,
        radius=UNITS["militia"].get("selection_radius", 3.25),
        scale=UNITS["militia"].get("scale"),
    )

    for _idx in range(int(steps) - 1):
        decisions.append(dict(planner.step()))
        if planner.relaunch_launched:
            break

    if planner.relaunch_count < 1:
        _fail("attrition planner did not relaunch after first failure")

    second_losses = _script_losses(ai, ai.wave_units("archer")[:2], "scripted_second_failed_push")
    casualty_decisions.extend(second_losses)
    outcome_decisions.append(planner.record_attack_outcome(
        "failed",
        reason="scripted_second_failed_push",
        target_name=getattr(player_villager, "name", None),
    ))

    for _idx in range(int(steps)):
        decisions.append(dict(planner.step()))
        if planner.relaunch_count >= 2:
            break

    if planner.relaunch_count < 2:
        _fail("attrition planner did not relaunch after second failure")

    place_entity(
        pressure,
        (player_barracks.pos[0] - 12.0, player_barracks.pos[2] - 10.0),
        faction_id=1,
        radius=UNITS["militia"].get("selection_radius", 3.25),
        scale=UNITS["militia"].get("scale"),
    )
    outcome_decisions.append(planner.record_attack_outcome(
        "success",
        reason="scripted_successful_relaunch",
        target_name=getattr(player_villager, "name", None),
    ))

    for _idx in range(int(steps)):
        decisions.append(dict(planner.step()))
        if planner.post_success_expansion_done:
            break

    snapshot = planner.snapshot()
    phase_counts = {}
    for phase in snapshot["phase_history"]:
        phase_counts[phase] = phase_counts.get(phase, 0) + 1

    STATE["attrition"] = {
        "decision_count": len(decisions),
        "phase_counts": phase_counts,
        "planner": snapshot,
        "ai": ai.snapshot(),
        "research_queue": research_queue.snapshot(),
        "live_scores_under_pressure": _live_scores(snapshot["score_history"]),
        "casualty_decisions": casualty_decisions,
        "outcome_decisions": outcome_decisions,
        "casualties_scripted": len(casualty_decisions),
        "pressure_position": list(_ent_xz(pressure)),
    }
    STATE["runtime"] = {
        "scene_obj_count": len(scene_objs),
        "steps_requested": int(steps),
        "steps_executed": len(decisions),
    }
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 15
    STATE["checks"]["initial_attack"] = (
        snapshot["initial_attack_launched"]
        and snapshot["initial_attack_step"] == 1
    )
    STATE["checks"]["live_pressure"] = (
        snapshot["pressure_defense_launched"]
        and snapshot["pressure_defense_step"] is not None
        and phase_counts.get("live_pressure_defense", 0) >= 1
    )
    STATE["checks"]["failed_attack"] = (
        snapshot["failed_wave_count"] >= 1
        and any(item.get("reason") == "detected_failed_attack" for item in snapshot["attack_outcome_history"])
        and snapshot["live_attack_count"] >= 3
    )
    STATE["checks"]["regroup"] = snapshot["regroup_done"] and phase_counts.get("failed_attack_regroup", 0) >= 1
    STATE["checks"]["recovery_training"] = (
        snapshot["recovery_training_count"] >= 2
        and phase_counts.get("attrition_rebuild", 0) >= 2
    )
    STATE["checks"]["relaunch"] = (
        snapshot["relaunch_launched"]
        and snapshot["relaunch_step"] is not None
        and snapshot["relaunch_step"] > snapshot["initial_attack_step"]
    )
    STATE["checks"]["second_failure"] = (
        snapshot["failed_wave_count"] >= 2
        and len([item for item in snapshot["attack_outcome_history"] if item.get("outcome") == "failed"]) >= 2
        and snapshot["active_target_army_count"] == 4
    )
    STATE["checks"]["second_rebuild"] = (
        snapshot["recovery_training_count"] >= 5
        and phase_counts.get("attrition_rebuild", 0) >= 5
    )
    STATE["checks"]["second_relaunch"] = (
        snapshot["relaunch_count"] >= 2
        and len([item for item in snapshot["wave_launch_history"] if item.get("kind") == "relaunch"]) >= 2
    )
    relaunch_steps = [
        item.get("step")
        for item in snapshot["wave_launch_history"]
        if item.get("kind") == "relaunch"
    ]
    STATE["checks"]["pressure_tech"] = (
        snapshot["pressure_tech_researched"]
        and snapshot["pressure_technology_id"] == "ranger_fletching"
        and "ranger_fletching" in snapshot["researched_technologies"]
        and snapshot["pressure_tech_step"] is not None
        and len(relaunch_steps) >= 2
        and snapshot["pressure_tech_step"] > relaunch_steps[0]
        and snapshot["pressure_tech_step"] < relaunch_steps[-1]
        and phase_counts.get("pressure_tech", 0) >= 1
    )
    STATE["checks"]["success_outcome"] = (
        snapshot["successful_wave_count"] == 1
        and any(item.get("outcome") == "success" for item in snapshot["attack_outcome_history"])
    )
    STATE["checks"]["post_success_economy"] = (
        snapshot["post_success_expansion_done"]
        and phase_counts.get("post_success_expansion", 0) >= 1
        and snapshot["base_count"] >= 2
    )
    STATE["checks"]["transition_pressure"] = len(STATE["attrition"]["live_scores_under_pressure"]) >= 1


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _set_phase("attrition_recovery")
        _run_probe(STATE["steps"])
        if all(STATE["checks"].values()):
            _succeed()
            return
        _fail("attrition recovery checks did not all pass: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["steps"] = int(args.steps)
    STATE["phase_started_at"] = time.monotonic()
    for path in (PROBE_PATH, ERROR_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
