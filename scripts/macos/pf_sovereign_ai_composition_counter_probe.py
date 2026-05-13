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
from sovereign.factory import validate_registries
from sovereign.systems.combat_rules import composition_duel, damage_breakdown
from sovereign.systems.skirmish import ai_composition_plan


PROBE_PATH = "/tmp/pf_sovereign_ai_composition_counter_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_composition_counter_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "phase_started_at": None,
    "phase_log": [],
    "output_dir": None,
    "expected_backend": None,
    "checks": {
        "runtime_scene": False,
        "plan_alignment": False,
        "damage_rules": False,
        "counter_matrix": False,
        "expected_wins": False,
        "expected_losses": False,
    },
    "cases": {},
    "runtime": {},
}


COUNTER_CASES = (
    {
        "case_id": "standard_favorable",
        "profile_id": "standard",
        "enemy_id": "archer_raiders",
        "defender_counts": {"archer": 2},
        "expected_winner": "attackers",
    },
    {
        "case_id": "standard_unfavorable",
        "profile_id": "standard",
        "enemy_id": "mass_archers",
        "defender_counts": {"archer": 5},
        "expected_winner": "defenders",
    },
    {
        "case_id": "booming_favorable",
        "profile_id": "booming",
        "enemy_id": "infantry_pair",
        "defender_counts": {"militia": 2},
        "expected_winner": "attackers",
    },
    {
        "case_id": "booming_unfavorable",
        "profile_id": "booming",
        "enemy_id": "infantry_mass",
        "defender_counts": {"militia": 4},
        "expected_winner": "defenders",
    },
    {
        "case_id": "hard_favorable",
        "profile_id": "hard",
        "enemy_id": "infantry_pair",
        "defender_counts": {"militia": 2},
        "expected_winner": "attackers",
    },
    {
        "case_id": "hard_unfavorable",
        "profile_id": "hard",
        "enemy_id": "infantry_mass",
        "defender_counts": {"militia": 5},
        "expected_winner": "defenders",
    },
)


def _parse_args():
    parser = argparse.ArgumentParser(description="Run Sovereign AI composition-counter checks.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-composition-counter")
    parser.add_argument("--expect-backend", default="METAL")
    return parser.parse_args()


def _write(path, payload):
    with open(path, "w") as outfile:
        outfile.write(payload + "\n")


