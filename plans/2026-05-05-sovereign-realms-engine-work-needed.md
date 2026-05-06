# Sovereign Realms Engine Work Needed Plan

This is the tracked copy of the 5 May 2026 Sovereign Realms engine plan. The
full implementation plan lives in `docs/sovereign/engine_work_needed.md`; this
file records execution status as slices are completed and verified.

## Current Status

- Repo/license scaffold: DONE.
- Initial Sovereign package layout: DONE.
- Asset intake folder and PFOBJ validator: DONE.
- Data-driven registry seed: DONE.
- Data-driven minimal factory spawn: DONE.
- Playable villager/economy behavior: DONE.
- Production queue and population behavior: DONE.
- Age advancement and tech tree behavior: DONE.
- Combat counter rules: DONE.
- Projectile/VFX proof: DONE.
- Projectile origin/facing polish: DONE.
- Sovereign save/load roundtrip: DONE.
- Basic AI/skirmish loop: DONE for the first deterministic MVP probe.
- Editor scenario sidecar export/reload/run: DONE for the first two-player
  metadata probe.
- Packaged editor sidecar export bridge: DONE behind
  `PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1`.
- Visible packaged editor authoring controls: DONE for scenario/player/resource
  metadata behind `PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1`.
- Map-click editor placement: DONE for player starts and resource clusters,
  including resource ownership/amount sidecar metadata and runtime validation.
- Placed unit/building authoring: DONE for palette-backed unit/building slots,
  ownership metadata, live validation text, and Metal runtime spawning.
- Editor object authoring ergonomics: DONE for add/duplicate/remove controls
  and simple map-space markers for starts, resources, units, and buildings.
- Editor validation navigation: DONE for issue-to-slot selection and active
  marker highlighting.
- Scenario metadata/export UX polish: DONE for scenario ID, export status,
  compact palette summaries, validation category summaries, and the selected
  placement preview panel.
- Larger-map palette/validation scaling: DONE for palette search/filter,
  category folding, filtered result summaries, and validation category jump
  controls.
- Editor sidecar import/reload: DONE for loading a saved map's `.sovereign.json`
  back into the authoring tab with metadata, palette, placements, export
  status, and markers restored.
- Larger authored-map stress fixture: DONE for 4 players, 16 resource clusters,
  12 placed objects, 32 editor markers, sidecar reload, and 68 Metal runtime
  objects.
- Production-map metadata polish: DONE for map seed, Conquest victory label,
  author notes, and sidecar export-report counts/validation status.
- Scenario metadata gameplay hooks: DONE for deterministic seed helpers,
  victory-mode dispatch, and scenario-level save/load roundtrip coverage.
- Scenario setup profiles and victory persistence: DONE for setup profiles,
  starting-resource presets, resource resolution, and victory-progress
  save/load coverage.
- Editor setup profile controls: DONE for visible profile/preset selection,
  sidecar save/reload, export-report persistence, and Metal runtime setup
  verification.
- Long skirmish-session probe: DONE for staged economy, production, attack
  waves, victory progress, native save/load, and queued-unit continuation after
  restore.
- Skirmish AI decision depth: DONE for resource shortfall, population block,
  house response, training, attack-readiness, and attack-order decisions.
- Sovereign repo packaging/push prep: DONE for publish preflight, artifact
  ignore updates, README/NOTICE/CHANGES polish, and handoff checklist.

## Completed Slice 1 — Repo/License And Package Bootstrap

Implemented:

- `NOTICE.md` and `CHANGES.md`.
- `docs/sovereign/engine_work_needed.md`.
- `docs/sovereign/repo_license_structure.md`.
- `scripts/sovereign/` package scaffold.
- `assets/sovereign/README.md`.
- `tools/asset_validation/validate_pfobj.py`.
- `.gitignore` exception for `assets/sovereign/**`.

Verification:

- `python3 -m py_compile` passed for the new Sovereign and validation Python
  files.
- `python3 scripts/sovereign/main.py` printed `SOVEREIGN_SCAFFOLD_READY`.
- `python3 tools/asset_validation/validate_pfobj.py assets/models/rock/rock.pfobj`
  printed `PFOBJ_VALID`.
- `python3 tools/asset_validation/validate_pfobj.py assets/models/knight/knight.pfobj`
  parsed structurally and reported expected skin-weight warnings.
- `git diff --check` passed.

## Completed Slice 2 — Data Registry To Runtime Factory

Implemented:

- Added placeholder runtime asset bindings to `scripts/sovereign/data/`.
- Added `scripts/sovereign/factory.py` for registry validation and minimal
  spawn-plan generation.
- Added `scripts/sovereign/entities/runtime.py` to map registry archetypes onto
  existing Permafrost entity classes.
- Added `scripts/sovereign/globals.py` for retaining Sovereign scene objects.
- Added `scripts/macos/pf_sovereign_factory_probe.py` as the first
  engine-runtime verification probe.

Minimal factory output:

- Civilization: `sovereign_default`.
- Entities: 10 total.
- Units: 3 villagers.
- Buildings: town center, house, barracks.
- Resources: food, wood, gold, stone nodes.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/main.py \
  scripts/sovereign/factory.py \
  scripts/sovereign/globals.py \
  scripts/sovereign/entities/runtime.py \
  scripts/sovereign/data/resources.py \
  scripts/sovereign/data/ages.py \
  scripts/sovereign/data/armor_classes.py \
  scripts/sovereign/data/units.py \
  scripts/sovereign/data/buildings.py \
  scripts/sovereign/data/technologies.py \
  scripts/sovereign/data/civilizations.py \
  scripts/macos/pf_sovereign_factory_probe.py
```

```sh
PYTHONPATH=scripts python3 -c \
  "from sovereign.factory import validate_registries, build_minimal_spawn_plan; errors = validate_registries(); plan = build_minimal_spawn_plan(); print('REGISTRY_ERRORS', len(errors)); print('SPAWN_ENTITIES', len(plan['entities']))"
```

Expected:

```text
REGISTRY_ERRORS 0
SPAWN_ENTITIES 10
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_factory_probe.py \
  --output-dir qa-output/sovereign-factory-probe
```

Expected:

```text
SOVEREIGN_FACTORY_PROBE_PASS backend=METAL entities=10 units=3 buildings=3 resources=4
```

Actual result matched the expected marker. Summary artifact:
`qa-output/sovereign-factory-probe/summary_sovereign_factory.json`.

## Completed Slice 3 — Minimal Economy Probe

Implemented:

- Added `scripts/macos/pf_sovereign_economy_probe.py`.
- The probe loads the minimal Sovereign scene from the data registries, orders
  a villager to gather food, drops it at the town center, and completes the
  house placeholder.
- The probe records harvest, storage, and build events and writes
  `summary_sovereign_economy.json`.
- Added opt-in `--capture-after-pass` visual QA capture for the native Metal
  window.
- Disabled fog of war and tightened the probe camera so the spawned scene is
  visible in capture output.

Verification:

```sh
python3 -m py_compile \
  scripts/macos/pf_sovereign_economy_probe.py \
  scripts/macos/pf_sovereign_factory_probe.py \
  scripts/sovereign/factory.py \
  scripts/sovereign/entities/runtime.py \
  scripts/sovereign/data/resources.py \
  scripts/sovereign/data/buildings.py \
  scripts/sovereign/data/units.py
```

```sh
PYTHONPATH=scripts python3 -c \
  "from sovereign.factory import validate_registries, build_minimal_spawn_plan; errors=validate_registries(); plan=build_minimal_spawn_plan(); print('REGISTRY_ERRORS', len(errors)); print('SPAWN_ENTITIES', len(plan['entities']))"
```

Expected:

```text
REGISTRY_ERRORS 0
SPAWN_ENTITIES 10
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_economy_probe.py \
  --output-dir qa-output/sovereign-economy-probe
```

Expected:

```text
SOVEREIGN_ECONOMY_PROBE_PASS backend=METAL gather=1 dropoff=1 build=1 storage_food=4
```

Visual QA:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_economy_probe.py \
  --output-dir qa-output/sovereign-economy-visual \
  --capture-after-pass
```

Expected capture:
`qa-output/sovereign-economy-visual/sovereign_economy_economy.png`.

Observed:

- Metal runtime pass marker matched the expected marker.
- Summary artifact:
  `qa-output/sovereign-economy-visual/summary_sovereign_economy.json`.
- Capture size: `3456x2234`.
- Visual capture showed the plain terrain, minimap, spawned units/buildings,
  starter resources, and resource HUD after the economy/build sequence.

## Completed Slice 4 — Production Queue And Population Probe

Implemented:

- Added `scripts/sovereign/systems/production.py`.
- Added `scripts/macos/pf_sovereign_production_probe.py`.
- Extended `scripts/sovereign/entities/runtime.py` with the first
  data-driven combat-unit runtime wrapper.
