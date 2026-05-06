import argparse
import json
import os
import sys
import time

import pf

sys.path.insert(0, pf.get_basedir() + "/scripts")

import sovereign.globals as sovereign_globals
from sovereign.data.buildings import BUILDINGS
from sovereign.data.units import UNITS
from sovereign.entities.runtime import create_entity, place_entity
from sovereign.scenario import build_runtime_scene, load_scenario, scenario_summary
from sovereign.systems.skirmish import ScriptedSkirmishAI


PROBE_PATH = "/tmp/pf_sovereign_ai_decision_probe.txt"
ERROR_PATH = "/tmp/pf_sovereign_ai_decision_probe_error.txt"

STATE = {
    "phase": "init",
    "ticks": 0,
    "output_dir": None,
    "expected_backend": None,
    "phase_started_at": None,
    "phase_log": [],
    "checks": {
        "runtime_scene": False,
        "resource_shortfall_decision": False,
        "population_block_decision": False,
        "population_recovery": False,
        "training_decision": False,
        "trained_units": False,
        "attack_ready_decision": False,
        "attack_order": False,
        "decision_log": False,
    },
    "runtime": {},
    "decisions": [],
    "entities": {},
    "ai": {},
}


def _parse_args():
    parser = argparse.ArgumentParser(description="Run the Sovereign skirmish AI decision-depth probe.")
    parser.add_argument("--output-dir", default="qa-output/sovereign-ai-decision-depth")
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
    print("SOVEREIGN_AI_DECISION_PHASE {0}".format(name))
    sys.stdout.flush()


def _summary_path():
    return os.path.join(STATE["output_dir"], "summary_sovereign_ai_decision.json")


def _ent_xz(ent):
    pos = ent.pos
    return (pos[0], pos[2])


def _snapshot_entity(ent):
    payload = {
        "name": getattr(ent, "name", None),
        "position": _ent_xz(ent),
        "faction_id": getattr(ent, "faction_id", None),
    }
    try:
        payload["hp"] = int(ent.hp)
    except (AttributeError, RuntimeError):
        payload["hp"] = None
    try:
        payload["anim"] = ent.get_anim()
    except (AttributeError, RuntimeError):
        payload["anim"] = None
    return payload


def _write_summary(status, reason=None):
    payload = {
        "status": status,
        "reason": reason,
        "backend": pf.get_render_info(),
        "expected_backend": STATE["expected_backend"],
        "phase_log": STATE["phase_log"],
        "checks": STATE["checks"],
        "runtime": STATE["runtime"],
        "decisions": STATE["decisions"],
        "ai": STATE["ai"],
        "entities": {
            key: _snapshot_entity(ent)
            for key, ent in STATE["entities"].items()
        },
    }
    with open(_summary_path(), "w") as outfile:
        json.dump(payload, outfile, indent=2, sort_keys=True)
        outfile.write("\n")
    print("SOVEREIGN_AI_DECISION_SUMMARY {0}".format(_summary_path()))
    sys.stdout.flush()


def _fail(reason):
    _write_summary("fail", reason)
    _write(ERROR_PATH, str(reason))
    print("SOVEREIGN_AI_DECISION_FAIL {0}".format(reason))
    sys.stdout.flush()
    os._exit(1)


def _succeed():
    marker = (
        "SOVEREIGN_AI_DECISION_PROBE_PASS resource={resource} pop={pop} "
        "train={train} attack={attack} decisions={decisions}"
    ).format(
        resource=int(STATE["checks"]["resource_shortfall_decision"]),
        pop=int(STATE["checks"]["population_block_decision"]),
        train=int(STATE["checks"]["trained_units"]),
        attack=int(STATE["checks"]["attack_ready_decision"]),
        decisions=len(STATE["decisions"]),
    )
    _write_summary("pass")
    _write(PROBE_PATH, marker)
    print(marker)
    sys.stdout.flush()
    os._exit(0)


def _building_entry(building_id, name):
    return {
        "kind": "building",
        "id": building_id,
        "name": name,
        "definition": BUILDINGS[building_id],
    }


def _spawned_entity(result, kind, entity_id):
    for entry, ent in zip(result["plan"]["entities"], result["entities"]):
        if entry["kind"] == kind and entry["id"] == entity_id:
            return ent
    return None


def _setup_render_state(scenario):
    pf.set_ambient_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_color((1.0, 1.0, 1.0))
    pf.set_emit_light_pos((1664.0, 1024.0, 384.0))
    pf.set_skybox("assets/skyboxes/clouds_blue", "jpg")
    pf.enable_unit_selection()
    pf.disable_fog_of_war()
    pf.set_minimap_render_all_ents(False)
    center = tuple(scenario["players"][1]["start"])
    camera = pf.Camera(
        name="sovereign_ai_decision_camera",
        mode=pf.CAM_MODE_FREE,
        position=(center[0], 128.0, center[1] + 12.0),
        pitch=-60.0,
        yaw=135.0,
    )
    pf.set_active_camera(camera)
    camera.center_over_location(center)
    sovereign_globals.scene_regions = [
        pf.Region(
            type=pf.REGION_RECTANGLE,
            name="sovereign_ai_decision_region",
            position=center,
            dimensions=(96.0, 80.0),
        )
    ]
    sovereign_globals.scene_cameras = [camera]


