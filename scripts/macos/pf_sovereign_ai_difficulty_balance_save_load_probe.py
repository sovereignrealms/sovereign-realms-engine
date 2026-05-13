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
from sovereign.session_state import attach_state
from sovereign.systems.production import player_state_from_spawn_result
from sovereign.systems.skirmish import BranchingStrategyPlanner, ScriptedSkirmishAI, ai_difficulty_profile


PROBE_PATH = "/tmp/pf_sovereign_ai_difficulty_balance_save_load_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_difficulty_balance_save_load_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "profile_divergence": False,
        "savepoint_snapshots": False,
        "restored_continuation": False,
        "balance_tuning": False,
        "state_attached": False,
        "session_save": False,
        "session_load_requested": False,
    },
    "profiles": {},
    "runtime": {},
    "session": {},
}

PROFILE_LAYOUTS = {
    "standard": {"player": (68.0, 64.0), "enemy": (118.0, 76.0), "expansion": [(150.0, 92.0), (164.0, 100.0)]},
    "booming": {"player": (68.0, 116.0), "enemy": (118.0, 128.0), "expansion": [(150.0, 144.0), (164.0, 152.0)]},
    "hard": {"player": (68.0, 168.0), "enemy": (118.0, 180.0), "expansion": [(150.0, 196.0), (164.0, 204.0)]},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run Sovereign difficulty A/B save-load balance checks.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-difficulty-balance-save-load")
    parser.add_argument("--expect-backend", default="METAL")
    parser.add_argument("--save-steps", type=int, default=13)
    parser.add_argument("--post-steps", type=int, default=14)
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    print("SOVEREIGN_AI_DIFFICULTY_BALANCE_PHASE {0}".format(name))
    sys.stdout.flush()


def _phase_elapsed():
    return time.monotonic() - STATE["phase_started_at"]


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_difficulty_balance_save_load.json")


def _restore_summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_difficulty_balance_save_load_restore.json")


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "profiles": STATE["profiles"],
        "runtime": STATE["runtime"],
        "session": STATE["session"],
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_AI_DIFFICULTY_BALANCE_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_DIFFICULTY_BALANCE_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


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


def _setup_render_state(profile_id):
    center = (124.0, 86.0)
    camera = pf.Camera(
        name="sovereign_ai_difficulty_balance_{0}_camera".format(profile_id),
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 136.0, center[1] + 12.0),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_difficulty_balance_{0}_region".format(profile_id),
            position=center,
            dimensions=(128.0, 96.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _rename_spawned(result, prefix):
    for ent in result["entities"]:
        ent.name = "{0}_{1}".format(prefix, ent.name)


def _create_existing_militia(scene_objs, enemy_state, name, point):
    definition = UNITS["militia"]
    ent = create_entity({
        "kind": "unit",
        "id": "militia",
        "name": name,
        "definition": definition,
    })
    place_entity(
        ent,
        point,
        faction_id=2,
        radius=definition.get("selection_radius", 3.25),
        scale=definition.get("scale"),
    )
    scene_objs.append(ent)
    enemy_state.add_unit("militia", ent)
    return ent


def _create_forward_villager(scene_objs, profile_id):
    definition = UNITS["villager"]
    ent = create_entity({
        "kind": "unit",
        "id": "villager",
        "name": "player_{0}_balance_worker".format(profile_id),
        "definition": definition,
    })
    place_entity(
        ent,
        (92.0, 80.0),
        faction_id=1,
        radius=definition.get("selection_radius", 2.5),
        scale=definition.get("scale"),
    )
    scene_objs.append(ent)
    return ent


def _decision_counts(decisions, key):
    counts = {}
    for item in decisions:
        value = item.get(key)
        if value is None:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _first_harass(decisions):
    for item in decisions:
        if item.get("action") == "counterattack" and item.get("reason") == "branching_harass":
            return item
    return {}


def _run_profile(profile_id, save_steps, post_steps, scene_objs):
    layout = PROFILE_LAYOUTS[profile_id]
    player_result = spawn_minimal_test_scene(center=layout["player"], faction_id=1, scene_objs=scene_objs)
    enemy_result = spawn_minimal_test_scene(center=layout["enemy"], faction_id=2, scene_objs=scene_objs)
    _rename_spawned(player_result, "player_{0}".format(profile_id))
    _rename_spawned(enemy_result, "ai_{0}".format(profile_id))
    player_state = player_state_from_spawn_result(
        player_result,
        completed_buildings=("town_center", "house", "barracks"),
    )
    enemy_state = player_state_from_spawn_result(
        enemy_result,
        completed_buildings=("town_center", "house", "barracks"),
    )
    _setup_render_state(profile_id)

    player_town_center = _spawned_entity(player_result, "building", "town_center")
    player_villager = _spawned_entity(player_result, "unit", "villager", "villager_1")
    player_barracks = _spawned_entity(player_result, "building", "barracks")
    enemy_town_center = _spawned_entity(enemy_result, "building", "town_center")
    enemy_barracks = _spawned_entity(enemy_result, "building", "barracks")
    if None in (player_town_center, player_villager, player_barracks, enemy_town_center, enemy_barracks):
        _fail("required difficulty-balance fixture entity was not spawned for {0}".format(profile_id))

    enemy_town_center.name = "ai_{0}_balance_enemy_town_center".format(profile_id)
    enemy_barracks.name = "ai_{0}_balance_enemy_barracks".format(profile_id)
    guard = create_entity({
        "kind": "unit",
        "id": "militia",
        "name": "player_{0}_balance_military_threat".format(profile_id),
        "definition": UNITS["militia"],
    })
    place_entity(
        guard,
        (layout["enemy"][0] + 4.0, layout["enemy"][1] + 12.0),
        faction_id=1,
        radius=UNITS["militia"].get("selection_radius"),
        scale=UNITS["militia"].get("scale"),
    )
    scene_objs.append(guard)

    militia_1 = _create_existing_militia(
        scene_objs,
        enemy_state,
        "ai_{0}_balance_defender_1".format(profile_id),
        (layout["enemy"][0] + 28.0, layout["enemy"][1] + 16.0),
    )
    militia_2 = _create_existing_militia(
        scene_objs,
        enemy_state,
        "ai_{0}_balance_defender_2".format(profile_id),
        (layout["enemy"][0] + 26.0, layout["enemy"][1] + 18.0),
    )
    forward_villager = _create_forward_villager(scene_objs, profile_id)
    place_entity(
        forward_villager,
        (layout["enemy"][0] - 26.0, layout["enemy"][1] + 4.0),
        faction_id=1,
        radius=UNITS["villager"].get("selection_radius", 2.5),
        scale=UNITS["villager"].get("scale"),
    )
    try:
        guard.face_towards(militia_1.pos)
        forward_villager.face_towards(enemy_barracks.pos)
        militia_1.face_towards(guard.pos)
        militia_2.face_towards(guard.pos)
        enemy_barracks.rally_point = (100.0, 84.0)
    except (AttributeError, RuntimeError):
        pass

    enemy_state.resources["food"] = 0
    enemy_state.resources["wood"] = 0
    enemy_state.resources["gold"] = 0
    enemy_state.resources["stone"] = 0
    enemy_state.population_cap = max(enemy_state.population_used + 6, enemy_state.population_cap)

    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=4242)
    target_groups = {
        "town_center": [player_town_center],
        "villagers": [forward_villager, player_villager],
        "military": [guard],
        "buildings": [player_barracks],
    }
    defended_assets = [enemy_barracks, enemy_town_center]
    expansion_points = layout["expansion"]
    planner = BranchingStrategyPlanner(
        ai,
        target_groups,
        defended_assets=defended_assets,
        difficulty_id=profile_id,
        expansion_points=layout["expansion"],
        target_bases=None,
        threat_radius=56.0,
    )

    pre_decisions = []
    for _idx in range(int(save_steps)):
        pre_decisions.append(dict(planner.step()))
    save_snapshot = planner.snapshot()

    restored_planner = BranchingStrategyPlanner.from_snapshot(
        save_snapshot,
        ai,
        target_groups,
        defended_assets=defended_assets,
        expansion_points=expansion_points,
    )
    post_decisions = []
    for _idx in range(int(post_steps)):
        post_decisions.append(dict(restored_planner.step()))
    final_snapshot = restored_planner.snapshot()
    total_decisions = pre_decisions + post_decisions
    profile = ai_difficulty_profile(profile_id)
    first_harass = _first_harass(total_decisions)
    expansion_events = [
        item for item in total_decisions
        if item.get("action") == "build_building" and item.get("reason") == "branching_expansion"
    ]
    harass_training = [
        item for item in total_decisions
        if item.get("action") == "train" and item.get("strategy_branch") == "branching_harass"
    ]

    report = {
        "profile": profile,
        "runtime": {
            "profile_id": profile_id,
            "player_center": list(layout["player"]),
            "enemy_center": list(layout["enemy"]),
        },
        "scene_obj_count": len(scene_objs),
        "save_step_count": int(save_steps),
        "post_step_count": int(post_steps),
        "pre_reason_counts": _decision_counts(pre_decisions, "reason"),
        "post_reason_counts": _decision_counts(post_decisions, "reason"),
        "reason_counts": _decision_counts(total_decisions, "reason"),
        "action_counts": _decision_counts(total_decisions, "action"),
        "first_harass": first_harass,
        "save_snapshot": {
            "step_index": save_snapshot["step_index"],
            "harass_wave_count": save_snapshot["harass_wave_count"],
            "base_count": save_snapshot["base_count"],
            "army_count": save_snapshot["army_count"],
            "defense_launched": save_snapshot["defense_launched"],
            "harass_unit_id": save_snapshot["harass_unit_id"],
            "harass_launch_history": list(save_snapshot["harass_launch_history"]),
        },
        "final_snapshot": {
            "step_index": final_snapshot["step_index"],
            "harass_wave_count": final_snapshot["harass_wave_count"],
            "base_count": final_snapshot["base_count"],
            "army_count": final_snapshot["army_count"],
            "defense_launched": final_snapshot["defense_launched"],
            "harass_unit_id": final_snapshot["harass_unit_id"],
            "harass_launch_history": list(final_snapshot["harass_launch_history"]),
        },
        "counts": {
            "bases": final_snapshot["base_count"],
            "army": final_snapshot["army_count"],
            "militia": ai.unit_count("militia"),
            "archer": ai.unit_count("archer"),
            "harass_waves": final_snapshot["harass_wave_count"],
            "expansions": len(expansion_events),
            "harass_training": len(harass_training),
        },
        "checks": {},
    }
    report["checks"]["savepoint"] = (
        save_snapshot["step_index"] == int(save_steps)
        and save_snapshot["defense_launched"]
        and save_snapshot["harass_wave_count"] >= 1
    )
    report["checks"]["post_snapshot_continuation"] = (
        final_snapshot["step_index"] == int(save_steps) + int(post_steps)
        and len(post_decisions) == int(post_steps)
        and final_snapshot["harass_wave_count"] >= save_snapshot["harass_wave_count"]
    )
    report["checks"]["branch_activity"] = (
        report["reason_counts"].get("branching_defense", 0) >= 1
        and report["reason_counts"].get("branching_expansion", 0) >= 1
        and report["reason_counts"].get("branching_harass", 0) >= 1
    )
    report["checks"]["profile_expectations"] = (
        report["counts"]["bases"] == int(profile["expansion_target_bases"])
        and report["counts"]["harass_waves"] == int(profile["max_harass_waves"])
        and final_snapshot["harass_unit_id"] == profile["preferred_military_unit"]
    )
    return report, enemy_town_center


def _balance_checks(profiles):
    standard = profiles["standard"]
    booming = profiles["booming"]
    hard = profiles["hard"]
    return {
        "profile_divergence": (
            standard["profile"]["personality_id"] == "balanced"
            and booming["profile"]["personality_id"] == "booming"
            and hard["profile"]["personality_id"] == "pressure"
            and standard["profile"]["harass_interval_steps"] > hard["profile"]["harass_interval_steps"]
            and booming["profile"]["harass_interval_steps"] > standard["profile"]["harass_interval_steps"]
        ),
        "expansion_tuning": (
            standard["counts"]["bases"] == 2
            and booming["counts"]["bases"] == 3
            and hard["counts"]["bases"] == 3
            and booming["counts"]["expansions"] > standard["counts"]["expansions"]
        ),
        "harassment_tuning": (
            standard["counts"]["harass_waves"] == 1
            and booming["counts"]["harass_waves"] == 1
            and hard["counts"]["harass_waves"] == 2
            and hard["final_snapshot"]["harass_launch_history"][1]["step"]
            - hard["final_snapshot"]["harass_launch_history"][0]["step"] == hard["profile"]["harass_interval_steps"]
        ),
        "target_tuning": (
            standard["first_harass"].get("target_role") == "buildings"
            and booming["first_harass"].get("target_role") == "buildings"
            and hard["first_harass"].get("target_role") == "villagers"
        ),
        "unit_tuning": (
            standard["final_snapshot"]["harass_unit_id"] == "militia"
            and booming["final_snapshot"]["harass_unit_id"] == "militia"
            and hard["final_snapshot"]["harass_unit_id"] == "archer"
            and hard["counts"]["archer"] >= 2
        ),
        "branch_coverage": all(
            report["checks"]["branch_activity"]
            and report["checks"]["savepoint"]
            and report["checks"]["post_snapshot_continuation"]
            for report in profiles.values()
        ),
    }


def _compact_profile_report(report):
    return {
        "profile": {
            "id": report["profile"]["id"],
            "personality_id": report["profile"]["personality_id"],
            "expansion_target_bases": report["profile"]["expansion_target_bases"],
            "harass_interval_steps": report["profile"]["harass_interval_steps"],
            "max_harass_waves": report["profile"]["max_harass_waves"],
            "preferred_military_unit": report["profile"]["preferred_military_unit"],
        },
        "counts": dict(report["counts"]),
        "checks": dict(report["checks"]),
        "first_harass": {
            "target_role": report["first_harass"].get("target_role"),
            "target_name": report["first_harass"].get("target_name"),
        },
        "save_snapshot": dict(report["save_snapshot"]),
        "final_snapshot": dict(report["final_snapshot"]),
        "reason_counts": dict(report["reason_counts"]),
        "post_reason_counts": dict(report["post_reason_counts"]),
    }


def _drive_balance_fixture(save_steps, post_steps):
    _setup_world()
    profiles = {}
    state_entity = None
    scene_objs = []
    sovereign_globals.scene_objs = scene_objs
    for profile_id in ("standard", "booming", "hard"):
        print("SOVEREIGN_AI_DIFFICULTY_BALANCE_PROFILE {0}".format(profile_id))
        sys.stdout.flush()
        profiles[profile_id], entity = _run_profile(profile_id, save_steps, post_steps, scene_objs)
        state_entity = entity

    balance = _balance_checks(profiles)
    STATE["profiles"] = profiles
    STATE["runtime"] = {
        "profile_count": len(profiles),
        "save_steps": int(save_steps),
        "post_steps": int(post_steps),
        "scene_obj_counts": {
            key: value["scene_obj_count"]
            for key, value in profiles.items()
        },
        "balance_checks": balance,
    }
    STATE["checks"]["runtime_scene"] = (
        len(profiles) == 3
        and all(value["scene_obj_count"] >= 25 for value in profiles.values())
    )
    STATE["checks"]["profile_divergence"] = balance["profile_divergence"]
    STATE["checks"]["savepoint_snapshots"] = all(value["checks"]["savepoint"] for value in profiles.values())
    STATE["checks"]["restored_continuation"] = all(value["checks"]["post_snapshot_continuation"] for value in profiles.values())
    STATE["checks"]["balance_tuning"] = all(balance.values())

    compact_profiles = {
        profile_id: _compact_profile_report(report)
        for profile_id, report in profiles.items()
    }
    payload = {
        "version": 1,
        "ai_difficulty_balance": {
            "profiles": compact_profiles,
            "balance_checks": balance,
            "balance_checks_passed": all(balance.values()),
            "save_steps": int(save_steps),
            "post_steps": int(post_steps),
        },
    }
    attach_state(state_entity, payload)
    STATE["checks"]["state_attached"] = True
    STATE["session"]["state_entity_name"] = getattr(state_entity, "name", None)
    STATE["session"]["payload_before_save"] = payload


def _request_save():
    save_path = os.path.join(STATE["output_dir"], "sovereign_ai_difficulty_balance_save_load.pfsave")
    STATE["session"]["save_path"] = save_path
    os.environ["PF_PY3_SESSION_GLOBALS_MODULE"] = "sovereign.globals"
    os.environ["PF_PY3_SESSION_RESTORE_MODULE"] = "sovereign.ai_difficulty_balance_restore"
    os.environ["PF_SOVEREIGN_AI_DIFFICULTY_BALANCE_RESTORE_SUMMARY"] = _restore_summary_path()
    os.environ["PF_SOVEREIGN_AI_DIFFICULTY_BALANCE_RESTORE_MARKER"] = PROBE_PATH
    os.environ["PF_SOVEREIGN_AI_DIFFICULTY_BALANCE_RESTORE_AUTOQUIT"] = "1"
    _write_summary("save_requested")
    pf.save_session(save_path)
    _set_phase("wait_save")


def _on_session_saved(user, event):
    del user
    del event
    if STATE["phase"] != "wait_save":
        return
    save_path = STATE["session"].get("save_path")
    STATE["checks"]["session_save"] = bool(save_path and os.path.exists(save_path) and os.path.getsize(save_path) > 0)
    if not STATE["checks"]["session_save"]:
        _fail("AI difficulty-balance session save file was not written")
    STATE["checks"]["session_load_requested"] = True
    STATE["session"]["save_size_bytes"] = os.path.getsize(save_path)
    _write_summary("load_requested")
    pf.load_session(save_path)
    _set_phase("wait_load")


def _on_session_save_fail(user, event):
    del user
    _fail("AI difficulty-balance session save failed: {0}".format(event))


def _on_session_load_fail(user, event):
    del user
    _fail("AI difficulty-balance session load failed: {0}".format(event))


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _drive_balance_fixture(STATE["save_steps"], STATE["post_steps"])
        _set_phase("save")
        return

    if STATE["phase"] == "save":
        pending_save_keys = ("session_save", "session_load_requested")
        if all(STATE["checks"][key] for key in STATE["checks"] if key not in pending_save_keys):
            _request_save()
            return
        _fail("AI difficulty-balance checks did not all pass before save: {0}".format(STATE["checks"]))

    if STATE["phase"] in ("wait_save", "wait_load") and _phase_elapsed() > 24.0:
        _fail("timed out in {0}".format(STATE["phase"]))


def main():
    args = _parse_args()
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["save_steps"] = int(args.save_steps)
    STATE["post_steps"] = int(args.post_steps)
    STATE["phase_started_at"] = time.monotonic()
    for path in (PROBE_PATH, ERROR_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)
    pf.register_ui_event_handler(pf.EVENT_SESSION_SAVED, _on_session_saved, None)
    pf.register_ui_event_handler(pf.EVENT_SESSION_FAIL_SAVE, _on_session_save_fail, None)
    pf.register_ui_event_handler(pf.EVENT_SESSION_FAIL_LOAD, _on_session_load_fail, None)


main()
