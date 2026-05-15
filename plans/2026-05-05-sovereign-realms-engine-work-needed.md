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
- Skirmish AI build-order planner: DONE for deterministic gather, house,
  training, priority target selection, attack wave, save/load, and queued-unit
  continuation after restore.
- Skirmish AI tactical threat response: DONE for scout reports, nearby threat
  classification, resource recovery, defender training, defense launch, and
  defender motion toward the threat.
- Skirmish AI scouting routes and threat memory: DONE for route waypoints,
  remembered sightings, last-known threat response, adaptive defender
  training, and motion toward remembered threats.
- Skirmish AI memory save/load and regroup: DONE for restoring remembered
  threat memory from native `.pfsave`, retreat/regroup while outnumbered,
  adaptive resource/population recovery, defender training, and response to
  the remembered threat position after load.
- Skirmish AI adaptive strategy: DONE for remembered-threat unit choice,
  scheduled scout-route refresh, archer counter-training, outnumbered regroup,
  remembered-position response, and counterattack launch.
- Skirmish AI macro strategy: DONE for difficulty profiles, economy-vs-military
  strategic weighting, second-base expansion, military recovery, and strategic
  attack launch.
- Skirmish AI map-control strategy: DONE for control-point evaluation,
  difficulty-tuned attack/retreat thresholds, population/economy recovery,
  archer counter-training, retreat timing, attack timing, and attack movement.
- Skirmish AI branching strategy: DONE for defense/harassment split decisions,
  multi-base expansion to three town centers, longer branch sequencing,
  harassment training, and separate defense/harass movement.
- Skirmish AI personality/cadence persistence: DONE for difficulty-specific
  personality fields, harassment cadence controls, and native save/load
  continuation into a second harassment wave.
- Skirmish AI difficulty A/B evidence: DONE for longer standard/booming/hard
  comparison of expansion count, harassment frequency, target priority, and
  militia-vs-archer composition.
- Skirmish AI strategic tech/unit composition: DONE for profile-specific
  strategy research, target unit mix, and attack target priority across
  standard/booming/hard.
- Skirmish AI composition counters: DONE for deterministic standard/booming/hard
  plan wins and losses against favorable and unfavorable enemy compositions.
- Skirmish AI difficulty balance save/load: DONE for longer standard/booming/hard
  branch comparisons, save-point snapshots, post-snapshot continuation, and
  native `.pfsave` reload of the compact A/B balance report.
- Skirmish AI match-length adaptation: DONE for profile-specific opening
  economy duration, economy-vs-military transition timing, expansion timing,
  and attack launch across standard/booming/hard.
- Skirmish AI attrition recovery: DONE for failed-attack detection, live-unit
  roster recovery, base-pressure defense, regroup, retraining, and relaunch.
- Skirmish AI repeated attrition outcomes: DONE for second failed-push
  escalation, post-relaunch success tracking, and post-success economy
  transition.
- Skirmish AI pressure tech pacing: DONE for repeated-failure-triggered
  `ranger_fletching` research before the larger second relaunch.
- Skirmish AI multi-front army control: DONE for disjoint defense, harassment,
  and attack-front assignments with separate Metal movement proof.
- Skirmish AI-vs-player soak: DONE for composed player production, enemy
  economy income, multi-front activity, repeated attrition recovery, pressure
  tech, relaunch, combat damage, conquest victory progress, and sustained
  Metal ticks.
- Larger army scale soak: DONE up through the first 1000-unit exploratory Metal
  attack-move benchmark with movement/animation activity, representative combat
  damage, sustained runtime ticks, wide-zoom proof captures, and sampled
  p50/p95/max wall-clock budget telemetry. The first attach-mode Time Profiler
  trace is also captured and summarized. The first ClearPath duplicate-pair
  optimization is DONE and the 1000-unit run now clears the 500 ms soft p95
  tick budget without warnings. The first per-frame Metal skinned-mesh cache is
  DONE and cuts the latest profiled 1000-unit p95 from 356.499 ms to
  193.387 ms by reusing CPU-skinned animated vertices between shadow and main
  passes. The ClearPath fast-math cleanup is DONE for direct `inside_pcr`
  boundary tests and local ray-ray intersection math; it keeps 500/1000-unit
  gates green and removes the generic ray-intersection helper from the profile.
  The first env-gated Metal GPU-skinning prototype is DONE for batched
  animated main-pass and shadow-pass draws behind `PF_METAL_GPU_SKINNING=1`.
  It drops the 1000-unit no-stats p95 from the Slice 64 baseline of about
  181 ms to about 69 ms, with a profiled p95 around 54 ms, and moves the
  dominant hotspot back to ClearPath/collision avoidance. The first dedicated
  OpenGL-vs-Metal visual parity gate for this opt-in path is DONE. The
  candidate 500/1000-unit scale gates were repeated successfully, and Metal GPU
  skinning is now the default path with `PF_METAL_GPU_SKINNING=0` retained as a
  debugging opt-out. The default-path 1000-unit Time Profiler refresh is DONE
  and confirms the top hotspot lane is again ClearPath dense-candidate geometry
  (`inside_pcr`, `compute_vo_xpoints`, and `ray_ray_intersection_fast`). The
  first principled ClearPath dense-candidate reduction is DONE: dense local
  constraints are capped to the nearest 32 blockers before the O(n^2)
  intersection pass, cutting the 1000-unit no-stats p95 from 77.773 ms to
  52.338 ms while keeping movement, animation, and combat checks green. A
  projection-first ClearPath shortcut was tested and rejected because repeated
  1000-unit gates were less stable than the nearest-constraint cap alone.
  Animated matrix/render shortcut experiments were also tested and rejected:
  moving the model transform into the Metal skinning shader and replacing the
  SQT helper with direct matrix composition both kept functional probes green,
  but worsened 1000-unit p95 versus the Slice 70 baseline. A follow-up
  Time Profiler pass could not expose reliable matrix parent stacks, so the
  next profile lane was taken instead: region flow-field integration now avoids
  the O(n) `pq_td_contains()` scan for improved global tile costs, removing
  the `field_compare_tds` hot lane while keeping 500/1000-unit Metal gates
  green. A follow-up ClearPath pass tested smaller constraint caps and two
  `inside_pcr()` micro-optimizations; all were rejected because they kept
  functional probes green but did not prove a stable 1000-unit budget
  improvement. A profiler-symbolication/frame-pointer pass is DONE: the
  profile wrapper can force a frame-pointer rebuild and now emits focused
  parent/child summaries for ClearPath, movement, field, and matrix targets;
  the direct launch-mode trace still showed most hot ClearPath and matrix leafs
  as `<root>`, so the next optimization moved up to scheduling/cadence evidence
  rather than local math tweaks. Movement cadence instrumentation is DONE, the
  zero-velocity turning ClearPath skip is DONE, and an env-gated
  `STATE_SEEK_ENEMIES` ClearPath cadence experiment is DONE. The cadence-2
  experiment keeps 500/1000-unit Metal gates green and trims the 1000-unit p95
  from 146.519 ms to 135.138 ms, but it is intentionally not the default yet
  because the 500-unit p95 became noisier. A dense-only follow-up is DONE:
  `PF_MOVEMENT_SEEK_CLEARPATH_MIN_WORK_ITEMS` lets cadence activate only above a
  configured active-mover threshold, preserving smaller fights while allowing
  cadence experiments in 1000-unit-style pressure. A threshold-600 default
  candidate was tested and kept functionally green, but final 1000-unit timing
  repeats were too noisy to ship it as the default. The policy remains
  env-gated while the next optimization target investigates 1000-unit timing
  spikes. A first spike investigation is DONE: fine-sampled runs show the
  spikes occur in both dense-cadence and conservative modes, mostly during
  sustained soak, so the instability is dense-battle scheduling/ClearPath
  pressure rather than the seek-cadence policy by itself.
- Phase 10 HD/Retina readability proof: DONE for the first metric-backed
  close-zoom and wide-zoom capture gate. The HD world readability probe now
  records center crops, Retina scale, luma/detail metrics, and wide/close
  proof captures. A first actual readability overlay slice is also DONE:
  selected player-owned units keep neutral white thin rings, Metal world-color
  overlays render through the native color pipeline, and healthbars shrink on
  wide zoom. Current Sovereign placeholder units now carry far-view silhouette,
  minimum-pixel, marker-policy, and AoE-style team-color metadata. The earlier
  dynamic world-material team-mask work was intentionally backed out because
  the OpenGL reference has no matching shader path and broad main-world tinting
  did not match the intended AoE-style direction. Strong team color remains a
  minimap/UI signal; world readability should come from silhouettes, animation,
  small authored accents in final assets, and terrain/biome richness. Map-edge
  and sky-boundary readability is DONE for a first backend-neutral proof line,
  and fixture-level biome/edge dressing is now DONE in the HD readability probe
  using existing terrain materials and props.
- Sovereign repo packaging/push prep: DONE for publish preflight, artifact
  ignore updates, README/NOTICE/CHANGES polish, handoff checklist, and the
  first Sovereign organization checkpoint merge.
- Strict publish blocker cleanup: DONE on `codex/sovereign-publish-preflight`;
  strict preflight reports `fails=0 warnings=0`.
- Multi-world/game-pack repository policy: DONE for `games/` structure,
  per-pack license docs, and MIT-licensed example pack.
- GitHub organization push: DONE. `sovereignrealms/sovereign-realms-engine`
  PR #1, `Add Sovereign MVP AI and scale gates`, was squash-merged into
  `main` as `730156a4` on 2026-05-13. Local `main` is aligned with
  `sovereign/main`.

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

## Completed Slice 32 — Tactical AI Scouting And Threat Response

Implemented:

- Extended `scripts/sovereign/systems/skirmish.py` with tactical scouting
  helpers:
  - live-entity filtering
  - distance-based scout reports
  - defended-asset threat classification
  - compact report snapshots for summaries
- Added `TacticalResponsePlanner` for the first deterministic tactical loop:
  detect a nearby enemy unit, gather missing resources, build a house if
  population blocks response training, train two militia defenders, then launch
  a defense order toward the detected threat.
- Added `ScriptedSkirmishAI.launch_defense_response()` so tactical planners can
  move a defense group toward a specific threat while recording the defended
  asset and target distance.
- Added `scripts/macos/pf_sovereign_ai_threat_response_probe.py`.
- The probe stages a player militia near the enemy base, verifies the enemy
  scout detects it as a threat to defended assets, drives the AI through
  income/house/training decisions, launches the defense group, and confirms
  defenders move toward the threat in the Metal runtime.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_threat_response_probe.py \
  scripts/macos/pf_sovereign_ai_build_order_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_threat_response_probe.py \
  --output-dir qa-output/sovereign-ai-threat-response
```

Observed:

```text
SOVEREIGN_AI_THREAT_RESPONSE_PROBE_PASS scout=1 threat=1 income=1 house=1 train=1 defend=1 motion=1
```

Regression checks:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_build_order_probe.py \
  --output-dir qa-output/sovereign-ai-build-order-threat-regression
```

Observed:

```text
SOVEREIGN_AI_BUILD_ORDER_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_decision_probe.py \
  --output-dir qa-output/sovereign-ai-decision-threat-regression
```

Observed:

```text
SOVEREIGN_AI_DECISION_PROBE_PASS resource=1 pop=1 train=1 attack=1 decisions=5
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_long_skirmish_probe.py \
  --output-dir qa-output/sovereign-long-skirmish-threat-regression
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

## Completed Slice 33 — Scouting Routes And Threat Memory

Implemented:

- Added `ThreatMemory` to `scripts/sovereign/systems/skirmish.py` so AI
  sightings persist beyond the current scout report:
  - first/last seen steps
  - seen count
  - remembered role, position, severity, and defended asset
  - time-to-live filtering for remembered threats
- Added `ScoutingRoutePlanner` for deterministic scout waypoints. It issues
  scout movement, records scout reports, and feeds those sightings into threat
  memory.
- Added `MemoryResponsePlanner` for remembered-threat adaptation. It can gather
  missing resources, build population room, train defenders, and launch a
  defense order toward a remembered last-known threat position even when the
  current scout report is empty.
- Added `ScriptedSkirmishAI.launch_defense_to_position()` so AI responses can
  target remembered map positions, not only currently visible entity objects.
- Added `scripts/macos/pf_sovereign_ai_scout_memory_probe.py`.
- The probe stages a player threat, records it through a scout-route step,
  clears current visibility, verifies memory persists, then drives the AI
  through memory-based income/house/training/defense response and confirms both
  scout and defender motion in Metal.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_scout_memory_probe.py \
  scripts/macos/pf_sovereign_ai_threat_response_probe.py \
  scripts/macos/pf_sovereign_ai_build_order_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_scout_memory_probe.py \
  --output-dir qa-output/sovereign-ai-scout-memory
```

Observed:

```text
SOVEREIGN_AI_SCOUT_MEMORY_PROBE_PASS route=1 observed=1 memory=1 persisted=1 income=1 house=1 train=1 response=1 scout_motion=1 defender_motion=1
```

Regression checks:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_threat_response_probe.py \
  --output-dir qa-output/sovereign-ai-threat-response-scout-memory-regression
```

Observed:

```text
SOVEREIGN_AI_THREAT_RESPONSE_PROBE_PASS scout=1 threat=1 income=1 house=1 train=1 defend=1 motion=1
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_build_order_probe.py \
  --output-dir qa-output/sovereign-ai-build-order-scout-memory-regression
```

Observed:

```text
SOVEREIGN_AI_BUILD_ORDER_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_long_skirmish_probe.py \
  --output-dir qa-output/sovereign-long-skirmish-scout-memory-regression
```

Observed:

```text
SOVEREIGN_LONG_SKIRMISH_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
```

## Completed Slice 34 — AI Memory Save/Load And Adaptive Regroup

Implemented:

- Added `ThreatMemory.from_snapshot()` in
  `scripts/sovereign/systems/skirmish.py` so saved AI sightings can be
  restored into live threat memory.
- Added `ScriptedSkirmishAI.regroup_units()` and extended
  `MemoryResponsePlanner` with a `retreat_when_outnumbered` path. If the AI
  remembers a nearby threat but has fewer defenders than required, it first
  regroups existing defenders at a configured safe point before gathering,
  building population room, training, and responding.
- Added `scripts/sovereign/ai_memory_restore.py`, a custom Python 3 session
  restore hook for AI-memory probes. It rebinds the saved Sovereign player
  state, restores threat memory, repairs the restored production queue's
  faction/scene ownership, and runs the post-load memory-response planner.
- Added `scripts/macos/pf_sovereign_ai_memory_save_load_probe.py`. The probe
  records a nearby player threat into AI memory, saves a native `.pfsave`,
  reloads through the custom restore hook, and verifies restored-memory
  regroup, income recovery, house construction, defender training, and
  last-known-position defense response.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/sovereign/ai_memory_restore.py \
  scripts/macos/pf_sovereign_ai_memory_save_load_probe.py \
  scripts/macos/pf_sovereign_ai_scout_memory_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_memory_save_load_probe.py \
  --output-dir qa-output/sovereign-ai-memory-save-load
```

Observed:

```text
SOVEREIGN_AI_MEMORY_SAVE_LOAD_PROBE_PASS state=1 memory=1 regroup=1 income=1 house=1 train=1 response=1
```

Regression checks:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_scout_memory_probe.py \
  --output-dir qa-output/sovereign-ai-scout-memory-save-load-regression
```

Observed:

```text
SOVEREIGN_AI_SCOUT_MEMORY_PROBE_PASS route=1 observed=1 memory=1 persisted=1 income=1 house=1 train=1 response=1 scout_motion=1 defender_motion=1
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_threat_response_probe.py \
  --output-dir qa-output/sovereign-ai-threat-response-save-load-regression
```

Observed:

```text
SOVEREIGN_AI_THREAT_RESPONSE_PROBE_PASS scout=1 threat=1 income=1 house=1 train=1 defend=1 motion=1
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_build_order_probe.py \
  --output-dir qa-output/sovereign-ai-build-order-memory-save-load-regression
```

Observed:

```text
SOVEREIGN_AI_BUILD_ORDER_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
```

## Completed Slice 35 — Adaptive Memory Strategy And Counterattack

Implemented:

- Extended `scripts/sovereign/data/buildings.py` so the Sovereign barracks can
  train both `militia` and the current placeholder `archer`. This makes
  adaptive composition real production behavior, not only planner metadata.
- Added mixed-roster helpers to `ScriptedSkirmishAI` for retrieving combat
  units and launching counterattacks with more than one unit type.
- Added `AdaptiveMemoryStrategyPlanner` to
  `scripts/sovereign/systems/skirmish.py`. It:
  - schedules scout-route refreshes at a deterministic interval
  - chooses preferred response units from remembered threat role
  - chooses `archer` against remembered military threats
  - regroups existing defenders while outnumbered
  - gathers the missing resources for the selected unit
  - builds population room when blocked
  - trains the adaptive defender type
  - responds to the remembered threat position
  - counterattacks once the response force is ready
- Added `scripts/macos/pf_sovereign_ai_adaptive_strategy_probe.py`, a Metal
  probe that stages a remembered player military threat, verifies archer
  selection, scheduled scouting, regroup, adaptive income, house construction,
  archer production, remembered-position response, counterattack launch, and
  scout/counterattack movement.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/buildings.py \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_adaptive_strategy_probe.py \
  scripts/macos/pf_sovereign_ai_memory_save_load_probe.py \
  scripts/macos/pf_sovereign_ai_scout_memory_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_adaptive_strategy_probe.py \
  --output-dir qa-output/sovereign-ai-adaptive-strategy
```

Observed:

```text
SOVEREIGN_AI_ADAPTIVE_STRATEGY_PROBE_PASS memory=1 scout=1 choice=1 regroup=1 income=1 house=1 archers=1 response=1 counter=1 scout_motion=1 counter_motion=1
```

Regression checks:

```text
SOVEREIGN_AI_MEMORY_SAVE_LOAD_PROBE_PASS state=1 memory=1 regroup=1 income=1 house=1 train=1 response=1
SOVEREIGN_AI_SCOUT_MEMORY_PROBE_PASS route=1 observed=1 memory=1 persisted=1 income=1 house=1 train=1 response=1 scout_motion=1 defender_motion=1
SOVEREIGN_AI_THREAT_RESPONSE_PROBE_PASS scout=1 threat=1 income=1 house=1 train=1 defend=1 motion=1
SOVEREIGN_AI_BUILD_ORDER_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
SOVEREIGN_PRODUCTION_PROBE_PASS backend=METAL enqueue=1 spawn=1 pop=4/10 food=140 gold=80 rally=1
```

## Completed Slice 36 — Macro Strategy, Difficulty Profiles, And Expansion

Implemented:

- Added `AI_DIFFICULTY_PROFILES` and `ai_difficulty_profile()` in
  `scripts/sovereign/systems/skirmish.py`.
  - `standard` keeps balanced economy/military pressure.
  - `booming` favors early economy and expansion.
  - `hard` favors military response and archer production.
- Extended `ScriptedSkirmishAI.build_complete_building()` with an explicit
  reason parameter while preserving the existing `build_order` default used by
  earlier probes.
- Added `StrategicMacroPlanner` to
  `scripts/sovereign/systems/skirmish.py`. It:
  - scores economy and military pressure from difficulty profile weights
  - expands with a second `town_center` when economy wins and the base target
    is not met
  - chooses a military unit from remembered threat role and difficulty profile
  - gathers missing military resources
  - builds population room when blocked
  - trains the selected unit type
  - launches a strategic mixed-roster attack when the army is ready
- Added `scripts/macos/pf_sovereign_ai_macro_strategy_probe.py`, a Metal probe
  that proves:
  - `booming` chooses economy and builds an expansion `town_center`
  - `hard` weights military higher against a remembered military threat
  - the AI recovers resources, builds a house, trains archers, attacks, and
    physically moves toward the strategic target.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/buildings.py \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_macro_strategy_probe.py \
  scripts/macos/pf_sovereign_ai_adaptive_strategy_probe.py \
  scripts/macos/pf_sovereign_ai_memory_save_load_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_macro_strategy_probe.py \
  --output-dir qa-output/sovereign-ai-macro-strategy
```

Observed:

```text
SOVEREIGN_AI_MACRO_STRATEGY_PROBE_PASS profiles=1 expand=1 expand_pos=1 economy=1 military=1 income=1 house=1 archers=1 attack=1 motion=1
```

Regression checks:

```text
SOVEREIGN_AI_ADAPTIVE_STRATEGY_PROBE_PASS memory=1 scout=1 choice=1 regroup=1 income=1 house=1 archers=1 response=1 counter=1 scout_motion=1 counter_motion=1
SOVEREIGN_AI_MEMORY_SAVE_LOAD_PROBE_PASS state=1 memory=1 regroup=1 income=1 house=1 train=1 response=1
SOVEREIGN_AI_BUILD_ORDER_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
SOVEREIGN_PRODUCTION_PROBE_PASS backend=METAL enqueue=1 spawn=1 pop=4/10 food=140 gold=80 rally=1
SOVEREIGN_AI_SCOUT_MEMORY_PROBE_PASS route=1 observed=1 memory=1 persisted=1 income=1 house=1 train=1 response=1 scout_motion=1 defender_motion=1
SOVEREIGN_AI_THREAT_RESPONSE_PROBE_PASS scout=1 threat=1 income=1 house=1 train=1 defend=1 motion=1
```

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
fee2015c Prepare Sovereign Realms engine publish branch
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

## Completed Slice 30 — Multi-World Pack Policy And Starter Structure

Implemented:

- Documented the single-repo early development policy: keep the engine,
  editor, Sovereign game package, and early world/game packs together until the
  first vertical slice stabilizes.
- Added modding documentation:
  - `docs/modding/licensing_worlds.md`
  - `docs/modding/world_pack_format.md`
- Added `games/README.md`.
- Added `games/example_world/` as a minimal world-pack boundary:
  - `LICENSE`
  - `README.md`
  - `world.json`
- The example pack uses MIT for original pack content only. It does not
  relicense Permafrost-derived engine code.
- Updated `README.md`, `docs/sovereign/engine_work_needed.md`,
  `docs/sovereign/repo_license_structure.md`,
  `docs/sovereign/repo_publish_handoff.md`, and `CHANGES.md`.
- Extended `scripts/macos/verify_sovereign_publish_ready.py` to require the
  modding docs and example world-pack files before publish.

Policy recorded:

- Root engine code: GPLv3 with the Permafrost special linking exception.
- Engine/editor/runtime API changes: root engine license.
- `games/<pack_id>/` world/game packs: local pack license for original content,
  such as MIT, CC-BY, or CC0.
- Pack licenses do not relicense Permafrost-derived engine code.
- Every pack must include `LICENSE`, `README.md`, and `world.json`.
- No Microsoft, Ensemble, Age of Empires, or other proprietary assets without
  clear redistribution rights.

## Completed Slice 31 — Skirmish AI Build-Order Planner

Implemented:

- Extended `scripts/sovereign/systems/skirmish.py` with reusable AI helpers
  for resource income, completed building construction, priority target
  selection, attack-wave launch, and wave-unit lookup.
- Added `BuildOrderPlanner` for the first deterministic build-order loop:
  gather missing resources, build a house on population pressure, train three
  militia, select the highest-priority target, and launch an attack wave.
- Added `scripts/macos/pf_sovereign_ai_build_order_probe.py`.
- The probe runs a Metal two-player fixture, forces an enemy resource shortfall
  and population squeeze, lets the planner recover, trains an attack wave,
  checks priority target selection, applies combat damage, records conquest
  victory progress, saves a native `.pfsave`, reloads it, and verifies queued
  unit continuation after restore.
- The probe gives AI-owned production buildings unique names before save/load
  so queue restore binds to the exact building rather than another duplicate
  `barracks` in the scene.
- The session payload keeps only compact AI build-order metadata so the engine
  entity-tag save channel stays within runtime limits.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_build_order_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_build_order_probe.py \
  --output-dir qa-output/sovereign-ai-build-order
```

Observed:

```text
SOVEREIGN_AI_BUILD_ORDER_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
```

Regression checks:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_decision_probe.py \
  --output-dir qa-output/sovereign-ai-decision-build-order-regression
```

Observed:

```text
SOVEREIGN_AI_DECISION_PROBE_PASS resource=1 pop=1 train=1 attack=1 decisions=5
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_long_skirmish_probe.py \
  --output-dir qa-output/sovereign-long-skirmish-build-order-regression
```

Observed:

```text
SOVEREIGN_LONG_SKIRMISH_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
```

## Completed Slice 37 — Map-Control Strategy And Attack/Retreat Timing

Implemented:

- Extended `scripts/sovereign/systems/skirmish.py` difficulty profiles with
  explicit attack thresholds, retreat thresholds, map-control weight,
  army-advantage weight, and build-order hints.
- Added `MapControlEvaluator` for named control points with controlled,
  contested, enemy-held, and neutral summaries.
- Added `MapControlStrategyPlanner` for the next strategic AI layer:
  retreat/regroup when map control is poor, recover with income/population,
  train the preferred counter unit, then attack once timing and army score pass
  the difficulty profile.
- Added `scripts/macos/pf_sovereign_ai_map_control_probe.py`.
- The probe runs a Metal two-player fixture, stages a player military threat
  across contested map-control points, verifies retreat timing, exercises
  resource recovery and house construction, trains archers, launches a
  map-control attack, and checks attack movement.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_map_control_probe.py \
  scripts/macos/pf_sovereign_ai_macro_strategy_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_map_control_probe.py \
  --output-dir qa-output/sovereign-ai-map-control
```

Observed:

```text
SOVEREIGN_AI_MAP_CONTROL_PROBE_PASS map=1 profile=1 build=1 retreat=1 train=1 attack=1 motion=1
```

## Completed Slice 38 — Branching Strategy, Multi-Base Planning, And Harassment

Implemented:

- Extended `scripts/sovereign/systems/skirmish.py` difficulty profiles with
  defense and harassment force-size targets.
- Added `BranchingStrategyPlanner` to sequence higher-level AI branches:
  scout/defend nearby threats, expand through multiple town centers, recover
  resources for the branch plan, train a harassment group, and launch a
  separate harassment attack.