- The probe loads the minimal Sovereign scene, completes the starter house and
  barracks placeholders, sets a pathable barracks rally point, enqueues one
  militia, spends resources, consumes population, spawns the trained unit, and
  records before/after Metal screenshots.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/entities/runtime.py \
  scripts/sovereign/systems/production.py \
  scripts/macos/pf_sovereign_production_probe.py
```

```sh
PYTHONPATH=scripts python3 -c \
  "from sovereign.factory import validate_registries, build_minimal_spawn_plan; from sovereign.systems.production import SovereignPlayerState; errors=validate_registries(); plan=build_minimal_spawn_plan(); state=SovereignPlayerState(); print('REGISTRY_ERRORS', len(errors)); print('SPAWN_ENTITIES', len(plan['entities'])); print('START_FOOD', state.resources['food'])"
```

Observed:

```text
REGISTRY_ERRORS 0
SPAWN_ENTITIES 10
START_FOOD 200
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_production_probe.py \
  --output-dir qa-output/sovereign-production-visual \
  --capture-proof
```

Observed:

```text
SOVEREIGN_PRODUCTION_PROBE_PASS backend=METAL enqueue=1 spawn=1 pop=4/10 food=140 gold=80 rally=1
```

Artifacts:

- `qa-output/sovereign-production-visual/summary_sovereign_production.json`.
- `qa-output/sovereign-production-visual/sovereign_production_before.png`.
- `qa-output/sovereign-production-visual/sovereign_production_after.png`.

State deltas:

- Population moved from `3/10` to `4/10`.
- Resources moved from `food=200, gold=100` to `food=140, gold=80`.
- The trained militia spawned at the pathable rally point `(88.0, 76.0)`.
- Both proof screenshots passed the nonblank PNG check at `3456x2234`.

## Next Slice

## Completed Slice 5 — Age Advancement And Technology Probe

Implemented:

- Added `scripts/sovereign/systems/technology.py`.
- Extended `scripts/sovereign/systems/production.py` player state with
  `current_age` and `researched_technologies`.
- Added `scripts/macos/pf_sovereign_age_tech_probe.py`.
- The probe loads the minimal Sovereign scene, researches
  `advance_to_rising` from the town center, spends food, advances from
  `founding` to `rising`, records the researched technology, and verifies
  wrong-age and duplicate research failures.
- Fixed the production probe's queue snapshot bookkeeping so its
  `after_enqueue` record is captured before `finish_next()`.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/production.py \
  scripts/sovereign/systems/technology.py \
  scripts/macos/pf_sovereign_age_tech_probe.py \
  scripts/macos/pf_sovereign_production_probe.py
```

```sh
PYTHONPATH=scripts python3 -c \
  "from sovereign.factory import validate_registries; from sovereign.systems.production import SovereignPlayerState; from sovereign.systems.technology import ResearchQueue; errors=validate_registries(); state=SovereignPlayerState(); state.resources['food']=600; print('REGISTRY_ERRORS', len(errors)); print('START_AGE', state.current_age); print('START_FOOD', state.resources['food'])"
```

Observed:

```text
REGISTRY_ERRORS 0
START_AGE founding
START_FOOD 600
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_age_tech_probe.py \
  --output-dir qa-output/sovereign-age-tech-visual \
  --capture-proof
```

Observed:

```text
SOVEREIGN_AGE_TECH_PROBE_PASS backend=METAL tech=1 age=rising food=100 prereq=1 duplicate=1
```

Artifacts:

- `qa-output/sovereign-age-tech-visual/summary_sovereign_age_tech.json`.
- `qa-output/sovereign-age-tech-visual/sovereign_age_tech_before.png`.
- `qa-output/sovereign-age-tech-visual/sovereign_age_tech_after.png`.

State deltas:

- Age moved from `founding` to `rising`.
- Food moved from `600` to `100`.
- `advance_to_rising` was recorded in `researched_technologies`.
- Wrong-age and duplicate research paths failed cleanly.
- Both proof screenshots passed the nonblank PNG check at `3456x2234`.

## Next Slice

## Completed Slice 6 — Combat Counter Rules Probe

Implemented:

- Added the first `DAMAGE_BONUSES` table to
  `scripts/sovereign/data/armor_classes.py`.
- Extended registry validation in `scripts/sovereign/factory.py` to reject
  damage-bonus tables that reference unknown damage or armor classes.
- Added `scripts/sovereign/systems/combat_rules.py`.
- Added `scripts/macos/pf_sovereign_combat_rules_probe.py`.
- The probe spawns two data-driven militia in a real Metal scene, applies the
  Sovereign damage rule, verifies the melee-vs-infantry bonus, and records
  before/after proof screenshots.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/armor_classes.py \
  scripts/sovereign/factory.py \
  scripts/sovereign/systems/combat_rules.py \
  scripts/macos/pf_sovereign_combat_rules_probe.py
```

```sh
PYTHONPATH=scripts python3 -c \
  "from sovereign.factory import validate_registries; from sovereign.systems.combat_rules import damage_breakdown; errors=validate_registries(); info=damage_breakdown('militia','militia'); print('REGISTRY_ERRORS', len(errors)); print('DAMAGE', info['total_damage']); print('BASE', info['base_damage']); print('BONUS', info['bonus_damage']); print('MATCHES', ','.join(info['matched_bonus_classes']))"
```

Observed:

```text
REGISTRY_ERRORS 0
DAMAGE 5
BASE 4
BONUS 1
MATCHES infantry
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_combat_rules_probe.py \
  --output-dir qa-output/sovereign-combat-rules-visual \
  --capture-proof
```

Observed:

```text
SOVEREIGN_COMBAT_RULES_PROBE_PASS backend=METAL damage=5 base=4 bonus=1 hp=45->40
```

Artifacts:

- `qa-output/sovereign-combat-rules-visual/summary_sovereign_combat_rules.json`.
- `qa-output/sovereign-combat-rules-visual/sovereign_combat_rules_before.png`.
- `qa-output/sovereign-combat-rules-visual/sovereign_combat_rules_after.png`.

State deltas:

- Militia melee damage resolved as `4 base + 1 infantry bonus = 5`.
- Target militia HP moved from `45` to `40`.
- The target stayed alive, so the probe verified damage without entering the
  death/zombie path.
- Both proof screenshots passed the nonblank PNG check at `3456x2234`.

## Next Slice

## Completed Slice 7 — Projectile And VFX Proof Probe

Implemented:

- Added a placeholder `archer` unit in `scripts/sovereign/data/units.py`
  with a data-driven projectile descriptor that uses the existing arrow,
  trail, and impact assets.
- Added the archer to `scripts/sovereign/data/civilizations.py`.
- Added a pierce-vs-infantry damage bonus in
  `scripts/sovereign/data/armor_classes.py`.
- Extended `scripts/sovereign/factory.py` validation to reject malformed
  projectile descriptors.
- Extended `scripts/sovereign/entities/runtime.py` so data-defined combat
  units can pass projectile descriptors through to the existing
  `pf.CombatableEntity` runtime.
- Added `scripts/macos/pf_sovereign_projectile_vfx_probe.py`.
- The probe spawns a data-driven archer and militia target in a real Metal
  scene, verifies projectile damage, records trail and impact sprite events,
  and renders fire/smoke sprite fixtures.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/armor_classes.py \
  scripts/sovereign/data/civilizations.py \
  scripts/sovereign/data/units.py \
  scripts/sovereign/entities/runtime.py \
  scripts/sovereign/factory.py \
  scripts/macos/pf_sovereign_projectile_vfx_probe.py
```

```sh
PYTHONPATH=scripts python3 -c \
  "from sovereign.factory import validate_registries; from sovereign.data.units import UNITS; errors=validate_registries(); projectile=UNITS['archer']['projectile']['descriptor']; print('REGISTRY_ERRORS', len(errors)); print('ARCHER_RANGE', UNITS['archer']['attack']['range']); print('PROJECTILE_MODEL', projectile[1]); print('IMPACT_SHEET', projectile[4][0][0]); print('TRAIL_SHEET', projectile[5][0][0])"
```

Observed:

```text
REGISTRY_ERRORS 0
ARCHER_RANGE 44.0
PROJECTILE_MODEL arrow-green.pfobj
IMPACT_SHEET impact_burst.png
TRAIL_SHEET projectile_trail.png
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_projectile_vfx_probe.py \
  --output-dir qa-output/sovereign-projectile-vfx-visual \
  --capture-proof
```

Observed:

```text
SOVEREIGN_PROJECTILE_VFX_PROBE_PASS backend=METAL damage=5 hp=45->40 trail=1 impact=1 fire=1 smoke=1
```

Artifacts:

- `qa-output/sovereign-projectile-vfx-visual/summary_sovereign_projectile_vfx.json`.
- `qa-output/sovereign-projectile-vfx-visual/sovereign_projectile_vfx_before.png`.
- `qa-output/sovereign-projectile-vfx-visual/sovereign_projectile_vfx_after.png`.

State and render evidence:

- Target militia HP moved from `45` to `40`.
- Projectile events recorded trail emission and one `impact_hit` using
  `impact_burst.png`.
