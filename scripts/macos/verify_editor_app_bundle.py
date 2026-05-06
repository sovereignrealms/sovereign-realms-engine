#!/usr/bin/env python3

import argparse
import os
import plistlib
import re
import shutil
import shlex
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _tail(path, max_lines=80):
    try:
        lines = Path(path).read_text(errors="replace").splitlines()
    except OSError:
        return "<missing>"
    return "\n".join(lines[-max_lines:])


def _write_env_file(path, values):
    lines = []
    for key, value in sorted(values.items()):
        lines.append("export {0}={1}".format(key, shlex.quote(str(value))))
    path.write_text("\n".join(lines) + "\n")


def _bundle_identifier(bundle_dir):
    plist_path = bundle_dir / "Contents" / "Info.plist"
    try:
        with plist_path.open("rb") as infile:
            info = plistlib.load(infile)
    except (OSError, plistlib.InvalidFileException):
        return "org.permafrostengine.editor.dev"
    return info.get("CFBundleIdentifier") or "org.permafrostengine.editor.dev"


def _png_nonblank(path):
    if not path.exists():
        return False
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/macos/check_png_nonblank.py"),
            str(path),
            "--min-nonblack-ratio",
            "0.01",
        ],
        cwd=str(ROOT),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=20,
    )
    return proc.returncode == 0


def _capture_to_path(cmd, path):
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        timeout=5,
    )
    if proc.returncode == 0 and _png_nonblank(path):
        return proc, True
    return proc, False


def _service_external_captures(capture_dir):
    if capture_dir is None or not capture_dir.exists():
        return
    for ready_path in sorted(capture_dir.glob("*.ready")):
        done_path = ready_path.with_suffix(".done")
        if done_path.exists():
            continue
        lines = ready_path.read_text().splitlines()
        if len(lines) < 2:
            continue
        window_id, capture_path = lines[0].strip(), Path(lines[1].strip())
        capture_path.parent.mkdir(parents=True, exist_ok=True)
        time.sleep(0.3)
        if window_id:
            cmd = ["/usr/sbin/screencapture", "-x", "-o", "-l{0}".format(window_id), str(capture_path)]
            proc, ok = _capture_to_path(cmd, capture_path)
        else:
            proc = subprocess.CompletedProcess([], 1, "", "no window id")
            ok = False
        if not ok:
            proc, ok = _capture_to_path(["/usr/sbin/screencapture", "-x", str(capture_path)], capture_path)
        if not ok:
            for display_idx in range(1, 5):
                proc, ok = _capture_to_path(
                    ["/usr/sbin/screencapture", "-x", "-D{0}".format(display_idx), str(capture_path)],
                    capture_path,
                )
                if ok:
                    break
        if not ok:
            raise RuntimeError(
                "external capture failed for {0}: {1}".format(ready_path.stem, proc.stderr.strip())
            )
        done_path.write_text(str(capture_path) + "\n")