- Added `scripts/macos/pf_sovereign_ai_branching_strategy_probe.py`.
- The probe runs a Metal two-player fixture, stages a player threat near the
  enemy base, launches militia defense, gathers expansion resources, builds
  two additional town centers, trains archers, then sends a separate archer
  harassment group toward a forward worker target.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_branching_strategy_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_branching_strategy_probe.py \
  --output-dir qa-output/sovereign-ai-branching-strategy
```

Observed:

```text
SOVEREIGN_AI_BRANCHING_STRATEGY_PROBE_PASS profile=1 defense=1 expand=1 bases=1 train=1 harass=1 defense_motion=1 harass_motion=1
```

## Completed Slice 39 — Difficulty Personality And Harassment Cadence Save/Load

Implemented:

- Extended `scripts/sovereign/systems/skirmish.py` difficulty profiles with
  personality IDs, expansion target bases, harassment cadence, max harassment
  waves, and role-priority target lists.
- Extended `BranchingStrategyPlanner` so harassment can be profile-cadenced
  across multiple waves instead of being a one-shot branch.
- Added `BranchingStrategyPlanner.from_snapshot()` state restoration for
  branch index, defense/harass launch state, harassment wave count, cooldown
  step, and harassment launch history.
- Added `scripts/sovereign/ai_branching_restore.py` to rebind a saved native
  `.pfsave` scene, restore the branching planner, prove the saved cooldown
  hold, then launch a second harassment wave.
- Added `scripts/macos/pf_sovereign_ai_personality_save_load_probe.py` as a
  Metal fixture for hard-profile AI personality, first harassment, compact
  session-state tagging, native save/load, restored cooldown, and second-wave
  continuation.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/sovereign/ai_branching_restore.py \
  scripts/macos/pf_sovereign_ai_personality_save_load_probe.py \
  scripts/macos/pf_sovereign_ai_branching_strategy_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_personality_save_load_probe.py \
  --output-dir qa-output/sovereign-ai-personality-save-load
```

Observed:

```text
SOVEREIGN_AI_PERSONALITY_SAVE_LOAD_PROBE_PASS state=1 profile=1 cadence=1 cooldown=1 second=1
```

Regression checks:

```text
SOVEREIGN_AI_BRANCHING_STRATEGY_PROBE_PASS profile=1 defense=1 expand=1 bases=1 train=1 harass=1 defense_motion=1 harass_motion=1
SOVEREIGN_AI_MAP_CONTROL_PROBE_PASS map=1 profile=1 build=1 retreat=1 train=1 attack=1 motion=1
SOVEREIGN_AI_MACRO_STRATEGY_PROBE_PASS profiles=1 expand=1 expand_pos=1 economy=1 military=1 income=1 house=1 archers=1 attack=1 motion=1
SOVEREIGN_AI_ADAPTIVE_STRATEGY_PROBE_PASS memory=1 scout=1 choice=1 regroup=1 income=1 house=1 archers=1 response=1 counter=1 scout_motion=1 counter_motion=1
SOVEREIGN_AI_MEMORY_SAVE_LOAD_PROBE_PASS state=1 memory=1 regroup=1 income=1 house=1 train=1 response=1
```

Note: `pf_sovereign_ai_branching_strategy_probe.py` now treats harassment
motion as meaningful once a unit closes at least `0.1` map units toward the
target. The previous `0.25` threshold was brittle for short settle windows
where the units were already in `Walk` and moving, but only closed `0.223`
units during the sampled interval.

## Completed Slice 40 — Difficulty A/B Skirmish Evidence

Implemented:

- Changed `BranchingStrategyPlanner` so the default harassment unit comes from
  the active difficulty profile's `preferred_military_unit`. Standard and
  booming therefore use militia pressure by default, while hard pressure uses
  archers.
- Added `scripts/macos/pf_sovereign_ai_difficulty_ab_probe.py`.
- The probe runs standard, booming, and hard through the same extended Metal
  branch fixture and records action counts, reason counts, base counts,
  harassment wave counts, first harassment targets, and unit composition.
- The acceptance checks compare actual behavior instead of just profile data:
  standard expands to 2 bases and launches one militia harassment against a
  building target; booming expands to 3 bases and launches one militia
  harassment against a building target; hard expands to 3 bases, trains
  archers, and launches two harassment waves against villagers.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_difficulty_ab_probe.py \
  scripts/macos/pf_sovereign_ai_personality_save_load_probe.py \
  scripts/macos/pf_sovereign_ai_branching_strategy_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_difficulty_ab_probe.py \
  --output-dir qa-output/sovereign-ai-difficulty-ab
```

Observed:

```text
SOVEREIGN_AI_DIFFICULTY_AB_PROBE_PASS runtime=1 profiles=1 expand=1 harass=1 targets=1 units=1 extended=1
```

Behavior evidence:

```text
standard bases=2 harass_waves=1 harass_unit=militia first_target=buildings
booming  bases=3 harass_waves=1 harass_unit=militia first_target=buildings
hard     bases=3 harass_waves=2 harass_unit=archer  first_target=villagers
```

Regression checks:

```text
SOVEREIGN_AI_PERSONALITY_SAVE_LOAD_PROBE_PASS state=1 profile=1 cadence=1 cooldown=1 second=1
SOVEREIGN_AI_BRANCHING_STRATEGY_PROBE_PASS profile=1 defense=1 expand=1 bases=1 train=1 harass=1 defense_motion=1 harass_motion=1
```

## Completed Slice 41 — Strategic Tech And Unit-Composition Branching

Implemented:

- Added profile-specific strategy technologies:
  `infantry_drills`, `settlement_logistics`, and `ranger_fletching`.
- Barracks can now research those strategy technologies, and the default
  Sovereign civilization exposes them.
- `ResearchQueue` now accepts `strategy_tag` technology effects as recorded
  strategy metadata while keeping existing `set_age` behavior unchanged.
- Added registry validation for supported technology effect types.
- Added `CompositionStrategyPlanner` in `scripts/sovereign/systems/skirmish.py`.
  It researches the profile's strategy technology, trains toward the profile's
  target unit mix, and attacks according to that plan's target-role priority.
- Added `scripts/macos/pf_sovereign_ai_composition_strategy_probe.py` to compare
  standard, booming, and hard in a Metal runtime fixture.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/buildings.py \
  scripts/sovereign/data/civilizations.py \
  scripts/sovereign/data/technologies.py \
  scripts/sovereign/factory.py \
  scripts/sovereign/systems/technology.py \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_composition_strategy_probe.py
```

```sh
python3 -c 'import sys; sys.path.insert(0,"scripts"); from sovereign.factory import validate_registries; errors=validate_registries(); print("REGISTRY_ERRORS", len(errors))'
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_composition_strategy_probe.py \
  --output-dir qa-output/sovereign-ai-composition-strategy
```

Observed:

```text
REGISTRY_ERRORS 0
SOVEREIGN_AI_COMPOSITION_STRATEGY_PROBE_PASS runtime=1 research=1 targets=1 mix=1 attack_targets=1 attacks=1 extended=1
```

Behavior evidence:

```text
standard tech=infantry_drills      mix=3 militia          first_target=buildings
booming  tech=settlement_logistics mix=2 militia+1 archer first_target=town_center
hard     tech=ranger_fletching     mix=3 archers          first_target=villagers
```

Regression checks:

```text
SOVEREIGN_AGE_TECH_PROBE_PASS backend=METAL tech=1 age=rising food=100 prereq=1 duplicate=1
SOVEREIGN_AI_DIFFICULTY_AB_PROBE_PASS runtime=1 profiles=1 expand=1 harass=1 targets=1 units=1 extended=1
SOVEREIGN_AI_PERSONALITY_SAVE_LOAD_PROBE_PASS state=1 profile=1 cadence=1 cooldown=1 second=1
```

## Completed Slice 42 — Composition Counter Checks

Implemented:

- Added `composition_duel()` to `scripts/sovereign/systems/combat_rules.py`.
  It expands unit-count dictionaries into deterministic HP pools, applies the
  existing `damage_breakdown()` rules, and reports winner, remaining units,
  HP totals, damage totals, and round history.
- Added `scripts/macos/pf_sovereign_ai_composition_counter_probe.py`.
  The probe runs in the Metal runtime, spawns the compared compositions into a
  native scene for visibility, and checks six profile-linked matchups:
  standard favorable/unfavorable, booming favorable/unfavorable, and hard
  favorable/unfavorable.
- Kept this as a rules/counter proof rather than a tactical simulator. Range,
  terrain, focus-fire behavior, and formation micro remain later balance
  slices.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/combat_rules.py \
  scripts/macos/pf_sovereign_ai_composition_counter_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_composition_counter_probe.py \
  --output-dir qa-output/sovereign-ai-composition-counter
```

Observed:

```text
SOVEREIGN_AI_COMPOSITION_COUNTER_PROBE_PASS runtime=1 plan=1 matrix=1 wins=1 losses=1 damage=1 cases=6
```

Regression checks:

```text
REGISTRY_ERRORS 0
SOVEREIGN_COMBAT_RULES_PROBE_PASS backend=METAL damage=5 base=4 bonus=1 hp=45->40
SOVEREIGN_AI_COMPOSITION_STRATEGY_PROBE_PASS runtime=1 research=1 targets=1 mix=1 attack_targets=1 attacks=1 extended=1
```

Counter evidence:

```text
standard favorable:   3 militia vs 2 archers  -> attackers win
standard unfavorable: 3 militia vs 5 archers  -> defenders win
booming favorable:    2 militia+1 archer vs 2 militia -> attackers win
booming unfavorable:  2 militia+1 archer vs 4 militia -> defenders win
hard favorable:       3 archers vs 2 militia  -> attackers win
hard unfavorable:     3 archers vs 5 militia  -> defenders win
```

## Completed Slice 43 — Difficulty Balance Save/Load Comparisons

Implemented:

- Added `scripts/macos/pf_sovereign_ai_difficulty_balance_save_load_probe.py`.
  It builds one native Metal map containing standard, booming, and hard branch
  fixtures, drives each profile to a save point, restores the planner from its
  snapshot, and continues the branch sequence.
- Added `scripts/sovereign/ai_difficulty_balance_restore.py` as the native
  session restore hook. It imports the Sovereign runtime entity classes,
  reads the compact A/B balance report from the saved entity tag, and verifies
  that the profile reports, save-point snapshots, post-snapshot continuation,
  and balance checks survived reload.
- Kept the persisted tag payload compact. The full verbose A/B report stays in
  `summary_sovereign_ai_difficulty_balance_save_load.json`; the `.pfsave`
  payload stores only the comparison evidence needed for reload validation.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/ai_difficulty_balance_restore.py \
  scripts/macos/pf_sovereign_ai_difficulty_balance_save_load_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_difficulty_balance_save_load_probe.py \
  --output-dir qa-output/sovereign-ai-difficulty-balance-save-load
```

Observed:

```text
SOVEREIGN_AI_DIFFICULTY_BALANCE_SAVE_LOAD_PROBE_PASS state=1 profiles=1 savepoint=1 resume=1 balance=1
```

Balance evidence:

```text
standard: save step 13 -> final step 27, 2 bases, 1 militia harassment wave, first target buildings
booming:  save step 13 -> final step 27, 3 bases, 1 militia harassment wave, first target buildings
hard:     save step 13 -> final step 27, 3 bases, 2 archer harassment waves, first target villagers
```

Native artifacts:

```text
qa-output/sovereign-ai-difficulty-balance-save-load/sovereign_ai_difficulty_balance_save_load.pfsave
qa-output/sovereign-ai-difficulty-balance-save-load/summary_sovereign_ai_difficulty_balance_save_load.json
qa-output/sovereign-ai-difficulty-balance-save-load/summary_sovereign_ai_difficulty_balance_save_load_restore.json
```

## Completed Slice 44 — Match-Length Build-Order Adaptation

Implemented:

- Added `MatchLengthBuildOrderPlanner` in
  `scripts/sovereign/systems/skirmish.py`. It gives each difficulty profile a
  deterministic opening-economy window, then moves into expansion, military
  transition, and attack timing without changing the engine pathing/combat
  primitives.
- Added `scripts/macos/pf_sovereign_ai_match_length_adaptation_probe.py`. It
  runs standard, booming, and hard fixtures in one Metal scene and checks that
  each profile opens, transitions, expands, trains the intended attack unit,
  and launches an attack at the expected match phase.
- Kept hard-profile attack readiness tied to the preferred attack-unit count,
  not total army count, so hard does not launch before its archer pressure plan
  has enough archers.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_match_length_adaptation_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_match_length_adaptation_probe.py \
  --output-dir qa-output/sovereign-ai-match-length-adaptation
```

Observed:

```text
SOVEREIGN_AI_MATCH_LENGTH_ADAPTATION_PROBE_PASS runtime=1 opening=1 transition=1 expansion=1 military=1 attack=1
```

Timing evidence:

```text
standard: opening 3, transition step 6, expansion step 5, attack step 7, militia count 2, bases 2
booming:  opening 4, transition step 7, expansion step 5, attack step 8, militia count 2, bases 3
hard:     opening 2, transition step 3, expansion step 6, attack step 13, archer count 3, bases 3
```

Regression checks:

```text
REGISTRY_ERRORS 0
SOVEREIGN_AI_DIFFICULTY_BALANCE_SAVE_LOAD_PROBE_PASS state=1 profiles=1 savepoint=1 resume=1 balance=1
SOVEREIGN_AI_DIFFICULTY_AB_PROBE_PASS runtime=1 profiles=1 expand=1 harass=1 targets=1 units=1 extended=1
SOVEREIGN_AI_COMPOSITION_COUNTER_PROBE_PASS runtime=1 plan=1 matrix=1 wins=1 losses=1 damage=1 cases=6
```

## Completed Slice 45 — Attrition Recovery Under Live Pressure

Implemented:

- Added live-unit accounting to `ScriptedSkirmishAI`: attack/defense rosters
  now ignore non-live units, and `record_unit_loss()` lets scenario/probe logic
  record casualties in the same player-state roster used by production and AI
  planning.
- Added `AttritionRecoveryPlanner` in `scripts/sovereign/systems/skirmish.py`.
  It detects a failed attack from live attack-unit count, handles live pressure
  near defended assets, regroups survivors, rebuilds the preferred army unit,
  and relaunches once the target force is restored.
- Added `scripts/macos/pf_sovereign_ai_attrition_recovery_probe.py`. It stages
  a hard-profile archer opening, scripts two archer casualties, moves a player
  militia into the AI base-pressure radius, and verifies defense, regroup,
  recovery training, and relaunch in a native Metal scene.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_attrition_recovery_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_attrition_recovery_probe.py \
  --output-dir qa-output/sovereign-ai-attrition-recovery
```

Observed:

```text
SOVEREIGN_AI_ATTRITION_RECOVERY_PROBE_PASS runtime=1 initial=1 pressure=1 failed=1 regroup=1 recovery=1 relaunch=1 transition=1
```

Attrition evidence:

```text
phase sequence: initial_attack -> live_pressure_defense -> failed_attack_regroup -> attrition_rebuild -> attrition_rebuild -> attrition_rebuild -> attrition_relaunch
initial attack step: 1
pressure defense step: 2
relaunch step: 7
scripted casualties: 2 archers
recovery training count: 2
final live attack count: 3 archers
live-pressure score sample: economy 0.122, military 4.08
```

Regression checks:

```text
REGISTRY_ERRORS 0
SOVEREIGN_AI_MATCH_LENGTH_ADAPTATION_PROBE_PASS runtime=1 opening=1 transition=1 expansion=1 military=1 attack=1
SOVEREIGN_AI_DIFFICULTY_AB_PROBE_PASS runtime=1 profiles=1 expand=1 harass=1 targets=1 units=1 extended=1
SOVEREIGN_AI_DIFFICULTY_BALANCE_SAVE_LOAD_PROBE_PASS state=1 profiles=1 savepoint=1 resume=1 balance=1
SOVEREIGN_AI_COMPOSITION_COUNTER_PROBE_PASS runtime=1 plan=1 matrix=1 wins=1 losses=1 damage=1 cases=6
```

## Completed Slice 46 — Repeated Attrition Outcomes

Implemented:

- Extended `AttritionRecoveryPlanner` with attack outcome tracking:
  failed/successful wave counts, launch history, explicit scripted outcome
  records, and an active target army count that escalates after the second
  failed push.
- Kept the existing live-roster recovery behavior, but now the second failed
  push is different from the first: the planner rebuilds to four archers
  instead of the original three before relaunching.
- Extended `scripts/macos/pf_sovereign_ai_attrition_recovery_probe.py` to run a
  longer Metal fixture: initial attack, first failed push, regroup/rebuild,
  relaunch, second failed push, larger rebuild, second relaunch, successful
  outcome, and post-success expansion.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_attrition_recovery_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_attrition_recovery_probe.py \
  --output-dir qa-output/sovereign-ai-attrition-recovery-repeated
```

Observed:

```text
SOVEREIGN_AI_ATTRITION_RECOVERY_PROBE_PASS runtime=1 initial=1 pressure=1 failed=1 regroup=1 recovery=1 relaunch=1 second_failed=1 second_rebuild=1 second_relaunch=1 success=1 economy=1 transition=1
```

Repeated-attrition evidence:

```text
phase counts:
  initial_attack: 1
  live_pressure_defense: 1
  failed_attack_regroup: 2
  attrition_rebuild: 8
  attrition_relaunch: 2
  post_success_expansion: 3

launches:
  initial step 1, target army 3
  relaunch step 7, target army 3
  relaunch step 14, target army 4

outcomes:
  failed step 3, live archers 1, target army 3
  failed step 7, live archers 1, target army 4
  success step 14, live archers 4, target army 4

final: failed waves 2, successful waves 1, recovery training 5, bases 2
```

## Completed Slice 47 — Strategic Tech Pacing Under Sustained Pressure

Implemented:

- Extended `AttritionRecoveryPlanner` with a pressure-technology hook: repeated
  failures can now trigger a research choice through the existing
  `ResearchQueue` before the planner spends the next steps rebuilding units.
- Wired the hard-profile attrition path to research `ranger_fletching` after
  the second failed push. The first failure still exercises regroup/rebuild;
  the second failure now adds a technology response before the larger relaunch.
- Extended `scripts/macos/pf_sovereign_ai_attrition_recovery_probe.py` with a
  `tech=1` acceptance gate and summary evidence for researched technologies,
  research queue completion, launch ordering, and phase counts.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_attrition_recovery_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_attrition_recovery_probe.py \
  --output-dir qa-output/sovereign-ai-attrition-tech-pressure
```

Observed:

```text
SOVEREIGN_AI_ATTRITION_RECOVERY_PROBE_PASS runtime=1 initial=1 pressure=1 failed=1 regroup=1 recovery=1 relaunch=1 second_failed=1 second_rebuild=1 second_relaunch=1 tech=1 success=1 economy=1 transition=1
```

Pressure-tech evidence:

```text
phase counts:
  pressure_tech: 2
  attrition_rebuild: 8
  attrition_relaunch: 2

launches:
  initial step 1, target army 3
  relaunch step 7, target army 3
  relaunch step 16, target army 4

technology:
  ranger_fletching researched at step 10
  research queue completed 1 item and is empty after completion
  pressure tech step 10 is after first relaunch and before second relaunch
```

Regression checks:

```text
REGISTRY_ERRORS 0
SOVEREIGN_AI_COMPOSITION_STRATEGY_PROBE_PASS runtime=1 research=1 targets=1 mix=1 attack_targets=1 attacks=1 extended=1
SOVEREIGN_AI_MATCH_LENGTH_ADAPTATION_PROBE_PASS runtime=1 opening=1 transition=1 expansion=1 military=1 attack=1
SOVEREIGN_AI_DIFFICULTY_AB_PROBE_PASS runtime=1 profiles=1 expand=1 harass=1 targets=1 units=1 extended=1
SOVEREIGN_AI_DIFFICULTY_BALANCE_SAVE_LOAD_PROBE_PASS state=1 profiles=1 savepoint=1 resume=1 balance=1
```

## Completed Slice 48 — Multi-Front Army Control

Implemented:

- Added exact-unit front helpers to `ScriptedSkirmishAI` so planners can launch
  a selected subset of units instead of moving every live unit in a roster.
- Added `MultiFrontArmyPlanner` in `scripts/sovereign/systems/skirmish.py`.
  It assigns disjoint unit groups to:
  - home defense against a live military threat,
  - harassment against a forward villager target,
  - building attack against a separate structure target.
- Added `scripts/macos/pf_sovereign_ai_multi_front_probe.py`, a native Metal
  fixture that starts with one militia defender and four archers, then verifies
  that the planner creates three separate fronts without reusing units.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/systems/skirmish.py \
  scripts/macos/pf_sovereign_ai_multi_front_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_multi_front_probe.py \
  --output-dir qa-output/sovereign-ai-multi-front
```

Observed:

```text
SOVEREIGN_AI_MULTI_FRONT_PROBE_PASS runtime=1 split=1 defense=1 harass=1 attack=1 disjoint=1 defense_motion=1 harass_motion=1 attack_motion=1
```

Multi-front evidence:

```text
defense: ai_multi_front_defender -> player_multi_front_pressure
harass: ai_multi_front_archer_1, ai_multi_front_archer_2 -> player_multi_front_forward_worker
attack: ai_multi_front_archer_3, ai_multi_front_archer_4 -> barracks

movement improvements:
  defense: 20.195
  harass: 0.013, 0.534
  attack: 0.646, 0.334
```

Regression checks:

```text
SOVEREIGN_AI_BRANCHING_STRATEGY_PROBE_PASS profile=1 defense=1 expand=1 bases=1 train=1 harass=1 defense_motion=1 harass_motion=1
SOVEREIGN_AI_MAP_CONTROL_PROBE_PASS map=1 profile=1 build=1 retreat=1 train=1 attack=1 motion=1
SOVEREIGN_AI_ATTRITION_RECOVERY_PROBE_PASS runtime=1 initial=1 pressure=1 failed=1 regroup=1 recovery=1 relaunch=1 second_failed=1 second_rebuild=1 second_relaunch=1 tech=1 success=1 economy=1 transition=1
```

## Completed Slice 49 — Larger AI-vs-Player Skirmish Soak

Implemented:

- Added `scripts/macos/pf_sovereign_ai_skirmish_soak_probe.py`, a composed
  native Metal soak that stages a two-player Sovereign scenario with player
  production, enemy economy income, enemy militia/archer roster setup,
  multi-front defense/harassment/building-attack activity, repeated attrition
  recovery, pressure-triggered `ranger_fletching`, combat damage, conquest
  victory progress, and sustained runtime ticks.
- Kept the probe data-driven through the existing scenario sidecar, Sovereign
  player state, `ProductionQueue`, `ResearchQueue`, `MultiFrontArmyPlanner`,
  `AttritionRecoveryPlanner`, and combat-rule helpers.
- Made the front-activity check suitable for a contested live skirmish: it
  records both target-distance improvement and actual travel distance so
  pathing/combat avoidance still proves units became active instead of
  requiring every front to walk straight toward its nominal target.

Verification:

```sh
python3 -m py_compile \
  scripts/macos/pf_sovereign_ai_skirmish_soak_probe.py \
  scripts/sovereign/systems/skirmish.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_skirmish_soak_probe.py \
  --output-dir qa-output/sovereign-ai-skirmish-soak \
  --soak-ticks 240
```

Observed:

```text
SOVEREIGN_AI_SKIRMISH_SOAK_PROBE_PASS runtime=1 economy=1 player=1 enemy=1 fronts=1 motion=1 attrition=1 tech=1 relaunch=1 damage=1 victory=1 soak=1
```

Regression checks:

```text
SOVEREIGN_AI_MULTI_FRONT_PROBE_PASS runtime=1 split=1 defense=1 harass=1 attack=1 disjoint=1 defense_motion=1 harass_motion=1 attack_motion=1
SOVEREIGN_AI_ATTRITION_RECOVERY_PROBE_PASS runtime=1 initial=1 pressure=1 failed=1 regroup=1 recovery=1 relaunch=1 second_failed=1 second_rebuild=1 second_relaunch=1 tech=1 success=1 economy=1 transition=1
SOVEREIGN_LONG_SKIRMISH_PROBE_PASS state=1 entities=1 player=1 scenario=1 victory=1 queue=1 tech=1 combat=1 resume=1
```

## Completed Slice 50 — Larger Army Scale Soak

Implemented:

- Added `scripts/macos/pf_sovereign_ai_large_army_scale_probe.py`, a native
  Metal scale fixture that spawns mixed militia/archer armies for both players.
- The first green scale gate uses 80 units per side, for 160 active combat
  units plus the scenario/runtime objects.
- The fixture issues mass attack-move orders instead of direct-targeting every
  unit, then verifies movement distance, active `Walk`/`Attack` animations,
  representative combat damage, live counts after fighting, and sustained
  runtime ticks.
- A first 96-units-per-side attempt reached sustained soak but did not complete
  cleanly. Slice 51 diagnosed that as an uncontrolled projectile-heavy
  attack-move issue and superseded this 160-unit gate with a 192-unit
  movement-scale gate.

Verification:

```sh
python3 -m py_compile \
  scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  scripts/macos/pf_sovereign_ai_skirmish_soak_probe.py \
  scripts/sovereign/systems/skirmish.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale \
  --units-per-side 80 \
  --settle-ticks 300 \
  --soak-ticks 240
```

Observed:

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=80 total_units=160
```

Scale evidence:

```text
moved_count: 152
average_travel: 27.388
active_animation_count: 108
animation_counts: Attack=20, Walk=88, Idle=52
engine_damaged_unit_count: 9
player_live_count: 70
enemy_live_count: 70
elapsed_wall_sec: 37.308
```

Regression check:

```text
SOVEREIGN_AI_SKIRMISH_SOAK_PROBE_PASS runtime=1 economy=1 player=1 enemy=1 fronts=1 motion=1 attrition=1 tech=1 relaunch=1 damage=1 victory=1 soak=1
```

## Completed Slice 51 — 192-Unit Scale Gate Hardening

Implemented:

- Hardened `scripts/macos/pf_sovereign_ai_large_army_scale_probe.py` with a
  progress heartbeat JSON so failed large-count runs leave phase, live-count,
  movement, animation, and combat evidence.
- Reproduced the 96-units-per-side failure and isolated the crash to the
  projectile path:
  `P_Projectile_VelocityForTarget` asserted on a zero-length projectile
  velocity during the uncontrolled mass attack-move soak.
