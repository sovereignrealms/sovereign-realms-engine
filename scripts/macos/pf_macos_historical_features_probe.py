import json
import os
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

from editor import map as editor_map
from editor import scene as editor_scene
from common.views import perf_stats_window
import rts.main as demo_main


PROBE_PATH = "/tmp/pf_macos_historical_features_probe.txt"
ERROR_PATH = "/tmp/pf_macos_historical_features_probe_error.txt"
DEFAULT_OUTPUT_DIR = "qa-output/historical-features-probe"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "output_dir": None,
    "expected_backend": None,
    "summary": {},
}


def _arg_value(name, default=None):
    if name not in sys.argv:
        return default
    idx = sys.argv.index(name)
    if idx + 1 >= len(sys.argv):
        return default
    return sys.argv[idx + 1]


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _summary_path():
    backend = pf.get_render_info().get("backend", "unknown").lower()
    return os.path.join(STATE["output_dir"], "summary_historical_features_{0}.json".format(backend))


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    print("HISTORICAL_FEATURES_PHASE {0}".format(name))
    sys.stdout.flush()


def _fail(reason):
    STATE["summary"]["status"] = "fail"
    STATE["summary"]["failure"] = str(reason)
    try:
        with open(_summary_path(), "w") as outfile:
            json.dump(STATE["summary"], outfile, indent=2, sort_keys=True)
            outfile.write("\n")
    except Exception:
        pass
    _write(ERROR_PATH, str(reason))
    print("HISTORICAL_FEATURES_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _source_text(relpath):
    with open(os.path.join(pf.get_basedir(), relpath), "r", errors="replace") as infile:
        return infile.read()


def _check(name, fn):
    try:
        value = fn()
        if isinstance(value, dict):
            value.setdefault("ok", True)
            return value
        return {"ok": True, "value": value}
    except Exception as exc:
        return {
            "ok": False,
            "error_type": exc.__class__.__name__,
            "error": str(exc),
        }


def _audit_map_ascii():
    probe_map = editor_map.Map(1, 1)
    tile = probe_map.chunks[0][0].tiles[0][0]
    tile.base_height = 2
    tile.top_mat_idx = 3
    tile.sides_mat_idx = 1
    tile.blend_mode = pf.BLEND_MODE_NOBLEND
    tile.blend_normals = 0

    map_text = probe_map.pfmap_str()
    parsed = editor_map.Map.from_string(map_text)
    if parsed is None:
        raise RuntimeError("editor Map.from_string returned None")

    parsed_tile = parsed.chunks[0][0].tiles[0][0]
    if parsed_tile.base_height != 2 or parsed_tile.top_mat_idx != 3:
        raise RuntimeError("editor map parser did not preserve probe tile")

    map_path = os.path.join(STATE["output_dir"], "historical_probe.pfmap")
    with open(map_path, "w") as outfile:
        outfile.write(map_text)

    pf.load_map_string(map_text, update_navgrid=False)
    return {
        "ok": True,
        "path": map_path,
        "bytes": len(map_text.encode("utf-8")),
        "chunk_rows": parsed.chunk_rows,
        "chunk_cols": parsed.chunk_cols,
        "materials": len(parsed.materials),
        "engine_load_map_string": True,
    }


def _audit_scene_ascii():
    scene_text = editor_scene.dumps_scene_from_objects([])
    scene_path = os.path.join(STATE["output_dir"], "historical_empty_scene.pfscene")
    with open(scene_path, "w") as outfile:
        outfile.write(scene_text)

    ents, regs, cams = pf.load_scene(scene_path, update_navgrid=False, absolute=True)
    return {
        "ok": True,
        "path": scene_path,
        "bytes": len(scene_text.encode("utf-8")),
        "entities_loaded": len(ents),
        "regions_loaded": len(regs),
        "cameras_loaded": len(cams),
    }


def _parse_header_value(line):
    parts = line.split()
    if len(parts) < 2:
        return None
    try:
        return int(parts[1])
    except ValueError:
        return None


def _parse_pfobj(relpath):
    path = os.path.join(pf.get_basedir(), relpath)
    counts = {
        "v": 0,
        "vt": 0,
        "vn": 0,
        "vw": 0,
        "vm": 0,
        "material": 0,
        "as": 0,
    }
    header = {}
    weight_sums = []

    with open(path, "r", errors="replace") as infile:
        for line in infile:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("num_verts"):
                header["num_verts"] = _parse_header_value(stripped)
            elif stripped.startswith("num_joints"):
                header["num_joints"] = _parse_header_value(stripped)
            elif stripped.startswith("num_materials"):
                header["num_materials"] = _parse_header_value(stripped)
            elif stripped.startswith("num_as"):
                header["num_as"] = _parse_header_value(stripped)
            elif stripped.startswith("v "):
                counts["v"] += 1
            elif stripped.startswith("vt "):
                counts["vt"] += 1
            elif stripped.startswith("vn "):
                counts["vn"] += 1
            elif stripped.startswith("vw"):
                counts["vw"] += 1
                weights = []
                for token in stripped.split()[1:]:
                    if "/" in token:
                        try:
                            weights.append(float(token.split("/", 1)[1]))
                        except ValueError:
                            pass
                if weights:
                    weight_sums.append(sum(weights))
            elif stripped.startswith("vm "):
                counts["vm"] += 1
            elif stripped.startswith("material "):
                counts["material"] += 1
            elif stripped.startswith("as "):
                counts["as"] += 1

    expected_verts = header.get("num_verts")
    if expected_verts is None:
        raise RuntimeError("{0} has no num_verts header".format(relpath))
    for key in ("v", "vt", "vn", "vw", "vm"):
        if counts[key] != expected_verts:
            raise RuntimeError("{0} {1} count {2} != num_verts {3}".format(
                relpath, key, counts[key], expected_verts))
    if counts["material"] != header.get("num_materials"):
        raise RuntimeError("{0} material count mismatch".format(relpath))
    if counts["as"] != header.get("num_as"):
        raise RuntimeError("{0} animation set count mismatch".format(relpath))

    return {
        "path": relpath,
        "header": header,
        "counts": counts,
        "weight_sum_min": min(weight_sums) if weight_sums else None,
        "weight_sum_max": max(weight_sums) if weight_sums else None,
    }


def _audit_pfobj_ascii():
    assets = (
        "assets/models/well/well.pfobj",
        "assets/models/knight/knight.pfobj",
    )
    return {
        "ok": True,
        "assets": [_parse_pfobj(path) for path in assets],
    }


def _audit_blender_exporter_syntax():
    exporter = os.path.join(pf.get_basedir(), "scripts", "io_scene_pfobj", "export_pfobj.py")
    with open(exporter, "r", errors="replace") as infile:
        compile(infile.read(), exporter, "exec")
    return {
        "ok": True,
        "path": "scripts/io_scene_pfobj/export_pfobj.py",
        "py_compile": True,
        "runtime_note": "Blender bpy integration is source/syntax checked here; Blender-driven export is not run by this engine probe.",
    }


def _audit_wang_quilt_source():
    texture_source = _source_text("src/render/gl_texture.c")
    quilt_source = _source_text("src/render/gl_image_quilt.c")
    terrain_source = _source_text("src/render/gl_terrain.c")

    checks = {
        "apple_silicon_fallback": "#if defined(__APPLE__) && defined(__aarch64__)" in texture_source,
        "fallback_uploads_8_wang_slices": "for(int j = 0; j < 8; j++)" in texture_source,
        "full_image_quilt_function_present": "R_GL_ImageQuilt_MakeTileset" in quilt_source,
        "terrain_uses_wang_tileset_array": "R_GL_Texture_ArrayMakeMapWangTileset" in terrain_source,
    }
    missing = [name for name, ok in checks.items() if not ok]
    if missing:
        raise RuntimeError("missing Wang/quilt source markers: {0}".format(", ".join(missing)))

    return {
        "ok": True,
        "checks": checks,
        "runtime_note": (
            "Apple Silicon uses the verified fast Wang-slice fallback; the original "
            "image-quilting generator remains present but OpenGL-owned and is not "
            "run during the Metal runtime audit."
        ),
    }


def _audit_perf_hooks():
    samples = []
    for _idx in range(5):
        samples.append(pf.prev_frame_ms())

    perfstats = pf.prev_frame_perfstats()
    memstats = pf.prev_frame_memstats() if hasattr(pf, "prev_frame_memstats") else {}
    navstats = pf.get_nav_perfstats()
    render_source = _source_text("src/render/gl_render.c")

    window = perf_stats_window.PerfStatsWindow()
    del window

    return {
        "ok": True,
        "frame_ms_samples": samples,
        "perf_threads": sorted(perfstats.keys()),
        "perfstats_has_children": any(bool(v.get("children")) for v in perfstats.values()),
        "memstats_keys": sorted(memstats.keys()),
        "navstats_keys": sorted(navstats.keys()),
        "perf_window_constructed": True,
        "metal_gpu_timestamp_note": (
            "R_Cmd_TimestampForCookie is guarded for PF_RENDER_BACKEND_METAL; "
            "do not enable trace_gpu as a parity requirement until a native "
            "Metal timestamp implementation exists."
        ),
        "metal_timestamp_guard_present": "PF_RENDER_BACKEND_METAL" in render_source and "*out = 0" in render_source,
    }


def _request_session_export():
    backend = pf.get_render_info().get("backend")
    if STATE["expected_backend"] and backend != STATE["expected_backend"]:
        _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))

    summary = {
        "status": "running",
        "backend": pf.get_render_info(),
        "python": {
            "version": sys.version,
            "major": sys.version_info[0],
            "minor": sys.version_info[1],
        },
        "checks": {},
    }
    STATE["summary"] = summary

    save_path = os.path.join(STATE["output_dir"], "historical_features_session_export.pfsave")
    summary["session_export"] = {
        "path": save_path,
        "requested": True,
    }
    pf.save_session(save_path)
    _set_phase("wait_save")


