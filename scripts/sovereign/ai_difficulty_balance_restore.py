import json
import os
import sys

import pf

from sovereign.entities import runtime as sovereign_entity_runtime
from sovereign.session_state import find_state_payload

del sovereign_entity_runtime


def _summary_path():
    return os.environ.get("PF_SOVEREIGN_AI_DIFFICULTY_BALANCE_RESTORE_SUMMARY")


def _marker_path():
    return os.environ.get("PF_SOVEREIGN_AI_DIFFICULTY_BALANCE_RESTORE_MARKER")


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
        "SOVEREIGN_AI_DIFFICULTY_BALANCE_SAVE_LOAD_PROBE_{status} "
        "state={state} profiles={profiles} savepoint={savepoint} "
        "resume={resume} balance={balance}"
    ).format(
        status=status.upper(),
        state=int(checks.get("state_payload", False)),
        profiles=int(checks.get("profile_reports", False)),
        savepoint=int(checks.get("savepoint_snapshots", False)),
        resume=int(checks.get("restored_continuation", False)),
        balance=int(checks.get("balance_tuning", False)),
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
            "state_payload": False,
            "profile_reports": False,
            "savepoint_snapshots": False,
            "restored_continuation": False,
            "balance_tuning": False,
        },
        "restore": {
            "object_count": len(scene_objs),
        },
    }

    try:
        payload, state_entity = find_state_payload(scene_objs)
        if payload is None:
            raise RuntimeError("Sovereign difficulty-balance state tag was not found")

        report = payload.get("ai_difficulty_balance", {})
        profiles = report.get("profiles", {})
        result["checks"]["state_payload"] = bool(state_entity is not None and report)
        result["checks"]["profile_reports"] = set(profiles.keys()) == set(("standard", "booming", "hard"))
        result["checks"]["savepoint_snapshots"] = all(
            profiles[key]["checks"].get("savepoint")
            for key in profiles
        )
        result["checks"]["restored_continuation"] = all(
            profiles[key]["checks"].get("post_snapshot_continuation")
            for key in profiles
        )
        result["checks"]["balance_tuning"] = bool(report.get("balance_checks_passed"))
        result["status"] = "pass" if all(result["checks"].values()) else "fail"
        result["state_entity"] = getattr(state_entity, "name", None)
        result["report"] = report
    except Exception as exc:
        result["reason"] = "{0}: {1}".format(exc.__class__.__name__, exc)

    _write_result(result["status"], result)
    if os.environ.get("PF_SOVEREIGN_AI_DIFFICULTY_BALANCE_RESTORE_AUTOQUIT") == "1":
        os._exit(0 if result["status"] == "pass" else 1)
    return result["status"] == "pass"