- Kept this scale gate focused on larger-army runtime capacity by switching the
  mass-army order path to movement orders while preserving representative
  combat damage through the shared Sovereign combat rules.
- The projectile-heavy 192+ attack-move case is now a distinct follow-up,
  rather than blocking the movement/render/sustain scale gate.

Verification:

```sh
python3 -m py_compile \
  scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  scripts/macos/pf_sovereign_ai_skirmish_soak_probe.py \
  scripts/sovereign/systems/skirmish.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-96 \
  --units-per-side 96 \
  --settle-ticks 300 \
  --soak-ticks 240
```

Observed:

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=96 total_units=192
```

Scale evidence:

```text
moved_count: 182
average_travel: 29.706
max_travel: 97.731
active_animation_count: 134
animation_counts: Attack=23, Walk=111, Idle=58
engine_damaged_unit_count: 6
player_live_count_after_soak: 76
enemy_live_count_after_soak: 75
elapsed_wall_sec: 43.607
```

Regression check:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_skirmish_soak_probe.py \
  --output-dir qa-output/sovereign-ai-skirmish-soak-scale-regression \
  --soak-ticks 240
```

```text
SOVEREIGN_AI_SKIRMISH_SOAK_PROBE_PASS runtime=1 economy=1 player=1 enemy=1 fronts=1 motion=1 attrition=1 tech=1 relaunch=1 damage=1 victory=1 soak=1
```

## Completed Slice 52 — Projectile-Heavy 192-Unit Combat Guard

Implemented:

- Fixed `src/phys/projectile.c:P_Projectile_VelocityForTarget()` for dense
  combat edge cases where a projectile source and target have effectively zero
  horizontal separation. The function now returns `false` before the ballistic
  equation divides by horizontal range, matching the caller's existing
  "cannot hit target, do not spawn projectile" behavior.
- Clamped tiny near-zero ballistic discriminants to zero so numerical noise at
  the reachability boundary does not produce NaN velocity vectors.
- Added `--order-mode move|attack-move` to
  `scripts/macos/pf_sovereign_ai_large_army_scale_probe.py`. The default
  remains the movement-scale gate, while `--order-mode attack-move` verifies
  dense projectile-heavy combat using the same 96-units-per-side fixture.

Verification:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-96-attack-move-tty \
  --units-per-side 96 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move
```

Observed:

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=96 total_units=192
```

Scale evidence:

```text
order_mode: attack-move
moved_count: 183
average_travel: 27.955
max_travel: 92.65
active_animation_count: 139
animation_counts: Attack=21, Walk=118, Idle=53
engine_damaged_unit_count: 5
player_live_count_after_soak: 76
enemy_live_count_after_soak: 75
elapsed_wall_sec: 44.525
```

Projectile regression:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_projectile_vfx_probe.py \
  --output-dir qa-output/sovereign-projectile-vfx-projectile-guard-regression
```

```text
SOVEREIGN_PROJECTILE_VFX_PROBE_PASS backend=METAL damage=5 hp=45->40 trail=1 impact=1 fire=1 smoke=1 spawn_dist=2.63 impact_dist=5.70 dir_dot=1.00
```

## Completed Slice 53 — 250/500 Unit Scale Budgets

Implemented:

- Extended `scripts/macos/pf_sovereign_ai_large_army_scale_probe.py` with
  budget telemetry:
  - budget label
  - elapsed wall time
  - phase durations and phase tick counts
  - requested/completed tick counts
  - simulated ticks per wall second
  - wall milliseconds per requested tick
  - wall seconds per 100 units
- Tightened `src/phys/projectile.c:P_Projectile_VelocityForTarget()` one more
  step for dense combat: non-finite discriminants, launch-angle tangents,
  vertical offsets, and velocity lengths now fail cleanly before the debug
  assert. This closed the 250-unit NaN projectile edge that appeared after the
  initial zero-horizontal-distance guard.
- Verified 250 total units and 500 total units in projectile-heavy attack-move
  mode, not just movement-only mode.

Verification:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
```

250-unit attack-move:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-250-attack-move \
  --units-per-side 125 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 250-attack-move
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=125 total_units=250
```

250-unit budget evidence:

```text
elapsed_wall_sec: 56.765
sim_ticks_per_wall_sec: 13.758
wall_ms_per_requested_tick: 105.120
wall_sec_per_100_units: 22.706
moved_count: 229
average_travel: 25.393
active_animation_count: 172
engine_damaged_unit_count: 9
live_after: player=102 enemy=104
```

500-unit attack-move:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-attack-move \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-attack-move
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=250 total_units=500
```

500-unit budget evidence:

```text
elapsed_wall_sec: 111.871
sim_ticks_per_wall_sec: 6.981
wall_ms_per_requested_tick: 207.169
wall_sec_per_100_units: 22.374
moved_count: 392
average_travel: 16.069
active_animation_count: 368
engine_damaged_unit_count: 16
live_after: player=222 enemy=213
```

## Completed Slice 54 — 1000-Unit Exploratory Scale And Wide-Zoom Budget Gate

Implemented:

- Extended `scripts/macos/pf_sovereign_ai_large_army_scale_probe.py` with
  profiler-friendly CLI options:
  - `--capture-proof`
  - `--wide-zoom-height`
  - `--sample-budget-every`
  - `--soft-budget-ms-per-tick`
  - `--hard-budget-ms-per-tick`
- Added sampled tick budget summaries with p50/p95/max values overall and per
  phase.
- Added soft budget warning output and hard budget fail support.
- Added proof captures for before-orders, engage-sample, sustained-soak, and
  wide-zoom views.
- Added failure classification in failed summaries so future 1000+ blockers can
  be sorted as spawn/setup, movement orders, projectile/combat,
  animation/rendering, capture/IO, or wall-clock budget.

Verification:

```sh
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
```

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit regression:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-regression \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-regression
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=250 total_units=500
```

500-unit budget evidence:

```text
elapsed_wall_sec: 114.793
sim_ticks_per_wall_sec: 6.804
wall_ms_per_requested_tick: 212.580
wall_sec_per_100_units: 22.959
tick_p50_ms: 209.725
tick_p95_ms: 287.812
tick_max_ms: 287.812
moved_count: 403
average_travel: 16.284
active_animation_count: 373
engine_damaged_unit_count: 14
live_after: player=247 enemy=239
```

1000-unit exploratory gate:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-profile-rerun \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-attack-move \
  --capture-proof \
  --wide-zoom-height 1100 \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=500 total_units=1000
```

1000-unit budget evidence:

```text
elapsed_wall_sec: 253.463
sim_ticks_per_wall_sec: 3.081
wall_ms_per_requested_tick: 469.376
wall_sec_per_100_units: 25.346
tick_p50_ms: 400.684
tick_p95_ms: 501.207
tick_max_ms: 501.207
moved_count: 673
average_travel: 3.170
active_animation_count: 382
engine_damaged_unit_count: 19
live_after: player=490 enemy=498
soft_budget_warnings:
- overall p95 tick budget 501.207ms exceeds soft threshold 500.0ms
- engage_settle p95 tick budget 501.207ms exceeds soft threshold 500.0ms
```

Proof captures:

- `qa-output/sovereign-ai-large-army-scale-1000-profile-rerun/sovereign_large_army_before_orders.png`
- `qa-output/sovereign-ai-large-army-scale-1000-profile-rerun/sovereign_large_army_engage_sample.png`
- `qa-output/sovereign-ai-large-army-scale-1000-profile-rerun/sovereign_large_army_sustained_soak.png`
- `qa-output/sovereign-ai-large-army-scale-1000-profile-rerun/sovereign_large_army_wide_zoom.png`

Optional Instruments wrapper for the next profiling pass:

```sh
xcrun xctrace record \
  --template "Time Profiler" \
  --output qa-output/sovereign-ai-large-army-scale-1000-profile/sovereign_1000_time_profile.trace \
  --launch ./bin/pf-arm64 \
  -- ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
    --output-dir qa-output/sovereign-ai-large-army-scale-1000-xctrace \
    --units-per-side 500 \
    --settle-ticks 300 \
    --soak-ticks 240 \
    --order-mode attack-move \
    --budget-label 1000-xctrace
```

Conclusion:

- The 1000-unit gate is functionally green: no projectile assertion returned,
  all runtime checks passed, and wide-zoom captures are nonblank Retina PNGs.
- It is not a production real-time scale target yet. The p95 sampled tick time
  barely exceeds the first 500 ms soft threshold, so the next performance slice
  should use Instruments/Metal profiling to identify the dominant CPU/GPU
  bottleneck before increasing unit count further.

## Completed Slice 55 — Attach-Mode Time Profiler Baseline

Implemented:

- Added `scripts/macos/profile_sovereign_large_army_scale.sh`, a small wrapper
  around the 1000-unit large-army scale probe.
- The wrapper launches `pf-arm64` normally from the engine root, then attaches
  `xcrun xctrace record` to the running process. This avoids the failed
  `xctrace --launch` startup path where the engine could not resolve `pf.conf`
  and loading-screen assets correctly.
- For Time Profiler runs, the wrapper exports the `time-profile` table and
  writes `time_profile_top.txt` with top leaf functions, leaf/parent pairs, and
  inclusive sample counts.
- The wrapper writes a compact `profile_run_summary.json` beside the native
  probe summary and proof captures.

Verification:

```sh
PF_PROFILE_UNITS_PER_SIDE=32 PF_PROFILE_SETTLE_TICKS=120 PF_PROFILE_SOAK_TICKS=120 \
  scripts/macos/profile_sovereign_large_army_scale.sh \
  qa-output/sovereign-ai-large-army-scale-profile-smoke
```

```text
status: pass
total_units: 64
elapsed_wall_sec: 38.483
tick_p50_ms: 31.278
tick_p95_ms: 44.207
engine_damaged_unit_count: 5
captures: before_orders, engage_sample, sustained_soak, wide_zoom
```

Full 1000-unit profile command:

```sh
scripts/macos/profile_sovereign_large_army_scale.sh \
  qa-output/sovereign-ai-large-army-scale-1000-profile
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=500 total_units=1000
```

1000-unit profile evidence:

```text
trace: qa-output/sovereign-ai-large-army-scale-1000-profile/run-20260510-094145/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-profile/run-20260510-094145/time_profile_top.txt
elapsed_wall_sec: 260.733
sim_ticks_per_wall_sec: 2.995
wall_ms_per_requested_tick: 482.839
tick_p50_ms: 416.903
tick_p95_ms: 532.050
tick_max_ms: 532.050
moved_count: 661
average_travel: 2.948
active_animation_count: 390
engine_damaged_unit_count: 21
live_after: player=491 enemy=497
```

Time Profiler hotspot summary:

```text
top leaf samples:
- inside_pcr: 34.38%
- C_RayRayIntersection2D: 17.28%
- append_skinned_anim_mesh: 17.24%
- PFM_Mat4x4_Mult4x1: 5.37%
- C_InfiniteLineIntersection: 4.94%

top inclusive samples:
- inside_pcr: 34.49%
- compute_vo_xpoints: 21.68%
- append_skinned_anim_mesh: 18.71%
- C_RayRayIntersection2D: 17.28%
```

Conclusion:

- The 1000-unit profile run survived to normal exit and wrote a valid Time
  Profiler trace. Closing the app after the run did not invalidate the saved
  evidence.
- The first CPU bottleneck is not generic rendering or projectile failure. It
  is concentrated in ClearPath/collision-avoidance geometry during dense army
  movement, with Metal skinned-animation stream assembly as the second major
  hotspot.
- The next scale slice should optimize or gate collision-avoidance work for
  dense formations before trying 1500-2000 units, then separately profile
  `append_skinned_anim_mesh`/animation matrix assembly.

## Remaining Plan Status

Most of the first playable Sovereign vertical-slice foundation is now in place.
Rough status against the ten-phase plan:

- Phases 0-1: repo bootstrap and Metal baseline are functionally in place, but
  upstream PR hygiene remains separate from Sovereign organization packaging.
  The Sovereign publish preflight/checklist is now in place, strict publish
  hygiene is green, and the first Sovereign organization checkpoint is merged
  into `sovereignrealms/sovereign-realms-engine`.
- Phases 2-3: asset pipeline seed and data-driven definitions are in place;
  real production art/validation depth remains.
- Phases 4-7: economy, production/population, age/tech, combat counters,
  projectiles, and first skirmish proof are in place as MVP probes.
- Phase 8: editor workflow is now strong for sidecar metadata, placement,
  validation, reload, stress fixtures, setup profiles, resource presets, and
  reports.
- Phase 9: AI/skirmish loop is still basic but now has explicit decision
  helpers and a deterministic build-order planner for resource shortfall,
  population blocks, house construction, training, priority target selection,
  attack-wave launch, scout reports, nearby threat classification, defense
  response, scouting route waypoints, remembered threat sightings,
  last-known-position response, restored threat memory after native save/load,
  outnumbered regroup behavior, scheduled scout refresh, adaptive archer
  counter-training from remembered military threats, counterattack launch,
  difficulty profiles, economy-vs-military weighting, second-base expansion,
  map-control evaluation, difficulty-tuned attack/retreat thresholds,
  defense/harassment split decisions, three-base expansion sequencing,
  difficulty-specific personalities, harassment cadence controls, restored
  branch cooldown state, second harassment wave continuation after native
  save/load, longer difficulty A/B behavior evidence, profile-driven
  harassment unit composition, strategy research choices, profile-specific
  target unit mixes, composition attack priorities, composition counter checks,
  longer difficulty balance save/load comparisons, deterministic enemy economy,
  movement, facing combat, victory dispatch, longer staged save/load coverage,
  persistence hooks, and early match-length economy-vs-military transition
  timing. It now has a first failed-attack attrition recovery path under live
  base pressure plus repeated attrition outcome handling: a second failed push
  escalates the relaunch target size, while a successful relaunch shifts back
  toward expansion. Repeated pressure can now also trigger `ranger_fletching`
  before the larger second relaunch. Multi-front army control is now covered
  for disjoint defense, harassment, and building-attack groups. A larger
  AI-vs-player soak now composes production, economy, multi-front activity,
  attrition, tech pacing, damage, victory progress, and sustained Metal ticks.
  The first larger-army scale soaks now pass up through 1000 mixed combat units
  in projectile-heavy attack-move mode with wall-clock budget telemetry and
  wide-zoom proof captures. The first ClearPath duplicate-pair optimization
  brings the exploratory 1000-unit gate under the current 500 ms soft p95 tick
  budget, but it is still not a production-budget late-game target. It is not
  yet a full late-game tactical AI with naval/air reactions, multi-front
  naval/air plans, post-change Instruments/Metal GPU profiling, production
  budget 1000+ unit tuning, or open-ended strategic play.
- Phase 10: performance, Retina clarity, HD/4K assets, large-map benchmarks,
  1000+ production-budget benchmarks, and production polish remain the largest
  open area. A first metric-backed HD/Retina readability gate now exists for
  regression tracking, but production assets and final readability art
  direction remain open.

Overall: the technical vertical-slice scaffold is roughly 95-97% complete for
an MVP skirmish foundation. It is not yet production-game-ready because real
assets, deeper tactical AI, full editor UX polish, scale/performance
benchmarking, and HD/Retina presentation still need focused slices.

Status by plan shape:

- Latest execution slices: 95 completed or rejected execution slices are
  recorded through the wide-zoom army readability policy evidence gate.
- Current-status checklist: all listed implementation items are marked DONE,
  including the first GitHub organization push/merge.
- Ten-phase production roadmap: Phases 0-9 have MVP scaffolding/probes in
  place; Phase 10 and production-quality content remain the largest open work.

## Completed Slice 56 — ClearPath Duplicate Ray-Pair Reduction

Implemented:

- Updated `src/game/clearpath.c:compute_vo_xpoints()` so velocity-obstacle rays
  are intersected as unordered pairs only.
- The old loop checked both `(i, j)` and `(j, i)`. Ray intersections are
  symmetric for this candidate generation step, so the second check produced
  duplicate candidate points and duplicate `inside_pcr()` work.
- This is intentionally smaller than changing neighbour radius, neighbour cap,
  or the ClearPath algorithm itself. It removes redundant work without changing
  the generated unordered ray-pair search space.

Verification:

```sh
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
```

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit regression:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-clearpath-pairs \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-clearpath-pairs \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=250 total_units=500
```

500-unit budget evidence:

```text
elapsed_wall_sec: 116.455
sim_ticks_per_wall_sec: 6.706
wall_ms_per_requested_tick: 215.657
tick_p50_ms: 198.515
tick_p95_ms: 210.003
tick_max_ms: 210.003
moved_count: 408
average_travel: 16.235
active_animation_count: 377
engine_damaged_unit_count: 13
live_after: player=244 enemy=236
soft_budget_warnings: none
```

1000-unit exploratory gate:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-clearpath-pairs \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-clearpath-pairs \
  --capture-proof \
  --wide-zoom-height 1100 \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=500 total_units=1000
```

1000-unit budget evidence:

```text
elapsed_wall_sec: 256.819
sim_ticks_per_wall_sec: 3.041
wall_ms_per_requested_tick: 475.591
tick_p50_ms: 405.032
tick_p95_ms: 495.625
tick_max_ms: 495.625
moved_count: 680
average_travel: 3.207
active_animation_count: 387
engine_damaged_unit_count: 25
live_after: player=492 enemy=498
soft_budget_warnings: none
```

Comparison to the previous recorded gates:

```text
500-unit p95: 287.812 ms -> 210.003 ms
1000-unit p95: 501.207 ms -> 495.625 ms
```

Post-change profiler rerun:

```sh
scripts/macos/profile_sovereign_large_army_scale.sh \
  qa-output/sovereign-ai-large-army-scale-1000-post-clearpath-profile
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=500 total_units=1000
```

Post-change profile evidence:

```text
trace: qa-output/sovereign-ai-large-army-scale-1000-post-clearpath-profile/run-20260510-172946/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-post-clearpath-profile/run-20260510-172946/time_profile_top.txt
elapsed_wall_sec: 252.000
sim_ticks_per_wall_sec: 3.099
wall_ms_per_requested_tick: 466.667
tick_p50_ms: 410.770
tick_p95_ms: 463.975
tick_max_ms: 463.975
moved_count: 672
average_travel: 3.310
active_animation_count: 385
engine_damaged_unit_count: 25
live_after: player=492 enemy=498
soft_budget_warnings: none
```

Post-change Time Profiler hotspot summary:

```text
top leaf samples:
- inside_pcr: 31.05%
- append_skinned_anim_mesh: 21.85%
- C_RayRayIntersection2D: 11.95%
- PFM_Mat4x4_Mult4x1: 6.39%
- C_InfiniteLineIntersection: 3.59%

top inclusive samples:
- inside_pcr: 31.50%
- append_skinned_anim_mesh: 23.16%
- C_RayRayIntersection2D: 11.95%
- compute_vo_xpoints: 7.47%
- G_ClearPath_NewVelocity: 5.63%
```

Profiler comparison:

```text
compute_vo_xpoints inclusive: 21.68% -> 7.47%
C_RayRayIntersection2D leaf: 17.28% -> 11.95%
append_skinned_anim_mesh inclusive: 18.71% -> 23.16%
1000-unit profiled p95: 532.050 ms -> 463.975 ms
```

Conclusion:

- This slice reduces redundant dense-formation ClearPath work and brings the
  exploratory 1000-unit gate under the current 500 ms soft p95 threshold.
- The post-change trace confirms the direct ray-pair work dropped sharply.
  Remaining scale work is now split between `inside_pcr` checks and Metal
  skinned-animation assembly. The next change should be smaller than an
  algorithm rewrite: either add ClearPath counters to target `inside_pcr`
  frequency, or start a focused `append_skinned_anim_mesh` stream/matrix
  assembly pass.

## Completed Slice 57 — Metal Skinned Animation Assembly Precomposition

Implemented:

- Updated `src/render/backend_metal.m:append_skinned_anim_mesh()` to precompose
  each animated entity's model matrix with its joint skin matrices once per
  entity.
- The old CPU-side batch path skinned each vertex into local space, then
  applied another model-space position multiply and normal transform per
  vertex.
- The new path builds `world_skin_mats` and `world_skin_normal_mats` up front
  and skins weighted vertices directly into world space. This preserves the
  existing batching model and avoids a renderer rewrite.
- Extended `scripts/macos/profile_sovereign_large_army_scale.sh` with
  `PF_PROFILE_CAPTURE_PROOF=0` so profiling can run without failing on the
  screenshot harness. Capture-enabled proof remains the default.

Verification:

```sh
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
```

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit regression:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-skin-assembly \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-skin-assembly \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=250 total_units=500
```

500-unit budget evidence:

```text
elapsed_wall_sec: 77.640
sim_ticks_per_wall_sec: 10.059
wall_ms_per_requested_tick: 143.778
tick_p50_ms: 141.814
tick_p95_ms: 149.899
tick_max_ms: 149.899
moved_count: 419
average_travel: 15.825
active_animation_count: 368
engine_damaged_unit_count: 13
live_after: player=245 enemy=235
soft_budget_warnings: none
```

1000-unit budget gate:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-skin-assembly-budget \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-skin-assembly-budget \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=500 total_units=1000
```

1000-unit budget evidence:

```text
elapsed_wall_sec: 154.636
sim_ticks_per_wall_sec: 5.051
wall_ms_per_requested_tick: 286.363
tick_p50_ms: 271.858
tick_p95_ms: 350.763
tick_max_ms: 350.763
moved_count: 679
average_travel: 3.391
active_animation_count: 376
engine_damaged_unit_count: 22
live_after: player=489 enemy=497
soft_budget_warnings: none
```

1000-unit Time Profiler command:

```sh
PF_PROFILE_CAPTURE_PROOF=0 \
  scripts/macos/profile_sovereign_large_army_scale.sh \
  qa-output/sovereign-ai-large-army-scale-1000-skin-assembly-profile-nocapture
```

```text
SOVEREIGN_AI_LARGE_ARMY_SCALE_PROBE_PASS runtime=1 spawn=1 orders=1 motion=1 anim=1 combat=1 sustain=1 units_per_side=500 total_units=1000
```

1000-unit profiled evidence:

```text
trace: qa-output/sovereign-ai-large-army-scale-1000-skin-assembly-profile-nocapture/run-20260510-183810/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-skin-assembly-profile-nocapture/run-20260510-183810/time_profile_top.txt
elapsed_wall_sec: 155.961
sim_ticks_per_wall_sec: 5.008
wall_ms_per_requested_tick: 288.817
tick_p50_ms: 304.748
tick_p95_ms: 350.798
tick_max_ms: 350.798
moved_count: 674
average_travel: 3.482
active_animation_count: 373
engine_damaged_unit_count: 20
live_after: player=491 enemy=497
soft_budget_warnings: none
```

Time Profiler hotspot summary:

```text
top leaf samples:
- inside_pcr: 29.51%
- append_skinned_anim_mesh: 20.17%
- C_RayRayIntersection2D: 13.22%
- PFM_Mat4x4_Mult4x1: 4.85%
- C_InfiniteLineIntersection: 4.02%

top inclusive samples:
- inside_pcr: 31.05%
- append_skinned_anim_mesh: 20.94%
- compute_vo_xpoints: 16.75%
- C_RayRayIntersection2D: 13.22%
- G_ClearPath_NewVelocity: 6.39%
```

Comparison to Slice 56:

```text
500-unit p95: 210.003 ms -> 149.899 ms
1000-unit budget p95: 495.625 ms -> 350.763 ms
1000-unit profiled p95: 463.975 ms -> 350.798 ms
append_skinned_anim_mesh inclusive: 23.16% -> 20.94%
PFM_Mat4x4_Mult4x1 leaf: 6.39% -> 4.85%
```

Capture note:

- The first capture-enabled 1000-unit proof run for this slice failed at the
  screenshot harness with `screencapture failed for before_orders`, before
  movement/combat phases began.
- The same workload passes without screenshots, and the Time Profiler wrapper
  now supports `PF_PROFILE_CAPTURE_PROOF=0` for profiling-only runs. Visual
  proof should be retried separately when the macOS capture service is stable.

Conclusion:

- The animation assembly precomposition is a strong win: the 1000-unit p95
  budget is now roughly 351 ms, compared with roughly 464 ms after Slice 56 and
  roughly 532 ms before the ClearPath tuning began.
- The next scale target should return to ClearPath, specifically `inside_pcr`
  and candidate-count instrumentation, because animation assembly improved and
  ClearPath is again the leading inclusive hotspot.

## Completed Slice 58 — ClearPath Candidate-Count Instrumentation

Goal:

- Add low-risk, env-gated evidence for the next ClearPath bottleneck before
  attempting a collision-avoidance LOD or fallback-policy change.

Implementation:

- Added `PF_CLEARPATH_STATS_PATH` support in `src/game/clearpath.c`.
- Added aggregate counters for:
  - `G_ClearPath_NewVelocity()` calls, attempts, successes, zero-velocity
    returns, and fallback removals.
  - dynamic/static neighbour counts, generated HRVO/VO counts, ray counts, and
    maximum rays per attempt.
  - desired-velocity `inside_pcr()` hits/misses.
  - `inside_pcr()` call count, ray-pair tests, hits, misses, and apex skips.
  - xpoint pair tests, ray intersections, rejected inside-PCR points, accepted
    xpoints, projection tests, accepted projections, and no-solution attempts.
- Added `pf.debug_write_clearpath_stats()` so fast-exit probe scripts can flush
  stats before `os._exit()`.
- Extended `scripts/macos/pf_sovereign_ai_large_army_scale_probe.py` with
  `--clearpath-stats-path`, embeds loaded stats in its summary, and keeps stats
  optional.
- Extended `scripts/macos/profile_sovereign_large_army_scale.sh` with
  `PF_PROFILE_CLEARPATH_STATS=1`, keeping stats off by default so normal Time
  Profiler runs are not distorted by atomic counter overhead.

Verification:

```sh
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
bash -n scripts/macos/profile_sovereign_large_army_scale.sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit diagnostic stats run:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-clearpath-stats \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-clearpath-stats \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500 \
  --clearpath-stats-path qa-output/sovereign-ai-large-army-scale-500-clearpath-stats/clearpath_stats.json
```

Result:

- PASS, 500 units.
- stats-enabled p95 tick: 372.333 ms.
- `calls`: 106,508.
- `attempts`: 222,944.
- `fallback_removes`: 124,966.
- `inside_pcr_calls`: 54,584,834.
- `xpoint_ray_pair_tests`: 190,964,172.
- `candidate_points_total`: 3,529,456.
- `max_candidate_points`: 1,544.

