from __future__ import print_function

import base64
import json
import os
import sys

import pf

import sovereign.globals as sovereign_globals
from sovereign.systems.production import ProductionQueue, SovereignPlayerState
from sovereign.systems.technology import ResearchQueue


ENTITY_TAG_PREFIX = "sovereign_entity:"
STATE_TAG_PREFIX = "sovereign_state:"
STATE_CHUNK_PREFIX = "sovereign_state_chunk:"
STATE_CHUNK_SIZE = 64


def _tag_payload(tag, prefix):
    if not tag.startswith(prefix):
        return None
    return tag[len(prefix):]


def _tags(ent):
    try:
        return tuple(ent.tags)
    except AttributeError:
        return ()


def _remove_prefixed_tags(ent, prefix):
    for tag in _tags(ent):
        if tag.startswith(prefix):
            ent.remove_tag(tag)


def tag_entity(ent, kind, entity_id):
    _remove_prefixed_tags(ent, ENTITY_TAG_PREFIX)
    ent.add_tag("{0}{1}:{2}".format(ENTITY_TAG_PREFIX, kind, entity_id))
    return ent


def entity_binding(ent):
    for tag in _tags(ent):
        payload = _tag_payload(tag, ENTITY_TAG_PREFIX)
        if not payload:
            continue
        parts = payload.split(":", 1)
        if len(parts) == 2:
            return {"kind": parts[0], "id": parts[1]}
    return None


def entity_bindings(scene_objs):
    ret = {}
    for ent in scene_objs:
        binding = entity_binding(ent)
        if not binding:
            continue
        key = "{0}:{1}:{2}".format(binding["kind"], binding["id"], getattr(ent, "name", ""))
        ret[key] = ent
    return ret


def _encode_payload(payload):
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_payload(encoded):
    padding = "=" * ((4 - (len(encoded) % 4)) % 4)
    raw = base64.urlsafe_b64decode((encoded + padding).encode("ascii"))
    return json.loads(raw.decode("utf-8"))


def attach_state(ent, payload):
    _remove_prefixed_tags(ent, STATE_TAG_PREFIX)
    _remove_prefixed_tags(ent, STATE_CHUNK_PREFIX)
    encoded = _encode_payload(payload)
    chunks = [
        encoded[idx:idx + STATE_CHUNK_SIZE]
        for idx in range(0, len(encoded), STATE_CHUNK_SIZE)
    ]
    ent.add_tag("{0}chunks:{1}".format(STATE_TAG_PREFIX, len(chunks)))
    for idx, chunk in enumerate(chunks):
        ent.add_tag("{0}{1:03d}:{2}".format(STATE_CHUNK_PREFIX, idx, chunk))
    return ent


def state_from_entity(ent):
    chunk_count = None
    chunks = {}
    for tag in _tags(ent):
        payload = _tag_payload(tag, STATE_TAG_PREFIX)
        if payload and payload.startswith("chunks:"):
            try:
                chunk_count = int(payload.split(":", 1)[1])
            except ValueError:
                return None
            continue
        if payload:
            return _decode_payload(payload)
        chunk_payload = _tag_payload(tag, STATE_CHUNK_PREFIX)
        if chunk_payload:
            parts = chunk_payload.split(":", 1)
            if len(parts) != 2:
                return None
            try:
                chunks[int(parts[0])] = parts[1]
            except ValueError:
                return None
    if chunk_count is not None:
        if len(chunks) != chunk_count:
            return None
        encoded = "".join(chunks[idx] for idx in range(chunk_count))
        return _decode_payload(encoded)
    return None


def find_state_payload(scene_objs):
    for ent in scene_objs:
        payload = state_from_entity(ent)
        if payload is not None:
            return payload, ent
    return None, None


def production_queue_state(queue):
    snapshot = queue.snapshot()
    snapshot["building_position"] = list(snapshot["building_position"])
    snapshot["rally_point"] = list(snapshot["rally_point"])
    return {
        "building_id": queue.building_id,
        "building_name": getattr(queue.building_ent, "name", None),
        "items": [dict(item) for item in queue.items],
        "completed": [
            {
                "item": dict(entry.get("item", {})),
                "entity_name": getattr(entry.get("entity"), "name", None),
            }
            for entry in queue.completed
        ],
        "snapshot": snapshot,
    }


def research_queue_state(queue):
    return {
        "building_id": queue.building_id,
        "building_name": getattr(queue.building_ent, "name", None),
        "items": [dict(item) for item in queue.items],
        "completed": [dict(item) for item in queue.completed],
        "snapshot": queue.snapshot(),
    }