- Render stats recorded `projectile_trail.png`, `impact_burst.png`,
  `fire_loop.png`, and `smoke_puff.png`.
- Both proof screenshots passed the nonblank PNG check at `3456x2234`.

## Completed Slice 8 — Projectile Origin And Facing Polish

Implemented:

- Fixed the shared projectile no-bone fallback in `src/game/combat.c` so
  `proj_fire_desc.offset` is treated as a local-space offset from the entity
  origin, matching `src/game/public/game.h`.
- Added env-gated projectile `spawn` events in `src/phys/projectile.c` so a
  projectile can be traced from parent UID to world-space origin.
- Added `pf.CombatableEntity.attack_entity(target)` in
  `src/script/py_entity.c` for deterministic direct-target proof scenes.
- Tightened direct attack handling so in-range attackers face their selected
  target immediately instead of first entering move-to-target state.
- Updated the placeholder Sovereign archer to use the Mage rig `palm_r` socket
  with low/direct fire mode in `scripts/sovereign/data/units.py`.
- Added attack animation start/end handling in
  `scripts/sovereign/entities/runtime.py` so socketed projectile fire frames
  advance during the proof.
- Extended `scripts/macos/pf_sovereign_projectile_vfx_probe.py` to verify:
  projectile spawn near attacker/socket, impact near target, target-ward
  direction, actor facing, and before/mid/after proof captures.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/entities/runtime.py \
  scripts/sovereign/data/units.py \
  scripts/macos/pf_sovereign_projectile_vfx_probe.py
```

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_projectile_vfx_probe.py \
  --output-dir qa-output/sovereign-projectile-vfx-facing \
  --capture-proof
```

Observed:

```text
SOVEREIGN_PROJECTILE_VFX_PROBE_PASS backend=METAL damage=5 hp=45->40 trail=1 impact=1 fire=1 smoke=1 spawn_dist=2.63 impact_dist=3.97 dir_dot=0.99
```

State and alignment evidence:

- All probe checks passed, including `actors_facing`,
  `projectile_spawn_near_attacker`, `projectile_impact_near_target`, and
  `projectile_direction_targetward`.
- Spawn position was `[60.592, 9.358, 71.538]`, `2.63` XZ units from the
  attacker/socket.
- Impact position was `[63.286, 7.720, 72.006]`, `3.97` XZ units from the
  target.
- Projectile direction dot product toward the target was `0.985`.
- Target militia HP moved from `45` to `40`.
- Proof captures were written:
  `qa-output/sovereign-projectile-vfx-facing/sovereign_projectile_vfx_before.png`,
  `qa-output/sovereign-projectile-vfx-facing/sovereign_projectile_vfx_mid.png`,
  and
  `qa-output/sovereign-projectile-vfx-facing/sovereign_projectile_vfx_after.png`.
- The older `pf_metal_gameplay_effects_probe.py` remains a separate legacy
  regression probe; no changes were left in that probe for this slice.

## Completed Slice 9 — Sovereign Save/Load Roundtrip

Implemented:

- Added env-gated Python 3 session module routing in `src/script/py_script.c`.
  The default path still restores through `rts.globals` and `rts.main`, while
  Sovereign probes can target `sovereign.globals` and
  `sovereign.entities.runtime`.
- Added `scripts/sovereign/session_state.py` for compact chunked state tags,
  registry entity tags, gameplay snapshots, and post-session-load rebind.
- Extended `scripts/sovereign/globals.py` with Sovereign runtime manager slots.
- Extended `scripts/sovereign/entities/runtime.py` with session scene metadata
  for Sovereign worker, storage building, buildable, resource, and combat
  entity classes.
- Added `scripts/macos/pf_sovereign_save_load_probe.py`.
- The probe creates registry-backed entities, completes starter buildings,
  spends resources, researches `advance_to_rising`, damages a target, leaves
  one militia queued, saves a native `.pfsave`, loads it, restores Sovereign
  Python manager state, and finishes the queued unit after reload.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/session_state.py \
  scripts/sovereign/entities/runtime.py \
  scripts/sovereign/globals.py \
  scripts/macos/pf_sovereign_save_load_probe.py
```

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_save_load_probe.py \
  --output-dir qa-output/sovereign-save-load-roundtrip
```

Observed:

```text
SOVEREIGN_SAVE_LOAD_PROBE_PASS state=1 entities=1 player=1 queue=1 tech=1 combat=1 resume=1
```

State evidence:

- Save file written:
  `qa-output/sovereign-save-load-roundtrip/sovereign_roundtrip.pfsave`
  (`710723` bytes in the verified run).
- Restore summary:
  `qa-output/sovereign-save-load-roundtrip/summary_sovereign_save_load.json`.
- Post-load object counts: `13` objects, `1` region, `1` camera.
- Player state after post-load queue resume: `food=140`, `gold=60`,
  `wood=200`, `stone=100`, population `5/10`, age `rising`,
  researched tech `advance_to_rising`.
- Production queue resumed after load: completed count moved to `2`,
  queue length moved to `0`, rally remained `[88.0, 76.0]`.
- Combat HP persisted: `save_load_target` restored at `40` HP.

## Slice 9: Basic Sovereign AI/Skirmish Loop

Implemented the first basic Sovereign AI/skirmish loop:

- fixed two-player setup
- scripted enemy economy/build/train loop
- simple attack wave
- natural walking animation check
- facing combat proof
- conquest-style victory check
- deterministic probe summary and screenshots

Implementation:

- Added `scripts/sovereign/systems/skirmish.py` with a deterministic
  `ScriptedSkirmishAI`, queue snapshotting, defeated-faction checks, and a
  conquest winner helper.
- Extended `scripts/sovereign/entities/runtime.py` so
  `SovereignCombatUnit` listens for engine motion-start/end events and plays
  `Walk` while moving, then returns to `Idle` unless it is attacking.
- Added `scripts/macos/pf_sovereign_skirmish_probe.py`.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/entities/runtime.py \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_skirmish_probe.py
```

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_skirmish_probe.py \
  --output-dir qa-output/sovereign-skirmish-loop \
  --capture-proof
```

Observed:

```text
SOVEREIGN_SKIRMISH_PROBE_PASS backend=METAL train=1 move=1 walk=1 attack=1 damage=5 victory=1 winner=2
```

Evidence:

- Summary: `qa-output/sovereign-skirmish-loop/summary_sovereign_skirmish.json`.
- Proof screenshots:
  - `qa-output/sovereign-skirmish-loop/sovereign_skirmish_setup.png`
  - `qa-output/sovereign-skirmish-loop/sovereign_skirmish_moving.png`
  - `qa-output/sovereign-skirmish-loop/sovereign_skirmish_combat.png`
  - `qa-output/sovereign-skirmish-loop/sovereign_skirmish_victory.png`
- Screenshot validation passed for all four captures at `3456x2234`.
- Movement evidence: enemy wave displacement `3.257`, max single-step
  `0.812`, `motion_start_events=1`, `motion_end_events=1`, and `Walk`
  animation observed.
- Combat/victory evidence: `Attack` animation observed, data damage applied
  through militia-vs-militia counter rules, target reduced to defeat threshold,
  conquest winner reported as faction `2`.

Regression checks:

```text
SOVEREIGN_PROJECTILE_VFX_PROBE_PASS backend=METAL damage=5 hp=45->40 trail=1 impact=1 fire=1 smoke=1 spawn_dist=2.63 impact_dist=6.67 dir_dot=0.99
SOVEREIGN_SAVE_LOAD_PROBE_PASS state=1 entities=1 player=1 queue=1 tech=1 combat=1 resume=1
```

Important caveat:

- This is an MVP deterministic skirmish loop, not a full autonomous AI planner.
  Enemy gathering/build-order planning, tactical target selection, persistent
  AI/victory state in saves, and real death/destruction presentation remain
  later production slices.

## Slice 10: Editor Scenario Sidecar Export/Reload/Run

Implemented the first Sovereign editor scenario sidecar workflow:

- Added `assets/sovereign/scenarios/two_player_skirmish.json` with two player
  starts, faction colors, starting resources, war diplomacy, conquest victory,
  and a Sovereign object/resource palette.
- Added `scripts/sovereign/scenario.py` for scenario validation, JSON
  export/reload, faction/diplomacy setup, runtime scene spawning, and summary
  generation.
- Updated `scripts/sovereign/factory.py` so runtime spawn plans honor each
  scenario player's `civilization_id`.
- Added `scripts/macos/pf_sovereign_editor_scenario_probe.py`.
- Updated the Sovereign asset README to reserve `assets/sovereign/scenarios/`
  for metadata sidecars.
- Hardened `scripts/sovereign/systems/combat_rules.py` so data-driven damage
  clamps to the engine-supported 1 HP defeat threshold instead of attempting
  to assign invalid zero HP.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/combat_rules.py \
  scripts/sovereign/factory.py \
  scripts/sovereign/scenario.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --output-dir qa-output/sovereign-editor-scenario \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=20 train=1 victory=1