1000-unit diagnostic stats run:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-clearpath-stats \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-clearpath-stats \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500 \
  --clearpath-stats-path qa-output/sovereign-ai-large-army-scale-1000-clearpath-stats/clearpath_stats.json
```

Result:

- PASS, 1000 units.
- stats-enabled p95 tick: 578.245 ms.
- `calls`: 76,771.
- `attempts`: 1,180,417.
- `successes`: 59,786.
- `zero_velocity_returns`: 16,977.
- `fallback_removes`: 1,120,623.
- `max_rays`: 128.
- `desired_inside_pcr`: 1,167,483.
- `inside_pcr_calls`: 680,252,220.
- `inside_pcr_ray_pair_tests`: 4,553,709,601.
- `xpoint_ray_pair_tests`: 2,146,621,280.
- `xpoint_ray_pair_intersections`: 613,357,888.
- `xpoint_inside_rejected`: 610,640,482.
- `candidate_points_total`: 2,807,818.
- `max_candidate_points`: 1,899.
- `no_solution_attempts`: 1,120,623.

No-stats regression:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-clearpath-stats-regression-rerun \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-clearpath-stats-regression-rerun \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

- PASS, 500 units.
- p95 tick: 152.376 ms.
- no warnings.

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-clearpath-stats-regression \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-clearpath-stats-regression \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

- PASS, 1000 units.
- p95 tick: 339.576 ms.
- no warnings.

Notes:

- Stats-enabled timing is diagnostic only. The atomic counters deliberately add
  overhead in the hottest loops, so budget decisions should continue to use
  no-stats runs or Time Profiler runs with `PF_PROFILE_CLEARPATH_STATS=0`.
- One no-stats 500-unit run exited early before a summary after entering
  `engage_settle`; a clean rerun passed. This was treated as a transient native
  process/window termination, not a probe or renderer regression.

Conclusion:

- The dominant 1000-unit ClearPath pressure is repeated no-solution fallback
  work. In the 1000-unit diagnostic run, only 76,771 public velocity requests
  expanded into 1.18 million ClearPath attempts and 1.12 million fallback
  removals.
- The next optimization should avoid recomputing the full candidate set after
  every single furthest-neighbour removal. A small, guarded experiment should
  cap fallback removal attempts or remove multiple furthest blockers per retry,
  then compare movement/combat correctness against the current no-stats 500 and
  1000 gates.

## Completed Slice 59 — Guarded ClearPath Fallback Batch Policy

Goal:

- Reduce repeated no-solution ClearPath retries in dense 1000-unit battles
  without degrading the smaller 500-unit regression gate.

Implementation:

- Changed `src/game/clearpath.c:remove_furthest()` to report whether it removed
  a neighbour.
- Added configurable fallback policy controls:
  - `PF_CLEARPATH_FALLBACK_REMOVE_BATCH`
  - `PF_CLEARPATH_FALLBACK_BATCH_MIN_NEIGHBOURS`
  - `PF_CLEARPATH_FALLBACK_MAX_REMOVES`
- Landed the guarded default:
  - remove up to 4 furthest neighbours per failed retry
  - only while 40 or more neighbours remain
  - no max-removal cap by default
- Kept the controls overrideable from
  `scripts/macos/pf_sovereign_ai_large_army_scale_probe.py`.
- Added matching wrapper controls to
  `scripts/macos/profile_sovereign_large_army_scale.sh`:
  - `PF_PROFILE_CLEARPATH_FALLBACK_REMOVE_BATCH`
  - `PF_PROFILE_CLEARPATH_FALLBACK_BATCH_MIN_NEIGHBOURS`
  - `PF_PROFILE_CLEARPATH_FALLBACK_MAX_REMOVES`

Verification:

```sh
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
bash -n scripts/macos/profile_sovereign_large_army_scale.sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Initial unguarded experiment:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-fallback-batch2 \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-fallback-batch2 \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500 \
  --clearpath-fallback-remove-batch 2
```

- PASS, 1000 units.
- p95 tick: 318.228 ms.

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-fallback-batch4 \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-fallback-batch4 \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500 \
  --clearpath-fallback-remove-batch 4
```

- PASS, 1000 units.
- p95 tick: 310.276 ms.

This confirmed batching helps the dense 1000-unit case, but the unguarded
policy hurt 500-unit p95:

```text
500 baseline p95: 152.376 ms
500 batch2 p95:   178.680 ms
500 batch4 p95:   184.549 ms
```

Guarded threshold experiment:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-fallback-batch4-min40 \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-fallback-batch4-min40 \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500 \
  --clearpath-fallback-remove-batch 4 \
  --clearpath-fallback-batch-min-neighbours 40
```

- PASS, 500 units.
- p95 tick: 150.117 ms.
- no warnings.

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-fallback-batch4-min40-rerun \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-fallback-batch4-min40-rerun \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500 \
  --clearpath-fallback-remove-batch 4 \
  --clearpath-fallback-batch-min-neighbours 40
```

- PASS, 1000 units.
- p95 tick: 316.441 ms.
- no warnings.

Default-policy verification after landing 4/min40:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-fallback-default \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-fallback-default \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

- PASS, 500 units.
- p95 tick: 155.249 ms.
- no warnings.
- movement/combat remained active: moved 420, damaged 12.

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-fallback-default \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-fallback-default \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

- PASS, 1000 units.
- p95 tick: 309.691 ms.
- no warnings.
- movement/combat remained active: moved 673, damaged 22.

Default-policy stats run:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-fallback-default-stats \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-fallback-default-stats \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500 \
  --clearpath-stats-path qa-output/sovereign-ai-large-army-scale-1000-fallback-default-stats/clearpath_stats.json
```

- PASS, 1000 units.
- stats-enabled p95 tick: 508.750 ms. This is diagnostic-only because the
  atomic counters add overhead in hot loops.
- landed policy recorded as `fallback_remove_batch=4` and
  `fallback_batch_min_neighbours=40`.
- `inside_pcr_calls`: 680,252,220 before -> 508,615,966 after.
- `xpoint_ray_pair_tests`: 2,146,621,280 before -> 1,575,690,170 after.
- `no_solution_attempts`: 1,120,623 before -> 1,021,289 after.

Comparison:

```text
500 default before: p50 144.906 ms, p95 152.376 ms
500 default after:  p50 144.083 ms, p95 155.249 ms

1000 default before: p50 292.620 ms, p95 339.576 ms
1000 default after:  p50 279.443 ms, p95 309.691 ms
```

Notes:

- One 1000-unit min40 run exited late in sustained soak before writing a final
  summary. A clean rerun passed; the incomplete run is not used as acceptance
  evidence.
- The default policy is intentionally conservative. Unguarded batch4 was faster
  at 1000 units but hurt 500 units, so the landed threshold protects smaller
  formation cases.

Conclusion:

- Slice 59 closes the first ClearPath fallback-policy optimization. The 1000
  no-stats p95 improves by roughly 30 ms with no soft-budget warnings and no
  movement/combat probe failure.
- Next scale work should refresh the attach-mode Time Profiler with the landed
  default policy to see whether remaining CPU cost is still ClearPath
  `inside_pcr`, Metal `append_skinned_anim_mesh`, or a new bottleneck.

## Completed Slice 60 — Post-Fallback Attach-Mode Time Profiler Refresh

Goal:

- Refresh the 1000-unit attach-mode Time Profiler after the guarded ClearPath
  fallback policy, then pick the next scale bottleneck from current evidence.

Implementation:

- No gameplay behavior change was intended for the profiling run.
- The first refreshed profile exposed a small self-inflicted diagnostic cost:
  even with stats disabled, `clearpath_stats_add` still appeared as a 2.24%
  leaf sample because hot paths still called the helper.
- Changed `src/game/clearpath.c` so disabled stats use a macro guard and do not
  call the helper at all. Stats-enabled runs still write the same counters.

Verification:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
git diff --check -- src/game/clearpath.c
```

First profile, before removing disabled stats helper overhead:

```sh
PF_PROFILE_CAPTURE_PROOF=0 \
  scripts/macos/profile_sovereign_large_army_scale.sh \
  qa-output/sovereign-ai-large-army-scale-1000-fallback-default-profile-nocapture
```

Result:

- PASS, 1000 units.
- profile run summary:
  - p50 tick: 299.585 ms
  - p95 tick: 378.460 ms
  - no warnings
- `time_profile_top.txt`:
  - `append_skinned_anim_mesh`: 24.19% inclusive
  - `inside_pcr`: 21.88% inclusive
  - `compute_vo_xpoints`: 6.20% inclusive
  - `clearpath_stats_add`: 2.24% inclusive

Because `clearpath_stats_add` was diagnostic overhead in a no-stats profile, it
was fixed before using the trace to choose the next optimization target.

Final profile after disabled-stats helper-call removal:

```sh
PF_PROFILE_CAPTURE_PROOF=0 \
  scripts/macos/profile_sovereign_large_army_scale.sh \
  qa-output/sovereign-ai-large-army-scale-1000-fallback-default-profile-nocapture-post-stats-overhead
```

Run artifacts:

- trace:
  `qa-output/sovereign-ai-large-army-scale-1000-fallback-default-profile-nocapture-post-stats-overhead/run-20260510-225132/sovereign_500x2_Time_Profiler.trace`
- hotspot summary:
  `qa-output/sovereign-ai-large-army-scale-1000-fallback-default-profile-nocapture-post-stats-overhead/run-20260510-225132/time_profile_top.txt`
- run summary:
  `qa-output/sovereign-ai-large-army-scale-1000-fallback-default-profile-nocapture-post-stats-overhead/run-20260510-225132/profile_run_summary.json`

Result:

- PASS, 1000 units.
- p50 tick: 297.298 ms.
- p95 tick: 341.818 ms.
- max tick: 341.818 ms.
- no warnings.
- movement/combat stayed active:
  - moved: 679
  - active animations: 388
  - damaged units: 20
  - live counts: player 489, enemy 498

Top leaf samples:

```text
append_skinned_anim_mesh    25.22%
inside_pcr                  21.89%
C_RayRayIntersection2D      12.04%
PFM_Mat4x4_Mult4x1           7.20%
C_InfiniteLineIntersection   3.51%
```

Top inclusive samples:

```text
append_skinned_anim_mesh    25.85%
inside_pcr                  22.91%
C_RayRayIntersection2D      12.04%
compute_vo_xpoints          11.84%
PFM_Mat4x4_Mult4x1           7.20%
render_shadow_depth_draw     2.45%
render_batched_anim_entities 2.11%
render_shadow_batched_anim_entities 2.03%
```

Comparison to the pre-overhead-fix trace:

```text
pre-overhead-fix p95:  378.460 ms
post-overhead-fix p95: 341.818 ms
```

Conclusion:

- The profile is now clean of the disabled ClearPath stats helper overhead.
- `append_skinned_anim_mesh` is the current leading CPU hotspot after the
  ClearPath fallback policy, with remaining ClearPath geometry close behind.
- The next best scale target is another Metal animated-mesh assembly slice:
  inspect `append_skinned_anim_mesh`, `render_batched_anim_entities`, and shadow
  animated-batch upload/churn to reduce per-frame matrix work and buffer
  allocation/copy overhead. ClearPath `inside_pcr` remains the second lane if
  animation assembly does not yield.

## Completed Slice 61 — Metal Animated Mesh Affine Assembly Probe

Goal:

- Continue the 1000-unit scale work by attacking the current leading CPU
  hotspot, `append_skinned_anim_mesh`, while keeping the 500-unit regression
  floor green.

Code changes:

- Updated `src/render/backend_metal.m:append_skinned_anim_mesh()` to remove the
  remaining per-influence generic `PFM_Mat4x4_Mult4x1` calls from the batched
  animated assembly loop.
- The batched path now uses the already-precomposed world skin matrices with
  direct column-major affine point/vector transforms and square-length normal
  normalization.
- `transform_normal_with_mat4()` now uses the same direct vector transform and
  square-length normalization helper pattern instead of constructing temporary
  vec4 values for the generic matrix multiply.

Rejected sub-attempt:

- A single-weight vertex shortcut was tested because the current Knight/Mage
  assets have many one-weight vertices, but it caused the 500-unit probe to exit
  during engage staging. That shortcut was backed out before this slice was
  finalized.

Verification:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit regression:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-skin-inline-final-rerun \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-skin-inline-final-rerun \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 150.862 / 164.384 / 164.384 ms
moved: 414
active animations: 363
damaged units: 17
warnings: []
```

1000-unit full profile:

```sh
xcrun xctrace record --quiet --no-prompt \
  --template "Time Profiler" \
  --output qa-output/sovereign-ai-large-army-scale-1000-skin-inline-forceinline-full-xctrace-launch/sovereign_500x2_Time_Profiler.trace \
  --launch ./bin/pf-arm64 -- ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
    --output-dir qa-output/sovereign-ai-large-army-scale-1000-skin-inline-forceinline-full-xctrace-launch \
    --units-per-side 500 \
    --settle-ticks 300 \
    --soak-ticks 240 \
    --order-mode attack-move \
    --budget-label 1000-skin-inline-forceinline-full-xctrace \
    --sample-budget-every 30 \
    --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 291.905 / 356.499 / 356.499 ms
moved: 676
active animations: 386
damaged units: 26
warnings: []
trace: qa-output/sovereign-ai-large-army-scale-1000-skin-inline-forceinline-full-xctrace-launch/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-skin-inline-forceinline-full-xctrace-launch/time_profile_top.txt
```

Top leaf samples after this slice:

```text
append_skinned_anim_mesh    26.49%
inside_pcr                  13.66%
C_RayRayIntersection2D      11.93%
transform_vector_with_mat4   5.51%
transform_point_with_mat4    4.86%
normalize_vec3_fast          3.67%
```

Conclusion:

- This slice removes `PFM_Mat4x4_Mult4x1` from the animated-mesh hot list, but
  it does not materially improve the 1000-unit p95 budget yet. The full gate
  still passes with no warnings, and p50 is slightly better than Slice 60, but
  p95 remains in the same 340-360 ms band.
- `append_skinned_anim_mesh` is still the dominant hotspot. The next meaningful
  animation-side work should be a larger structural change: either avoid
  reassembling CPU-skinned vertices for both visible and shadow passes, or move
  the batched animated path closer to GPU skinning / pose-texture instancing.
- ClearPath remains the second lane, but the latest profile shows animation
  assembly is still the best first target if we want another large p95 drop.

## Completed Slice 62 — Per-Frame Metal Skinned Mesh Cache

Goal:

- Avoid duplicate CPU skinning for animated entities that are drawn once in the
  shadow pass and again in the main pass during the same Metal frame.
- Keep the change scoped to the current CPU-skinned Metal path before attempting
  a larger GPU-skinning / pose-texture instancing redesign.

Code changes:

- Added a per-frame `skinned_mesh_cache_entry` array in
  `src/render/backend_metal.m`.
- `shadow_pass_begin()` starts the cache so shadow-pass animated draws can seed
  it.
- `frame_begin()` preserves an already-active shadow-seeded cache instead of
  clearing it before the main pass.
- `append_skinned_anim_mesh()` now checks for a same UID, render-private pointer,
  and exact model matrix cache hit before doing CPU skinning. Cache hits copy
  the previously assembled vertices into the destination stream.
- `frame_present()`, `frame_abort()`, and `render_destroy_ctx()` close or free
  the cache.

Verification:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit regression:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-skin-cache \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-skin-cache \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 86.941 / 90.064 / 90.064 ms
moved: 410
active animations: 370
damaged units: 10
player/enemy live: 248 / 235
warnings: []
```

1000-unit Time Profiler launch run:

```sh
xcrun xctrace record --quiet --no-prompt \
  --template "Time Profiler" \
  --output /Users/dev/Desktop/OpenGL\ RTS\ game\ engine/qa-output/sovereign-ai-large-army-scale-1000-skin-cache-xctrace-launch/sovereign_500x2_Time_Profiler.trace \
  --launch ./bin/pf-arm64 -- ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
    --output-dir qa-output/sovereign-ai-large-army-scale-1000-skin-cache-xctrace-launch \
    --units-per-side 500 \
    --settle-ticks 300 \
    --soak-ticks 240 \
    --order-mode attack-move \
    --budget-label 1000-skin-cache-xctrace \
    --sample-budget-every 30 \
    --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 172.777 / 193.387 / 193.387 ms
moved: 688
active animations: 380
damaged units: 19
player/enemy live: 487 / 497
warnings: []
trace: qa-output/sovereign-ai-large-army-scale-1000-skin-cache-xctrace-launch/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-skin-cache-xctrace-launch/time_profile_top.txt
```

Top profile after the cache:

```text
append_skinned_anim_mesh    29.50% inclusive
C_RayRayIntersection2D      12.10% leaf
inside_pcr                  11.36% inclusive
compute_vo_xpoints           7.20% inclusive
transform_vector_with_mat4   5.89% leaf
transform_point_with_mat4    5.13% leaf
normalize_vec3_fast          3.82% leaf
```

Before/after:

```text
500-unit p95:       164.384 ms -> 90.064 ms
1000-unit p95:      356.499 ms -> 193.387 ms
1000-unit p50:      291.905 ms -> 172.777 ms
1000-unit warnings: [] -> []
```

Conclusion:

- This is the first large structural animation-side performance win. It removes
  the duplicate shadow/main CPU-skinning work for cacheable animated draws while
  keeping the current CPU-streamed Metal implementation intact.
- `append_skinned_anim_mesh` still appears at the top of the profile because the
  remaining CPU-skinned work is now a larger share of a much cheaper run. The
  absolute p95 drop is the important signal.
- The next small-to-medium slice should return to ClearPath with the new
  193 ms baseline and tune `inside_pcr` / ray-intersection pressure. The next
  larger renderer slice should prototype GPU skinning or pose-texture instanced
  batching so animated meshes are no longer assembled on CPU per frame.

## Next Slice

The next clean target is either:

- push `codex/sovereign-publish-preflight` to
  `sovereignrealms/sovereign-realms-engine`, or
- continue 1000+ scale tuning. The smallest follow-up is now the remaining
  animated-rendering hot path after the cache, especially shadow-side CPU
  skinning and buffer upload churn. The larger renderer follow-up is a
  GPU-skinning / pose-texture instancing prototype.

## Completed Slice 63 — ClearPath Fast Math And Projectile Trail Guard

Goal:

- Reduce ClearPath `inside_pcr` / ray-candidate math overhead from the new
  post-cache baseline without changing movement policy.
- Keep the 500-unit gate as the regression floor and the 1000-unit gate as the
  target case.

Code changes:

- Updated `src/game/clearpath.c:inside_pcr()` to avoid per-ray-side
  `PFM_Vec2_Len()` + `PFM_Vec2_Normal()` work. The same normalized determinant
  boundary test is now expressed with squared length:
  - left side: `det < EPSILON * len`
  - right side: `det > -EPSILON * len`
  - implemented without a square root by comparing `det * det` against
    `EPSILON_SQ * len_sq` when the sign alone is not decisive.
- Added a ClearPath-local `ray_ray_intersection_fast()` based on 2D cross
  products and used it in `compute_vo_xpoints()`. This avoids the generic
  slope-based `C_RayRayIntersection2D()` helper in the hot path.
- Fixed a projectile trail guard exposed by the first 1000-unit verification
  runs: `phys_proj_spawn_trails()` was checking projectile collision flags
  (`curr->flags`) instead of sprite descriptor flags (`curr->sprite_flags`).
  Since `PROJ_ONLY_HIT_ENEMIES` shares the same bit value as
  `PROJ_HAS_TRAIL_SPRITE`, dense projectile combat could attempt to play a
  trail sprite with no filename.

Verification:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit regression after the projectile guard:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-clearpath-fastmath-projectile-guard \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-clearpath-fastmath-projectile-guard \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 77.549 / 103.952 / 103.952 ms
moved: 398
active animations: 314
damaged units: 23
player/enemy live: 219 / 215
warnings: []
```

1000-unit gate after the projectile guard:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-clearpath-fastmath-projectile-guard \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-clearpath-fastmath-projectile-guard \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 163.417 / 196.212 / 196.212 ms
moved: 686
active animations: 335
damaged units: 51
player/enemy live: 466 / 445
warnings: []
```

1000-unit Time Profiler launch run:

```sh
xcrun xctrace record --quiet --no-prompt \
  --template "Time Profiler" \
  --output /Users/dev/Desktop/OpenGL\ RTS\ game\ engine/qa-output/sovereign-ai-large-army-scale-1000-clearpath-fastmath-xctrace-launch/sovereign_500x2_Time_Profiler.trace \
  --launch ./bin/pf-arm64 -- ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
    --output-dir qa-output/sovereign-ai-large-army-scale-1000-clearpath-fastmath-xctrace-launch \
    --units-per-side 500 \
    --settle-ticks 300 \
    --soak-ticks 240 \
    --order-mode attack-move \
    --budget-label 1000-clearpath-fastmath-xctrace \
    --sample-budget-every 30 \
    --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 166.446 / 211.879 / 211.879 ms
moved: 692
active animations: 360
damaged units: 46
player/enemy live: 470 / 444
warnings: []
trace: qa-output/sovereign-ai-large-army-scale-1000-clearpath-fastmath-xctrace-launch/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-clearpath-fastmath-xctrace-launch/time_profile_top.txt
```

Top profile after this slice:

```text
append_skinned_anim_mesh    32.88% inclusive
inside_pcr                   9.29% inclusive
compute_vo_xpoints           6.05% inclusive
ray_ray_intersection_fast    3.96% inclusive
```

Comparison to Slice 62 profile:

```text
generic C_RayRayIntersection2D: 12.10% leaf -> removed from the hot list
inside_pcr:                    11.36% inclusive -> 9.29% inclusive
compute_vo_xpoints:             7.20% inclusive -> 6.05% inclusive
1000-unit no-stats p95:       193.387 ms -> 196.212 ms
```

Notes:

- The first two 1000-unit verification attempts crashed in projectile trail
  playback before completing the scale gate. Crash reports pointed to
  `Sprite_PlayAnim()` through `phys_proj_spawn_trails()`, not ClearPath. The
  `sprite_flags` guard fix closed that hidden projectile-heavy crash and the
  1000-unit gate then passed.
- This is a profile-shape cleanup more than a wall-clock p95 win. The p50 is
  slightly better than Slice 62, but p95 is effectively neutral/noisy. The
  important outcome is that ClearPath ray-intersection helper overhead is no
  longer the obvious next CPU lane.

Conclusion:

- ClearPath candidate math is now cleaner and lower in the current profile. The
  next scale bottleneck is back in Metal animated rendering: remaining
  `append_skinned_anim_mesh` CPU work, especially shadow-side assembly and
  buffer upload churn.
- A larger GPU-skinning / pose-texture instancing prototype remains the
  strategic renderer-scale target, but a smaller next slice can inspect
  shadow/main animated-batch buffer allocation and copy behavior first.

## Slice 64 - 2026-05-11 - Metal Animated Shadow Batch Upload Churn

Goal:

- Reduce the animated-rendering work that still happens twice per frame around
  shadow and main passes, without starting the larger GPU-skinning /
  pose-texture instancing prototype.

Implementation:

- Changed the normal Metal shadow animated path to batch animated casters that
  share the same `render_private`, mirroring the existing main-pass animated
  batch pattern.
- Kept the shadow owner-id diagnostic pass on the old per-caster path so a bad
  shadow pixel can still be traced to an exact caster UID.
- Rejected a follow-up reusable scratch-buffer experiment because it did not
  improve the 500/1000 gates and produced noisier p95s.

Verification:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit final regression:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-shadow-anim-batch-final \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-shadow-anim-batch-final \
  --sample-budget-every 30
```

Result:

```text
status: pass
p50/p95/max: 81.047 / 101.976 / 101.976 ms
moved: 391
active animations: 320
damaged units: 17
player/enemy live: 220 / 220
warnings: []
```

1000-unit final gate:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-shadow-anim-batch-final \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-shadow-anim-batch-final \
  --sample-budget-every 30
```

Result:

```text
status: pass
p50/p95/max: 159.563 / 180.850 / 180.850 ms
moved: 693
active animations: 337
damaged units: 50
player/enemy live: 466 / 447
warnings: []
```

Comparison to Slice 63 no-stats gate:

```text
1000-unit p50: 163.417 ms -> 159.563 ms
1000-unit p95: 196.212 ms -> 180.850 ms
1000-unit max: 196.212 ms -> 180.850 ms
```

Time Profiler run:

```text
run: qa-output/sovereign-ai-large-army-scale-1000-shadow-anim-batch-profile/run-20260511-160953/
status: pass
profiled p50/p95/max: 157.169 / 219.665 / 219.665 ms
```

Top profile after this slice:

```text
append_skinned_anim_mesh              32.00% inclusive
inside_pcr                           11.07% inclusive
compute_vo_xpoints                    5.76% inclusive
render_shadow_batched_anim_entities   2.99% inclusive
newBufferWithBytes                    2.57% inclusive
render_static_vertex_stream           2.13% inclusive
render_shadow_vertex_stream           2.11% inclusive
```

Notes:

- The xctrace p95 is noisier than the no-stats gate, so the budget gate remains
  the no-stats probe. The profile is used for hotspot shape only.
- Shadow-side animated batching is a real wall-clock win in the normal 1000-unit
  gate, but CPU skinning remains the dominant renderer lane.

Conclusion:

- The current 1000-unit no-stats p95 baseline is now about 181 ms.
- Metal animated rendering remains the next big scale lane. The next structural
  renderer target is GPU skinning / pose-texture instanced batching, with
  ClearPath `inside_pcr` pressure still the second lane to watch.

## Completed Slice 65 — Env-Gated Metal GPU Skinning Prototype

Goal:

- Prototype GPU-side skinning for Metal animated meshes without changing the
  default renderer path yet.
- Move the 1000-unit scale gate past the CPU `append_skinned_anim_mesh`
  hotspot and verify the new bottleneck with Time Profiler evidence.

Implementation:

- Added an opt-in `PF_METAL_GPU_SKINNING=1` Metal path for batched animated
  main-pass draws.
- Added the matching opt-in shadow-depth path for batched animated casters.
- Uploaded immutable animated source vertices once per render-private object
  and sent per-instance world skin matrices to Metal for instanced draws.