def snapshot_gameplay_state(
    player_state,
    production_queue,
    research_queue,
    combat,
    scene_objs,
    scenario_state=None,
    victory_state=None,
):
    return {
        "version": 1,
        "scenario_state": copy_payload(scenario_state) if scenario_state is not None else None,
        "victory_state": copy_payload(victory_state) if victory_state is not None else None,
        "player": player_state.snapshot(),
        "player_entities": {
            "units": [getattr(record["entity"], "name", None) for record in player_state.units],
            "buildings": [getattr(record["entity"], "name", None) for record in player_state.buildings],
        },
        "production_queue": production_queue_state(production_queue),
        "research_queue": research_queue_state(research_queue),
        "combat": dict(combat),
        "tagged_entities": [
            {
                "name": getattr(ent, "name", None),
                "binding": entity_binding(ent),
                "hp": getattr(ent, "hp", None) if hasattr(ent, "hp") else None,
            }
            for ent in scene_objs
            if entity_binding(ent)
        ],
    }


def copy_payload(payload):
    if payload is None:
        return None
    return json.loads(json.dumps(payload, sort_keys=True))


def _entity_named(scene_objs, name):
    for ent in scene_objs:
        if getattr(ent, "name", None) == name:
            return ent
    return None


def _restore_player_state(payload, scene_objs):
    snapshot = payload["player"]
    player = SovereignPlayerState(
        civilization_id=snapshot["civilization_id"],
        resources=snapshot["resources"],
        current_age=snapshot["current_age"],
        researched_technologies=snapshot["researched_technologies"],
    )
    player.population_used = int(snapshot["population_used"])
    player.population_cap = int(snapshot["population_cap"])
    player_entities = payload.get("player_entities", {})
    for name in player_entities.get("units", []):
        ent = _entity_named(scene_objs, name)
        binding = entity_binding(ent) if ent is not None else None
        if binding and binding["kind"] == "unit":
            player.units.append({"id": binding["id"], "entity": ent})
    for name in player_entities.get("buildings", []):
        ent = _entity_named(scene_objs, name)
        binding = entity_binding(ent) if ent is not None else None
        if binding and binding["kind"] == "building":
            player.buildings.append({"id": binding["id"], "entity": ent})
    return player


def _restore_production_queue(snapshot, player, scene_objs):
    building = _entity_named(scene_objs, snapshot.get("building_name"))
    saved_rally = snapshot.get("snapshot", {}).get("rally_point")
    if building is not None and saved_rally is not None:
        try:
            building.rally_point = (float(saved_rally[0]), float(saved_rally[1]))
        except (TypeError, ValueError, RuntimeError):
            pass
    queue = ProductionQueue(player, snapshot["building_id"], building, scene_objs=scene_objs)
    queue.items = [dict(item) for item in snapshot.get("items", [])]
    queue.completed = [
        {
            "item": dict(entry.get("item", {})),
            "entity": _entity_named(scene_objs, entry.get("entity_name")),
        }
        for entry in snapshot.get("completed", [])
    ]
    return queue


def _restore_research_queue(snapshot, player, scene_objs):
    building = _entity_named(scene_objs, snapshot.get("building_name"))
    queue = ResearchQueue(player, snapshot["building_id"], building)
    queue.items = [dict(item) for item in snapshot.get("items", [])]
    queue.completed = [dict(item) for item in snapshot.get("completed", [])]
    return queue


def restore_from_scene(scene_objs):
    payload, state_entity = find_state_payload(scene_objs)
    if payload is None:
        raise RuntimeError("Sovereign session state tag was not found")
    player = _restore_player_state(payload, scene_objs)
    production_queue = _restore_production_queue(payload["production_queue"], player, scene_objs)
    research_queue = _restore_research_queue(payload["research_queue"], player, scene_objs)
    return {
        "payload": payload,
        "state_entity": state_entity,
        "player": player,
        "production_queue": production_queue,
        "research_queue": research_queue,
    }


def _summary_path():
    return os.environ.get("PF_SOVEREIGN_SESSION_RESTORE_SUMMARY")


def _marker_path():
    return os.environ.get("PF_SOVEREIGN_SESSION_RESTORE_MARKER")