def _complete_house_for_ai(ai, point):
    ent = create_entity(_building_entry("house", "ai_decision_house"))
    place_entity(
        ent,
        point,
        faction_id=ai.faction_id,
        radius=BUILDINGS["house"].get("selection_radius", 2.5),
        scale=BUILDINGS["house"].get("scale"),
    )
    ent.mark()
    ent.found(force=True)
    ent.supply()
    ent.complete()
    ai.queue.scene_objs.append(ent)
    ai.player_state.add_building("house", ent)
    STATE["entities"]["ai_house"] = ent
    return ent


def _run_decision_sequence():
    scenario = load_scenario(os.path.join(pf.get_basedir(), "assets/sovereign/scenarios/two_player_skirmish.json"))
    scene_objs = []
    runtime = build_runtime_scene(scenario, scene_objs=scene_objs)
    _setup_render_state(scenario)

    enemy_record = runtime["players"][2]
    enemy_state = enemy_record["state"]
    enemy_barracks = _spawned_entity(enemy_record["spawn_result"], "building", "barracks")
    if enemy_barracks is None:
        _fail("enemy barracks was not spawned")
    enemy_barracks.rally_point = (128.0, 88.0)
    ai = ScriptedSkirmishAI(enemy_state, enemy_barracks, 2, scene_objs, map_seed=runtime["map_seed"])

    enemy_state.resources["food"] = 0
    enemy_state.resources["gold"] = 0
    shortfall = ai.choose_next_action("militia", min_attack_units=2)
    STATE["decisions"].append(shortfall)
    STATE["checks"]["resource_shortfall_decision"] = shortfall["action"] == "gather_resources"

    ai.seed_opening_resources({"food": 180, "wood": 300, "gold": 90, "stone": 100})
    enemy_state.population_used = enemy_state.population_cap
    pop_block = ai.choose_next_action("militia", min_attack_units=2)
    STATE["decisions"].append(pop_block)
    STATE["checks"]["population_block_decision"] = pop_block["action"] == "build_house"

    _complete_house_for_ai(ai, (138.0, 82.0))
    STATE["checks"]["population_recovery"] = enemy_state.population_cap > enemy_state.population_used

    first, train_decision = ai.train_from_decision("militia", min_attack_units=2)
    STATE["decisions"].append(train_decision)
    if first is not None:
        first.name = "ai_decision_wave_1"
        first.face_towards((108.0, first.pos[1], 90.0))
        STATE["entities"]["wave_one"] = first
    second, second_train_decision = ai.train_from_decision("militia", min_attack_units=2)
    STATE["decisions"].append(second_train_decision)
    if second is not None:
        second.name = "ai_decision_wave_2"
        second.face_towards((108.0, second.pos[1], 90.0))
        STATE["entities"]["wave_two"] = second

    STATE["checks"]["training_decision"] = train_decision["action"] == "train"
    STATE["checks"]["trained_units"] = first is not None and second is not None and ai.unit_count("militia") >= 2

    attack = ai.choose_next_action("militia", min_attack_units=2)
    STATE["decisions"].append(attack)
    STATE["checks"]["attack_ready_decision"] = attack["action"] == "attack"

    if first is not None and second is not None:
        first.move((110.0, 90.0))
        second.move((112.0, 92.0))
        pf.set_unit_selection([first, second])
        STATE["checks"]["attack_order"] = True

    STATE["runtime"] = scenario_summary(runtime)
    STATE["runtime"]["scene_obj_count_after_ai"] = len(scene_objs)
    STATE["ai"] = ai.snapshot()
    STATE["entities"]["enemy_barracks"] = enemy_barracks
    STATE["checks"]["runtime_scene"] = len(scene_objs) >= 29 and len(runtime["players"]) == 2
    STATE["checks"]["decision_log"] = len(ai.decision_log) >= 6


def on_update(user, event):
    del user
    del event
    STATE["ticks"] += 1

    if STATE["phase"] == "init":
        backend = pf.get_render_info().get("backend")
        if STATE["expected_backend"] and backend != STATE["expected_backend"]:
            _fail("expected {0} backend, got {1}".format(STATE["expected_backend"], backend))
        _run_decision_sequence()
        _set_phase("settle")
        return

    if STATE["phase"] == "settle":
        if STATE["ticks"] >= 10:
            if all(STATE["checks"].values()):
                _succeed()
                return
            _fail("AI decision checks did not all pass: {0}".format(STATE["checks"]))


def main():
    args = _parse_args()
    if not os.path.isdir(args.output_dir):
        os.makedirs(args.output_dir)
    STATE["output_dir"] = args.output_dir
    STATE["expected_backend"] = args.expect_backend
    for path in (PROBE_PATH, ERROR_PATH):
        try:
            os.unlink(path)
        except OSError:
            pass
    pf.register_event_handler(pf.EVENT_UPDATE_START, on_update, None)


main()