def _set_phase(name):
    STATE["phase"] = name
    STATE["ticks"] = 0
    STATE["phase_started_at"] = time.monotonic()
    STATE["phase_log"].append(name)
    print("SOVEREIGN_AI_COMPOSITION_COUNTER_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_composition_counter.json")


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "runtime": STATE["runtime"],
        "cases": STATE["cases"],
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_AI_COMPOSITION_COUNTER_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_COMPOSITION_COUNTER_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_COMPOSITION_COUNTER_PROBE_PASS runtime={runtime} "
        "plan={plan} matrix={matrix} wins={wins} losses={losses} damage={damage} cases={cases}"
    ).format(
        runtime=int(STATE["checks"]["runtime_scene"]),
        plan=int(STATE["checks"]["plan_alignment"]),
        matrix=int(STATE["checks"]["counter_matrix"]),
        wins=int(STATE["checks"]["expected_wins"]),
        losses=int(STATE["checks"]["expected_losses"]),
        damage=int(STATE["checks"]["damage_rules"]),
        cases=len(STATE["cases"]),
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _ensure_factions():
    if len(pf.get_factions_list()) == 0:
        pf.add_faction("Neutral", (160, 160, 160, 255))
        pf.add_faction("Sovereign", (40, 90, 255, 255))
        pf.add_faction("Opponent", (220, 50, 50, 255))


def _setup_render_state():
    pf.load_map("assets/maps", "plain.pfmap")
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    _ensure_factions()

    center = (72.0, 76.0)
    camera = pf.Camera(
        name="sovereign_ai_composition_counter_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 120.0, center[1] + 16.0),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_objs = []
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_composition_counter_region",
            position=center,
            dimensions=(120.0, 96.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _unit_entry(unit_id, name):
    return {
        "kind": "unit",
        "id": unit_id,
        "name": name,
        "definition": UNITS[unit_id],
    }


def _spawn_counted_units(counts, origin, faction_id, name_prefix, face_point):
    spawned = []
    slot = 0
    for unit_id in sorted(counts):
        for _idx in range(int(counts[unit_id])):
            row = slot // 4
            col = slot % 4
            point = (origin[0] + col * 3.5, origin[1] + row * 4.0)
            ent = create_entity(_unit_entry(unit_id, "{0}_{1}_{2}".format(name_prefix, unit_id, slot + 1)))
            place_entity(
                ent,
                point,
                faction_id=faction_id,
                radius=UNITS[unit_id].get("selection_radius", 2.5),
                scale=UNITS[unit_id].get("scale"),
            )
            try:
                ent.face_towards((face_point[0], ent.pos[1], face_point[1]))
            except (AttributeError, RuntimeError):
                pass
            sovereign_globals.scene_objs.append(ent)
            spawned.append(ent)
            slot += 1
    return spawned


def _run_case(case, visual_index):
    plan = ai_composition_plan(case["profile_id"])
    attacker_counts = dict(plan["unit_targets"])
    defender_counts = dict(case["defender_counts"])
    result = composition_duel(attacker_counts, defender_counts)
    passed = result["winner"] == case["expected_winner"]

    z = 42.0 + visual_index * 12.0
    attacker_origin = (38.0, z)
    defender_origin = (68.0, z)
    attackers = _spawn_counted_units(
        attacker_counts,
        attacker_origin,
        1,
        case["case_id"] + "_attacker",
        defender_origin,
    )
    defenders = _spawn_counted_units(
        defender_counts,
        defender_origin,
        2,
        case["case_id"] + "_defender",
        attacker_origin,
    )

    return {
        "case_id": case["case_id"],
        "profile_id": case["profile_id"],
        "composition_plan_id": plan["plan_id"],
        "enemy_id": case["enemy_id"],
        "attacker_counts": attacker_counts,
        "defender_counts": defender_counts,
        "expected_winner": case["expected_winner"],
        "actual_winner": result["winner"],
        "passed": passed,
        "rounds_run": result["rounds_run"],
        "attacker_hp": result["attacker_hp"],
        "defender_hp": result["defender_hp"],
        "attacker_remaining": result["attacker_remaining"],
        "defender_remaining": result["defender_remaining"],
        "damage_totals": result["damage_totals"],
        "visual_spawn_count": len(attackers) + len(defenders),
    }


def _run_counter_probe():
    errors = validate_registries()
    if errors:
        _fail("registry errors: {0}".format(errors))
    _setup_render_state()

    total_spawned = 0
    for idx, case in enumerate(COUNTER_CASES):
        record = _run_case(case, idx)
        STATE["cases"][case["case_id"]] = record
        total_spawned += int(record["visual_spawn_count"])

    profile_counts = {
        profile_id: ai_composition_plan(profile_id)["unit_targets"]
        for profile_id in ("standard", "booming", "hard")
    }
    damage = {
        "archer_vs_militia": damage_breakdown("archer", "militia"),
        "militia_vs_archer": damage_breakdown("militia", "archer"),
        "militia_vs_militia": damage_breakdown("militia", "militia"),
    }
    STATE["runtime"] = {
        "visual_spawn_count": total_spawned,
        "scene_obj_count": len(sovereign_globals.scene_objs),
        "profile_counts": profile_counts,
        "damage": damage,
    }
    STATE["checks"]["runtime_scene"] = total_spawned >= 30 and len(sovereign_globals.scene_objs) == total_spawned
    STATE["checks"]["plan_alignment"] = (
        profile_counts["standard"] == {"militia": 3}
        and profile_counts["booming"] == {"militia": 2, "archer": 1}
        and profile_counts["hard"] == {"archer": 3}
    )
    STATE["checks"]["damage_rules"] = (
        damage["archer_vs_militia"]["bonus_damage"] == 1
        and damage["militia_vs_archer"]["bonus_damage"] == 0
        and damage["militia_vs_militia"]["bonus_damage"] == 1
    )
    STATE["checks"]["counter_matrix"] = all(record["passed"] for record in STATE["cases"].values())
    STATE["checks"]["expected_wins"] = all(
        STATE["cases"][case_id]["actual_winner"] == "attackers"
        for case_id in ("standard_favorable", "booming_favorable", "hard_favorable")
    )
    STATE["checks"]["expected_losses"] = all(
        STATE["cases"][case_id]["actual_winner"] == "defenders"
        for case_id in ("standard_unfavorable", "booming_unfavorable", "hard_unfavorable")
    )


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _set_phase("composition_counter")
        _run_counter_probe()
        if all(STATE["checks"].values()):
            _succeed()
            return
        _fail("composition-counter checks did not all pass: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    output_dir = args.output_dir
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(pf.get_basedir(), output_dir)
    if not os.path.isdir(output_dir):
        os.makedirs(output_dir)
    STATE["output_dir"] = output_dir
    STATE["expected_backend"] = args.expect_backend
    STATE["phase_started_at"] = time.monotonic()
    for path in (PROBE_PATH, ERROR_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
