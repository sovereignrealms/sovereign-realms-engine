import json
import os
import sys

import pf

from sovereign.entities import runtime as sovereign_entity_runtime
import sovereign.globals as sovereign_globals
from sovereign.session_state import restore_from_scene
from sovereign.systems.skirmish import MemoryResponsePlanner, ScriptedSkirmishAI, ThreatMemory

del sovereign_entity_runtime


def _summary_path():
    return os.environ.get("PF_SOVEREIGN_AI_MEMORY_RESTORE_SUMMARY")


def _marker_path():
    return os.environ.get("PF_SOVEREIGN_AI_MEMORY_RESTORE_MARKER")


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
        "SOVEREIGN_AI_MEMORY_SAVE_LOAD_PROBE_{status} "
        "state={state} memory={memory} regroup={regroup} income={income} "
        "house={house} train={train} response={response}"
    ).format(
        status=status.upper(),
        state=int(checks.get("state_tag", False)),
        memory=int(checks.get("memory_restored", False)),
        regroup=int(checks.get("regroup_decision", False)),
        income=int(checks.get("memory_income", False)),
        house=int(checks.get("memory_house", False)),
        train=int(checks.get("memory_training", False)),
        response=int(checks.get("memory_response", False)),
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
            "memory_restored": False,
            "regroup_decision": False,
            "memory_income": False,
            "memory_house": False,
            "memory_training": False,
            "memory_response": False,
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
        ai_payload = payload.get("ai_memory", {})
        memory = ThreatMemory.from_snapshot(ai_payload.get("memory"))
        threat = memory.best_threat(current_step=ai_payload.get("current_step", 1))

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
        planner = MemoryResponsePlanner(
            ai,
            memory,
            min_defenders=int(ai_payload.get("min_defenders", 2)),
            regroup_point=ai_payload.get("regroup_point"),
        )

        decisions = []
        for _idx in range(10):
            decision = planner.step()
            decisions.append(dict(decision))
            if planner.response_launched:
                break

        result["checks"]["state_tag"] = True
        result["checks"]["memory_restored"] = (
            threat is not None
            and threat.get("name") == ai_payload.get("expected_threat_name")
        )
        result["checks"]["regroup_decision"] = any(
            item.get("action") == "retreat_regroup"
            and item.get("reason") == "memory_outnumbered"
            for item in decisions
        )
        result["checks"]["memory_income"] = any(
            item.get("action") == "gather_resources"
            and item.get("reason") == "memory_response_income"
            for item in decisions
        )
        result["checks"]["memory_house"] = any(
            item.get("action") == "build_house"
            for item in decisions
        )
        result["checks"]["memory_training"] = ai.unit_count("militia") >= int(ai_payload.get("min_defenders", 2))
        result["checks"]["memory_response"] = any(
            item.get("action") == "defend"
            and item.get("reason") == "memory_threat_response"
            and item.get("target_name") == ai_payload.get("expected_threat_name")
            for item in decisions
        )
        result["status"] = "pass" if all(result["checks"].values()) else "fail"
        result["payload_ai_memory"] = ai_payload
        result["memory"] = memory.snapshot(ai_payload.get("current_step", 1))
        result["decisions"] = decisions
        result["ai"] = ai.snapshot()
        result["planner"] = planner.snapshot()
        sovereign_globals.player_state = player
        sovereign_globals.production_queue = production_queue
        sovereign_globals.ai_memory = memory
        sovereign_globals.ai_memory_response = planner
        sovereign_globals.session_state = payload
    except Exception as exc:
        result["reason"] = "{0}: {1}".format(exc.__class__.__name__, exc)

    _write_result(result["status"], result)
    if os.environ.get("PF_SOVEREIGN_AI_MEMORY_RESTORE_AUTOQUIT") == "1":
        os._exit(0 if result["status"] == "pass" else 1)
    return result["status"] == "pass"
