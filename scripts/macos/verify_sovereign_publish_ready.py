#!/usr/bin/env python3

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TARGET_REMOTE = "https://github.com/sovereignrealms/sovereign-realms-engine.git"

REQUIRED_PATHS = [
    "LICENSE.txt",
    "README.md",
    "NOTICE.md",
    "CHANGES.md",
    "docs/sovereign/engine_work_needed.md",
    "docs/sovereign/repo_license_structure.md",
    "docs/sovereign/repo_publish_handoff.md",
    "docs/modding/licensing_worlds.md",
    "docs/modding/world_pack_format.md",
    "games/README.md",
    "games/example_world/LICENSE",
    "games/example_world/README.md",
    "games/example_world/world.json",
    "scripts/sovereign",
    "assets/sovereign",
    "tools/asset_validation/validate_pfobj.py",
]

REQUIRED_IGNORE_PATTERNS = [
    "/bin/",
    "/dist/",
    "/lib/",
    "/obj/",
    "/qa-output/",
    "visual_parity_captures/",
    "*.pfsave",
    "*.gputrace",
]

TRACKED_ARTIFACT_PREFIXES = (
    "bin/",
    "dist/",
    "lib/",
    "obj/",
    "qa-output/",
    "visual_parity_captures/",
)

TRACKED_ARTIFACT_SUFFIXES = (
    ".gputrace",
    ".trace",
)

LOCAL_NOTEBOOKS = {
    "a.md",
}

LOCAL_SAVE_FILES = {
    "session.pfsave",
    "tmp_native_session_roundtrip.pfsave",
    "tmp_native_session_region_camera_roundtrip.pfsave",
    "tmp_native_session_ui_roundtrip.pfsave",
    "tmp_native_session_ui_region_camera_roundtrip.pfsave",
    "assets/maps/test.pfsave",
}


def _run(cmd):
    return subprocess.run(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=30,
    )


def _git_lines(*args):
    proc = _run(["git"] + list(args))
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip())
    return [line for line in proc.stdout.splitlines() if line.strip()]


def _tracked_files():
    return _git_lines("ls-files")


def _remote_url(name):
    proc = _run(["git", "remote", "get-url", name])
    if proc.returncode != 0:
        return None
    return proc.stdout.strip()


def _status_short():
    return _git_lines("status", "--short")


def _add_issue(issues, severity, message):
    issues.append((severity, message))
    print("SOVEREIGN_PUBLISH_{0} {1}".format(severity, message))


def _check_required_paths(issues):
    for relpath in REQUIRED_PATHS:
        if not (ROOT / relpath).exists():
            _add_issue(issues, "FAIL", "missing_required_path path={0}".format(relpath))


def _check_ignore_patterns(issues):
    try:
        ignore_text = (ROOT / ".gitignore").read_text()
    except OSError:
        _add_issue(issues, "FAIL", "missing_gitignore")
        return
    for pattern in REQUIRED_IGNORE_PATTERNS:
        if pattern not in ignore_text:
            _add_issue(issues, "FAIL", "missing_ignore_pattern pattern={0}".format(pattern))


def _tracked_artifact_reason(path):
    if path in LOCAL_NOTEBOOKS:
        return "local_notebook"
    if path in LOCAL_SAVE_FILES:
        return "local_save"
    if path.startswith(TRACKED_ARTIFACT_PREFIXES):
        return "generated_artifact"
    if path.endswith(TRACKED_ARTIFACT_SUFFIXES):
        return "trace_artifact"
    return None


def _check_tracked_artifacts(issues):
    for path in _tracked_files():
        reason = _tracked_artifact_reason(path)
        if reason:
            _add_issue(issues, "WARN", "tracked_{0} path={1}".format(reason, path))


def _check_remote(issues):
    url = _remote_url("sovereign")
    if not url:
        _add_issue(
            issues,
            "WARN",
            "missing_sovereign_remote target={0}".format(TARGET_REMOTE),
        )
        return
    if url != TARGET_REMOTE and not url.endswith("sovereign-realms-engine.git"):
        _add_issue(
            issues,
            "WARN",
            "unexpected_sovereign_remote url={0}".format(url),
        )


def _check_branch_and_status(issues):
    branch = _git_lines("branch", "--show-current")
    branch_name = branch[0] if branch else "<detached>"
    if branch_name in ("main", "master"):
        _add_issue(issues, "WARN", "publishing_from_default_branch branch={0}".format(branch_name))
    else:
        print("SOVEREIGN_PUBLISH_INFO branch={0}".format(branch_name))

    status = _status_short()
    if status:
        _add_issue(issues, "WARN", "working_tree_has_changes count={0}".format(len(status)))


def main():
    parser = argparse.ArgumentParser(description="Check whether this checkout is ready to publish as sovereign-realms-engine.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Treat warnings as publish blockers.",
    )
    args = parser.parse_args()

    issues = []
    _check_required_paths(issues)
    _check_ignore_patterns(issues)
    _check_tracked_artifacts(issues)
    _check_remote(issues)
    _check_branch_and_status(issues)

    fail_count = len([severity for severity, _ in issues if severity == "FAIL"])
    warn_count = len([severity for severity, _ in issues if severity == "WARN"])
    if fail_count or (args.strict and warn_count):
        print(
            "SOVEREIGN_PUBLISH_READY_FAIL fails={0} warnings={1} strict={2}".format(
                fail_count,
                warn_count,
                int(args.strict),
            )
        )
        return 1

    print(
        "SOVEREIGN_PUBLISH_READY_PASS fails={0} warnings={1} strict={2}".format(
            fail_count,
            warn_count,
            int(args.strict),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
