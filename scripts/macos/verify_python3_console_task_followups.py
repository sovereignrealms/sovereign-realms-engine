#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CONSOLE_MARKER = Path("/tmp/pf_python3_console_selftest.txt")
TASK_MARKER = Path("/tmp/pf_metal_task_probe.txt")
TASK_ERROR = Path("/tmp/pf_metal_task_probe_error.txt")


def _unlink(path):
    try:
        path.unlink()
    except OSError:
        pass


def _read(path):
    try:
        return path.read_text(errors="replace").strip()
    except OSError:
        return ""


def _fail(message, stdout="", stderr=""):
    print("PYTHON3_CONSOLE_TASK_FOLLOWUP_FAIL {0}".format(message), file=sys.stderr)
    if stdout:
        print("stdout:\n{0}".format(stdout[-4000:]), file=sys.stderr)
    if stderr:
        print("stderr:\n{0}".format(stderr[-4000:]), file=sys.stderr)
    return 1


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default="METAL")
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "visual_parity_captures/python3-console-task-followups"),
    )
    parser.add_argument("--timeout", type=int, default=90)
    args = parser.parse_args()

    binary = ROOT / "bin/pf-arm64"
    if not binary.exists():
        return _fail("missing_binary path={0}".format(binary))

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in (CONSOLE_MARKER, TASK_MARKER, TASK_ERROR):
        _unlink(path)

    env = os.environ.copy()
    env["PF_CONSOLE_SELFTEST_PATH"] = str(CONSOLE_MARKER)
    try:
        proc = subprocess.run(
            [
                str(binary),
                "./",
                "./scripts/macos/pf_metal_task_probe.py",
                "--output-dir",
                str(output_dir),
                "--expect-backend",
                args.backend,
            ],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            timeout=args.timeout,
        )
    except subprocess.TimeoutExpired as exc:
        subprocess.run(["/usr/bin/killall", "-9", "pf-arm64"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return _fail(
            "probe_timeout timeout={0} task_error={1}".format(args.timeout, _read(TASK_ERROR)),
            exc.stdout or "",
            exc.stderr or "",
        )

    if proc.returncode != 0:
        return _fail(
            "probe_failed returncode={0} task_error={1}".format(proc.returncode, _read(TASK_ERROR)),
            proc.stdout,
            proc.stderr,
        )

    console = _read(CONSOLE_MARKER)
    task = _read(TASK_MARKER)
    if not console.startswith("PY_CONSOLE_SELFTEST_PASS"):
        return _fail("console_selftest_missing marker={0}".format(console), proc.stdout, proc.stderr)
    if not task.startswith("METAL_TASK_PROBE_PASS"):
        return _fail("task_probe_missing marker={0}".format(task), proc.stdout, proc.stderr)

    print("PYTHON3_CONSOLE_TASK_FOLLOWUP_PASS console='{0}' task='{1}'".format(console, task))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