def _write_restore_result(status, payload):
    summary_path = _summary_path()
    if summary_path:
        out_dir = os.path.dirname(summary_path)
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir)
        with open(summary_path, "w") as outfile:
            json.dump(payload, outfile, indent=2, sort_keys=True)
            outfile.write("\n")

    marker_prefix = os.environ.get("PF_SOVEREIGN_SESSION_RESTORE_MARKER_PREFIX", "SOVEREIGN_SAVE_LOAD_PROBE")
    marker = "{0}_{1}".format(marker_prefix, status.upper())
    if payload.get("checks"):
        checks = payload["checks"]
        marker = (
            "{0} state={state} entities={entities} player={player} "
            "scenario={scenario} victory={victory} queue={queue} tech={tech} combat={combat} resume={resume}"
        ).format(
            marker,
            state=int(checks.get("state_tag", False)),
            entities=int(checks.get("entity_tags", False)),
            player=int(checks.get("player_state", False)),
            scenario=int(checks.get("scenario_state", False)),
            victory=int(checks.get("victory_state", False)),
            queue=int(checks.get("production_queue", False)),
            tech=int(checks.get("research_state", False)),
            combat=int(checks.get("combat_hp", False)),
            resume=int(checks.get("production_queue_resumed", False)),
        )
    marker_path = _marker_path()
    if marker_path:
        with open(marker_path, "w") as outfile:
            outfile.write(marker + "\n")
    print(marker)
    sys.stdout.flush()


def restore_runtime_after_session_load(scene_objs=None, scene_regions=None, scene_cameras=None):
    if scene_objs is None:
        scene_objs = []
    if scene_regions is None:
        scene_regions = []
    if scene_cameras is None:
        scene_cameras = []

    sovereign_globals.scene_objs = scene_objs
    sovereign_globals.scene_regions = scene_regions
    sovereign_globals.scene_cameras = scene_cameras

    result = {
        "status": "fail",
        "backend": pf.get_render_info(),
        "checks": {
            "state_tag": False,
            "entity_tags": False,
            "scenario_state": False,
            "victory_state": False,
            "player_state": False,
            "production_queue": False,
            "research_state": False,
            "combat_hp": False,
            "production_queue_resumed": False,
        },
        "restore": {
            "object_count": len(scene_objs),
            "region_count": len(scene_regions),
            "camera_count": len(scene_cameras),
        },
    }

    try:
        restored = restore_from_scene(scene_objs)
        payload = restored["payload"]
        player = restored["player"]
        production_queue = restored["production_queue"]
        research_queue = restored["research_queue"]

        sovereign_globals.player_state = player
        sovereign_globals.production_queue = production_queue
        sovereign_globals.research_queue = research_queue
        sovereign_globals.session_state = payload

        tagged_count = len([ent for ent in scene_objs if entity_binding(ent)])
        scenario_state = payload.get("scenario_state")
        sovereign_globals.scenario_state = scenario_state
        result["checks"]["state_tag"] = True
        result["checks"]["entity_tags"] = tagged_count == len(payload.get("tagged_entities", []))
        result["checks"]["scenario_state"] = (
            isinstance(scenario_state, dict)
            and isinstance(scenario_state.get("metadata", {}).get("map_seed"), int)
            and scenario_state.get("victory", {}).get("mode") == "conquest"
        )
        victory_state = payload.get("victory_state")
        scenario_victory = (scenario_state or {}).get("victory", {})
        result["checks"]["victory_state"] = (
            isinstance(victory_state, dict)
            and victory_state.get("mode") == scenario_victory.get("mode")
            and isinstance(victory_state.get("elapsed_ticks"), int)
            and isinstance(victory_state.get("alive_factions"), list)
            and isinstance(victory_state.get("defeated_factions"), list)
        )
        result["checks"]["player_state"] = player.snapshot() == payload["player"]
        result["checks"]["production_queue"] = production_queue_state(production_queue) == payload["production_queue"]
        result["checks"]["research_state"] = research_queue_state(research_queue) == payload["research_queue"]

        combat = payload.get("combat", {})
        target = _entity_named(scene_objs, combat.get("target_name"))
        target_hp = int(getattr(target, "hp", -1)) if target is not None else -1
        result["checks"]["combat_hp"] = target_hp == int(combat.get("target_hp_after", -2))

        if production_queue.items:
            before_pop = player.population_used
            trained = production_queue.finish_next()
            result["checks"]["production_queue_resumed"] = (
                trained is not None
                and len(production_queue.items) == 0
                and player.population_used == before_pop + 1
            )

        result["status"] = "pass" if all(result["checks"].values()) else "fail"
        result["player"] = player.snapshot()
        result["scenario_state"] = scenario_state
        result["victory_state"] = victory_state
        result["production_queue_after_resume"] = production_queue.snapshot()
        result["research_queue"] = research_queue.snapshot()
        result["combat"] = {
            "target_name": combat.get("target_name"),
            "target_hp_after": target_hp,
        }
    except Exception as exc:
        result["reason"] = "{0}: {1}".format(exc.__class__.__name__, exc)

    _write_restore_result(result["status"], result)
    if os.environ.get("PF_SOVEREIGN_SESSION_RESTORE_AUTOQUIT") == "1":
        os._exit(0 if result["status"] == "pass" else 1)
    return result["status"] == "pass"