```

Evidence:

- Exported sidecar:
  `qa-output/sovereign-editor-scenario/editor_two_player_skirmish.sovereign.json`.
- Summary:
  `qa-output/sovereign-editor-scenario/summary_sovereign_editor_scenario.json`.
- Proof screenshots:
  - `qa-output/sovereign-editor-scenario/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-scenario/sovereign_editor_scenario_validated.png`
- Screenshot validation passed for both captures at `3456x2234`.
- Runtime evidence: two players, `20` scenario-spawned objects before the
  probe guard, war diplomacy, player resources matching sidecar data, enemy
  barracks training one militia, data damage reducing the guard to the 1 HP
  defeat threshold, and conquest winner reported as faction `2`.

Regression checks:

```text
SOVEREIGN_COMBAT_RULES_PROBE_PASS backend=METAL damage=5 base=4 bonus=1 hp=45->40
SOVEREIGN_SKIRMISH_PROBE_PASS backend=METAL train=1 move=1 walk=1 attack=1 damage=5 victory=1 winner=2
SOVEREIGN_SAVE_LOAD_PROBE_PASS state=1 entities=1 player=1 queue=1 tech=1 combat=1 resume=1
```

Important caveat:

- This proves the scenario sidecar contract and native runtime path, not the
  final packaged editor authoring UI. The editor still needs controls for
  placing Sovereign starts, ownership, diplomacy, object palettes, and
  map-author-facing validation messages.

## Slice 11: Packaged Editor Sovereign Sidecar Export Bridge

Implemented the first packaged-editor authoring bridge for Sovereign scenario
metadata:

- Added `scripts/sovereign/editor_scenario.py` with the default Sovereign
  authoring palette, two-player starts/resources/diplomacy, map-to-sidecar path
  convention, and sidecar writer.
- Updated the editor menu save path so Save/Save As writes a
  `.sovereign.json` sidecar beside PFMAP/PFSCENE when
  `PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1`.
- Extended the editor workflow probe marker with `sovereign_sidecar=...`.
- Extended the editor workflow probe validation to parse and validate the
  emitted Sovereign sidecar when the export flag is enabled.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/main.py \
  scripts/editor/view_controllers/menu_vc.py
```

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-authoring \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed editor marker:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-authoring/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-authoring/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-authoring/editor_workflow_probe.sovereign.json
```

Then verified the exact editor-exported sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-authoring/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-authoring-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=20 train=1 victory=1
```

Evidence:

- Editor-exported map:
  `qa-output/sovereign-editor-authoring/editor_workflow_probe.pfmap`.
- Editor-exported scene:
  `qa-output/sovereign-editor-authoring/editor_workflow_probe.pfscene`.
- Editor-exported Sovereign sidecar:
  `qa-output/sovereign-editor-authoring/editor_workflow_probe.sovereign.json`.
- Runtime summary:
  `qa-output/sovereign-editor-authoring-runtime/summary_sovereign_editor_scenario.json`.
- Runtime screenshots:
  - `qa-output/sovereign-editor-authoring-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-authoring-runtime/sovereign_editor_scenario_validated.png`
- Screenshot validation passed for both captures at `3456x2234`.

Important caveat:

- This is the sidecar export bridge, not the final user-facing editor UI. The
  current sidecar uses default two-player Sovereign metadata. The next slice
  should expose author controls instead of relying on defaults.

## Slice 12: Visible Packaged Editor Authoring Controls

Implemented the first visible packaged-editor controls for Sovereign scenario
metadata:

- Added `scripts/editor/views/sovereign_tab_window.py`.
- Added `scripts/editor/view_controllers/sovereign_tab_vc.py`.
- Extended `scripts/sovereign/editor_scenario.py` with shared authoring state,
  reset/get helpers, and sidecar generation from the edited state.
- Added a fourth `Sovereign` editor tab when
  `PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1`.
- The tab exposes scenario name, player selection, player names,
  civilization, start X/Z, food/wood/gold/stone, diplomacy, and the active
  Sovereign object/resource palette.
- Extended the editor workflow probe with
  `PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1`, which selects the Sovereign tab,
  mutates visible-authoring metadata, saves, and verifies the sidecar contains
  the edited values.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/view_controllers/sovereign_tab_vc.py \
  scripts/editor/main.py \
  scripts/editor/view_controllers/menu_vc.py
```

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-visible-controls \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed editor marker:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-visible-controls/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-visible-controls/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-visible-controls/editor_workflow_probe.sovereign.json
```

Sidecar evidence:

- Scenario name saved as `Authoring Probe Scenario`.
- Player 1 saved as `Blue Author`, start `[72.0, 82.0]`,
  food `310`, wood `333`.
- Player 2 saved as `Red Author`, start `[132.0, 76.0]`,
  food `640`, wood `640`.
- Diplomacy saved as player 1 versus player 2 `war`.

Then verified the exact editor-exported sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-visible-controls/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-visible-controls-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=20 train=1 victory=1
```

Runtime evidence:

- Player 1 resources loaded as `food=310`, `wood=333`, `gold=140`,
  `stone=100`.
- Player 2 resources loaded as `food=640`, `wood=640`, `gold=200`,
  `stone=100`; after training one militia, probe summary showed `food=580`,
  `gold=180`.
- Runtime proof screenshots:
  - `qa-output/sovereign-editor-visible-controls-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-visible-controls-runtime/sovereign_editor_scenario_validated.png`
- Screenshot validation passed for both captures at `3456x2234`.

Important caveat:

- This is visible metadata editing, not map-click placement. Starts/resources
  are editable as numeric values and palette items are visible, but direct
  placement tools for starts, ownership, and resource clusters were deferred to
  Slice 13 below.

## Slice 13: Map-Click Player Start And Resource Placement

Implemented the first direct map-placement authoring workflow for Sovereign
scenario sidecars:

- Extended `scripts/sovereign/editor_scenario.py` with default
  `placed_resources` and placement selection state.
- Extended `scripts/editor/views/sovereign_tab_window.py` with placement mode
  controls for player starts versus resource clusters, selected cluster,
  owner, amount, and current point.
- Extended `scripts/editor/view_controllers/sovereign_tab_vc.py` so left-clicks
  on the map apply to the selected Sovereign player start or resource cluster.
- Extended `scripts/sovereign/scenario.py` to validate placed resource IDs,
  owners, amounts, points, required food/wood/gold/stone cluster coverage, and
  start/resource pathability during runtime scene load.
- Runtime scene construction now spawns placed resource clusters and reports
  `placed_resource_count` plus placed resource metadata in scenario summaries.
- Extended `scripts/macos/pf_sovereign_editor_scenario_probe.py` so the Metal
  runtime probe requires placed resource validation when clusters are present.
- Extended the editor workflow probe so the authoring step applies placement
  points, ownership, and amounts before saving, then verifies the exact sidecar
  metadata.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/view_controllers/sovereign_tab_vc.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-map-click-placement \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed editor marker:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-map-click-placement/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-map-click-placement/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-map-click-placement/editor_workflow_probe.sovereign.json
```

Sidecar evidence:

- Player 1 saved as `Blue Author`, start `[74.0, 84.0]`, food `310`,
  wood `333`.
- Player 2 saved as `Red Author`, start `[136.0, 78.0]`, food `640`,
  wood `640`.
- Food cluster saved at `[66.0, 96.0]`, owner player `1`, amount `420`.
- Wood cluster saved at `[146.0, 74.0]`, owner player `2`, amount `510`.
- Gold and stone clusters remain neutral defaults, so the sidecar satisfies the
  required food/wood/gold/stone coverage check.

Then verified the exact editor-exported sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-map-click-placement/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-map-click-placement-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=24 train=1 victory=1
```

Runtime evidence:

- Runtime summary reported `placed_resource_count=4`.
- All scenario checks passed, including `placed_resources`, `runtime_scene`,
  `player_resources`, war diplomacy, enemy training, and conquest victory.
- Runtime proof screenshots:
  - `qa-output/sovereign-editor-map-click-placement-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-map-click-placement-runtime/sovereign_editor_scenario_validated.png`
- Screenshot validation passed for both captures at `3456x2234`.

Implementation note:

- The first editor probe run exposed a shape bug: default resource clusters were
  tuple-backed while scenario validation requires JSON-style lists. That was
  fixed in `scripts/sovereign/editor_scenario.py` before accepting the slice.

## Slice 14: Placed Unit/Building Authoring

Implemented the first unit/building placement authoring workflow for Sovereign
scenario sidecars:

- Extended `scripts/sovereign/editor_scenario.py` with default
  `placed_objects`, selected object index, and live `validation_errors`.
- Extended `scripts/editor/views/sovereign_tab_window.py` so the Sovereign tab
  can choose `Start`, `Resource`, `Unit`, or `Building` placement, select a
  placed object slot, choose a palette-backed unit/building ID, assign player
  ownership, and show live validation status before save.
- Extended `scripts/editor/view_controllers/sovereign_tab_vc.py` so map clicks
  apply to the selected unit/building slot as well as starts/resources.
- Extended `scripts/sovereign/scenario.py` with `placed_objects` validation for
  duplicate IDs, unknown unit/building IDs, bad ownership, bad points, runtime
  pathability, Metal spawning, and player-state registration.
- Extended the editor workflow probe so its authoring step places a player-1
  militia and a player-2 barracks, then verifies the exact saved sidecar
  metadata.
- Extended `scripts/macos/pf_sovereign_editor_scenario_probe.py` so the Metal
  runtime scenario probe requires placed object evidence when present.
- Updated `assets/sovereign/scenarios/two_player_skirmish.json` with the first
  default placed unit/building examples.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/view_controllers/sovereign_tab_vc.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-placed-objects \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed editor marker:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-placed-objects/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-placed-objects/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-placed-objects/editor_workflow_probe.sovereign.json
```