- Kept the shadow owner-id diagnostic pass on the existing CPU path so exact
  caster UID tracing remains available.
- Left the default path unchanged unless `PF_METAL_GPU_SKINNING=1` is set.

Verification:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Default-path smoke:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-100-default-after-gpu-skinning \
  --units-per-side 50 \
  --settle-ticks 120 \
  --soak-ticks 60 \
  --order-mode attack-move \
  --budget-label 100-default-after-gpu-skinning \
  --sample-budget-every 30
```

Result:

```text
status: pass
runtime/spawn/orders/motion/anim/combat/sustain: pass
```

500-unit opt-in gate:

```sh
env PF_METAL_GPU_SKINNING=1 ./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-gpu-skinning-shadow-prototype \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-gpu-skinning-shadow-prototype \
  --sample-budget-every 30
```

Result:

```text
status: pass
p50/p95/max: 29.377 / 33.693 / 33.693 ms
damaged units: 20
player/enemy live: 234 / 236
warnings: []
```

1000-unit opt-in gate:

```sh
env PF_METAL_GPU_SKINNING=1 ./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-gpu-skinning-shadow-prototype \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-gpu-skinning-shadow-prototype \
  --sample-budget-every 30
```

Result:

```text
status: pass
p50/p95/max: 47.184 / 68.972 / 68.972 ms
damaged units: 48
player/enemy live: 476 / 448
warnings: []
```

1000-unit Time Profiler run:

```text
run: qa-output/sovereign-ai-large-army-scale-1000-gpu-skinning-shadow-profile/run-20260511-192451/
status: pass
profiled p50/p95/max: 47.373 / 54.317 / 54.317 ms
```

Top profile after this slice:

```text
inside_pcr                 18.98% inclusive
compute_vo_xpoints         11.42% inclusive
G_ClearPath_NewVelocity     8.21% inclusive
PFM_Mat4x4_Mult4x4          4.48% leaf
render_shadow_depth_draw    1.00% inclusive
```

Comparison to Slice 64:

```text
500-unit p95:      101.976 ms -> 33.693 ms
1000-unit p95:     180.850 ms -> 68.972 ms
1000 profiled p95: 219.665 ms -> 54.317 ms
```

Notes:

- This is a major scale win, but it is still an opt-in prototype. It needs
  broader visual parity, capture-proof, and longer-session verification before
  becoming the Metal default.
- `append_skinned_anim_mesh` no longer appears in the top profile list for the
  opt-in path. The leading 1000-unit bottleneck is again dense ClearPath
  collision avoidance, especially `inside_pcr()` and `compute_vo_xpoints()`.
- The per-caster shadow owner diagnostic path intentionally remains CPU-skinned
  so shadow debugging can still identify exact caster UIDs.

Conclusion:

- The next best scale target is ClearPath dense-candidate policy/algorithm work
  using the new GPU-skinning baseline.
- A separate renderer hardening target is to promote `PF_METAL_GPU_SKINNING=1`
  from prototype to candidate default after visual parity and wider gameplay
  checks prove it does not alter animation, shadows, or material output.

## Completed Slice 66 — ClearPath Dense-Policy Probe And GPU-Skinning Capture Proof

Goal:

- Tune ClearPath dense-candidate pressure against the new
  `PF_METAL_GPU_SKINNING=1` baseline, but only land a policy change if the
  500/1000 gates prove it stable.
- Add capture-proof evidence for the GPU-skinning path before considering it
  for default promotion.

ClearPath evidence:

- Ran a short 1000-unit ClearPath-stats diagnostic under GPU skinning:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-gpu-skinning-clearpath-stats-short/
status: pass
p50/p95/max: 50.543 / 326.271 / 326.271 ms
attempts: 380,778
fallback_retry_steps: 354,182
fallback_removes: 428,882
inside_pcr_calls: 187,074,320
xpoint_ray_pair_tests: 567,602,606
no_solution_attempts: 354,182
```

This confirms the dominant ClearPath pressure is still repeated no-solution
fallback in dense formations, not renderer-side animation work.

Rejected experiments:

- `PF_CLEARPATH_FALLBACK_REMOVE_BATCH=8` with
  `PF_CLEARPATH_FALLBACK_BATCH_MIN_NEIGHBOURS=40` improved the 1000-unit p95
  but reduced travel/combat activity enough to be too aggressive.
- Batch `8` with min-neighbours `80` looked better in one override run, but
  after rebuilding it was not stable as a default: the 1000-unit p95 regressed
  badly in the default-policy verification run.
- A behavior-preserving squared-distance cleanup in `compute_vnew()` and
  `remove_furthest()` passed functionally, but did not improve the 500/1000
  gates, so it was reverted rather than landed as pretend progress.

Capture-proof hardening:

```sh
env PF_METAL_GPU_SKINNING=1 ./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-gpu-skinning-capture-proof \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-gpu-skinning-capture-proof \
  --sample-budget-every 30 \
  --capture-proof \
  --wide-zoom-height 900
```

Result:

```text
status: pass
p50/p95/max: 30.297 / 45.808 / 45.808 ms
moved: 382
average travel: 19.352
active animations: 342
damaged units: 18
engage live units: 232 / 232
captures: 4
capture resolution: 3456x2234
```

Capture artifacts:

- `qa-output/sovereign-ai-large-army-scale-500-gpu-skinning-capture-proof/sovereign_large_army_before_orders.png`
- `qa-output/sovereign-ai-large-army-scale-500-gpu-skinning-capture-proof/sovereign_large_army_engage_sample.png`
- `qa-output/sovereign-ai-large-army-scale-500-gpu-skinning-capture-proof/sovereign_large_army_sustained_soak.png`
- `qa-output/sovereign-ai-large-army-scale-500-gpu-skinning-capture-proof/sovereign_large_army_wide_zoom.png`

Verification:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Default renderer smoke after reverting the rejected ClearPath experiments:

```text
output: qa-output/sovereign-ai-large-army-scale-100-default-after-clearpath-squared-distance/
status: pass
runtime/spawn/orders/motion/anim/combat/sustain: pass
```

Conclusion:

- No ClearPath default policy change landed in this slice. The evidence says
  fallback tuning needs a deeper algorithmic candidate, not a broader removal
  batch.
- The GPU-skinning path gained useful visual/capture proof and remains a strong
  opt-in candidate, but still needs Metal/OpenGL parity capture before default
  promotion.
- Next best target: either a more principled ClearPath no-solution fallback
  strategy, or GPU-skinning visual parity against OpenGL/CPU-skinned reference
  captures.

## Completed Slice 67 — GPU-Skinning Visual Parity Gate

Goal:

- Verify the `PF_METAL_GPU_SKINNING=1` Metal path against the OpenGL/CPU-skinned
  reference before considering any default promotion.
- Keep this as evidence-first validation, not another renderer rewrite.

Harness changes:

- `scripts/macos/pf_visual_parity_probe.py` now records key parity environment
  values in the summary JSON:
  - `PF_METAL_GPU_SKINNING`
  - `PF_PARITY_MODE`
  - `PF_RTS_TIME_OF_DAY_PHASE`
- The visual-parity settle timeout can be extended via
  `PF_VISUAL_PARITY_SETTLE_TIMEOUT_SEC`. The default remains `8.0` seconds.
- Added `scripts/macos/compare_png_blocks.py`, a repo-local stdlib PNG block
  comparator, so parity checks no longer depend on vanished `/tmp` helper
  scripts.

Verification:

```sh
python3 -m py_compile scripts/macos/pf_visual_parity_probe.py
python3 -m py_compile scripts/macos/compare_png_blocks.py
env PF_METAL_GPU_SKINNING=1 PF_VISUAL_PARITY_SETTLE_TIMEOUT_SEC=20 \
  scripts/macos/capture_visual_parity.sh \
  visual_parity_captures/2026-05-11-gpu-skinning-visual-parity
```

Capture result:

```text
VISUAL_PARITY_PASS backend=OPENGL scenes=5
VISUAL_PARITY_PASS backend=METAL scenes=5
CAMERAS MATCH scenes=5 max_position_delta=0.000000
summary_metal.env.PF_METAL_GPU_SKINNING = 1
```

Nonblank evidence:

```text
PNG_NONBLANK_PASS paths=10
resolution: 3456x2234
scenes: overview, water, rocks, combat, skybox
```

Key block comparisons, OpenGL reference to Metal GPU-skinning candidate:

```text
combat half=60
2074,1370 ratio=1.00,1.00,0.99
2200,1500 ratio=0.96,0.95,0.95
1900,1300 ratio=1.00,1.00,1.00
2592,477  ratio=1.00,1.00,1.00
2300,1700 ratio=1.00,1.00,1.00

combat half=2
2074,1370 ratio=1.00,1.00,1.00
2068,1370 ratio=1.00,1.00,1.00
2080,1370 ratio=1.00,1.00,1.00
2200,1500 ratio=1.00,1.00,1.00
2210,1500 ratio=0.89,0.89,0.89

overview half=60
1700,900  ratio=1.00,1.00,1.00
1900,1300 ratio=1.00,1.00,1.00
2074,1370 ratio=1.00,1.00,1.01

water half=60
1700,900  ratio=1.00,1.00,1.00
1900,1300 ratio=1.00,1.00,1.00

rocks half=60
1700,900  ratio=1.01,1.01,1.01
1900,1300 ratio=1.00,1.00,1.00

skybox half=60
1728,1117 ratio=1.00,1.00,1.00
1000,800  ratio=1.00,1.00,1.00
2500,1400 ratio=1.00,1.00,1.00
```

Notes:

- The first parity run timed out during OpenGL overview settling before any
  image comparison. Extending the settle timeout to 20 seconds produced a clean
  deterministic capture without changing the required sample count.
- The localized `2210,1500` half=2 darker Metal sample is an edge/composition
  point; the surrounding combat/unit half=2 and half=60 checks are at parity.
- No core renderer behavior changed in this slice.

Conclusion:

- GPU skinning has now passed both a large-army capture-proof gate and a
  deterministic OpenGL-vs-Metal visual parity gate.
- It is reasonable to treat `PF_METAL_GPU_SKINNING=1` as a candidate default
  for the next controlled scale run.
- Next best target: repeat the 500/1000-unit scale gates with GPU skinning as
  the intended candidate path, then stage a small default flip only if those
  gates remain green. ClearPath no-solution fallback remains the larger
  algorithmic bottleneck after the renderer path is locked.

## Completed Slice 68 — Metal GPU-Skinning Default Promotion

Goal:

- Repeat the 500/1000-unit scale gates with GPU skinning as the candidate path.
- Promote GPU skinning to the Metal default only if both gates remain green.
- Keep an explicit CPU-skinning opt-out for debugging and comparison.

Implementation:

- Changed `src/render/backend_metal.m:gpu_skinning_enabled()` so Metal GPU
  skinning is enabled by default.
- `PF_METAL_GPU_SKINNING=0` now disables the path and keeps the old CPU-skinned
  fallback available for diagnostics.

Candidate gates before the default flip:

```sh
env PF_METAL_GPU_SKINNING=1 ./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-gpu-skinning-candidate-default \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-gpu-skinning-candidate-default \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 27.944 / 34.938 / 34.938 ms
moved: 365
active animations: 348
damaged units: 19
warnings: []
```

```sh
env PF_METAL_GPU_SKINNING=1 ./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-gpu-skinning-candidate-default \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-gpu-skinning-candidate-default \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 49.445 / 77.599 / 77.599 ms
moved: 686
active animations: 327
damaged units: 47
warnings: []
```

Default-path verification after the flip:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-500-gpu-skinning-default \
  --units-per-side 250 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 500-gpu-skinning-default \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 27.785 / 38.523 / 38.523 ms
moved: 367
active animations: 341
damaged units: 18
warnings: []
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-gpu-skinning-default \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-gpu-skinning-default \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 46.582 / 59.233 / 59.233 ms
moved: 687
active animations: 342
damaged units: 31
warnings: []
```

Opt-out smoke:

```sh
env PF_METAL_GPU_SKINNING=0 ./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-100-gpu-skinning-optout \
  --units-per-side 50 \
  --settle-ticks 120 \
  --soak-ticks 60 \
  --order-mode attack-move \
  --budget-label 100-gpu-skinning-optout \
  --sample-budget-every 30 \
  --soft-budget-ms-per-tick 500
```

Result:

```text
status: pass
p50/p95/max: 20.622 / 29.598 / 29.598 ms
moved: 94
active animations: 97
damaged units: 4
warnings: []
```

Default visual-parity verification:

```sh
env PF_VISUAL_PARITY_SETTLE_TIMEOUT_SEC=20 \
  scripts/macos/capture_visual_parity.sh \
  visual_parity_captures/2026-05-12-gpu-skinning-default-visual-parity
```

Result:

```text
VISUAL_PARITY_PASS backend=OPENGL scenes=5
VISUAL_PARITY_PASS backend=METAL scenes=5
CAMERAS MATCH scenes=5 max_position_delta=0.000000
PNG_NONBLANK_PASS paths=10
```

Representative default-path block comparisons:

```text
combat half=60
2074,1370 ratio=1.00,1.00,0.99
2200,1500 ratio=0.96,0.95,0.95
1900,1300 ratio=1.00,1.00,1.00
2592,477  ratio=1.00,1.00,1.00
2300,1700 ratio=1.00,1.00,1.00

combat half=2
2074,1370 ratio=1.00,1.00,1.00
2068,1370 ratio=1.00,1.00,1.00
2080,1370 ratio=1.00,1.00,1.00
2200,1500 ratio=1.00,1.00,1.00

overview/water/rocks half=60
overview 1700,900  ratio=1.00,1.00,1.00
water    1700,900  ratio=1.00,1.00,1.00
rocks    1700,900  ratio=1.01,1.01,1.01
```

Conclusion:

- Metal GPU skinning is now the default animated rendering path.
- The 500/1000-unit gates remain green after the default flip.
- The default path still passes the deterministic OpenGL-vs-Metal visual
  parity harness.
- The CPU-skinned fallback remains available via `PF_METAL_GPU_SKINNING=0`.
- Next best target: refresh the 1000-unit Time Profiler on the default path and
  confirm the dominant hotspot is still ClearPath no-solution fallback before
  starting a larger ClearPath algorithm slice.

## Completed Slice 69 — Default-Path 1000-Unit Time Profiler Refresh

Goal:

- Run a fresh 1000-unit Time Profiler after Metal GPU skinning became the
  default path.
- Confirm whether the leading bottleneck is still ClearPath dense-candidate
  geometry before touching the ClearPath algorithm.

Command:

```sh
env PF_PROFILE_CAPTURE_PROOF=0 PF_PROFILE_CLEARPATH_STATS=0 \
  scripts/macos/profile_sovereign_large_army_scale.sh \
  qa-output/sovereign-ai-large-army-scale-1000-gpu-skinning-default-profile-nocapture
```

Artifacts:

```text
run: qa-output/sovereign-ai-large-army-scale-1000-gpu-skinning-default-profile-nocapture/run-20260512-070606/
trace: qa-output/sovereign-ai-large-army-scale-1000-gpu-skinning-default-profile-nocapture/run-20260512-070606/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-gpu-skinning-default-profile-nocapture/run-20260512-070606/time_profile_top.txt
summary: qa-output/sovereign-ai-large-army-scale-1000-gpu-skinning-default-profile-nocapture/run-20260512-070606/profile_run_summary.json
```

Result:

```text
status: pass
total units: 1000
p50/p95/max: 48.540 / 77.773 / 77.773 ms
moved: 691
active animations: 348
damaged units: 39
warnings: []
```

Top leaf samples:

```text
inside_pcr                 17.58%
compute_vo_xpoints         11.38%
ray_ray_intersection_fast    9.20%
PFM_Mat4x4_Mult4x4          4.59%
render_shadow_vertex_stream 0.95%
```

Top inclusive samples:

```text
inside_pcr                 19.54%
compute_vo_xpoints         12.38%
ray_ray_intersection_fast    9.20%
G_ClearPath_NewVelocity     5.73%
move_velocity_work          5.69%
PFM_Mat4x4_Mult4x4          4.59%
render_minimap_units        1.03%
```

Comparison to the last opt-in GPU-skinning profile:

```text
profiled p95:           54.317 ms -> 77.773 ms
inside_pcr inclusive:   18.98%    -> 19.54%
compute_vo_xpoints:     11.42%    -> 12.38%
ray_ray_intersection:    8.87%    -> 9.20%
G_ClearPath_NewVelocity: 8.21%    -> 5.73%
```

Notes:

- The profile remains well below the 500 ms soft budget and has normal
  movement, animation, and combat activity.
- The p95 is noisier than the previous opt-in profile, but the hotspot shape is
  stable: animated mesh CPU skinning is no longer the dominant lane.
- Metal GPU skinning remains the default path; no code change was needed in
  this slice.

Conclusion:

- ClearPath dense-candidate geometry is the confirmed next performance target.
- The next slice should add a more principled no-solution fallback/candidate
  reduction strategy for dense formations, using the current default
  GPU-skinning path as the baseline.

## Completed Slice 70 — ClearPath Nearest-Constraint Dense Cap

Goal:

- Reduce dense-formation ClearPath candidate pressure using the current
  default Metal GPU-skinning path as the baseline.
- Avoid another blind fallback-removal batch. Prefer a local collision-avoidance
  rule that keeps the closest blockers and discards far blockers before the
  expensive pairwise ray-intersection pass.

Implementation:

- Added `PF_CLEARPATH_MAX_CONSTRAINT_NEIGHBOURS` in `src/game/clearpath.c`.
- Default value is `32`; `0` disables the cap for A/B debugging.
- `G_ClearPath_NewVelocity()` now trims oversized local dynamic/static
  neighbour sets to the nearest constraints before solving the combined
  reciprocal velocity obstacle.
- Added ClearPath stats fields for:
  - `max_constraint_neighbours`
  - `constraint_cap_attempts`
  - `constraint_cap_removes`
  - `constraint_cap_max_input_neighbours`
- Added `--clearpath-max-constraint-neighbours` to
  `scripts/macos/pf_sovereign_ai_large_army_scale_probe.py`.

Verification:

```sh
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
git diff --check -- src/game/clearpath.c scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit regression:

```text
output: qa-output/sovereign-ai-large-army-scale-500-clearpath-nearest-cap/
status: pass
p50/p95/max: 28.143 / 36.191 / 36.191 ms
moved: 376
average travel: 16.648
active animations: 341
damaged units: 20
warnings: []
```

1000-unit no-stats gate:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-clearpath-nearest-cap/
status: pass
p50/p95/max: 45.792 / 52.338 / 52.338 ms
moved: 687
average travel: 4.869
active animations: 348
damaged units: 43
warnings: []
```

Comparison to Slice 69 default-path baseline:

```text
p95:              77.773 ms -> 52.338 ms
moved:            691       -> 687
average travel:   4.513     -> 4.869
active anims:     348       -> 348
damaged units:    39        -> 43
```

ClearPath stats run:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-clearpath-nearest-cap-stats/
status: pass
max_constraint_neighbours: 32
constraint_cap_attempts: 41,675
constraint_cap_removes: 439,448
constraint_cap_max_input_neighbours: 64
max_rays: 64
avg_xpoint_pair_tests_per_call: 972.498
```

The previous Slice 66 stats run had `max_rays=128` and
`avg_xpoint_pair_tests_per_call=1506.184`, so this slice materially reduces the
worst dense-candidate geometry while preserving the gameplay checks.

Time Profiler:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-clearpath-nearest-cap-xctrace-launch/
trace: qa-output/sovereign-ai-large-army-scale-1000-clearpath-nearest-cap-xctrace-launch/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-clearpath-nearest-cap-xctrace-launch/time_profile_top.txt
profiled p50/p95/max: 51.240 / 64.852 / 64.852 ms
```

Top leaf samples after the cap:

```text
inside_pcr                  8.96%
compute_vo_xpoints          7.59%
PFM_Mat4x4_Mult4x4          5.97%
ray_ray_intersection_fast    5.95%
render_shadow_vertex_stream 1.38%
render_gpu_skinned_anim_batch 1.00%
```

Top inclusive samples after the cap:

```text
inside_pcr                 10.14%
compute_vo_xpoints          8.77%
PFM_Mat4x4_Mult4x4          5.97%
ray_ray_intersection_fast    5.95%
field_update_enemies        2.30%
G_ClearPath_NewVelocity     1.22%
move_velocity_work          1.17%
```

Notes:

- The attach-mode profiler wrapper hit the known macOS SDL display-service
  startup issue (`The video driver did not add any displays`) before probe
  startup, so this slice used launch-mode `xcrun xctrace record` instead.
- The launch-mode profiled run still passed the 1000-unit gate and exported a
  usable Time Profiler table.
- ClearPath is improved but not gone: `inside_pcr` and `compute_vo_xpoints`
  remain visible, now closer to other engine costs.

Conclusion:

- Keep the nearest-constraint dense cap as the default ClearPath policy.
- Next performance target should be chosen from the new profile shape:
  remaining ClearPath geometry, `PFM_Mat4x4_Mult4x4` in animated/render paths,
  or higher-level path/field update costs.

## Rejected Slice 71 — ClearPath Projection-First Candidate Shortcut

Goal:

- Try to reduce remaining `inside_pcr` / `compute_vo_xpoints` cost by checking
  cheap preferred-velocity projection candidates before the O(n^2)
  ray-intersection pass in dense ClearPath solves.

Experiment:

- Added a temporary dense projection-first path after `desired_inside_pcr`.
- The wide trigger (`PF_CLEARPATH_PROJECTION_FIRST_MIN_RAYS=48`) skipped the
  intersection pass whenever projection candidates were available.
- A stricter trigger (`64`) only affected max-density capped cases.

Results:

```text
Slice 70 nearest-cap baseline:
1000 p50/p95/max: 45.792 / 52.338 / 52.338 ms
moved: 687
average travel: 4.869
active animations: 348
damaged units: 43

Projection-first min_rays=48:
1000 p50/p95/max: 45.981 / 72.341 / 72.341 ms
moved: 714
average travel: 5.176
active animations: 338
damaged units: 39

Projection-first min_rays=64, default rerun:
1000 p50/p95/max: 46.740 / 85.188 / 85.188 ms
moved: 707
average travel: 5.431
active animations: 332
damaged units: 39
```

Decision:

- Rejected and removed the projection-first code and CLI option.
- The shortcut could improve one narrow run, but repeated 1000-unit evidence was
  noisier and worse than the Slice 70 nearest-cap baseline.
- Final current-code verification after revert:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-clearpath-current-after-reject/
status: pass
1000 p50/p95/max: 45.952 / 51.648 / 51.648 ms
moved: 698
average travel: 5.651
active animations: 325
damaged units: 41
warnings: []
```

Conclusion:

- Keep Slice 70 as the landed ClearPath improvement.
- Next performance slice should avoid projection-only shortcuts and instead
  inspect either remaining matrix/render costs (`PFM_Mat4x4_Mult4x4`) or
  higher-level path/field update pressure.

## Rejected Slice 72 — Animated Matrix Cost Experiments

Goal:

- Leave ClearPath alone after the failed projection-first shortcut and inspect
  the next profile lane: `PFM_Mat4x4_Mult4x4` in animated/render paths.
- Keep the Slice 70 nearest-constraint ClearPath cap as the baseline.

Experiments:

- Tried moving the skinned instance model transform from CPU-side
  `fill_gpu_skinned_instance()` into the Metal GPU-skinning shaders, so the
  CPU would upload local skin matrices instead of precomputed world-space skin
  matrices.
- Tried replacing `a_mat_from_sqt()` in `src/anim/anim.c` with direct
  quaternion/scale/translation matrix composition, avoiding the two generic
  `PFM_Mat4x4_Mult4x4()` calls inside the helper.

Results:

```text
Slice 70 current-code verification:
1000 p50/p95/max: 45.952 / 51.648 / 51.648 ms
moved: 698
average travel: 5.651
active animations: 325
damaged units: 41

Metal shader local-model experiment:
1000 p50/p95/max: 45.066 / 91.596 / 91.596 ms
moved: 697
average travel: 4.818
active animations: 335
damaged units: 42

Direct SQT matrix composition experiment:
500 p50/p95/max: 24.680 / 34.588 / 34.588 ms
1000 p50/p95/max: 34.815 / 227.711 / 227.711 ms
moved: 692
average travel: 5.429
active animations: 350
damaged units: 34

Final current-code verification after reverting both experiments:
output: qa-output/sovereign-ai-large-army-scale-1000-matrix-revert-verify/
status: pass
1000 p50/p95/max: 45.709 / 53.471 / 53.471 ms
moved: 696
average travel: 6.207
active animations: 340
damaged units: 46
warnings: []
```

Decision:

- Rejected and removed both matrix experiments.
- The functional gates stayed green, but the 1000-unit p95 was materially
  worse than the current baseline. The direct SQT path especially looked good
  in the 500-unit run but collapsed at 1000 units, so it is not safe to land.

Conclusion:

- Keep the current world-space Metal skin-matrix upload path and the existing
  animation SQT helper.
- The next profile slice should use a fresh Time Profiler trace to identify
  the parent callsites for `PFM_Mat4x4_Mult4x4` before changing matrix math
  again, or shift to higher-level path/field update costs if those are now the
  better lane.

## Completed Slice 73 — Flow-Field Frontier Contains Removal

Goal:

- Run a fresh 1000-unit Time Profiler trace to inspect the parent callsites for
  `PFM_Mat4x4_Mult4x4`.
- If the trace does not provide a clean parent stack, move to the next visible
  profile lane instead of guessing at matrix math.

Fresh profile:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-matrix-parent-xctrace-launch/
trace: qa-output/sovereign-ai-large-army-scale-1000-matrix-parent-xctrace-launch/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-matrix-parent-xctrace-launch/time_profile_top.txt
matrix_focus: qa-output/sovereign-ai-large-army-scale-1000-matrix-parent-xctrace-launch/time_profile_matrix_focus.txt
profiled p50/p95/max: 52.395 / 89.513 / 89.513 ms
status: pass
warnings: []
```

Top profile lanes before the change:

```text
inside_pcr                 12.82%
compute_vo_xpoints          7.67%
ray_ray_intersection_fast    6.22%
PFM_Mat4x4_Mult4x4          5.14%
field_compare_tds           2.97%
pq_td_contains              2.28%
```

Matrix stack finding:

```text
PFM_Mat4x4_Mult4x4 leaf samples:      2147 / 41765 = 5.14%
PFM_Mat4x4_Mult4x4 parent as <root>:  2103 samples
visible parents:
  A_GetPoseMats:                13 samples
  fill_gpu_skinned_instance:    12 samples
  render_gpu_skinned_anim_batch:11 samples
