import json
import os
import sys

import pf

from sovereign.entities import runtime as sovereign_entity_runtime
import sovereign.globals as sovereign_globals
from sovereign.session_state import restore_from_scene
from sovereign.systems.skirmish import BranchingStrategyPlanner, ScriptedSkirmishAI

del sovereign_entity_runtime


def _summary_path():
    return os.environ.get("PF_SOVEREIGN_AI_BRANCHING_RESTORE_SUMMARY")


def _marker_path():
    return os.environ.get("PF_SOVEREIGN_AI_BRANCHING_RESTORE_MARKER")


def _entity_named(scene_objs, name):
    for ent in scene_objs:
        if getattr(ent, "name", None) == name:
            return ent
    return None


def _group_from_names(scene_objs, names):
    ret = []
    for name in names:
        ent = _entity_named(scene_objs, name)
        if ent is not None:
            ret.append(ent)
    return ret


def _write_result(status, payload):
    summary_path = _summary_path()
    if summary_path:
        out_dir = os.path.dirname(summary_path)
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(summary_path, "w") as outfile:
            json.dump(payload, outfile, indent=2, sort_keys=True)
            outfile.write("\n")

    checks = payload.get("checks", {})
    marker = (
        "SOVEREIGN_AI_PERSONALITY_SAVE_LOAD_PROBE_{status} "
        "state={state} profile={profile} cadence={cadence} "
        "cooldown={cooldown} second={second}"
    ).format(
        status=status.upper(),
        state=int(checks.get("state_tag", False)),
        profile=int(checks.get("profile_restored", False)),
        cadence=int(checks.get("cadence_restored", False)),
        cooldown=int(checks.get("cooldown_hold", False)),
        second=int(checks.get("second_harass", False)),
    )
    marker_path = _marker_path()
    if marker_path:
        with open(marker_path, "w") as outfile:
            outfile.write(marker + "\n")
    print(marker)
    sys.stdout.flush()


def restore_runtime_after_session_load(scene_objs=None, scene_regions=None, scene_cameras=None):
    del scene_regions
    del scene_cameras
    if scene_objs is None:
        scene_objs = []

    result = {
        "status": "fail",
        "backend": pf.get_render_info(),
        "checks": {
            "state_tag": False,
            "profile_restored": False,
            "cadence_restored": False,
            "cooldown_hold": False,
            "second_harass": False,
        },
        "restore": {
            "object_count": len(scene_objs),
        },
    }

    try:
        restored = restore_from_scene(scene_objs)
        payload = restored["payload"]
        player = restored["player"]
        production_queue = restored["production_queue"]
        ai_payload = payload.get("ai_branching", {})
        planner_payload = ai_payload.get("planner", {})

        ai = ScriptedSkirmishAI(
            player,
            production_queue.building_ent,
            int(ai_payload.get("faction_id", 2)),
            scene_objs,
            map_seed=payload.get("scenario_state", {}).get("metadata", {}).get("map_seed", 0),
        )
        ai.queue = production_queue
        ai.queue.faction_id = ai.faction_id
        ai.queue.scene_objs = scene_objs

        target_names = ai_payload.get("target_names", {})
        target_groups = {
            "town_center": _group_from_names(scene_objs, target_names.get("town_center", [])),
            "villagers": _group_from_names(scene_objs, target_names.get("villagers", [])),
            "military": _group_from_names(scene_objs, target_names.get("military", [])),
            "buildings": _group_from_names(scene_objs, target_names.get("buildings", [])),
        }
        defended_assets = _group_from_names(scene_objs, ai_payload.get("defended_asset_names", []))
        planner = BranchingStrategyPlanner.from_snapshot(
            planner_payload,
            ai,
            target_groups,
            defended_assets=defended_assets,
            expansion_points=ai_payload.get("expansion_points", []),
        )

        decisions = []
        for _idx in range(6):
            decision = planner.step()
            decisions.append(dict(decision))
            if (
                decision.get("action") == "counterattack"
                and decision.get("reason") == "branching_harass"
                and decision.get("harass_wave_count") >= 2
            ):
                break

        result["checks"]["state_tag"] = True
        result["checks"]["profile_restored"] = (
            planner.profile.get("id") == "hard"
            and planner.profile.get("personality_id") == "pressure"
        )
        result["checks"]["cadence_restored"] = (
            planner.harass_interval_steps == 2
            and planner.max_harass_waves == 2
            and planner.harass_wave_count >= 2
        )
        result["checks"]["cooldown_hold"] = any(
            item.get("action") == "hold_position"
            and item.get("reason") == "branching_harass_cooldown"
            for item in decisions
        )
        result["checks"]["second_harass"] = any(
            item.get("action") == "counterattack"
            and item.get("reason") == "branching_harass"
            and item.get("harass_wave_count") >= 2
            for item in decisions
        )
        result["status"] = "pass" if all(result["checks"].values()) else "fail"
        result["payload_ai_branching"] = ai_payload
        result["decisions"] = decisions
        result["ai"] = ai.snapshot()
        result["planner"] = planner.snapshot()
        sovereign_globals.player_state = player
        sovereign_globals.production_queue = production_queue
        sovereign_globals.ai_branching_strategy = planner
        sovereign_globals.session_state = payload
    except Exception as exc:
        result["reason"] = "{0}: {1}".format(exc.__class__.__name__, exc)

    _write_result(result["status"], result)
    if os.environ.get("PF_SOVEREIGN_AI_BRANCHING_RESTORE_AUTOQUIT") == "1":
        os._exit(0 if result["status"] == "pass" else 1)
    return result["status"] == "pass"
