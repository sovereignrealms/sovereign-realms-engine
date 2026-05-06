import argparse
import json
import os
import sys

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import sovereign.globals as sovereign_globals
from sovereign.factory import build_minimal_spawn_plan, spawn_minimal_test_scene, validate_registries


def _parse_args():
    parser = argparse.ArgumentParser(description="Spawn the minimal Sovereign data-driven test scene.")
    parser.add_argument("--output-dir", default=None)
    parser.add_argument("--expect-backend", default=None)
    return parser.parse_args()


def _ensure_factions():
    if len(pf.get_factions_list()) == 0:
        pf.add_faction("Neutral", (160, 160, 160, 255))
        pf.add_faction("Sovereign", (40, 90, 255, 255))
        pf.add_faction("Opponent", (220, 50, 50, 255))


def _write_summary(output_dir, payload):
    if not output_dir:
        return
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    path = os.path.join(output_dir, "summary_sovereign_factory.json")
    with open(path, "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_FACTORY_PROBE_SUMMARY {0}".format(path))


def _setup_scene():
    pf.load_map("assets/maps", "plain.pfmap")
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    _ensure_factions()

    center = (64.0, 64.0)
    camera = pf.Camera(
        name="sovereign_factory_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 220.0, center[1]),
        pitch=-65.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)

    sovereign_globals.scene_objs = []
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_factory_region",
            position=center,
            dimensions=(72.0, 72.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]
    return center


def main():
    args = _parse_args()
    backend = pf.get_render_info().get("backend")
    if args.expect_backend and backend != args.expect_backend:
        raise RuntimeError("expected {0} backend, got {1}".format(args.expect_backend, backend))

    errors = validate_registries()
    if errors:
        raise RuntimeError("registry validation failed: " + "; ".join(errors))

    center = _setup_scene()
    result = spawn_minimal_test_scene(center=center, faction_id=1, scene_objs=sovereign_globals.scene_objs)
    plan = build_minimal_spawn_plan()
    counts = {}
    for entry in plan["entities"]:
        counts[entry["kind"]] = counts.get(entry["kind"], 0) + 1

    payload = {
        "status": "pass",
        "backend": pf.get_render_info(),
        "registry_errors": errors,
        "entity_count": len(result["entities"]),
        "counts": counts,
        "civilization_id": plan["civilization_id"],
        "entity_names": [getattr(ent, "name", "entity") for ent in result["entities"]],
    }
    _write_summary(args.output_dir, payload)

    marker = (
        "SOVEREIGN_FACTORY_PROBE_PASS backend={backend} entities={entities} "
        "units={units} buildings={buildings} resources={resources}"
    ).format(
        backend=backend,
        entities=len(result["entities"]),
        units=counts.get("unit", 0),
        buildings=counts.get("building", 0),
        resources=counts.get("resource", 0),
    )
    print(marker)
    sys.stdout.flush()
    os._exit(0)


main()