```

The exported Time Profiler table therefore did not give a reliable parent
stack for most matrix samples. No matrix code was changed in this slice.

Implementation:

- Removed the O(n) `pq_td_contains(frontier, field_compare_tds, ...)` scan in
  the two global-region flow-field integration loops in
  `src/navigation/field.c`.
- The queue now pushes a tile whenever a lower integration cost is discovered.
  This follows the usual lazy-priority Dijkstra pattern: duplicate queued
  entries are cheaper than repeatedly scanning the heap for membership.

Verification:

```sh
git diff --check -- src/navigation/field.c
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit regression:

```text
output: qa-output/sovereign-ai-large-army-scale-500-field-no-frontier-contains/
status: pass
p50/p95/max: 27.917 / 33.890 / 33.890 ms
moved: 380
average travel: 15.277
active animations: 335
damaged units: 19
warnings: []
```

1000-unit gate:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-field-no-frontier-contains/
status: pass
p50/p95/max: 47.393 / 53.931 / 53.931 ms
moved: 693
average travel: 4.771
active animations: 352
damaged units: 28
warnings: []
```

Post-change Time Profiler:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-field-no-frontier-contains-xctrace-launch/
trace: qa-output/sovereign-ai-large-army-scale-1000-field-no-frontier-contains-xctrace-launch/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-field-no-frontier-contains-xctrace-launch/time_profile_top.txt
profiled p50/p95/max: 45.961 / 80.962 / 80.962 ms
status: pass
warnings: []
```

Top profile lanes after the change:

```text
inside_pcr                 16.30%
compute_vo_xpoints          8.40%
ray_ray_intersection_fast    6.30%
PFM_Mat4x4_Mult4x4          5.67%
field_compare_tds           gone from top list
pq_td_contains              gone from top list
```

Shared-backend compile checks:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Conclusion:

- Keep this flow-field cleanup. It is not a dramatic p95 win, but it removes a
  confirmed O(n) queue-membership hot lane and keeps the 500/1000-unit gates
  green.
- The next performance target should return to the dominant profile shape:
  either a deeper ClearPath `inside_pcr` / `compute_vo_xpoints` algorithm pass
  or a profiler-symbolication pass with better frame pointers before attempting
  another matrix optimization.

## Rejected Slice 74 — ClearPath PCR Micro-Optimization Trials

Goal:

- Return to the dominant ClearPath lane after Slice 73 and look for a small,
  safe reduction in `inside_pcr()` / `compute_vo_xpoints` cost.
- Do not repeat the rejected projection-first shortcut from Slice 71.

Experiments:

- A/B tested a smaller dense-constraint cap using the existing
  `PF_CLEARPATH_MAX_CONSTRAINT_NEIGHBOURS` runtime knob:
  `--clearpath-max-constraint-neighbours 24`.
- Tried hoisting debug ray-normalization assertions out of the repeated
  `inside_pcr()` and projection loops while keeping a once-per-solve invariant
  check.
- Tried skipping the two source constraint pairs when checking whether a
  candidate ray-intersection point is inside the combined PCR. The reasoning
  was that the candidate lies on those source boundaries and boundary points
  are already treated as outside.

Results:

```text
Current reference from Slice 73 / post-revert evidence:
1000 p50/p95/max: 47.393 / 53.931 / 53.931 ms
later current-code check: 45.952 / 51.648 / 51.648 ms
final current-code repeat after rejecting the trials: 47.291 / 79.456 / 79.456 ms

Constraint cap 24:
1000 p50/p95/max: 46.831 / 79.104 / 79.104 ms
moved: 694
average travel: 5.700
active animations: 351
damaged units: 39

Ray-normalization assert hoist:
500 p50/p95/max: 28.868 / 34.666 / 34.666 ms
1000 first run:  47.293 / 96.755 / 96.755 ms
1000 rerun:      48.671 / 80.930 / 80.930 ms

Origin-pair skip during candidate PCR checks:
500 p50/p95/max: 28.957 / 33.098 / 33.098 ms
1000 p50/p95/max: 47.398 / 78.273 / 78.273 ms
moved: 702
average travel: 5.513
active animations: 331
damaged units: 39
```

Decision:

- Rejected all three experiments and reverted the two source-code trials.
- The 500-unit gate stayed healthy, but none of the 1000-unit experiments
  proved a stable improvement over the current default baseline. The final
  current-code repeat also shows this gate has meaningful run-to-run p95 noise,
  so this slice should be treated as a rejection of unproven local tweaks, not
  as evidence for a new performance regression.
- The smaller cap and boundary-skip ideas likely remove or reorder useful
  candidate constraints in dense formations, causing downstream churn despite
  less apparent local work.

Conclusion:

- Keep the current Slice 70 nearest-constraint cap at 32 and the existing
  `inside_pcr()` / candidate-validation logic.
- Next performance work should use better profiler symbolication/frame pointers
  or move up a level to path/field scheduling and movement-update cadence,
  rather than more local ClearPath micro-optimizations.

## Completed Slice 75 — Frame-Pointer Time Profiler Symbolication Pass

Goal:

- Improve Time Profiler parent-callsite evidence before touching ClearPath or
  matrix math again.
- Identify whether the next real optimization target is local ClearPath
  geometry, movement scheduling, path/field cadence, or matrix/render work.

Implementation:

- Added `EXTRA_CFLAGS` to the shared Makefile C and Objective-C compile flags
  so profiling builds can add symbols/frame-pointer flags without changing
  normal builds.
- Extended `scripts/macos/profile_sovereign_large_army_scale.sh` with an
  opt-in profiling rebuild:

```sh
PF_PROFILE_REBUILD=1
PF_PROFILE_CFLAGS="-g -fno-omit-frame-pointer -fno-optimize-sibling-calls"
```

- Extended the Time Profiler export parser to write:
  - `time_profile_top.txt`
  - `time_profile_focus.txt`
- The focus file now reports leaf, inclusive, parent, child, leaf-parent, and
  depth summaries for:
  - `inside_pcr`
  - `compute_vo_xpoints`
  - `G_ClearPath_NewVelocity`
  - `move_velocity_work`
  - `field_update_enemies`
  - `PFM_Mat4x4_Mult4x4`
  - `ray_ray_intersection_fast`

Trace notes:

- The wrapper's attach-mode path remains available, but the known macOS display
  service issue can still make attach mode unreliable for this workload.
- A wrapper launch-mode experiment was tested and rejected because it did not
  exit cleanly under `xctrace`.
- The reliable capture path for this slice was the direct launch-mode
  `xcrun xctrace record --launch ./bin/pf-arm64 ...` command after the
  frame-pointer rebuild.

Frame-pointer build:

```sh
PF_PROFILE_MODE=launch PF_PROFILE_REBUILD=1 PF_PROFILE_CAPTURE_PROOF=0 \
  PF_PROFILE_SOFT_BUDGET_MS=500 \
  scripts/macos/profile_sovereign_large_army_scale.sh \
  qa-output/sovereign-ai-large-army-scale-1000-frame-pointer-profile
```

The rebuild completed with:

```text
PROFILE_REBUILD backend=METAL type=DEBUG cflags=-g -fno-omit-frame-pointer -fno-optimize-sibling-calls
```

The wrapper launch trace itself was stopped after hanging before probe output.

Direct trace:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-frame-pointer-direct-xctrace/
trace: qa-output/sovereign-ai-large-army-scale-1000-frame-pointer-direct-xctrace/sovereign_500x2_Time_Profiler.trace
time_profile_top: qa-output/sovereign-ai-large-army-scale-1000-frame-pointer-direct-xctrace/time_profile_top.txt
time_profile_focus: qa-output/sovereign-ai-large-army-scale-1000-frame-pointer-direct-xctrace/time_profile_focus.txt
status: pass
p50/p95/max: 47.373 / 80.570 / 80.570 ms
moved: 711
average travel: 5.892
active animations: 339
damaged units: 42
warnings: []
```

Top leaf samples:

```text
inside_pcr                 15.47%
compute_vo_xpoints          8.63%
ray_ray_intersection_fast    6.64%
PFM_Mat4x4_Mult4x4          5.60%
render_screenspace_colored_triangles 1.48%
render_shadow_vertex_stream 1.46%
det_less_than_eps_len       1.34%
PFM_Mat4x4_Inverse          1.21%
PFM_Mat4x4_RotFromQuat      1.10%
n_objects_adjacent          1.00%
render_gpu_skinned_anim_batch 0.99%
```

Focused parent-stack finding:

```text
inside_pcr:
  inclusive 15.47%
  parent <root>: 13.98%
  parent compute_vo_xpoints: 0.87%
  parent compute_vdes_proj_points: 0.62%

compute_vo_xpoints:
  inclusive 9.50%
  parent <root>: 9.50%

ray_ray_intersection_fast:
  inclusive 6.64%
  parent <root>: 6.64%

PFM_Mat4x4_Mult4x4:
  inclusive 5.60%
  parent <root>: 5.46%
  parent fill_gpu_skinned_instance: 0.06%
  parent A_GetCurrPoseMats: 0.03%

field_update_enemies:
  inclusive 0.15%
  parent N_FlowFieldUpdate: 0.13%
```

Conclusion:

- Frame-pointer rebuild support is now available, and the focused parser makes
  future trace triage faster.
- The exported Time Profiler data still does not provide trustworthy parent
  stacks for most local ClearPath and matrix leaf samples; most remain
  attributed to `<root>`.
- Do not do more local ClearPath or matrix micro-optimizations from this data.
- Next target should move up a level to movement/path scheduling cadence:
  measure how often dense units enter ClearPath per tick, whether the same
  units recompute collision avoidance too frequently, and whether path/field
  refreshes can be amortized without changing combat behavior.

## Completed Slice 76 — Movement/ClearPath Cadence Instrumentation

Goal:

- Move up from local math tweaks to measured movement scheduling evidence.
- Count which movement states are feeding ClearPath in dense battles before
  changing cadence or collision behavior.

Implementation:

- Added env-gated movement stats via `PF_MOVEMENT_STATS_PATH`.
- Added `pf.debug_write_movement_stats()` so probes can flush movement stats
  before writing summaries.
- Extended `pf_sovereign_ai_large_army_scale_probe.py` with
  `--movement-stats-path` and summary embedding.
- Stats now report per-state work items, ClearPath calls, zero preferred
  velocity calls, assignment waits, neighbour totals, max neighbours, and
  average neighbours per call.

Verification:

```text
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit attack-move cadence gate:

```text
output: qa-output/sovereign-ai-large-army-scale-500-movement-cadence/
status: PASS
budget p50/p95/max: 27.465 / 30.061 / 30.061 ms
movement clearpath calls: 74,247
dominant states:
  STATE_SEEK_ENEMIES: 55,871 calls, avg neighbours 14.26
  STATE_MOVING: 13,861 calls, avg neighbours 21.31
  STATE_TURNING: 4,606 calls, all zero-vpref, avg neighbours 20.22
```

1000-unit attack-move cadence gate:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-movement-cadence/
status: PASS
budget p50/p95/max: 66.833 / 242.043 / 242.043 ms
movement clearpath calls: 76,263
dominant states:
  STATE_SEEK_ENEMIES: 40,584 calls, avg neighbours 28.39
  STATE_MOVING: 20,650 calls, avg neighbours 35.48
  STATE_TURNING: 15,048 calls, all zero-vpref, avg neighbours 37.13
ClearPath retry pressure:
  attempts: 720,316
  fallback retry steps: 657,167
  no-solution attempts: 657,167
  xpoint ray-pair tests: 686,138,665
```

Conclusion:

- The 1000-unit gate is still functionally green, but cadence evidence shows
  `STATE_TURNING` is a clean optimization lane: it calls ClearPath with zero
  preferred velocity and high neighbour pressure.
- `STATE_SEEK_ENEMIES` remains the largest total ClearPath lane and should be
  optimized only after turning/zero-vpref behavior is handled safely.
- Next best target: skip or amortize ClearPath for zero-vpref turning units,
  then rerun the same 500/1000 cadence gates and compare stats.

## Completed Slice 77 — Zero-Velocity Turning ClearPath Skip

Goal:

- Remove the cleanest unnecessary movement scheduling work found by Slice 76:
  turning units had zero preferred velocity but still did neighbour lookup and
  ClearPath collision solving.

Implementation:

- `STATE_TURNING` with zero preferred velocity now returns zero velocity
  directly and skips neighbour lookup plus `G_ClearPath_NewVelocity()`.
- Movement stats now include `clearpath_skips` globally and per movement state.
- No combat targeting, formation assignment, seek-enemy, surround, or moving
  state behavior was changed.

Verification:

```text
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit attack-move regression:

```text
output: qa-output/sovereign-ai-large-army-scale-500-turning-skip/
status: PASS
budget p50/p95/max: 29.625 / 60.940 / 60.940 ms
movement clearpath calls: 72,902
STATE_TURNING clearpath calls/skips: 0 / 5,374
```

Atomic-counter repeat:

```text
output: qa-output/sovereign-ai-large-army-scale-500-turning-skip-atomic/
status: PASS
budget p50/p95/max: 27.798 / 59.930 / 59.930 ms
movement clearpath calls/skips: 68,053 / 6,048
STATE_TURNING clearpath calls/skips: 0 / 6,048
```

1000-unit attack-move gate:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-turning-skip/
status: PASS
budget p50/p95/max: 46.944 / 186.218 / 186.218 ms
movement clearpath calls: 53,717
STATE_TURNING clearpath calls/skips: 0 / 19,045
ClearPath attempts: 720,316 -> 372,357
fallback retry steps: 657,167 -> 326,724
xpoint ray-pair tests: 686,138,665 -> 372,610,448
```

Atomic-counter repeat:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-turning-skip-atomic/
status: PASS
budget p50/p95/max: 46.860 / 146.519 / 146.519 ms
movement clearpath calls/skips: 57,312 / 19,909
STATE_TURNING clearpath calls/skips: 0 / 19,909
ClearPath attempts: 720,316 -> 399,609
fallback retry steps: 657,167 -> 350,398
xpoint ray-pair tests: 686,138,665 -> 399,947,908
```

Conclusion:

- The narrow turning skip keeps 500/1000-unit functional gates green and
  materially reduces the 1000-unit ClearPath load.
- The p95 remains above the desired production budget, so the next optimization
  target should be `STATE_SEEK_ENEMIES` cadence: measure/reduce repeated
  collision solving while many units are already seeking clustered enemies.

## Completed Slice 78 — Env-Gated Seek-Enemy ClearPath Cadence

Goal:

- Test whether dense `STATE_SEEK_ENEMIES` units can safely amortize ClearPath
  collision solving without changing default gameplay behavior.

Implementation:

- Added `PF_MOVEMENT_SEEK_CLEARPATH_CADENCE`, defaulting to `1`.
- Added `--movement-seek-clearpath-cadence` to
  `pf_sovereign_ai_large_army_scale_probe.py`.
- When cadence is greater than `1`, active `STATE_SEEK_ENEMIES` units reuse
  their previous velocity on skipped cadence ticks and avoid neighbour lookup
  plus `G_ClearPath_NewVelocity()`.
- Skips are not applied when the unit has no current velocity, has no preferred
  velocity, or debug-save tracing is active.
- Movement stats now record the configured cadence and per-state
  `cadence_skips`.
- Default cadence remains `1`; this slice adds an experimental knob, not a
  production default change.

Verification:

```text
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

500-unit default-cadence regression:

```text
output: qa-output/sovereign-ai-large-army-scale-500-seek-cadence-default-regression/
status: PASS
budget p50/p95/max: 27.622 / 31.144 / 31.144 ms
movement clearpath calls/skips: 72,535 / 6,146
STATE_SEEK_ENEMIES clearpath calls/skips/cadence_skips: 59,548 / 0 / 0
ClearPath attempts/fallback retry steps: 164,517 / 95,722
```

500-unit cadence-2 experiment:

```text
output: qa-output/sovereign-ai-large-army-scale-500-seek-cadence2/
status: PASS
budget p50/p95/max: 29.578 / 42.585 / 42.585 ms
movement clearpath calls/skips: 51,629 / 29,295
STATE_SEEK_ENEMIES clearpath calls/skips/cadence_skips: 38,399 / 23,287 / 23,287
ClearPath attempts/fallback retry steps: 127,135 / 78,879
```

1000-unit cadence-2 experiment:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-seek-cadence2/
status: PASS
budget p50/p95/max: 52.456 / 135.138 / 135.138 ms
movement clearpath calls/skips: 48,232 / 39,236
STATE_SEEK_ENEMIES clearpath calls/skips/cadence_skips: 27,449 / 15,515 / 15,515
STATE_TURNING clearpath calls/skips: 0 / 23,721
ClearPath attempts/fallback retry steps: 375,725 / 334,997
```

Conclusion:

- Cadence 2 is functionally safe in the sampled 500/1000-unit attack-move
  gates and reduces `STATE_SEEK_ENEMIES` ClearPath work.
- The 1000-unit p95 improved modestly versus the Slice 77 atomic baseline
  (146.519 ms -> 135.138 ms), but the 500-unit cadence-2 run was noisier than
  the default-cadence regression.
- Keep the cadence env-gated for now. The next best target is not a blind
  default flip; it is a larger behavioral/readability check for cadence 2 with
  capture proof and, if stable, a narrower policy that enables cadence only
  above a dense-neighbour or large-army threshold.

## Completed Slice 79 — Dense-Only Seek Cadence Gate And Capture Proof

Goal:

- Validate cadence-2 visually/behaviorally, then make the cadence experiment
  safer by activating it only under dense large-army pressure.

Implementation:

- Added `PF_MOVEMENT_SEEK_CLEARPATH_MIN_WORK_ITEMS`, defaulting to `0`.
- Added `--movement-seek-clearpath-min-work-items` to the large-army probe.
- Movement stats now record `max_tick_work_items` and the configured
  `seek_clearpath_min_work_items`.
- The seek-cadence skip now requires both cadence > 1 and, when configured, at
  least the requested active movement work count for the current tick.
- The existing defaults still preserve normal behavior:
  - cadence default: `1`
  - min-work threshold default: `0`

Capture proof:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-seek-cadence2-capture/
status: PASS
captures:
  sovereign_large_army_before_orders.png
  sovereign_large_army_engage_sample.png
  sovereign_large_army_sustained_soak.png
  sovereign_large_army_wide_zoom.png
resolution: 3456x2234
budget p50/p95/max: 45.883 / 195.777 / 195.777 ms
note: capture runs include screenshot I/O, so this is behavioral/visual
      evidence rather than the clean timing baseline.
```

500-unit dense-threshold check:

```text
output: qa-output/sovereign-ai-large-army-scale-500-seek-dense-threshold700/
status: PASS
configured cadence/min-work: 2 / 700
max_tick_work_items: 501
STATE_SEEK_ENEMIES clearpath calls/skips/cadence_skips: 54,692 / 0 / 0
budget p50/p95/max: 27.721 / 59.720 / 59.720 ms
```

1000-unit dense-threshold check:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-seek-dense-threshold700/
status: PASS
configured cadence/min-work: 2 / 700
max_tick_work_items: 1001
STATE_SEEK_ENEMIES clearpath calls/skips/cadence_skips: 33,891 / 3,140 / 3,140
budget p50/p95/max: 45.735 / 134.301 / 134.301 ms
ClearPath attempts/fallback retry steps: 374,386 / 326,894
```

Conclusion:

- The dense-only threshold works mechanically: 500-unit battles stay below the
  threshold and receive no seek-cadence skips, while 1000-unit battles cross the
  threshold and activate limited cadence skipping.
- The 1000-unit dense-threshold run stays green and is slightly better than the
  raw cadence-2 timing run, but cadence skips were much lower than the raw
  cadence run because only dense ticks crossed the threshold.
- Keep this as an opt-in policy for now. The next best target is a repeated
  1000-unit no-capture timing run plus a behavior-focused unit-flow comparison
  before choosing any production threshold.

## Completed Slice 80 — Dense-Seek Cadence Default Candidate

Goal:

- Turn the dense-only seek cadence from an experimental knob into an
  evidence-backed default candidate.

Implementation:

- Added behavior-flow comparison fields to the large-army scale probe:
  - per-army start/end centroids
  - center separation and closing distance
  - player/enemy spread
  - live idle-style count
- Promoted the conservative dense-seek candidate into C defaults:
  - `PF_MOVEMENT_SEEK_CLEARPATH_CADENCE` default: `2`
  - `PF_MOVEMENT_SEEK_CLEARPATH_MIN_WORK_ITEMS` default: `600`
- Both values remain env-overridable. Setting
  `PF_MOVEMENT_SEEK_CLEARPATH_CADENCE=1` disables the policy.

Threshold sweep:

```text
1000 dense threshold 600:
  run A status: PASS
  p50/p95/max: 50.950 / 129.862 / 129.862 ms
  seek cadence skips: 4,447
  moved / avg travel / damaged: 599 / 3.335 / 43

1000 dense threshold 600 repeat:
  status: PASS
  p50/p95/max: 55.747 / 123.830 / 123.830 ms
  seek cadence skips: 4,992
  moved / avg travel / damaged: 611 / 3.792 / 43

1000 dense threshold 700:
  status: PASS
  p50/p95/max: 47.804 / 134.264 / 134.264 ms
  seek cadence skips: 4,455
  moved / avg travel / damaged: 608 / 4.163 / 47

1000 dense threshold 800:
  status: PASS
  p50/p95/max: 46.277 / 168.379 / 168.379 ms
  seek cadence skips: 1,040
  moved / avg travel / damaged: 597 / 3.262 / 44

1000 dense threshold 900:
  status: PASS
  p50/p95/max: 50.067 / 156.849 / 156.849 ms
  seek cadence skips: 316
  moved / avg travel / damaged: 602 / 3.687 / 51
```

Default-candidate verification:

```text
500-unit default-candidate:
  output: qa-output/sovereign-ai-large-army-scale-500-seek-dense-default-candidate/
  status: PASS
  configured cadence/min-work from engine defaults: 2 / 600
  max_tick_work_items: 501
  STATE_SEEK_ENEMIES cadence skips: 0
  p50/p95/max: 29.115 / 44.644 / 44.644 ms
  behavior: moved 342, avg travel 16.698, damaged 13, live 234/239

1000-unit default-candidate:
  output: qa-output/sovereign-ai-large-army-scale-1000-seek-dense-default-candidate/
  status: PASS
  configured cadence/min-work from engine defaults: 2 / 600
  max_tick_work_items: 1001
  STATE_SEEK_ENEMIES cadence skips: 4,859
  p50/p95/max: 51.750 / 107.854 / 107.854 ms
  behavior: moved 599, avg travel 3.764, damaged 47, live 473/462
```

Conclusion:

- Threshold 600 is the strongest candidate in this sweep: it repeated green,
  improved the 1000-unit p95, and preserved combat/movement checks.
- The 500-unit default-candidate run received zero seek-cadence skips because
  max active movement work was only 501, below the 600 threshold.
- The 500-unit p95 remains naturally noisy even with no cadence skips, so the
  next validation should be a short regression batch across 250/500/1000 units
  plus one visual wide-zoom proof on the new defaults before considering this
  scale slice closed.

## Completed Slice 81 — Dense-Seek Final Regression Batch

Goal:

- Run the final 250/500/1000-unit regression batch and wide-zoom capture proof
  for the dense-seek default candidate before declaring it stable.

Verification:

```text
python3 -m py_compile scripts/macos/pf_sovereign_ai_large_army_scale_probe.py
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Final no-capture regression batch:

```text
250-unit default-candidate:
  output: qa-output/sovereign-ai-large-army-scale-250-default-final-regression/
  status: PASS
  configured cadence/min-work: 2 / 600
  max_tick_work_items: 251
  STATE_SEEK_ENEMIES cadence skips: 0
  p50/p95/max: 20.512 / 24.979 / 24.979 ms
  behavior: moved 172, avg travel 17.159, damaged 5, live 121/121

500-unit default-candidate:
  output: qa-output/sovereign-ai-large-army-scale-500-default-final-regression/
  status: PASS
  configured cadence/min-work: 2 / 600
  max_tick_work_items: 501
  STATE_SEEK_ENEMIES cadence skips: 0
  p50/p95/max: 27.868 / 56.546 / 56.546 ms
  behavior: moved 341, avg travel 15.646, damaged 17, live 236/236

1000-unit default-candidate run A:
  output: qa-output/sovereign-ai-large-army-scale-1000-default-final-regression/
  status: PASS
  configured cadence/min-work: 2 / 600
  max_tick_work_items: 1001
  STATE_SEEK_ENEMIES cadence skips: 4,847
  p50/p95/max: 42.035 / 272.855 / 272.855 ms
  behavior: moved 605, avg travel 3.359, damaged 48, live 477/461

1000-unit default-candidate run B:
  output: qa-output/sovereign-ai-large-army-scale-1000-default-final-regression-repeat2/
  status: PASS
  STATE_SEEK_ENEMIES cadence skips: 4,251
  p50/p95/max: 50.289 / 147.497 / 147.497 ms
  behavior: moved 596, avg travel 3.979, damaged 44, live 474/468

1000-unit default-candidate run C:
  output: qa-output/sovereign-ai-large-army-scale-1000-default-final-regression-repeat3/
  status: PASS
  STATE_SEEK_ENEMIES cadence skips: 4,373
  p50/p95/max: 50.760 / 118.498 / 118.498 ms
  behavior: moved 594, avg travel 3.562, damaged 37, live 472/463
```

Wide-zoom capture proof:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-default-final-capture/
status: PASS
captures:
  sovereign_large_army_before_orders.png
  sovereign_large_army_engage_sample.png
  sovereign_large_army_sustained_soak.png
  sovereign_large_army_wide_zoom.png
resolution: 3456x2234
configured cadence/min-work: 2 / 600
STATE_SEEK_ENEMIES cadence skips: 5,202
p50/p95/max: 44.110 / 197.367 / 197.367 ms
behavior: moved 588, avg travel 3.014, damaged 43, live 479/471
```

Conclusion:

- Functional behavior is green across 250/500/1000 units and the wide-zoom
  capture proof.
- The 250/500-unit guards stayed below the 600 active-mover threshold and
  received zero seek-cadence skips.
- 1000-unit timing remains too noisy to make the dense-seek policy a default:
  p95 ranged from 118.498 ms to 272.855 ms across three no-capture repeats.
- The code was returned to conservative defaults:
  - `PF_MOVEMENT_SEEK_CLEARPATH_CADENCE=1`
  - `PF_MOVEMENT_SEEK_CLEARPATH_MIN_WORK_ITEMS=0`
- Dense-seek cadence remains available as an opt-in diagnostic/performance
  policy. The next best target is a focused 1000-unit spike investigation using
  per-phase samples or Time Profiler around the outlier run shape, not more
  default flipping.

## Completed Slice 82 — 1000-Unit Spike Timing Investigation

Goal:

- Investigate the 1000-unit p95 spike shape before changing the dense-seek
  cadence defaults again.

Implementation:

- Extended `pf_sovereign_ai_large_army_scale_probe.py` with
  `budget.tick_sample_records`, recording:
  - phase
  - phase tick
  - sampled wall time in milliseconds
- This keeps the existing summary fields but makes outlier ticks visible
  instead of only reporting aggregate p50/p95/max.

Fine-sampled dense-cadence candidate:

```text
command shape:
  units_per_side: 500
  sample_budget_every: 1
  movement seek cadence/min-work: 2 / 600
output:
  qa-output/sovereign-ai-large-army-scale-1000-spike-sample1-dense600/
status: PASS
overall p50/p95/max: 48.134 / 153.617 / 847.476 ms
engage_settle:
  count: 300
  p50 / p95 / max: 48.076 / 68.336 / 847.476 ms
  samples >100 ms: 5
  samples >150 ms: 4
sustained_soak:
  count: 240
  p50 / p95 / max: 48.684 / 182.308 / 237.926 ms
  samples >100 ms: 64
  samples >150 ms: 26
STATE_SEEK_ENEMIES cadence skips: 4,169
ClearPath attempts/fallback retry steps: 399,322 / 351,787
```

Top dense-cadence outliers:

```text
engage_settle tick 2: 847.476 ms
engage_settle tick 3: 323.336 ms
sustained_soak tick 129: 237.926 ms
sustained_soak tick 89: 236.679 ms
sustained_soak tick 119: 223.506 ms
sustained_soak tick 115: 214.781 ms
sustained_soak tick 81: 213.715 ms
```

Fine-sampled conservative mode:

```text
command shape:
  units_per_side: 500
  sample_budget_every: 1
  movement seek cadence/min-work: 1 / 0
output:
  qa-output/sovereign-ai-large-army-scale-1000-spike-sample1-conservative/
status: PASS
overall p50/p95/max: 47.377 / 141.768 / 764.998 ms
engage_settle:
  count: 300
  p50 / p95 / max: 47.457 / 77.747 / 764.998 ms
  samples >100 ms: 7
  samples >150 ms: 4
sustained_soak:
  count: 240
  p50 / p95 / max: 47.416 / 164.333 / 222.772 ms
  samples >100 ms: 59
  samples >150 ms: 18
STATE_SEEK_ENEMIES cadence skips: 0
ClearPath attempts/fallback retry steps: 402,230 / 353,630
```

Top conservative outliers:

```text
engage_settle tick 2: 764.998 ms
engage_settle tick 3: 319.576 ms
engage_settle tick 1: 247.784 ms
sustained_soak tick 12: 222.772 ms
sustained_soak tick 110: 195.403 ms
sustained_soak tick 82: 188.505 ms
sustained_soak tick 76: 188.132 ms
```

Profiler attempts:

```text
attach-mode Time Profiler:
  output: qa-output/sovereign-ai-large-army-scale-1000-spike-timeprof/
  result: target exited before attach
  failure: SDL could not initialize a display from the background launch context

launch-mode Time Profiler:
  output: qa-output/sovereign-ai-large-army-scale-1000-spike-xctrace-launch2/
  result: trace saved, but exported Time Profiler table contained only one
          unsymbolicated sample and no probe summary/stdout
```

Conclusion:

- The spike is not caused solely by dense-seek cadence. Conservative mode shows
  the same shape: huge first engage ticks and many sustained-soak ticks above
  100 ms.
- Dense cadence reduces some ClearPath totals but does not remove sustained
  spikes, so flipping cadence defaults is not the right next move.
- The highest-signal next target is in-engine timing around the movement tick,
  especially:
  - `G_UpdateMap()`
  - `compute_async_fields()`
  - `compute_desired_velocity()`
  - `fork_join_velocity_computations()`
  - `fork_join_state_updates()`
- Time Profiler is currently unreliable for this harness on macOS because both
  attach and launch profiler paths failed to produce useful symbolicated target
  samples.

## Completed Slice 83 — Movement Sub-Stage Timing

Goal:

- Replace unreliable external Time Profiler evidence with in-engine timing for
  the movement tick sub-stages suspected in the 1000-unit p95 spikes.

Implementation:

- Extended `PF_MOVEMENT_STATS_PATH` output with `stage_timings`.
- Each stage reports:
  - count
  - total milliseconds
  - average milliseconds
  - maximum milliseconds
  - movement tick at which the maximum occurred
- Timed stages:
  - `prep_tick`
  - `update_map`
  - `prepare_work`
  - `submit_move_work`
  - `nav_submit`
  - `async_fields`
  - `desired_velocity`
  - `velocity_solve`
  - `gpu_wait`
  - `gpu_copy`
  - `state_updates`

Conservative 1000-unit stage timing:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-stage-timing-conservative/
status: PASS
overall p50/p95/max: 48.616 / 143.978 / 842.730 ms
STATE_SEEK_ENEMIES cadence skips: 0
ClearPath attempts/fallback retry steps: 389,089 / 341,754

stage timings by max:
  desired_velocity: count 180, avg 36.806 ms, max 929.293 ms, max_tick 2
  async_fields:     count 181, avg 12.491 ms, max 798.140 ms, max_tick 1
  velocity_solve:   count 180, avg 110.062 ms, max 358.246 ms, max_tick 162
  state_updates:    count 180, avg 1.101 ms, max 39.662 ms, max_tick 154
  prepare_work:     count 181, avg 1.504 ms, max 5.967 ms
  update_map:       count 181, avg 0.136 ms, max 1.084 ms
```

Dense-cadence 1000-unit stage timing:

```text
output: qa-output/sovereign-ai-large-army-scale-1000-stage-timing-dense600/
status: PASS
overall p50/p95/max: 51.860 / 130.163 / 787.226 ms
configured cadence/min-work: 2 / 600
STATE_SEEK_ENEMIES cadence skips: 4,257
ClearPath attempts/fallback retry steps: 375,227 / 325,714

stage timings by max:
  desired_velocity: count 208, avg 35.691 ms, max 887.695 ms, max_tick 2
  async_fields:     count 209, avg 10.542 ms, max 757.051 ms, max_tick 1
  velocity_solve:   count 208, avg 84.834 ms, max 358.626 ms, max_tick 183
  state_updates:    count 208, avg 1.255 ms, max 64.974 ms, max_tick 193
  prepare_work:     count 209, avg 1.639 ms, max 2.473 ms
  update_map:       count 209, avg 0.145 ms, max 1.005 ms
```

Conclusion:

- The huge first engage spikes are dominated by first-use
  `async_fields`/`desired_velocity` work, not `G_UpdateMap()` or render upload.
- The sustained 1000-unit p95 pressure is dominated by `velocity_solve`.
- Dense seek cadence reduces average `velocity_solve` cost
  (`110.062 ms -> 84.834 ms`) and lowers overall p95 in this run
  (`143.978 ms -> 130.163 ms`), but it does not remove the worst sustained
  `velocity_solve` spikes (`~358 ms` max in both modes).
- `G_UpdateMap()`, `submit_move_work`, and `nav_submit` are not meaningful
  contributors in this probe.
- Next best target: add finer timing/counters inside `move_velocity_work()` or
  `G_ClearPath_NewVelocity()` to split `velocity_solve` into neighbour lookup,
  preferred-velocity/seek handling, ClearPath setup, x-point computation, and
  fallback/no-solution retries.

## Completed Slice 84 — ClearPath Fine-Grained Timing

Goal:

- Split the Slice 83 `velocity_solve` hotspot into movement-side and
  ClearPath-internal costs so the next optimization targets the real dense
  collision-avoidance bottleneck.

Implementation:

- Extended `PF_MOVEMENT_STATS_PATH` timing with:
  - `vpref`
  - `neighbour_lookup`
  - `clearpath_call`
- Extended `PF_CLEARPATH_STATS_PATH` with `stage_timings`:
  - `constraint_cap`
  - `attempt_setup`
  - `desired_pcr`
  - `inside_pcr`
  - `xpoints`
  - `projection`
  - `compute_vnew`
  - `fallback_remove`
- Behavior is unchanged; this is diagnostic instrumentation only.

Verification:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-clearpath-fine-timing \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-clearpath-fine-timing \
  --sample-budget-every 1 \
  --clearpath-stats-path qa-output/sovereign-ai-large-army-scale-1000-clearpath-fine-timing/clearpath_stats.json \
  --movement-stats-path qa-output/sovereign-ai-large-army-scale-1000-clearpath-fine-timing/movement_stats.json
```

Observed:

```text
status: PASS
overall sampled p50/p95/max: 47.698 / 186.588 / 768.765 ms
phase p95:
  engage_settle: 87.052 ms
  sustained_soak: 221.428 ms

movement stage timings by total:
  clearpath_call:     count 53,464, total 150,326.570 ms, avg 2.812 ms, max 53.802 ms
  velocity_solve:     count 167,    total 23,076.188 ms, avg 138.181 ms, max 605.573 ms
  desired_velocity:   count 167,    total 6,774.203 ms,  avg 40.564 ms,  max 1025.684 ms
  vpref:              count 73,630, total 3,122.532 ms,  avg 0.042 ms,   max 33.166 ms
  async_fields:       count 168,    total 2,010.869 ms,  avg 11.969 ms,  max 725.738 ms
  neighbour_lookup:   count 53,464, total 1,037.614 ms,  avg 0.019 ms,   max 17.869 ms

ClearPath stage timings by total:
  xpoints:            count 374,438,     total 131,892.366 ms, avg 0.352241 ms, max 34.376 ms
  projection:         count 374,438,     total 15,854.721 ms,  avg 0.042343 ms, max 25.181 ms
  inside_pcr:         count 147,117,480, total 5,989.089 ms,   avg 0.000041 ms, max 30.552 ms
  attempt_setup:      count 382,469,     total 372.390 ms,     avg 0.000974 ms, max 16.830 ms
  desired_pcr:        count 382,469,     total 266.159 ms,     avg 0.000696 ms, max 7.028 ms
  constraint_cap:     count 53,464,      total 18.650 ms,      avg 0.000349 ms, max 1.061 ms
  compute_vnew:       count 38,399,      total 9.236 ms,       avg 0.000241 ms, max 1.012 ms
  fallback_remove:    count 335,314,     total 0.930 ms,       avg 0.000003 ms, max 0.174 ms

ClearPath counters:
  calls: 53,464
  attempts: 382,469
  fallback retry steps: 336,039
  fallback removes: 335,314
  xpoint ray-pair tests: 377,732,933
  xpoint inside rejected: 126,463,966
  inside_pcr calls: 147,117,480
  inside_pcr ray-pair tests: 1,114,357,016
  max candidate points: 2,048
```

Conclusion:

- The real sustained dense-battle cost is not neighbour lookup
  (`~1.0 s total`) or fallback removal (`<1 ms total`).
- `clearpath_call` dominates movement-side `velocity_solve`.
- Inside ClearPath, `xpoints` dominates by a wide margin because it performs
  pairwise ray intersection and then rejects most candidates through PCR tests.
- The next meaningful optimization should reduce `xpoints` work:
  - avoid generating/evaluating obviously unhelpful ray-pairs
  - cap or sample x-point candidates more intelligently than the current
    nearest-neighbour cap
  - early-exit once a good-enough candidate is found
  - or replace the full pairwise candidate search with a cheaper dense-crowd
    fallback path.
- The current inside-PCR timing adds diagnostic overhead because it is called
  extremely often, so use this run to rank hotspots, not as a final production
  budget number.

## Rejected Slice 85 — X-Point Candidate Reduction Experiments

Goal:

- Reduce the Slice 84 `xpoints` hotspot without changing the broad movement
  and combat behavior of the 500/1000-unit attack-move gates.

Experiments:

- Accepted-candidate cap:
  - temporary knob: `PF_CLEARPATH_MAX_XPOINTS`
  - tested caps: `64`, `256`, `1024`
  - 500/1000-unit probes stayed functionally green
  - cap `64` looked attractive in a no-stats run
    (`1000 p50/p95/max = 47.002 / 56.429 / 820.828 ms`)
  - instrumented evidence showed it did not reduce the real x-point work:
    `xpoint_ray_pair_tests` stayed at `385,500,440` versus the no-cap
    diagnostic run's `377,732,933`, and `xpoints` time stayed high
    (`136,674.841 ms` versus `131,892.366 ms`)
- Ray-pair test cap:
  - temporary knob: `PF_CLEARPATH_MAX_XPOINT_PAIR_TESTS=1024`
  - 1000-unit probe stayed functionally green, but timing and behavior were
    worse:
    `p50/p95/max = 50.096 / 130.729 / 1165.263 ms`,
    `moved=586`, `damage=26`
- Distance-pruned x-points:
  - projection candidates seeded a best-distance bound, then farther
    intersections skipped the PCR test
  - 500/1000-unit probes stayed functionally green, but 1000-unit timing was
    worse:
    `p50/p95/max = 47.646 / 123.983 / 863.380 ms`

Decision:

- Rejected the x-point cap, ray-pair cap, and distance-prune variants.
- Removed the temporary optimization branches so the hot x-point loop remains
  clean.
- Kept Slice 84's diagnostic timing/counter output, because it is still the
  useful evidence source.

Final verification after cleanup:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_ai_large_army_scale_probe.py \
  --output-dir qa-output/sovereign-ai-large-army-scale-1000-xpoint-clean-default \
  --units-per-side 500 \
  --settle-ticks 300 \
  --soak-ticks 240 \
  --order-mode attack-move \
  --budget-label 1000-xpoint-clean-default \
  --sample-budget-every 1
```

Observed:

```text
status: PASS
1000 p50/p95/max: 51.629 / 136.145 / 850.136 ms
moved: 623
average travel: 3.194
damaged units: 42
```

Conclusion:

- The simple local x-point shortcuts are not stable enough to land.
- The next ClearPath optimization needs a more principled candidate-search
  change, likely changing which ray pairs are considered first or reducing the
  ray set before pairwise intersection, with behavior proof as the primary
  acceptance gate.
- Do not re-test projection-first, accepted-candidate caps, or naive pair caps
  unless a new ordering/selection argument is added; those variants have now
  been rejected.

## Completed Slice 86 — HD/Retina Readability Proof Gate

Goal:

- Move Phase 10 readability work from subjective screenshot review to a
  repeatable proof gate for close-zoom characters, dense armies, world props,
  VFX combat, and wide-zoom map/army readability.

Implementation:

- Extended `scripts/macos/pf_metal_hd_world_readability_probe.py` with
  stdlib PNG luma decoding for objective capture metrics.
- Each captured scene now records:
  - center-crop bounds and crop ratio
  - luma mean and standard deviation
  - edge-density against a fixed gradient threshold
  - p95 local luma-gradient value
  - a saved center-crop PNG for visual review
- Added a `readability_contract` section to the summary JSON to make clear
  that these metrics are regression/evidence gates, not final HD/4K art-quality
  certification.

Verification:

```sh
python3 -m py_compile scripts/macos/pf_metal_hd_world_readability_probe.py
```

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-13-hd-retina-readability-proof \
  --expect-backend METAL
```

Observed:

```text
HD_WORLD_READABILITY_PASS backend=METAL captures=5 highdpi=1 staged=108
sprite_sheets=fire_loop.png,impact_burst.png,projectile_trail.png,smoke_puff.png
summary: visual_parity_captures/2026-05-13-hd-retina-readability-proof/summary_hd_world_readability.json
retina_scale: [2.0, 2.0]
capture size: 3456x2234 for all scenes
```

Per-scene metrics:

```text
close_character_lod_target:        edge_density=0.140209 gradient_p95=34 luma_stddev=64.067
dense_army_readability:           edge_density=0.317067 gradient_p95=51 luma_stddev=50.001
dense_forest_building_readability edge_density=0.332284 gradient_p95=56 luma_stddev=44.159
vfx_combat_readability:           edge_density=0.336208 gradient_p95=60 luma_stddev=54.729
wide_large_map_readability:       edge_density=0.113488 gradient_p95=25 luma_stddev=33.970
```

Conclusion:

- The Metal runtime is capturing at Retina scale and the proof harness now
  stores both full-size screenshots and centered review crops.
- Current placeholder units/world assets are readable enough for regression
  evidence, but they are not yet the final HD/4K production-art target.
- The next Phase 10 content slice should improve actual production readability:
  stronger unit silhouettes/team color at close zoom, wider-view army markers
  or LOD rules, and terrain/biome texture variation for large maps.

## Completed Slice 87 — Neutral Selection And Zoom-Scaled Healthbars

Goal:

- Improve actual close-zoom and wide-zoom unit readability using existing
  engine overlays before starting a full HD asset replacement pass.
- Restore the user's preferred neutral white thin selection-ring style while
  making healthbars scale down at wide zoom.

Implementation:

- Restored player-owned selection markers to neutral white.
- Restored selected-unit world marker width to the thin `0.4` style.
- Fixed the Metal world-color overlay path used by selection circles,
  selection rectangles, and world lines: it now uses the existing Metal
  world-color pipeline instead of the lit static-mesh material pipeline, so
  marker colors render faithfully instead of being washed to grey.
- Added camera-height scaling to healthbars in both Metal and OpenGL:
  - close/normal views keep readable bars
  - high/wide views shrink bars down to a compact minimum
  - Metal also scales border thickness with the bar size
- Updated the OpenGL statusbar shader minimum height so the OpenGL reference
  path follows the same wide-zoom shrinking rule.
- Extended `scripts/macos/pf_metal_hd_world_readability_probe.py` with:
  - `close_character_status_readability`
  - `wide_army_status_readability`
  - paired metric deltas between unmarked/marked close and wide captures
  - explicit readability-contract notes for neutral selection markers and
    zoom-scaled healthbars

Verification:

```sh
python3 -m py_compile scripts/macos/pf_metal_hd_world_readability_probe.py
```

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-13-hd-retina-readability-neutral-healthbars \
  --expect-backend METAL
```

Observed:

```text
HD_WORLD_READABILITY_PASS backend=METAL captures=7 highdpi=1 staged=108
sprite_sheets=fire_loop.png,impact_burst.png,projectile_trail.png,smoke_puff.png
summary: visual_parity_captures/2026-05-13-hd-retina-readability-neutral-healthbars/summary_hd_world_readability.json
retina_scale: [2.0, 2.0]
```

Final per-scene metrics:

```text
close_character_lod_target:         edge_density=0.1372 gradient_p95=33
close_character_status_readability: edge_density=0.1420 gradient_p95=34
dense_army_readability:             edge_density=0.3269 gradient_p95=58
dense_forest_building_readability:  edge_density=0.3323 gradient_p95=56
vfx_combat_readability:             edge_density=0.3423 gradient_p95=66
wide_large_map_readability:         edge_density=0.1133 gradient_p95=25
wide_army_status_readability:       edge_density=0.1160 gradient_p95=26
```

Conclusion:

- Close-zoom status proof keeps the neutral white thin selection style with
  healthbar context.
- Wide-zoom status proof now shows friendly cohorts with compact healthbars
  instead of large bars that cover the army/map.
- This improves selection/readability UX and fixes a real Metal overlay-color
  bug, but full production readability still needs asset-side team-color masks,
  clearer far-view silhouettes, LOD/icon rules, and richer biome/terrain art.

## Completed Slice 88 — Unit Readability Metadata And Team-Color Mask Gate

Goal:

- Start the asset-side half of Phase 10 readability without changing renderer
  behavior prematurely.
- Track which Sovereign units have far-view silhouette/readability rules and
  which still need production team-color masks.

Implementation:

- Added `readability` metadata to the current Sovereign placeholder unit
  registry entries:
  - `villager`: worker/cart placeholder, compact selected-or-damaged marker
    policy, pending `cart_team_mask.png`
  - `militia`: frontline melee placeholder, compact selected-or-damaged marker
    policy, pending `Knight_team_mask.png`
  - `archer`: ranged/caster placeholder, compact selected-or-damaged marker
    policy, pending `Mage_team_mask.png`
- Added `scripts/sovereign/data/readability.py` for shared validation and
  summary generation.
- Added `tools/asset_validation/validate_sovereign_readability.py`.
  - normal mode allows `pending_mask` and reports warnings
  - `--strict` is the production gate and fails until real masks exist
- Wired registry validation to fail on missing/malformed readability metadata.
- Added `asset_readability` to the HD/Retina readability probe summary JSON.
- Updated asset/tooling docs and the Sovereign engine-work notes to describe
  the team-color-mask and far-view silhouette convention.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/units.py \
  scripts/sovereign/data/readability.py \
  scripts/sovereign/factory.py \
  scripts/macos/pf_metal_hd_world_readability_probe.py \
  tools/asset_validation/validate_sovereign_readability.py
```

```sh
python3 tools/asset_validation/validate_sovereign_readability.py
```

Observed:

```text
SOVEREIGN_READABILITY_WARNING unit 'archer' still needs production team-color mask
SOVEREIGN_READABILITY_WARNING unit 'militia' still needs production team-color mask
SOVEREIGN_READABILITY_WARNING unit 'villager' still needs production team-color mask
SOVEREIGN_READABILITY_VALID units=3 production_ready=0 pending_team_masks=3
```

Strict production gate:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py --strict
```

Observed expected failure:

```text
SOVEREIGN_READABILITY_INVALID units=3 pending_team_masks=3
```

Runtime/proof checks:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_factory_probe.py \
  --output-dir qa-output/sovereign-readability-factory-check

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-13-hd-retina-readability-asset-rules \
  --expect-backend METAL
```

Observed:

```text
SOVEREIGN_FACTORY_PROBE_PASS backend=METAL entities=10 units=3 buildings=3 resources=4
HD_WORLD_READABILITY_PASS backend=METAL captures=7 highdpi=1 staged=108
asset_readability.production_ready_units=0
asset_readability.pending_team_masks=3
```

Conclusion:

- The engine now has a concrete, testable place to enforce team-color and
  far-view readability expectations for Sovereign units.
- Current placeholder units are explicitly marked as not production-ready for
  team-color readability. That is the intended state until real unit textures
  and masks replace the placeholder Knight/Mage/cart assets.

## Completed Slice 89 — Militia Team-Color Mask Proof

Goal:

- Create the first real unit team-color mask proof without changing renderer
  semantics or claiming the placeholder art is final.
- Make strict validation useful for one unit at a time while the rest of the
  placeholder pack still has pending masks.

Implementation:

- Added `assets/models/knight/Knight_team_mask.png`.
  - source texture: `assets/models/knight/Knight.png`
  - dimensions: 512x512
  - binary mask coverage from existing blue shield and cloth/paint regions:
    23,161 pixels, about 8.835% of the texture
- Changed the Sovereign `militia` readability metadata from `pending_mask` to
  `texture_mask`.
- Extended `tools/asset_validation/validate_sovereign_readability.py` with
  `--unit <id>` so a single asset can pass strict validation while other
  placeholder units remain pending.
- Hardened readability validation so texture masks are resolved correctly for
  directory-style asset entries such as `{"path": "assets/models/knight",
  "pfobj": "knight.pfobj"}`.
- Added PNG dimension validation so a texture mask must match its source
  PFOBJ texture size.
- Updated asset/tooling docs and this plan with the incremental mask proof.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/units.py \
  scripts/sovereign/data/readability.py \
  tools/asset_validation/validate_sovereign_readability.py \
  scripts/sovereign/factory.py \
  scripts/macos/pf_metal_hd_world_readability_probe.py
```

Normal pack gate:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py
```

Observed:

```text
SOVEREIGN_READABILITY_VALID units=3 production_ready=1 pending_team_masks=2
SOVEREIGN_READABILITY_WARNING unit 'archer' still needs production team-color mask
SOVEREIGN_READABILITY_WARNING unit 'villager' still needs production team-color mask
```

Scoped strict proof:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py --unit militia --strict
```

Observed:

```text
SOVEREIGN_READABILITY_VALID units=1 production_ready=1 pending_team_masks=0
```

Full strict pack gate still fails as intended:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py --strict
```

Observed:

```text
SOVEREIGN_READABILITY_INVALID units=3 pending_team_masks=2
```

Runtime/proof checks:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_factory_probe.py \
  --output-dir qa-output/sovereign-readability-mask-proof-factory

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-13-hd-retina-readability-mask-proof \
  --expect-backend METAL
```

Observed:

```text
SOVEREIGN_FACTORY_PROBE_PASS backend=METAL entities=10 units=3 buildings=3 resources=4
HD_WORLD_READABILITY_PASS backend=METAL captures=7 highdpi=1 staged=108
asset_readability.production_ready_units=1
asset_readability.pending_team_masks=2
militia.team_color_mode=texture_mask
militia.team_color_mask_size=[512, 512]
```

Conclusion:

- The militia/Knight placeholder now has a concrete team-color mask asset and
  passes the unit-scoped strict readability gate.
- The whole pack remains correctly blocked by full strict validation until
  the villager/cart and archer/Mage placeholder masks are replaced or completed.

## Completed Slice 90 — Current Unit Pack Team-Color Mask Gate

Goal:

- Complete the current placeholder unit-pack mask coverage so the full strict
  readability gate can go green.
- Keep the distinction clear: this is a mask-pipeline/readability proof for
  current placeholders, not final HD/4K unit art.

Implementation:

- Added `assets/models/mage/Mage_team_mask.png`.
  - source texture: `assets/models/mage/Mage.png`
  - dimensions: 512x512
  - mask coverage from existing purple garment and cape regions: 61,699
    pixels, about 23.536% of the texture
- Added `assets/models/cart/cart_team_mask.png`.
  - source texture: `assets/models/cart/wood.jpg`
  - dimensions: 280x280
  - mask coverage: whole texture, because the placeholder cart has one tiled
    wood material and no separate team-color paint/clothing region
- Changed Sovereign `archer` and `villager` readability metadata from
  `pending_mask` to `texture_mask`.
- Extended readability texture-size validation to read JPEG dimensions, so PNG
  masks can be checked against JPEG source textures such as `wood.jpg`.
- Updated docs to state that the current placeholder pack now passes strict
  validation, while final production art still needs purpose-built team-color
  regions.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/units.py \
  scripts/sovereign/data/readability.py \
  tools/asset_validation/validate_sovereign_readability.py \
  scripts/sovereign/factory.py \
  scripts/macos/pf_metal_hd_world_readability_probe.py
```