Sidecar evidence:

- Placed unit `p1_guard`: `militia`, owner player `1`, point `[101.0, 94.0]`.
- Placed building `p2_forward_barracks`: `barracks`, owner player `2`, point
  `[152.0, 88.0]`.
- Existing authored resource cluster evidence from Slice 13 remained intact.

Then verified the exact editor-exported sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-placed-objects/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-placed-objects-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=26 train=1 victory=1
```

Runtime evidence:

- Runtime summary reported `placed_object_count=2` and
  `placed_resource_count=4`.
- Player 1 runtime summary gained the authored militia (`unit_count=4` before
  the probe guard is added).
- Player 2 runtime summary gained the authored barracks (`building_count=4`).
- All scenario checks passed, including `placed_objects`, `placed_resources`,
  `runtime_scene`, `player_resources`, war diplomacy, enemy training, and
  conquest victory.
- Runtime proof screenshots:
  - `qa-output/sovereign-editor-placed-objects-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-placed-objects-runtime/sovereign_editor_scenario_validated.png`
- Screenshot validation passed for both captures at `3456x2234`.

Implementation note:

- The first editor run exposed a state-sync bug: the tab's selected object
  index could lag behind the scripted placement state and normalize the wrong
  slot. `scripts/editor/views/sovereign_tab_window.py` now synchronizes
  selected resource/object indices from the shared placement state before
  rendering the relevant combo boxes.

## Completed Slice 15 — Editor Object Authoring Ergonomics

Implemented:

- Added editor-side helper operations for duplicating and removing player
  starts, resource clusters, and placed unit/building objects.
- Added visible Add, Duplicate, and Remove controls in the Sovereign editor tab
  for authored resources and objects, plus Duplicate/Remove controls for player
  starts.
- Added simple map-space region markers for authored player starts, resources,
  and placed objects so authors can see what the sidecar will export.
- Extended the packaged editor workflow probe to exercise the add, duplicate,
  and remove paths, keep an extra authored food cluster and archer, and assert
  the marker count.
- Kept the exported sidecar compatible with the runtime scenario probe.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/globals.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/view_controllers/sovereign_tab_vc.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-object-ergonomics \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed editor marker:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-object-ergonomics/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-object-ergonomics/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-object-ergonomics/editor_workflow_probe.sovereign.json sovereign_markers=10
```

Sidecar evidence:

- `placed_resources=5`, including the new authored food cluster
  `p1_extra_food` at `[70.0, 100.0]`.
- `placed_objects=3`, including the new authored archer
  `p1_forward_archer` at `[108.0, 98.0]`.
- `sovereign_markers=10`, matching 2 player starts + 5 resources + 3 objects.

Then verified the exact editor-exported sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-object-ergonomics/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-object-ergonomics-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=28 train=1 victory=1
```

Runtime evidence:

- Runtime summary reported `placed_object_count=3` and
  `placed_resource_count=5`.
- All scenario checks passed, including placed objects, placed resources,
  runtime scene spawn, player resources, war diplomacy, enemy training, and
  conquest victory.
- Runtime proof screenshots:
  - `qa-output/sovereign-editor-object-ergonomics-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-object-ergonomics-runtime/sovereign_editor_scenario_validated.png`
- Screenshot validation passed for both captures.
- `git diff --check` passed.

## Completed Slice 16 — Editor Validation Navigation And Marker Polish

Implemented:

- Added editor-only structured validation issues on top of the existing
  scenario validation strings, keeping runtime scenario validation stable.
- Added target selection for validation issues so player-start, resource, and
  placed-object errors can jump to the offending authoring slot.
- Added Go controls next to targetable validation messages in the Sovereign
  editor tab.
- Fixed marker refresh after player-start and resource placement changes, not
  just object placement changes.
- Added active marker naming/radius polish so the currently selected
  start/resource/object is the only marker ending in `_ACTIVE`.
- Extended the packaged editor workflow probe with temporary resource, object,
  and player-start validation failures, verified that each selects the correct
  slot, restored the scenario, and checked that exactly one active marker is
  present.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/globals.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/view_controllers/sovereign_tab_vc.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-validation-navigation \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed editor marker:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-validation-navigation/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-validation-navigation/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-validation-navigation/editor_workflow_probe.sovereign.json sovereign_markers=10
```

Then verified the exact editor-exported sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-validation-navigation/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-validation-navigation-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=28 train=1 victory=1
```

Runtime evidence:

- Runtime summary reported `placed_object_count=3` and
  `placed_resource_count=5`.
- All runtime scenario checks passed.
- Runtime proof screenshots:
  - `qa-output/sovereign-editor-validation-navigation-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-validation-navigation-runtime/sovereign_editor_scenario_validated.png`
- Screenshot validation passed for both captures.

## Completed Slice 17 — Scenario Metadata And Export UX Polish

Implemented:

- Added editor export-status state for Sovereign sidecars: `not_saved`,
  `saved`, or `error`, with sidecar path and a concise message.
- Updated sidecar export to record saved/error status without changing the
  runtime scenario JSON schema.
- Added editable Scenario ID to the Sovereign editor tab. Blank IDs still fall
  back to the saved map name.
- Added a compact scenario-size summary in the tab: player count, resource
  cluster count, authored unit count, and authored building count.
- Reworked the palette panel into compact count/type summaries instead of a
  long repeated list.
- Added validation category counts for starts, resources, objects, and other
  errors before the targetable Go list.
- Extended the editor workflow probe assertions so the exported sidecar keeps
  the authored Scenario ID, and export status records success, path, and a
  useful message.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/globals.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/view_controllers/sovereign_tab_vc.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

Headless export-status check with a minimal `pf` stub:

```text
SOVEREIGN_EXPORT_UX_HEADLESS_PASS export_ux_probe saved /private/tmp/export_ux_probe.sovereign.json
```

Generated a compatible sidecar against the last verified editor map:

```text
SOVEREIGN_EXPORT_UX_SIDECAR_READY qa-output/sovereign-editor-export-ux/editor_workflow_probe.sovereign.json Exported 2 player(s), 4 resource cluster(s), 2 placed object(s)
```

Then verified that sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-export-ux/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-export-ux-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=26 train=1 victory=1
```

Runtime evidence:

- Runtime summary reported `scenario_valid=true`, `placed_resources=true`,
  `placed_objects=true`, `object_count=26`, `placed_resource_count=4`, and
  `placed_object_count=2`.
- Screenshot validation passed for both runtime captures:
  - `qa-output/sovereign-editor-export-ux-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-export-ux-runtime/sovereign_editor_scenario_validated.png`

Follow-up packaged editor rerun:

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-export-ux \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-export-ux/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-export-ux/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-export-ux/editor_workflow_probe.sovereign.json sovereign_markers=10
```

## Completed Slice 18 — Selected Palette Preview Quality-Of-Life

Implemented:

- Added a selected-placement preview panel under the compact palette summary.
- Player-start preview shows player id, name, point, and civilization.
- Resource preview shows display name, amount, owner, radius, and backing asset.
- Unit preview shows display name, role/archetype, HP, cost, population/range,
  and backing asset.
- Building preview shows display name, archetype, HP, cost, footprint,
  population provided, and backing asset.
- Kept previews text/data driven from existing Sovereign registries; no asset
  thumbnail pipeline or renderer changes were added.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/globals.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/view_controllers/sovereign_tab_vc.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

Packaged editor probe:

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-palette-preview \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-palette-preview/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-palette-preview/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-palette-preview/editor_workflow_probe.sovereign.json sovereign_markers=10
```