def _run_post_save_checks():
    checks = STATE["summary"]["checks"]
    checks["pfmap_ascii_roundtrip"] = _check("pfmap_ascii_roundtrip", _audit_map_ascii)
    checks["pfscene_ascii_roundtrip"] = _check("pfscene_ascii_roundtrip", _audit_scene_ascii)
    checks["pfobj_ascii_assets"] = _check("pfobj_ascii_assets", _audit_pfobj_ascii)
    checks["blender_pfobj_exporter_syntax"] = _check("blender_pfobj_exporter_syntax", _audit_blender_exporter_syntax)
    checks["wang_quilt_source_and_fallback"] = _check("wang_quilt_source_and_fallback", _audit_wang_quilt_source)
    checks["perf_stats_hooks"] = _check("perf_stats_hooks", _audit_perf_hooks)

    failed = [name for name, result in checks.items() if not result.get("ok")]
    if failed:
        _fail("historical feature checks failed: {0}".format(", ".join(failed)))


def _write_summary(status):
    STATE["summary"]["status"] = status
    with open(_summary_path(), "w") as outfile:
        json.dump(STATE["summary"], outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    marker = "HISTORICAL_FEATURES_READY backend={0} status={1}".format(
        pf.get_render_info().get("backend"),
        status,
    )
    _write(PROBE_PATH, marker)
    print(marker)
    print("HISTORICAL_FEATURES_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _on_session_saved(user, event):
    del user
    del event
    if STATE["phase"] != "wait_save":
        return

    save_info = STATE["summary"].setdefault("session_export", {})
    save_path = save_info.get("path")
    save_info["saved"] = bool(save_path and os.path.exists(save_path))
    save_info["bytes"] = os.path.getsize(save_path) if save_info["saved"] else 0
    if not save_info["saved"] or save_info["bytes"] <= 0:
        _fail("session export did not produce a non-empty save file")

    _run_post_save_checks()
    _write_summary("pass")
    os._exit(0)


def _on_session_save_fail(user, event):
    del user
    _fail("session export failed: {0}".format(event))


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init" and STATE["ticks"] >= 30:
        _request_session_export()
        return

    if STATE["phase"] == "wait_save" and time.monotonic() - STATE["phase_started_at"] > 15.0:
        _fail("timed out waiting for session export")


def main():
    output_dir = _arg_value("--output-dir", os.environ.get("PF_HISTORICAL_FEATURES_OUTPUT_DIR", DEFAULT_OUTPUT_DIR))
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = _arg_value(
        "--expect-backend",
        os.environ.get("PF_HISTORICAL_FEATURES_EXPECT_BACKEND", "METAL"),
    )

    for path in (PROBE_PATH, ERROR_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass

    _set_phase("init")
    demo_main.main()
    pf.register_ui_event_handler(pf.EVENT_UPDATE_START, on_update, None)
    pf.register_ui_event_handler(pf.EVENT_SESSION_SAVED, _on_session_saved, None)
    pf.register_ui_event_handler(pf.EVENT_SESSION_FAIL_SAVE, _on_session_save_fail, None)


main()