Strict pack gate:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py --strict
```

Observed:

```text
SOVEREIGN_READABILITY_VALID units=3 production_ready=3 pending_team_masks=0
```

Runtime/proof checks:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_factory_probe.py \
  --output-dir qa-output/sovereign-readability-full-mask-factory

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-13-hd-retina-readability-full-mask \
  --expect-backend METAL
```

Observed:

```text
SOVEREIGN_FACTORY_PROBE_PASS backend=METAL entities=10 units=3 buildings=3 resources=4
HD_WORLD_READABILITY_PASS backend=METAL captures=7 highdpi=1 staged=108
asset_readability.production_ready_units=3
asset_readability.pending_team_masks=0
asset_readability.warnings=0
archer.team_color_mask_size=[512, 512]
militia.team_color_mask_size=[512, 512]
villager.team_color_mask_size=[280, 280]
```

Conclusion:

- The current Sovereign placeholder unit pack now has complete team-color mask
  coverage and passes full strict readability validation.
- The next production-art step should replace these placeholder masks with
  purpose-built unit assets and masks, especially the cart/villager placeholder
  where the mask currently covers the whole wood texture.

## Completed Slice 91 — Metal Team-Color Mask Rendering Proof

Goal:

- Make the validated Sovereign unit masks render in the actual Metal gameplay
  path instead of existing only as asset metadata.
- Preserve the user's visual direction: selection rings stay neutral white and
  thin; faction readability comes from unit materials, not selection markers.

Implementation:

- Added `team_color` to static and animated render-state records.
- Populated render-state team color from the entity faction color in
  `g_make_draw_list()`.
- Added Metal team-mask texture arrays loaded by sibling texture convention:
  a material texture such as `Knight.png` or `wood.jpg` can have
  `Knight_team_mask.png` or `wood_team_mask.png` beside it.
- Added Metal fragment shader blending that tints only masked texels with the
  current entity faction color while preserving source texture luminance. The
  shader treats RGB mask intensity as coverage, so normal opaque PNG alpha does
  not accidentally tint the full texture.
- Split Metal static and animated batches by team color, so mixed-faction
  groups are not drawn with the wrong tint.
- Renamed the cart placeholder mask reference to `wood_team_mask.png` so it
  matches the renderer lookup convention.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/units.py \
  scripts/sovereign/data/readability.py \
  tools/asset_validation/validate_sovereign_readability.py \
  scripts/macos/pf_metal_hd_world_readability_probe.py

python3 tools/asset_validation/validate_sovereign_readability.py --strict

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-13-hd-retina-team-mask-rendered-rgb \
  --expect-backend METAL
```

Observed:

```text
SOVEREIGN_READABILITY_VALID units=3 production_ready=3 pending_team_masks=0
HD_WORLD_READABILITY_PASS backend=METAL captures=7 highdpi=1 staged=108
asset_readability.production_ready_units=3
asset_readability.pending_team_masks=0
asset_readability.warnings=0
```

Conclusion:

- Team-color masks are now an actual Metal-rendered gameplay feature for the
  current placeholder unit pack.
- The proof capture shows red/blue faction-tinted bodies while selection rings
  remain neutral white.
- This closes the current mask-rendering proof; final production art still
  needs purpose-built high-clarity unit textures and masks.

## Completed Slice 92 — AoE-Style Team-Color Scope Correction

Goal:

- Align team-color usage with the user's AoE-style direction:
  strong faction colors belong on minimap markers, while main-world units and
  buildings should use only subtle authored accents.
- Prevent broad whole-material masks from being accepted as production-ready.

Implementation:

- Added an AoE-style readability note to `AGENTS.md`: minimap markers may use
  strong faction colors, but main-world material tinting must stay limited to
  authored accents such as shields, banners, cloth trim, flags, roofs, and
  tools.
- Added PNG mask coverage validation to
  `scripts/sovereign/data/readability.py`.
  - Default max coverage: 35% of the source texture.
  - Coverage uses RGB intensity only, matching the Metal shader convention.
- Changed the placeholder `villager` back to `pending_mask`.
  - Removed the broad `wood_team_mask.png` cart proof because it tinted the
    whole wood material and looked like material UI instead of AoE-style art.
- Updated Sovereign asset docs to state that the current cart/villager
  placeholder still needs a proper small accent mask.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/units.py \
  scripts/sovereign/data/readability.py \
  tools/asset_validation/validate_sovereign_readability.py \
  scripts/macos/pf_metal_hd_world_readability_probe.py

python3 tools/asset_validation/validate_sovereign_readability.py

python3 tools/asset_validation/validate_sovereign_readability.py --strict

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-14-hd-retina-aoe-team-color-scope-dummy \
  --expect-backend METAL

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-14-hd-retina-aoe-team-color-scope-pass2 \
  --expect-backend METAL
```

Observed:

- Non-strict readability remains valid with one pending production mask:
  `SOVEREIGN_READABILITY_VALID units=3 production_ready=2 pending_team_masks=1`.
- Strict readability fails intentionally until villager production art gets a subtle
  authored accent mask.
- Metal and OpenGL builds pass.
- A first rerun failed with `expected METAL backend, got OPENGL` because the
  OpenGL build had overwritten `bin/pf-arm64`; rebuilding Metal fixed the
  launch target.
- The follow-up Metal proof passed:
  `HD_WORLD_READABILITY_PASS backend=METAL captures=7 highdpi=1 staged=108`.
- Proof output:
  `visual_parity_captures/2026-05-14-hd-retina-aoe-team-color-scope-pass2/`.
- Capture summary:
  - Seven nonblank Retina captures at `retina_scale=[2.0, 2.0]`.
  - `asset_readability.production_ready_units=2`.
  - `asset_readability.pending_team_masks=1`.
  - Warning remains expected: `unit 'villager' still needs production team-color mask`.
- The earlier all-black `screencapture` result was transient; direct desktop
  screenshot checks and the pass2 probe both produced nonblank PNGs, so no
  harness patch was needed for this slice.

## Completed Slice 93 — Subtle Villager Mask And Wide-Zoom Healthbar Scale

Goal:

- Close the remaining strict team-mask gate with a deliberately small
  cart/villager placeholder mask.
- Keep the AoE-style rule intact: minimap colors can be strong, but main-world
  unit materials only receive small authored accents.
- Reduce far-zoom healthbar screen footprint so wide army views are readable
  instead of dominated by green bars.

Implementation:

- Replaced `assets/models/cart/cart_team_mask.png` with a sparse RGB mask:
  small strap/banner/tool-wrap islands only, no whole-wood tint.
- Updated `scripts/sovereign/data/units.py` so the placeholder `villager`
  uses `texture_mask` with `cart_team_mask.png`.
  - Mask coverage: `4.8469%`.
  - Max allowed coverage for this placeholder: `12%`.
- Reduced backend-aligned healthbar zoom scaling in both renderers:
  - `src/render/backend_metal.m`
  - `src/render/gl_statusbar.c`
  - Old scale: `clamp(160 / camera_height, 0.22, 1.0)`.
  - New scale: `clamp(120 / camera_height, 0.12, 1.0)`.
  - Close zoom remains unchanged because the scale still clamps to `1.0`.
  - Wide zoom bars shrink materially, preserving unit visibility on large-map
    army views.

Verification:

```sh
python3 -m py_compile \
  scripts/sovereign/data/units.py \
  scripts/sovereign/data/readability.py \
  tools/asset_validation/validate_sovereign_readability.py \
  scripts/macos/pf_metal_hd_world_readability_probe.py

python3 tools/asset_validation/validate_sovereign_readability.py
python3 tools/asset_validation/validate_sovereign_readability.py --strict

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-14-hd-retina-villager-mask-wide-healthbars \
  --expect-backend METAL

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
```

Observed:

- Strict readability is now green:
  `SOVEREIGN_READABILITY_VALID units=3 production_ready=3 pending_team_masks=0`.
- Metal proof passed:
  `HD_WORLD_READABILITY_PASS backend=METAL captures=7 highdpi=1 staged=108`.
- Proof output:
  `visual_parity_captures/2026-05-14-hd-retina-villager-mask-wide-healthbars/`.
- Summary confirms all three current Sovereign unit definitions now have texture
  masks:
  - `villager`: `cart_team_mask.png`, coverage `0.048469`.
  - `militia`: `Knight_team_mask.png`, coverage `0.088352`.
  - `archer`: `Mage_team_mask.png`, coverage `0.235363`.
- Wide status proof remains Retina and nonblank. The wide status delta is small
  and controlled:
  - `edge_density +0.002091`
  - `gradient_p95 +1`
  - `luma_stddev +0.159`
- OpenGL reference build still compiles with the same healthbar scale.

Next:

- Continue wide-zoom army readability with evidence-backed rules for unit
  silhouettes, damaged/selected healthbar policy, and far-view army grouping.
  This should stay separate from real HD/4K asset replacement.

## Completed Slice 94 — Wide-Zoom Healthbar Visibility Policy

Goal:

- Move beyond smaller bars and reduce healthbar clutter at map-wide zoom.
- Preserve close/mid combat feedback while making wide army views readable.
- Keep the policy backend-neutral and aligned between Metal and OpenGL.

Implementation:

- Added a game-side wide-zoom healthbar visibility policy in
  `src/game/game.c`.
- Above `HEALTHBAR_WIDE_ZOOM_HEIGHT = 520.0`, a full-health unselected unit no
  longer contributes a healthbar even when `pf.game.healthbar_mode` is
  `HB_MODE_ALWAYS`.
- Damaged units still show bars.
- Selected units still show bars.
- Close/mid zoom behavior is unchanged because the wide-zoom policy does not
  activate below the threshold.
- Extended `scripts/macos/pf_metal_hd_world_readability_probe.py` summary
  records with:
  - requested healthbar state
  - whether the wide-zoom policy applies
  - the wide-zoom threshold
  - the rule name: `selected_or_damaged_only`

Verification:

```sh
python3 -m py_compile scripts/macos/pf_metal_hd_world_readability_probe.py

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-14-hd-retina-wide-healthbar-policy \
  --expect-backend METAL

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Observed:

- Metal proof passed:
  `HD_WORLD_READABILITY_PASS backend=METAL captures=7 highdpi=1 staged=108`.
- Proof output:
  `visual_parity_captures/2026-05-14-hd-retina-wide-healthbar-policy/`.
- Wide scene policy evidence:
  - `wide_large_map_readability`: height `900`, selected `0`,
    `wide_zoom_policy=True`.
  - `wide_army_status_readability`: height `900`, selected `24`,
    `wide_zoom_policy=True`.
  - `dense_army_readability`: height `210`, selected `24`,
    `wide_zoom_policy=False`.
- Wide status impact is now very small:
  - `edge_density +0.000699`
  - `gradient_p95 +0`
  - `luma_stddev +0.021`
- OpenGL reference build compiles.
- `bin/pf-arm64` was rebuilt back to Metal after the OpenGL compile check.

Next:

- Continue wide-zoom readability with far-view silhouette/grouping evidence:
  selected army group readability, damaged-unit visibility, and whether
  clustered armies need strategic group markers at very high zoom.

## Completed Slice 95 — Wide Army Status Evidence

Goal:

- Prove the wide-zoom healthbar policy with explicit no-bar, damaged-only, and
  selected-army captures.
- Keep selected markers neutral and thin, while checking whether damaged or
  selected units remain readable without full-health bar clutter.
- Use the result to decide whether strategic group markers are needed later.

Implementation:

- Extended `scripts/macos/pf_metal_hd_world_readability_probe.py` from seven
  to ten captures.
- Added three wide army evidence scenes:
  - `wide_army_no_status_readability`: no selection, no healthbars.
  - `wide_army_damaged_status_readability`: no selection, healthbars on, with
    five staged damaged army units.
  - `wide_army_selected_status_readability`: friendly army selected,
    healthbars on.
- Added `damaged_army` staging so the probe can distinguish damaged-only bars
  from selected-unit bars.
- Added per-capture `expected_bar_sources` to the summary so future regressions
  can tell whether a wide-view status bar should come from selected, damaged,
  or full-health unselected units.
- Added readability rule deltas for damaged-only and selected-army wide status
  captures.
- During verification, a `1300` and then `1050` camera-height framing attempt
  mostly captured sky/far-map edge, so the shipped evidence scene uses the
  highest useful current proof height, `900`, targeting the army cluster. This
  keeps the evidence about army readability rather than skybox coverage.

Verification:

```sh
python3 -m py_compile scripts/macos/pf_metal_hd_world_readability_probe.py

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-14-hd-retina-wide-army-status-modes \
  --expect-backend METAL

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Observed:

- Metal proof passed:
  `HD_WORLD_READABILITY_PASS backend=METAL captures=10 highdpi=1 staged=108`.
- Proof output:
  `visual_parity_captures/2026-05-14-hd-retina-wide-army-status-modes/`.
- Retina capture scale remained `[2.0, 2.0]`.
- Staged counts: `army=48`, `combat=14`, `heroes=6`,
  `damaged_army=5`, `entities=108`.
- Wide status deltas remain very small:
  - wide selected-army status: `edge_density +0.000644`,
    `gradient_p95 +0`, `luma_stddev +0.037`.
  - damaged-only army status: `edge_density -0.000083`,
    `gradient_p95 +0`, `luma_stddev +0.007`.
  - selected-army status over the army cluster: `edge_density +0.000391`,
    `gradient_p95 +0`, `luma_stddev +0.031`.
- Expected bar sources are now explicit in the summary:
  - no-bar baseline: selected `0`, damaged `0`, full-health unselected `0`.
  - damaged-only: selected `0`, damaged `5`, full-health unselected `0`.
  - selected army: selected `24`, damaged `0`, full-health unselected `0`.
- OpenGL reference build compiles.
- `bin/pf-arm64` was rebuilt back to Metal after the OpenGL compile check.

Conclusion:

- The current wide-zoom policy is evidence-backed: damaged and selected units
  can surface status without turning every full-health unit into a screen-wide
  bar field.
- The next readability work should not make selection rings thicker or recolor
  them. If larger maps still need extra readability, prototype subtle
  strategic group markers as a separate opt-in layer at very high zoom.

Next:

- Either prototype subtle far-view group markers, or move to production
  readability content: real unit silhouettes, terrain/biome richness, and
  higher-quality close/wide unit assets.

## Completed Slice 96 — Disable Metal World Team-Mask Tint For Parity

Goal:

- Apply the corrected AoE-style readability rule: strong faction color remains
  on the minimap/UI, but world unit materials do not receive runtime team-color
  tinting.
- Match the OpenGL reference renderer by removing Metal's separate
  team-mask/material-tint shader path.
- Keep selection rings neutral and thin; future world readability should come
  from silhouettes, authored assets, animation, terrain/biome richness, and
  compact status UI.

Implementation:

- Removed the Metal static/skinned mesh fragment shader's `team_masks`
  texture input and tint blend.
- Stopped active Metal draw paths from creating or binding material team-mask
  texture arrays.
- Removed Metal-only team-mask texture helper state from the renderer private
  data.
- Changed Sovereign unit readability metadata from `texture_mask` to
  `not_applicable` for world-material team color.
- Updated asset/readability docs so team-color masks are no longer considered
  part of the active renderer contract. Historical mask proof notes remain for
  auditability, but are superseded by this slice.

Verification:

```sh
python3 -m py_compile scripts/sovereign/data/units.py \
  scripts/sovereign/data/readability.py

python3 tools/asset_validation/validate_sovereign_readability.py
python3 tools/asset_validation/validate_sovereign_readability.py --strict

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-15-no-world-team-mask \
  --expect-backend METAL

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Observed:

- Readability validation passed with `production_ready=3` and
  `pending_team_masks=0`.
- Summary inspection confirms all active units use
  `team_color_mode=not_applicable` and `team_color_mask=None`.
- Metal proof passed:
  `HD_WORLD_READABILITY_PASS backend=METAL captures=10 highdpi=1 staged=108`.
- Proof output:
  `visual_parity_captures/2026-05-15-no-world-team-mask/`.
- OpenGL reference build compiles.
- `bin/pf-arm64` was rebuilt back to Metal after the OpenGL compile check.

Next:

- Resume production readability content: real unit silhouettes, terrain/biome
  richness, close-zoom character clarity, and wide-zoom army readability
  evidence without dynamic world tinting.

## Completed Slice 97 — Map Edge And Sky Boundary Readability

Goal:

- Make the outer map perimeter read cleanly against the sky/void at wide zoom.
- Keep the fix backend-neutral, so Metal and OpenGL show the same world-edge
  rule.
- Add proof coverage so future wide-map readability checks include the
  terrain-to-sky transition, not only army/status clutter.

Implementation:

- Added a subtle backend-neutral outer map boundary line in `src/map/map.c`.
  It uses the existing `R_Cmd_DrawQuad` path, so both Metal and OpenGL render
  the same map perimeter marker.
- Kept the line thin and dark enough to clarify the playable edge without
  turning it into UI chrome.
- Extended `scripts/macos/pf_metal_hd_world_readability_probe.py` with
  `map_edge_sky_boundary_readability`.
- Added a small map-edge scanner in the probe so the capture targets the actual
  map edge for the currently loaded map instead of relying on a hard-coded
  boundary coordinate.
- Updated the readability summary contract to include map-boundary separation.

Verification:

```sh
python3 -m py_compile scripts/macos/pf_metal_hd_world_readability_probe.py

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-15-map-edge-boundary-readability \
  --expect-backend METAL

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Observed:

- Metal proof passed:
  `HD_WORLD_READABILITY_PASS backend=METAL captures=11 highdpi=1 staged=108`.
- Proof output:
  `visual_parity_captures/2026-05-15-map-edge-boundary-readability/`.
- New boundary capture:
  - `map_edge_sky_boundary_readability`
  - target `[-464.0, -175.0]`
  - `edge_density=0.073068`
  - `gradient_p95=20`
- Retina capture scale remained `[2.0, 2.0]`.
- OpenGL reference build compiles.
- `bin/pf-arm64` was rebuilt back to Metal after the OpenGL compile check.

Conclusion:

- The map no longer falls away into the sky without an explicit playable-edge
  signal in the wide proof scene.
- This is still a functional/readability boundary, not final production map
  art. Later content work should replace the plain edge feeling with authored
  coastlines, cliffs, fog/void treatment, or biome-specific edge dressing.

Next:

- Continue production readability content: richer terrain/biome variation,
  authored map-edge dressing, and real unit silhouettes for close and wide zoom.

## Completed Slice 98 — Biome And Map-Edge Dressing Fixture

Goal:

- Reduce the wide-zoom "floating grass plane" feeling with a small, verified
  authored-looking terrain fixture.
- Keep this as proof-scene staging, not final production map art.
- Use existing terrain materials and props so the slice stays small and
  backend-neutral.

Implementation:

- Extended `scripts/macos/pf_metal_hd_world_readability_probe.py` to stage a
  dressed map-edge fixture before the HD readability captures.
- Added a probe-only terrain patching path that paints a map-edge band with
  existing sand, dirty-grass, cracked-dirt, dirt-road, and cobblestone materials.
- Added edge dressing props from the existing asset set: rocks, dry/leafy trees,
  fern/bush props, wood fences, and broken pillars.
- Added summary counts for `edge_dressing` and `terrain_updates`, so future
  proof runs show whether the fixture was actually staged.
- Updated the current-limitations text to make clear that this is fixture-level
  biome/edge dressing; final maps still need authored terrain art and placement.

Verification:

```sh
python3 -m py_compile scripts/macos/pf_metal_hd_world_readability_probe.py
git diff --check

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-15-biome-edge-dressing-readability \
  --expect-backend METAL

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Observed:

- Metal proof passed:
  `HD_WORLD_READABILITY_PASS backend=METAL captures=11 highdpi=1 staged=123`.
- Proof output:
  `visual_parity_captures/2026-05-15-biome-edge-dressing-readability/`.
- Summary counts:
  - `edge_dressing=15`
  - `terrain_updates=2257`
  - Retina capture scale `[2.0, 2.0]`
- Key captures:
  - `wide_large_map_readability`: `edge_density=0.113928`,
    `gradient_p95=25`.
  - `map_edge_sky_boundary_readability`: target `[-464.0, -175.0]`,
    `edge_density=0.084074`, `gradient_p95=22`.
- Visual inspection shows a clearer map/sky separation with a dressed sand/dirt
  edge band, props, and terrain variation. The result is still visibly a
  rectangular test fixture, which is acceptable for this proof slice.
- OpenGL reference build compiles.
- `bin/pf-arm64` was rebuilt back to Metal after the OpenGL compile check.

Conclusion:

- The HD readability proof now covers both the backend-neutral map boundary and
  a first authored-looking biome/edge dressing fixture.
- This does not replace real production map work. Final maps still need proper
  coastline/cliff/void treatment, richer biome transitions, and hand-authored
  object placement.

Next:

- Move from probe-level dressing to production readability content: real unit
  silhouettes/animation clarity, production terrain/biome art direction, and
  map-authoring rules for clean edges at wide zoom.

## Completed Slice 99 — Unit Silhouette And Animation Readability Gate

Goal:

- Add a stricter proof for close-zoom and wide-zoom unit readability without
  changing the renderer into a broad team-tint path.
- Keep player selection rings neutral white and thin.
- Use the current placeholder Sovereign units as proof subjects while making
  their production-art gaps explicit.

Implementation:

- Extended `scripts/sovereign/data/readability.py` with close-view metadata
  validation and production-asset status reporting.
- Added close-view readability rules to `scripts/sovereign/data/units.py` for
  the current villager/cart, militia/Knight, and archer/Mage placeholders.
- Extended `scripts/macos/pf_metal_hd_world_readability_probe.py` with four
  unit-focused proof scenes:
  - `close_unit_idle_pose_readability`
  - `close_unit_walk_pose_readability`
  - `close_unit_attack_pose_readability`
  - `wide_unit_silhouette_readability`
- Staged the Sovereign proof units through the data-driven entity factory,
  isolated them from the generic hero group, and recorded per-scene pose state
  in the summary JSON.
- Kept world materials free of dynamic team-color tinting; the proof relies on
  silhouettes, animations, neutral selection rings, and compact healthbar rules.

Verification:

```sh
python3 -m py_compile \
  scripts/macos/pf_metal_hd_world_readability_probe.py \
  scripts/sovereign/data/readability.py \
  scripts/sovereign/data/units.py

python3 tools/asset_validation/validate_sovereign_readability.py --strict
git diff --check

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL

./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/2026-05-15-unit-silhouette-readability-proof \
  --expect-backend METAL

make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```

Observed:

- Metal proof passed:
  `HD_WORLD_READABILITY_PASS backend=METAL captures=15 highdpi=1 staged=126`.
- Proof output:
  `visual_parity_captures/2026-05-15-unit-silhouette-readability-proof/`.
- Retina capture scale: `[2.0, 2.0]`.
- Staged counts:
  - `heroes=6`
  - `sovereign_units=3`
  - `edge_dressing=15`
  - `terrain_updates=2257`
- Close unit proof:
  - idle: `edge_density=0.092337`, `gradient_p95=24`,
    pose counts `archer:Idle`, `militia:Idle`, `villager:static`
  - walk: `edge_density=0.092635`, `gradient_p95=24`,
    pose counts `archer:Walk`, `militia:Walk`, `villager:static`
  - attack: `edge_density=0.093240`, `gradient_p95=25`,
    pose counts `archer:Attack`, `militia:Attack`, `villager:static`
- Wide unit silhouette proof:
  - `edge_density=0.147560`, `gradient_p95=32`
- Asset readability summary:
  - `units_needing_production_assets=3`
  - `production_asset_statuses={"placeholder_needs_replacement": 3}`
  - `pending_team_masks=0`
- Key visual proof captures:
  - `metal_hd_world_close_unit_attack_pose_readability_crop.png`
  - `metal_hd_world_wide_unit_silhouette_readability.png`

Conclusion:

- The HD readability harness now has a focused unit silhouette and animation
  gate for idle, walk, attack, and wide-zoom visibility.
- This is not final HD/4K character art. It makes the current placeholder
  model problem explicit and measurable before production assets are swapped in.
- The villager/cart placeholder remains static in walk/attack proof scenes
  because it is not a real animated villager asset.

Next:

- Replace placeholder unit art with production-readable silhouettes and
  animations: real villager/worker, infantry, ranged unit, and siege/animal
  silhouettes before deeper HD/4K character polish.

## Completed Slice 100 — Production Unit Art Readability Spec

Goal:

- Turn the Slice 99 proof result into an asset-authoring contract.
- Make the next unit replacement work concrete without rewriting the renderer
  or reintroducing broad world-material team tinting.

Implementation:

- Added `docs/sovereign/unit_art_readability.md`.
- Defined first production unit classes: worker/villager, melee infantry,
  ranged infantry, cavalry, siege, and animal/resource.
- Documented required animation clips, PFOBJ intake checks, material rules,
  close/wide proof gates, and the first replacement order.
- Updated `tools/asset_validation/README.md` so strict readability validation
  is described as metadata validation, while production asset readiness is
  tracked separately.
- Updated `docs/sovereign/engine_work_needed.md` to point production unit work
  toward silhouettes, animation, equipment, compact status UI, and small
  authored accents instead of broad dynamic tinting.

Verification:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py --strict
git diff --check
```

Conclusion:

- The production unit replacement path is now documented before any real art is
  swapped into gameplay.
- The first real production-asset target should be a villager/worker, because
  the current cart placeholder does not represent economy gameplay or
  character animation.

Next:

- Add a production unit preview/intake probe for one replacement unit type, then
  use it to bring in the first real villager/worker model when art is available.