Then verified the exact editor-exported sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-palette-preview/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-palette-preview-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=28 train=1 victory=1
```

Runtime evidence:

- Runtime summary reported `scenario_valid=true`, `placed_resources=true`,
  `placed_objects=true`, `object_count=28`, `placed_resource_count=5`, and
  `placed_object_count=3`.
- Screenshot validation passed for both runtime captures:
  - `qa-output/sovereign-editor-palette-preview-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-palette-preview-runtime/sovereign_editor_scenario_validated.png`

## Completed Slice 19 — Larger-Map Palette And Validation Scaling

Implemented:

- Added local palette filtering/search in the Sovereign editor tab.
- Added palette category folding for units, buildings, and resources.
- Reworked the palette group to show filtered counts plus the first matching
  entries, with a compact overflow line for larger registries.
- Added validation category jump controls for starts, resources, objects, and
  other issues.
- Added compact validation "showing/jumpable" counts so larger maps do not
  flood the left editor pane.
- Extended the editor workflow probe to assert unit/building palette filtering
  and category folding, plus resource/object/player-start validation summary
  indexing.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/globals.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/view_controllers/sovereign_tab_vc.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

Packaged editor probe:

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-palette-scaling \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-palette-scaling/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-palette-scaling/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-palette-scaling/editor_workflow_probe.sovereign.json sovereign_markers=10
```

Then verified the exact editor-exported sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-palette-scaling/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-palette-scaling-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=28 train=1 victory=1
```

Runtime evidence:

- Runtime summary checks reported `scenario_valid=true`, `palette_valid=true`,
  `placed_resources=true`, `placed_objects=true`, `scenario_reloaded=true`, and
  `conquest_victory=true`.
- Screenshot validation passed for both runtime captures:
  - `qa-output/sovereign-editor-palette-scaling-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-palette-scaling-runtime/sovereign_editor_scenario_validated.png`

## Completed Slice 20 — Editor Sidecar Import/Reload

Implemented:

- Added `load_editor_scenario()` in `scripts/sovereign/editor_scenario.py`.
- Loading a saved editor map now imports the adjacent `.sovereign.json` when
  `PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1` is enabled.
- Imported authoring state restores scenario id/name, players, palette, placed
  resources, placed objects, diplomacy state, export status, and default
  selected placement.
- Extended the editor workflow reload probe with
  `PF_EDITOR_SOVEREIGN_AUTHORING_RELOAD_PROBE=1` so it asserts the imported
  authoring state exactly matches the saved sidecar and rebuilds the expected
  placement markers.
- Confirmed the earlier screenshot error was a bad local invocation where the
  `.pfmap` path was accidentally passed as the Python script. The corrected
  command passes `./scripts/editor/main.py` first, then the map and scene.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/globals.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/view_controllers/sovereign_tab_vc.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

Packaged editor save/export probe:

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-sidecar-reload \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-sidecar-reload/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-sidecar-reload/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-sidecar-reload/editor_workflow_probe.sovereign.json sovereign_markers=10
```

Packaged editor reload/import probe:

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_RELOAD_ONLY=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_RELOAD_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_EXPECT_OBJECTS=2 \
./bin/pf-arm64 ./ ./scripts/editor/main.py \
  qa-output/sovereign-editor-sidecar-reload/editor_workflow_probe.pfmap \
  qa-output/sovereign-editor-sidecar-reload/editor_workflow_probe.pfscene
```

Observed:

```text
EDITOR_SOVEREIGN_SCENARIO_LOADED qa-output/sovereign-editor-sidecar-reload/editor_workflow_probe.sovereign.json
EDITOR_WORKFLOW_RELOAD_READY backend=METAL renderer=Apple M2 Max loaded_objects=2 sovereign_sidecar=qa-output/sovereign-editor-sidecar-reload/editor_workflow_probe.sovereign.json sovereign_markers=10
```

Then verified the same editor-exported sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-sidecar-reload/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-sidecar-reload-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=2 objects=28 train=1 victory=1
```

Runtime evidence:

- Runtime summary checks reported `scenario_valid=true`, `palette_valid=true`,
  `placed_resources=true`, `placed_objects=true`, `scenario_reloaded=true`, and
  `conquest_victory=true`.
- Screenshot validation passed for both runtime captures:
  - `qa-output/sovereign-editor-sidecar-reload-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-sidecar-reload-runtime/sovereign_editor_scenario_validated.png`

## Completed Slice 21 — Larger Authored-Map Stress Fixture

Implemented:

- Added `PF_EDITOR_SOVEREIGN_AUTHORING_STRESS_PROBE=1` to the packaged editor
  workflow probe.
- The stress fixture authors:
  - 4 player starts.
  - 16 resource clusters covering food, wood, gold, and stone around each
    start.
  - 12 placed units/buildings across the four players.
- The stress fixture reuses the existing palette filtering/category folding
  assertions and validation navigation checks.
- Save/export now verifies the stress sidecar's player/resource/object counts.
- Reload/import verifies the saved sidecar restores the authoring tab and all
  32 map-space placement markers.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/globals.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/view_controllers/sovereign_tab_vc.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

Packaged editor stress save/export probe:

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_STRESS_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-stress-fixture \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-stress-fixture/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-stress-fixture/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-stress-fixture/editor_workflow_probe.sovereign.json sovereign_markers=32
```

Packaged editor stress reload/import probe:

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_RELOAD_ONLY=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_RELOAD_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_EXPECT_OBJECTS=2 \
./bin/pf-arm64 ./ ./scripts/editor/main.py \
  qa-output/sovereign-editor-stress-fixture/editor_workflow_probe.pfmap \
  qa-output/sovereign-editor-stress-fixture/editor_workflow_probe.pfscene
```

Observed:

```text
EDITOR_SOVEREIGN_SCENARIO_LOADED qa-output/sovereign-editor-stress-fixture/editor_workflow_probe.sovereign.json
EDITOR_WORKFLOW_RELOAD_READY backend=METAL renderer=Apple M2 Max loaded_objects=2 sovereign_sidecar=qa-output/sovereign-editor-stress-fixture/editor_workflow_probe.sovereign.json sovereign_markers=32
```

Then verified the same stress sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-stress-fixture/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-stress-fixture-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=4 objects=68 train=1 victory=1
```

Runtime evidence:

- Sidecar counts: 4 players, 16 resource clusters, and 12 placed objects.
- Runtime summary checks reported `scenario_valid=true`, `palette_valid=true`,
  `placed_resources=true`, `placed_objects=true`, `scenario_reloaded=true`, and
  `conquest_victory=true`.
- Screenshot validation passed for both runtime captures:
  - `qa-output/sovereign-editor-stress-fixture-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-stress-fixture-runtime/sovereign_editor_scenario_validated.png`

## Completed Slice 22 — Production Map Metadata And Export Report

Implemented:

- Extended Sovereign scenario sidecars with production-map metadata:
  - `metadata.map_seed`
  - `metadata.author_notes`
  - `victory.label`
- Added a structured `export_report` to generated sidecars with:
  - player/resource/object/unit/building/marker counts
  - diplomacy and palette counts
  - validation status, issue count, and first validation messages
- Restored metadata and export-report counts when an existing sidecar is loaded
  back into the packaged editor authoring tab.
- Added visible packaged-editor controls/readouts for map seed, victory label,
  author notes, report counts, and validation-report status.
- Updated the editor workflow probe so save/export and reload fail if metadata,
  victory label, report counts, report validation status, or export-status
  message quality regress.
- Updated the Metal runtime scenario probe to require metadata/report checks
  before declaring the sidecar production-ready.
- Updated the default two-player Sovereign sidecar fixture with metadata and an
  export report.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/scenario.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

Packaged editor save/export with the larger authored-map fixture:

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_STRESS_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-metadata-report \
./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-metadata-report/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-metadata-report/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-metadata-report/editor_workflow_probe.sovereign.json sovereign_markers=32
```

Packaged editor sidecar reload/import:

```sh
PF_EDITOR_WORKFLOW_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_RELOAD_ONLY=1 \
PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
PF_EDITOR_SOVEREIGN_AUTHORING_RELOAD_PROBE=1 \
PF_EDITOR_WORKFLOW_PROBE_EXPECT_OBJECTS=2 \
./bin/pf-arm64 ./ ./scripts/editor/main.py \
  qa-output/sovereign-editor-metadata-report/editor_workflow_probe.pfmap \
  qa-output/sovereign-editor-metadata-report/editor_workflow_probe.pfscene
```

Observed:

```text
EDITOR_SOVEREIGN_SCENARIO_LOADED qa-output/sovereign-editor-metadata-report/editor_workflow_probe.sovereign.json
EDITOR_WORKFLOW_RELOAD_READY backend=METAL renderer=Apple M2 Max loaded_objects=2 sovereign_sidecar=qa-output/sovereign-editor-metadata-report/editor_workflow_probe.sovereign.json sovereign_markers=32
```