def _run_probe(bundle_dir, label, marker_path, env_updates, args, timeout, external_capture_dir=None):
    wrapper = bundle_dir / "Contents" / "MacOS" / "pf-arm64"
    runtime_dir = bundle_dir / "Contents" / "Resources" / "permafrost"
    env_file = Path("/tmp/{0}.env".format(_bundle_identifier(bundle_dir)))
    if not wrapper.exists():
        raise RuntimeError("missing packaged engine executable: {0}".format(wrapper))
    if not runtime_dir.exists():
        raise RuntimeError("missing editor runtime: {0}".format(runtime_dir))

    output_dir = marker_path.parent
    stdout_path = output_dir / "{0}.stdout.log".format(label)
    app_log_path = output_dir / "{0}.app.log".format(label)
    env = os.environ.copy()
    env.update(env_updates)
    env["PF_EDITOR_APP_LOG"] = str(app_log_path)
    env["PF_EDITOR_APP_ENV_FILE"] = str(env_file)
    _write_env_file(env_file, env_updates | {
        "PF_EDITOR_APP_ENV_FILE": str(env_file),
        "PF_EDITOR_APP_LOG": str(app_log_path),
    })

    start = time.monotonic()
    try:
        proc = subprocess.run(
            [
                "/usr/bin/open",
                "-n",
                str(bundle_dir),
                "--args",
            ] + list(args),
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            timeout=10,
        )
    except subprocess.TimeoutExpired:
        subprocess.run(["/usr/bin/killall", "-9", "pf-arm64"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        raise
    if proc.returncode != 0:
        try:
            env_file.unlink()
        except OSError:
            pass
        raise RuntimeError("{0} open failed {1}\nstdout:\n{2}".format(label, proc.returncode, proc.stdout))

    seen_process = False
    while time.monotonic() - start < timeout:
        _service_external_captures(external_capture_dir)
        if marker_path.exists():
            break
        pgrep = subprocess.run(
            ["/usr/bin/pgrep", "-f", "pf-arm64-bin .*pf_editor_app.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            universal_newlines=True,
        )
        if pgrep.returncode == 0:
            seen_process = True
        elif seen_process:
            break
        time.sleep(0.25)
    else:
        subprocess.run(["/usr/bin/killall", "-9", "pf-arm64"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    try:
        env_file.unlink()
    except OSError:
        pass
    elapsed = time.monotonic() - start
    stdout_path.write_text(proc.stdout)
    if proc.returncode != 0:
        raise RuntimeError(
            "{0} probe exited {1}\nstdout:\n{2}\napp log:\n{3}".format(
                label,
                proc.returncode,
                _tail(stdout_path),
                _tail(app_log_path),
            )
        )
    if not marker_path.exists():
        raise RuntimeError(
            "{0} probe did not write marker {1}\nstdout:\n{2}\napp log:\n{3}".format(
                label,
                marker_path,
                _tail(stdout_path),
                _tail(app_log_path),
            )
        )
    marker = marker_path.read_text().strip()
    print("PACKAGED_EDITOR_QA_STEP {0} elapsed={1:.2f}s marker={2}".format(label, elapsed, marker))
    return marker


def _expect_backend(marker, expected):
    if "backend={0}".format(expected) not in marker:
        raise RuntimeError("expected backend={0} in marker: {1}".format(expected, marker))


def _parse_workflow_marker(marker):
    match = re.search(
        r"saved_map=(?P<map>.+?) saved_scene=(?P<scene>.+?) "
        r"placed_objects=(?P<placed>\d+) saved_objects=(?P<saved>\d+)",
        marker,
    )
    if not match:
        raise RuntimeError("could not parse workflow marker: {0}".format(marker))
    placed = int(match.group("placed"))
    saved = int(match.group("saved"))
    if placed < 2 or saved < placed:
        raise RuntimeError("unexpected workflow object counts: {0}".format(marker))
    return Path(match.group("map")), Path(match.group("scene")), placed


def _check_pngs(paths):
    cmd = [sys.executable, str(ROOT / "scripts/macos/check_png_nonblank.py")] + [str(p) for p in paths]
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        timeout=20,
    )
    print(proc.stdout.rstrip())
    if proc.returncode != 0:
        raise RuntimeError("PNG nonblank check failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle-dir", required=True)
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--expect-backend", default="METAL")
    parser.add_argument("--timeout", type=float, default=45.0)
    args = parser.parse_args()

    bundle_dir = Path(args.bundle_dir).resolve()
    runtime_dir = bundle_dir / "Contents" / "Resources" / "permafrost"
    output_dir = Path(args.output_dir or (ROOT / "visual_parity_captures/2026-05-01-packaged-editor-editing-qa")).resolve()
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True)
    runtime_qa_dir = runtime_dir / "qa-output"
    if runtime_qa_dir.exists():
        shutil.rmtree(runtime_qa_dir)
    runtime_qa_dir.mkdir(parents=True)

    feature_marker = output_dir / "feature.marker"
    feature = _run_probe(
        bundle_dir,
        "feature",
        feature_marker,
        {
            "PF_EDITOR_FEATURE_PROBE": "1",
            "PF_EDITOR_FEATURE_PROBE_AUTOQUIT": "1",
            "PF_EDITOR_FEATURE_PROBE_PATH": str(feature_marker),
            "PF_EDITOR_FEATURE_PROBE_TRACE_PATH": str(output_dir / "feature.trace"),
            "PF_EDITOR_FEATURE_PROBE_QUIT_AFTER": "110",
        },
        (),
        args.timeout,
    )
    _expect_backend(feature, args.expect_backend)

    workflow_output_arg = "qa-output/workflow"
    workflow_dir = runtime_dir / workflow_output_arg
    workflow_dir.mkdir(parents=True)
    workflow_marker = output_dir / "workflow.marker"
    workflow = _run_probe(
        bundle_dir,
        "workflow",
        workflow_marker,
        {
            "PF_EDITOR_WORKFLOW_PROBE": "1",
            "PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT": "1",
            "PF_EDITOR_WORKFLOW_PROBE_PATH": str(workflow_marker),
            "PF_EDITOR_WORKFLOW_PROBE_TRACE_PATH": str(output_dir / "workflow.trace"),
            "PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR": workflow_output_arg,
            "PF_EDITOR_WORKFLOW_PROBE_QUIT_AFTER": "45",
        },
        (),
        args.timeout,
    )
    _expect_backend(workflow, args.expect_backend)
    map_path, scene_path, placed_objects = _parse_workflow_marker(workflow)
    map_file = map_path if map_path.is_absolute() else runtime_dir / map_path
    scene_file = scene_path if scene_path.is_absolute() else runtime_dir / scene_path
    if not map_file.exists() or not scene_file.exists():
        raise RuntimeError("workflow did not create saved map/scene")

    reload_marker = output_dir / "reload.marker"
    reload = _run_probe(
        bundle_dir,
        "reload",
        reload_marker,
        {
            "PF_EDITOR_WORKFLOW_PROBE": "1",
            "PF_EDITOR_WORKFLOW_PROBE_RELOAD_ONLY": "1",
            "PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT": "1",
            "PF_EDITOR_WORKFLOW_PROBE_EXPECT_OBJECTS": str(placed_objects),
            "PF_EDITOR_WORKFLOW_PROBE_PATH": str(reload_marker),
            "PF_EDITOR_WORKFLOW_PROBE_TRACE_PATH": str(output_dir / "reload.trace"),
            "PF_EDITOR_WORKFLOW_PROBE_QUIT_AFTER": "12",
        },
        (str(map_path), str(scene_path)),
        args.timeout,
    )
    _expect_backend(reload, args.expect_backend)

    visual_dir = output_dir / "visual"
    visual_dir.mkdir(parents=True)
    visual_save_arg = "qa-output/visual-save"
    (runtime_dir / visual_save_arg).mkdir(parents=True)
    visual_marker = output_dir / "visual.marker"
    visual = _run_probe(
        bundle_dir,
        "visual",
        visual_marker,
        {
            "PF_EDITOR_VISUAL_PROBE": "1",
            "PF_EDITOR_VISUAL_PROBE_AUTOQUIT": "1",
            "PF_EDITOR_VISUAL_PROBE_PATH": str(visual_marker),
            "PF_EDITOR_VISUAL_PROBE_TRACE_PATH": str(output_dir / "visual.trace"),
            "PF_EDITOR_VISUAL_PROBE_OUTPUT_DIR": visual_save_arg,
            "PF_EDITOR_VISUAL_PROBE_EXTERNAL_CAPTURE_DIR": str(visual_dir),
            "PF_EDITOR_VISUAL_PROBE_QUIT_AFTER": "1200",
        },
        (),
        max(args.timeout, 120.0),
        external_capture_dir=visual_dir,
    )
    _expect_backend(visual, args.expect_backend)
    if "captures=2" not in visual:
        raise RuntimeError("visual probe did not complete both editor captures: {0}".format(visual))
    terrain_png = visual_dir / "editor_terrain.png"
    objects_png = visual_dir / "editor_objects.png"
    _check_pngs((terrain_png, objects_png))

    print(
        "PACKAGED_EDITOR_QA_PASS bundle={0} output_dir={1} backend={2} "
        "feature=1 workflow=1 reload=1 visual=1".format(
            bundle_dir,
            output_dir,
            args.expect_backend,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