Then verified the same metadata-rich sidecar in the Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-metadata-report/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-metadata-report-runtime \
  --capture-proof
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=4 objects=68 train=1 victory=1
```

Export-report evidence:

- Sidecar seed: `20260506`.
- Victory label: `Conquest`.
- Counts: 4 players, 16 resource clusters, 12 placed objects, 4 placed units,
  8 placed buildings, 32 markers.
- Validation report: `ready`, `issue_count=0`.
- Runtime summary checks reported `metadata_seed=true` and `export_report=true`.
- Screenshot validation passed for:
  - `qa-output/sovereign-editor-metadata-report-runtime/sovereign_editor_scenario_loaded.png`
  - `qa-output/sovereign-editor-metadata-report-runtime/sovereign_editor_scenario_validated.png`

## Completed Slice 23 — Actionable Scenario Metadata

Implemented:

- Added shared scenario runtime helpers for:
  - normalized scenario metadata
  - deterministic map seed access
  - seeded random choice hooks
  - normalized victory metadata
  - compact scenario runtime state
- `build_runtime_scene()` now stores scenario runtime state and map seed in the
  returned runtime payload and in `sovereign.globals.scenario_state`.
- Added skirmish AI seed ownership and deterministic attack-unit selection
  hooks.
- Added `victory_winner()` and `scenario_victory_winner()` dispatch helpers so
  gameplay code asks the scenario's victory mode instead of directly calling
  Conquest-specific logic.
- Extended Sovereign save/load payloads with `scenario_state`, including map
  seed, author notes, map reference, and victory mode/label.
- Extended restore checks so session reload fails if scenario-level state is
  missing or malformed.
- Updated editor-scenario and skirmish probes to verify seeded setup and
  victory-mode dispatch.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/scenario.py \
  scripts/sovereign/systems/skirmish.py \
  scripts/sovereign/session_state.py \
  scripts/sovereign/globals.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py \
  scripts/macos/pf_sovereign_skirmish_probe.py \
  scripts/macos/pf_sovereign_save_load_probe.py
```

Editor-exported stress sidecar through Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-metadata-report/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-scenario-actionable-metadata
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=4 objects=68 train=1 victory=1
```

Summary checks included:

- `seeded_setup=true`
- `victory_dispatch=true`
- `metadata_seed=true`
- `export_report=true`
- runtime seed `20260506`

Skirmish loop with seeded scenario state:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_skirmish_probe.py \
  --output-dir qa-output/sovereign-skirmish-actionable-metadata
```

Observed:

```text
SOVEREIGN_SKIRMISH_PROBE_PASS backend=METAL train=1 move=1 walk=1 attack=1 damage=5 victory=1 winner=2
```

Summary checks included `seeded_setup=true` and `victory_dispatch=true`.

Save/load scenario-level roundtrip:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_save_load_probe.py \
  --output-dir qa-output/sovereign-save-load-scenario-metadata
```

Observed:

```text
SOVEREIGN_SAVE_LOAD_PROBE_PASS state=1 entities=1 player=1 scenario=1 queue=1 tech=1 combat=1 resume=1
```

Restore summary includes:

- scenario id `two_player_skirmish`
- map seed `20260505`
- author notes from the sidecar fixture
- victory mode `conquest`
- victory label `Conquest`

## Completed Slice 24 — Scenario Setup Profiles And Victory Persistence

Implemented:

- Added scenario setup profiles:
  - `standard_skirmish`
  - `fast_skirmish`
- Added starting-resource presets:
  - `standard`
  - `generous`
  - `low`
- Added `setup` sidecar metadata for generated editor scenarios and the default
  `two_player_skirmish` fixture.
- Added `scenario_setup()` and `scenario_player_starting_resources()` so runtime
  player resources resolve from a preset, then apply per-player overrides.
- Extended scenario validation for unknown setup profiles, resource presets,
  and setup victory modes.
- Added `victory_progress_state()` for longer skirmish state snapshots:
  alive factions, defeated factions, winner, mode/label, and elapsed ticks.
- Extended Sovereign save/load payloads with `victory_state`, and made restore
  fail if victory progress is missing or malformed.
- Extended editor scenario, skirmish, and save/load probes to verify setup
  profile, preset, resolved resources, and victory-state persistence.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/scenario.py \
  scripts/sovereign/editor_scenario.py \
  scripts/sovereign/systems/skirmish.py \
  scripts/sovereign/session_state.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py \
  scripts/macos/pf_sovereign_skirmish_probe.py \
  scripts/macos/pf_sovereign_save_load_probe.py
```

Editor-exported stress sidecar through Metal runtime:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-metadata-report/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-scenario-setup-profiles
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=4 objects=68 train=1 victory=1
```

Summary checks included:

- `setup_profile=true`
- `seeded_setup=true`
- `victory_dispatch=true`
- player 1 resolved resources: food `520`, wood `520`, gold `260`, stone `180`

Skirmish loop with setup profile and victory progress:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_skirmish_probe.py \
  --output-dir qa-output/sovereign-skirmish-setup-profiles
```

Observed:

```text
SOVEREIGN_SKIRMISH_PROBE_PASS backend=METAL train=1 move=1 walk=1 attack=1 damage=5 victory=1 winner=2
```

Summary checks included `setup_profile=true`, and victory progress recorded:

- alive factions: `[2]`
- defeated factions: `[1]`
- winner: `2`
- mode: `conquest`

Save/load victory-state roundtrip:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_save_load_probe.py \
  --output-dir qa-output/sovereign-save-load-victory-state
```

Observed:

```text
SOVEREIGN_SAVE_LOAD_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
```

Restore summary includes:

- setup profile `standard_skirmish`
- starting-resource preset `standard`
- victory state mode `conquest`
- alive factions `[1, 2]`
- defeated factions `[]`
- elapsed ticks `37`

## Completed Slice 25 — Editor Setup Profile Controls

Implemented:

- Added visible Sovereign editor controls for setup profile selection.
- Added visible Sovereign editor controls for starting-resource preset
  selection.
- Added compact preset resource readout in the authoring tab.
- Persisted `setup.profile` and `setup.starting_resource_preset` from editor
  authoring state into the exported `.sovereign.json` sidecar.
- Added setup metadata to the sidecar `export_report`.
- Restored setup profile and resource preset when a saved sidecar is reloaded
  into the editor authoring tab.
- Extended the packaged editor workflow probe to choose the non-default
  `fast_skirmish` profile and `generous` resource preset, then fail if save or
  reload loses those values.
- Extended the runtime editor-scenario probe to compare runtime setup against
  the exported scenario setup instead of a hard-coded default.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/editor_scenario.py \
  scripts/editor/views/sovereign_tab_window.py \
  scripts/editor/main.py \
  scripts/macos/pf_sovereign_editor_scenario_probe.py
```

Packaged editor save/export stress probe:

```sh
env PF_EDITOR_WORKFLOW_PROBE=1 \
  PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
  PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
  PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1 \
  PF_EDITOR_SOVEREIGN_AUTHORING_STRESS_PROBE=1 \
  PF_EDITOR_WORKFLOW_PROBE_OUTPUT_DIR=qa-output/sovereign-editor-setup-controls \
  ./bin/pf-arm64 ./ ./scripts/editor/main.py
```

Observed:

```text
EDITOR_WORKFLOW_READY backend=METAL renderer=Apple M2 Max saved_map=qa-output/sovereign-editor-setup-controls/editor_workflow_probe.pfmap saved_scene=qa-output/sovereign-editor-setup-controls/editor_workflow_probe.pfscene placed_objects=2 saved_objects=2 sovereign_sidecar=qa-output/sovereign-editor-setup-controls/editor_workflow_probe.sovereign.json sovereign_markers=32
```

Packaged editor sidecar reload probe:

```sh
env PF_EDITOR_WORKFLOW_PROBE=1 \
  PF_EDITOR_WORKFLOW_PROBE_RELOAD_ONLY=1 \
  PF_EDITOR_WORKFLOW_PROBE_AUTOQUIT=1 \
  PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1 \
  PF_EDITOR_SOVEREIGN_AUTHORING_RELOAD_PROBE=1 \
  PF_EDITOR_WORKFLOW_PROBE_EXPECT_OBJECTS=2 \
  ./bin/pf-arm64 ./ ./scripts/editor/main.py \
    qa-output/sovereign-editor-setup-controls/editor_workflow_probe.pfmap \
    qa-output/sovereign-editor-setup-controls/editor_workflow_probe.pfscene
```

Observed:

```text
EDITOR_WORKFLOW_RELOAD_READY backend=METAL renderer=Apple M2 Max loaded_objects=2 sovereign_sidecar=qa-output/sovereign-editor-setup-controls/editor_workflow_probe.sovereign.json sovereign_markers=32
```

Metal runtime sidecar probe:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_editor_scenario_probe.py \
  --scenario qa-output/sovereign-editor-setup-controls/editor_workflow_probe.sovereign.json \
  --output-dir qa-output/sovereign-editor-setup-controls-runtime
```

Observed:

```text
SOVEREIGN_EDITOR_SCENARIO_PROBE_PASS backend=METAL export=1 reload=1 players=4 objects=68 train=1 victory=1
```

Saved sidecar and export report both contain:

```text
profile=fast_skirmish
starting_resource_preset=generous
victory_mode=conquest
```

Runtime setup resolved:

```text
profile_label=Fast Skirmish
starting_resource_preset_label=Generous
starting_resources={food:500, wood:500, gold:200, stone:100}
```

`git diff --check` passed for the touched files.

## Completed Slice 26 — Long Skirmish Session Probe

Implemented:

- Added `scripts/macos/pf_sovereign_long_skirmish_probe.py`.
- The probe stages a longer Sovereign skirmish session in Metal:
  - loads the two-player scenario fixture through the scenario runtime path
  - runs villager food gathering and drop-off
  - builds an extra house
  - trains a player militia and leaves another queued item pending
  - trains two scripted enemy attack-wave units
  - verifies enemy movement before combat
  - applies staged attack damage
  - records conquest victory progress before and after player defeat
  - writes a native `.pfsave`
  - reloads the session and verifies restored scenario, victory, player,
    production, research, combat, and entity-tag state
  - resumes the queued production item after restore
- Added a restore marker prefix hook in `scripts/sovereign/session_state.py` so
  the shared restore path can emit a probe-specific pass marker.
- Added `docs/sovereign/repo_publish_handoff.md` for the future
  `sovereign-realms-engine` GitHub organization repo and local sibling folder
  shape.

Verification:

```sh
python3 -m py_compile \
  scripts/macos/pf_sovereign_long_skirmish_probe.py \
  scripts/sovereign/session_state.py
```

Long skirmish session:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_long_skirmish_probe.py \
  --output-dir qa-output/sovereign-long-skirmish-session
```

Observed:

```text
SOVEREIGN_LONG_SKIRMISH_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
```

Pre-save staged summary:

```text
qa-output/sovereign-long-skirmish-session/summary_sovereign_long_skirmish.json
```

Restore summary:

```text
qa-output/sovereign-long-skirmish-session/summary_sovereign_long_skirmish_restore.json
```

Observed staged checks:

- economy gather/drop-off: true
- extra house construction: true
- player production: true
- enemy waves: true
- wave movement: true
- attack damage: true
- victory progress: winner `2`
- native session save/load: true
- queued production resumed after restore: true

## Completed Slice 27 — Skirmish AI Decision Depth

Implemented:

- Extended `scripts/sovereign/systems/skirmish.py` with small AI decision
  helpers:
  - resource shortfall detection
  - population-space detection
  - attack-wave readiness
  - train/wait/attack/build-house/gather decision logging
  - unit-count and available-population helpers
- Added `scripts/macos/pf_sovereign_ai_decision_probe.py`.
- The probe stages a deterministic Metal two-player skirmish fixture and
  verifies that the scripted AI can:
  - decide to gather when food/gold are short
  - decide to build a house when population is capped
  - recover population after a house is completed
  - train two militia from decisions
  - switch to attack once the wave threshold is met
  - issue a movement/attack-wave order to the trained units

This remains decision-depth scaffolding, not a full tactical AI planner.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_decision_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_decision_probe.py \
  --output-dir qa-output/sovereign-ai-decision-depth
```

Observed:

```text
SOVEREIGN_AI_DECISION_PROBE_PASS resource=1 pop=1 train=1 attack=1 decisions=5
```

Regression probes:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_skirmish_probe.py \
  --output-dir qa-output/sovereign-skirmish-ai-decision-regression
```

Observed:

```text
SOVEREIGN_SKIRMISH_PROBE_PASS backend=METAL train=1 move=1 walk=1 attack=1 damage=5 victory=1 winner=2
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_long_skirmish_probe.py \
  --output-dir qa-output/sovereign-long-skirmish-ai-decision-regression
```

Observed:

```text
SOVEREIGN_LONG_SKIRMISH_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
```

Summary:

```text
qa-output/sovereign-ai-decision-depth/summary_sovereign_ai_decision.json
```

Key summary facts:

- Checks all true: runtime scene, resource shortfall decision, population
  block decision, population recovery, training decision, trained units,
  attack-ready decision, attack order, and decision log.
- Decision sequence: `gather_resources`, `build_house`, `train`, `train`,
  `attack`.
- AI snapshot includes two trained militia and a full decision log.

## Completed Slice 28 — Sovereign Repo Packaging And Push Prep

Implemented:

- Added `scripts/macos/verify_sovereign_publish_ready.py`.
- The preflight checks:
  - required license/planning files
  - `scripts/sovereign/`, `assets/sovereign/`, and asset-validation tooling
  - required artifact ignore patterns
  - tracked local artifacts that should not ship to the organization repo
  - `sovereign` remote presence/shape
  - branch/status warnings
- Updated `.gitignore` for local `.pfsave`, `.gputrace`, and `.trace`
  artifacts.
- Updated `README.md` with the intended
  `sovereignrealms/sovereign-realms-engine` target and publish preflight
  command.
- Updated `NOTICE.md` and `CHANGES.md` so the Sovereign fork has visible
  modification and licensing context.
- Updated `docs/sovereign/repo_publish_handoff.md` with strict/non-strict
  preflight usage, known publish blockers, and local remote setup.
- Added the local `sovereign` remote:

```text
https://github.com/sovereignrealms/sovereign-realms-engine.git
```

Verification:

```sh
python3 -m py_compile scripts/macos/verify_sovereign_publish_ready.py
```

```sh
python3 scripts/macos/verify_sovereign_publish_ready.py
```

Observed:

```text
SOVEREIGN_PUBLISH_READY_PASS fails=0 warnings=8 strict=0
```

The warnings are expected for this active working tree. They identify tracked
local notebook/save artifacts and the dirty worktree. The final organization
push should use:

```sh
python3 scripts/macos/verify_sovereign_publish_ready.py --strict
```

and should not proceed until the strict run passes.

Current strict result:

```text
SOVEREIGN_PUBLISH_READY_FAIL fails=0 warnings=8 strict=1
```

## Completed Slice 29 — Strict Publish Blocker Cleanup

Implemented:

- Created focused publish branch:

```text
codex/sovereign-publish-preflight
```

- Removed local-only artifacts from Git tracking without deleting local files:
  - `a.md`
  - `assets/maps/test.pfsave`
  - `session.pfsave`
  - `tmp_native_session_roundtrip.pfsave`
  - `tmp_native_session_region_camera_roundtrip.pfsave`
  - `tmp_native_session_ui_roundtrip.pfsave`
  - `tmp_native_session_ui_region_camera_roundtrip.pfsave`
- Added `a.md` to `.gitignore`; `.pfsave` files were already covered by the
  publish-preflight ignore update.

Verification after untracking:

```sh
python3 scripts/macos/verify_sovereign_publish_ready.py --strict
```

Observed:

```text
SOVEREIGN_PUBLISH_INFO branch=codex/sovereign-publish-preflight
SOVEREIGN_PUBLISH_WARN working_tree_has_changes count=58
SOVEREIGN_PUBLISH_READY_FAIL fails=0 warnings=1 strict=1
```

Interpretation:

- The artifact-specific strict blockers are resolved.
- The only remaining strict blocker is the dirty working tree. A focused commit
  on this branch is the last step before strict publish preflight can pass.

Final publish-preflight commit:

```text
76cf7de0 Prepare Sovereign Realms engine publish branch
```

Final strict verification:

```sh
python3 scripts/macos/verify_sovereign_publish_ready.py --strict
```

Observed:

```text
SOVEREIGN_PUBLISH_INFO branch=codex/sovereign-publish-preflight
SOVEREIGN_PUBLISH_READY_PASS fails=0 warnings=0 strict=1
```

## Remaining Plan Status

Most of the first playable Sovereign vertical-slice foundation is now in place.
Rough status against the ten-phase plan:

- Phases 0-1: repo bootstrap and Metal baseline are functionally in place, but
  upstream PR hygiene remains separate from Sovereign organization packaging.
  The Sovereign publish preflight/checklist is now in place.
- Phases 2-3: asset pipeline seed and data-driven definitions are in place;
  real production art/validation depth remains.
- Phases 4-7: economy, production/population, age/tech, combat counters,
  projectiles, and first skirmish proof are in place as MVP probes.
- Phase 8: editor workflow is now strong for sidecar metadata, placement,
  validation, reload, stress fixtures, setup profiles, resource presets, and
  reports.
- Phase 9: AI/skirmish loop is still basic but now has explicit decision
  helpers for resource shortfall, population blocks, training, attack-wave
  readiness, deterministic enemy economy, train wave, movement, facing combat,
  victory dispatch, longer staged save/load coverage, and persistence hooks.
  It is not yet a real economy planner or tactical AI.
- Phase 10: performance, Retina clarity, HD/4K assets, large-map benchmarks,
  and production polish remain the largest open area.

Overall: the technical vertical-slice scaffold is roughly 73-77% complete for
an MVP skirmish foundation. It is not yet production-game-ready because real
assets, deeper AI, full editor UX polish, scale/performance benchmarking,
save/load of longer live orders, and HD/Retina presentation still need focused
slices.

## Next Slice

The next clean target is either:

- resolve strict publish blockers for `sovereign-realms-engine` by removing or
  relocating tracked local notebooks/save artifacts on a focused publish branch,
  or
- continue gameplay depth with tactical AI/build-order planning after the
  packaging path is cleanly documented.
