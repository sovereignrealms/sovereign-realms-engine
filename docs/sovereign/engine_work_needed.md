# Sovereign Realms Engine Work Needed

Sovereign Realms should build on Permafrost Engine rather than replace it. The
first production target is a small AoE2-like skirmish vertical slice on macOS
Apple Silicon using the native Metal renderer, with OpenGL retained as the
visual reference backend until parity and scale are repeatedly verified.

## Repository And License Structure

Recommended GitHub organization layout:

- `sovereignrealms/sovereign-realms-engine`: Permafrost-derived engine fork,
  keeping the upstream repository layout for easier upstream syncing.
- `sovereignrealms/sovereign-realms-game`: later split-out game repository once
  the first vertical slice is stable.

The initial game package lives inside the engine fork:

```text
scripts/sovereign/
assets/sovereign/
games/
docs/sovereign/
docs/modding/
tools/asset_validation/
```

Engine code stays under GPLv3 with the existing special linking exception unless
the upstream copyright holder grants a different license in writing. Original
Sovereign Realms assets must carry their own source and license records. Do not
import Microsoft, Ensemble Studios, or Age of Empires assets.

The early repository intentionally keeps the engine and world/game packs
together. Community packs live under `games/<pack_id>/` and must include their
own `LICENSE`, `README.md`, and `world.json`. A pack may choose its own license
for original maps, data, scripts, and assets, including MIT or Creative Commons
licenses, as long as it does not copy or relicense Permafrost-derived engine
code.

## Current Engine Baseline

Permafrost already provides the important RTS substrate:

- Native Metal renderer for macOS Apple Silicon and an OpenGL reference backend.
- PFOBJ meshes/animations, PFMAP terrain, and PFSCENE scene data.
- Python gameplay scripting on the macOS runtime path.
- Selection, movement, formations, pathfinding, fog of war, minimap, combat,
  projectiles, buildings, harvesting, storage, resources, garrison/transport,
  automation, save/load, and editor support.
- Skeletal animation, static meshes, terrain splatting, water, skybox, shadows,
  sprites/VFX, UI, and minimap rendering.
- Layered land/water/air navigation, hierarchical flow fields, dynamic
  obstacles, formation placement, and large-map systems.

The missing production layer is a clean game package, reliable asset pipeline,
data-driven rules, editor validation, and scale testing.

## Metal Renderer Readiness

Metal is ready for active Sovereign prototyping, but production default status
requires repeated proof against OpenGL in the visible gameplay loops:

| Item | Why it matters | Main areas | Verification |
|---|---|---|---|
| Visual parity baseline | screenshots and gameplay readability | `src/render/`, `scripts/macos/` | `scripts/macos/capture_visual_parity.sh <out>` |
| Skybox/reflections | atmosphere and water maps | skybox/water render paths | skybox plus water scene comparison |
| Water/refraction | rivers, coasts, naval maps | water path, map tiles | water-edge staged probe |
| Shadows | unit/building depth and terrain clarity | shadow pass, static/skinned meshes | owner/depth diagnostics and combat captures |
| Terrain materials | biomes, roads, cliffs, farms | map/terrain render paths | custom terrain fixture |
| Animated units | close-zoom character quality | `src/anim/`, PFOBJ material upload | close character capture |
| Sprites/VFX | arrows, impacts, fire, smoke | sprite/projectile paths | effects probe with spawn/socket alignment |
| UI/minimap | fog and command readability | UI, minimap, fog | minimap fog and Retina UI probes |
| Performance | large battles | animation, nav, Metal backend | 100/500/1000/2000-unit benchmarks |

Renderer work should stay incremental: fix one explicit Metal state, data path,
or shader behavior at a time.

## Asset Pipeline Work

Ship the first vertical slice with PFOBJ. Add glTF/GLB import later after the
PFOBJ pipeline is dependable.

Required conventions:

- Animation names: `Idle`, `Walk`, `Attack`, `Die`, `Gather`, `Carry`, `Build`,
  `Repair`, `Shoot`.
- Every unit, building, tree, prop, resource node, and siege asset needs bounds
  or a documented reason it is non-interactive.
- Texture files must exist beside the PFOBJ or in a documented asset pack path.
- Team color starts as material/texture variants or masks; a formal shader
  convention can come later.
- Large-army readability needs close, normal, and far-view asset rules before
  500+ unit scenes are judged.

Use `tools/asset_validation/validate_pfobj.py` as the first validation gate.

## Gameplay Data Architecture

Keep gameplay rules in Python/data first:

```text
scripts/sovereign/data/
  resources.py
  units.py
  buildings.py
  technologies.py
  civilizations.py
  ages.py
  armor_classes.py
```

Data should define unit stats, costs, train times, population, armor classes,
building footprints, production/research options, resources, ages, civilization
bonuses, and damage counters. C changes should be limited to missing engine
primitives or performance-critical behavior.

Current implementation status:

- `scripts/sovereign/data/` contains initial registries for resources, ages,
  armor classes, units, buildings, technologies, and civilizations.
- `scripts/sovereign/factory.py` validates cross-registry references and builds
  a minimal spawn plan from `sovereign_default`.
- `scripts/sovereign/entities/runtime.py` maps the first data archetypes onto
  existing Permafrost engine entity classes.
- `scripts/macos/pf_sovereign_factory_probe.py` verifies the registries can
  spawn a real Metal runtime scene.
- `scripts/macos/pf_sovereign_economy_probe.py` verifies the first playable
  Sovereign loop: gather food, drop it at the town center, and complete the
  house placeholder. Its opt-in `--capture-after-pass` mode writes a Metal
  window screenshot for visual QA.
- `scripts/sovereign/systems/production.py` adds the first data-driven
  production queue and population helper.
- `scripts/macos/pf_sovereign_production_probe.py` verifies a barracks can
  train one militia from registry data, deduct food/gold, consume population,
  respect the house-provided cap, and spawn at a pathable rally point. Its
  `--capture-proof` mode writes before/after Metal screenshots for visual QA.
- `scripts/sovereign/systems/technology.py` adds the first data-driven
  research queue and age-effect helper.
- `scripts/macos/pf_sovereign_age_tech_probe.py` verifies the town center can
  research `advance_to_rising`, spend food, move from `founding` to `rising`,
  record the researched technology, and reject wrong-age or duplicate research.
  Its `--capture-proof` mode writes before/after Metal screenshots for visual
  QA.
- `scripts/sovereign/systems/combat_rules.py` adds the first data-driven
  damage/counter helper using `DAMAGE_BONUSES`.
- `scripts/macos/pf_sovereign_combat_rules_probe.py` verifies a militia
  melee attack against infantry resolves through registry data and changes
  target HP in a real Metal scene.
- `scripts/sovereign/data/units.py` now includes a placeholder `archer`
  projectile descriptor wired to existing arrow, trail, and impact assets; its
  current fire descriptor uses the Mage rig `palm_r` socket as a temporary
  direct-fire archer socket.
- `scripts/sovereign/entities/runtime.py` passes data-defined projectile
  descriptors through to the existing `pf.CombatableEntity` runtime and plays
  attack animations around ranged attacks so socket fire frames advance.
- `scripts/macos/pf_sovereign_projectile_vfx_probe.py` verifies projectile
  damage, trail emission, impact sprites, fire/smoke sprite rendering,
  attacker/target facing, spawn near the attacker socket, impact near the
  target, and target-ward projectile direction in a real Metal scene.
- `scripts/sovereign/session_state.py` adds the first explicit Sovereign
  Python 3 save/load layer: registry entity tags, compact chunked gameplay
  state tags, and post-native-session-load manager rebind.
- `scripts/macos/pf_sovereign_save_load_probe.py` verifies native Metal
  `.pfsave` roundtrip for registry-created entities, resources/population,
  production queue, age/technology state, combat HP, and post-load queued-unit
  continuation.
- `scripts/sovereign/systems/skirmish.py` adds the first deterministic
  scripted skirmish helper: enemy economy resource seeding, barracks training,
  wave state snapshots, and a conquest-style victory predicate.
- `scripts/sovereign/entities/runtime.py` now switches Sovereign combat units
  into `Walk` on engine motion-start and back to `Idle` on motion-end, matching
  the older RTS unit pattern so moving/fighting proof scenes can check natural
  animation state.
- `scripts/macos/pf_sovereign_skirmish_probe.py` verifies a fixed two-player
  setup, scripted enemy economy/build/train loop, smooth attack-wave movement,
  observed `Walk` and `Attack` clips, target-facing combat staging, data-driven
  damage, and conquest-style victory in a real Metal scene. Its
  `--capture-proof` mode writes setup, moving, combat, and victory screenshots.
- `scripts/macos/pf_sovereign_ai_decision_probe.py` verifies the first explicit
  scripted-AI decision depth in Metal: resource shortfall, population block,
  house response, training, attack readiness, attack order, and decision-log
  snapshots.
- `assets/sovereign/scenarios/two_player_skirmish.json` adds the first
  Sovereign scenario sidecar for player starts, diplomacy, starting resources,
  victory mode, and editor palette metadata.
- `scripts/sovereign/scenario.py` validates, exports, reloads, and spawns that
  sidecar into a real two-player runtime scene.
- `scripts/macos/pf_sovereign_editor_scenario_probe.py` verifies the sidecar
  export/reload/run path in Metal, trains an enemy militia from the
  scenario-created barracks, executes a conquest-style data victory check, and
  writes loaded/validated screenshots.
- `scripts/sovereign/editor_scenario.py` adds the first packaged-editor bridge:
  when the editor is launched with `PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1`,
  Save/Save As writes a `.sovereign.json` scenario sidecar beside the saved
  PFMAP/PFSCENE output.
- `scripts/editor/views/sovereign_tab_window.py` adds the first visible
  packaged-editor Sovereign tab for scenario name, player selection, player
  names, civilizations, start positions, setup profile, starting-resource
  preset, player starting resources, diplomacy, and the current Sovereign
  object palette.
- The Sovereign tab now exposes a placement mode for player starts versus
  resource clusters, units, and buildings; it records resource ownership,
  cluster amounts, object ownership, selected palette object, and current
  placement coordinates. Its controller applies map clicks to the selected
  start, resource cluster, unit, or building slot.
- The scenario sidecar now records `placed_resources` and `placed_objects`,
  validates ownership and food/wood/gold/stone cluster coverage, checks
  starts/resources/objects against pathable terrain, and spawns authored
  clusters, units, and buildings into Metal.
- The existing editor workflow probe now validates that exported sidecar,
  including placed resource/object metadata, setup profile, starting-resource
  preset, and export-report setup metadata, and records its path in the
  `EDITOR_WORKFLOW_READY` marker.

## AoE2-Like Systems To Build

MVP systems:

- Villager gather/build/repair/drop-off.
- Food, wood, gold, stone, and population.
- Town center, house, drop-off building, barracks, basic military unit.
- Single-building production queues with rally points.
- One age advancement and one upgrade.
- Basic damage counters and projectile combat.
- Simple skirmish victory condition. Initial deterministic conquest-style
  probe is in place.
- Scripted AI that gathers, builds, trains, and attacks. Initial enemy
  economy-seed/build/train/attack-wave proof and resource/population/training/
  attack-readiness decisions are in place; autonomous gather, build-order
  timing, scouting, and tactical target selection remain later slices.

Later systems:

- Farms with reseeding/depletion.
- Connected walls and gates.
- Siege splash damage and destruction states.
- Civilization bonuses and full tech trees.
- Random maps, teams, difficulty, campaigns, and trigger-like scenario logic.

## Editor And Tooling

The editor must become a production map/scenario workflow:

- Terrain painting for biomes, roads, cliffs, shallow/deep water.
- Object palette driven by Sovereign data registries.
- Player starts, team ownership, diplomacy, resources, animals, buildings, units.
- Scenario metadata: map name, players, teams, victory mode, starting resources,
  and random seed.
- Validation for unreachable resources, blocked starts, invalid drop-off
  placement, disconnected water, bad pathing, and missing asset licenses.

MVP editor goal: create, export, reload, and run a two-player skirmish map.
The first sidecar save/export bridge, visible authoring tab, map-click
placement for player starts/resource clusters/units/buildings,
resource/object ownership metadata, and runtime pathability validation are now
in place behind `PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1`. The tab also shows
live validation status so authors can see structural/pathing problems before
save. Add, duplicate, and remove controls are now in place for starts,
resources, units, and buildings, and the editor controller draws simple
map-space region markers for authored starts/resources/objects. Validation
messages now carry editor-only targets, and the tab can jump to the offending
start, resource, unit, or building slot with a Go control. The selected slot's
map marker is rendered as the single active marker. Scenario metadata/export UX
now includes an editable scenario ID, scenario-size summary, sidecar export
state/path/message, compact palette summaries, and validation category counts
that remain useful as maps accumulate more authored starts/resources/objects.
The selected-preview panel now shows useful authoring facts for the current
start, resource, unit, or building, including role/archetype, cost, HP, range,
footprint, and asset path where applicable. Palette search/filtering and
category folding now keep the registry-backed palette readable as more
definitions are added. Validation summaries now show category jump controls and
compact "showing/jumpable" counts so larger authored maps stay navigable
without flooding the left pane. Existing `.sovereign.json` sidecars now import
back into the authoring tab when a saved editor map is loaded, restoring
scenario id/name, players, palette, placed resources, placed objects,
diplomacy, export status, and placement markers for further edits. The
authored-map stress fixture now verifies a four-player sidecar with 16 resource
clusters, 12 placed objects, 32 editor markers, reload/import parity, and Metal
runtime spawn. Production-map metadata now records a deterministic map seed,
author notes, and a labeled Conquest victory mode, and each sidecar carries a
large-map export report with counts and validation status that survives
save/reload and runtime scenario verification.

## Performance And Scale

Benchmark targets:

- 100 units: 60 FPS target.
- 500 units: 45-60 FPS target.
- 1000 units: 30-60 FPS target depending on battle density.
- 2000 units: stress target, not the first shipping bar.

Benchmark scenes should include economy workers, mixed army movement, dense
formations, large villages, fog/minimap updates, and projectile-heavy siege.

Measure frame time, sim time, render time, pathfinding time, animation batch
size, projectile count, fog/minimap update cost, Metal GPU time where available,
and memory growth over longer sessions.

## Save/Load And Determinism

Sovereign save/load must cover map, scene, factions, diplomacy, unit orders,
resources, population, production queues, technology state, age state,
construction progress, projectiles, farms/resource depletion, fog of war, AI
state, victory state, and random seeds.

Current Python 3 session support saves native scene/entity state, then uses the
Sovereign session layer to rebind gameplay managers after load. The first probe
now covers registry-created entities, resources/population, production queue,
age/technology state, combat HP, queued-unit continuation, and scenario-level
state. Scenario runtime state now includes map seed, author notes, map
reference, and victory mode/label, and the restore probe checks that this data
survives the native `.pfsave` roundtrip. Setup profiles and starting-resource
presets now resolve runtime resources before per-player overrides, and
victory-progress snapshots track alive/defeated factions, winner, mode/label,
and elapsed ticks. Later skirmish work must add longer AI progression state and
longer order/task coverage.

All skirmish generation should record a seed. The first shared seed helpers are
in place for deterministic runtime choices, and the skirmish probes verify that
seeded setup and victory-mode dispatch stay wired. Dynamic time-of-day must be
fixed or disabled in deterministic probes unless that system is the test target.

## Test Matrix

| Test | Expected result |
|---|---|
| Native launch probe | Metal runtime starts and reports ready marker |
| Gameplay smoke | no Python dialog and core systems progress |
| Sovereign factory probe | data registries spawn real engine entities |
| Visual parity capture | OpenGL/Metal cameras match |
| Resource economy probe | villager gathers, drops off, and completes a starter building |
| Villager build probe | building reaches completed state |
| Production queue probe | `pf_sovereign_production_probe.py` trains one militia and resources/pop update |
| Age advancement probe | `pf_sovereign_age_tech_probe.py` advances to Rising Age and records the tech |
| Combat counter probe | `pf_sovereign_combat_rules_probe.py` applies registry damage and expected bonus |
| Siege projectile probe | `pf_sovereign_projectile_vfx_probe.py` records projectile damage, trail, impact, fire, smoke, spawn/socket alignment, impact proximity, and target-ward direction |
| Fog/minimap probe | main map and minimap visibility agree |
| Save/load roundtrip | `pf_sovereign_save_load_probe.py` reloads native `.pfsave` and restores entity tags, scenario seed/setup/victory metadata, victory progress, player state, production queue, technology state, combat HP, and queued-unit continuation |
| AI/skirmish loop | `pf_sovereign_skirmish_probe.py` trains an enemy wave from seeded scenario state, verifies setup profile, smooth motion and `Walk` animation, stages facing combat, applies data damage, and reports victory progress through the scenario victory dispatcher |
| AI decision-depth probe | `pf_sovereign_ai_decision_probe.py` verifies resource shortfall, population block, house response, training, attack readiness, attack order, and decision logging in a Metal two-player fixture |
| Long skirmish session | `pf_sovereign_long_skirmish_probe.py` runs staged economy, building construction, player production, enemy attack waves, conquest victory progress, native session save, session load, and queued-unit continuation after restore |
| Editor workflow probe | editor Save As writes PFMAP/PFSCENE plus a `.sovereign.json` sidecar when `PF_EDITOR_SOVEREIGN_SCENARIO_EXPORT=1`; with `PF_EDITOR_SOVEREIGN_AUTHORING_PROBE=1`, the editor tab edits player starts/resources/objects, setup profile, resource preset, scenario seed, author notes, and victory label, applies placement points, and validates ownership/clusters before save; with `PF_EDITOR_SOVEREIGN_AUTHORING_RELOAD_PROBE=1`, loading the saved map imports the sidecar and export report back into the authoring tab; `pf_sovereign_editor_scenario_probe.py` validates, exports, reloads, spawns placed resources/objects, verifies metadata/report checks, setup profile/resource preset, seeded setup, victory dispatch, trains from, and victory-checks that sidecar |
| Asset validation | no missing textures, bounds, or required animations |

Python exception dialogs, camera mismatches, missing assets, or non-deterministic
state deltas fail the gate.

## Roadmap

1. Repo/license bootstrap.
2. Metal parity baseline.
3. Asset pipeline hardening.
4. Data-driven definitions. Initial registry validation, factory spawn, and
   minimal economy behavior are in place.
5. Production queues and population. Initial queue, cost, population-cap, and
   rally-spawn behavior are in place.
6. Age advancement and tech tree. Initial age-up cost, prerequisite, duplicate
   blocking, and `set_age` effect behavior are in place.
7. Siege/combat expansion. Initial data-driven combat-counter math and
   projectile/VFX plus projectile origin/facing proof are in place; siege
   splash, destruction states, and real archer/weapon rigs are later production
   slices.
8. Save/load and determinism. Initial native Metal `.pfsave` roundtrip for
   Sovereign registry state, scenario seed/setup/victory metadata, victory
   progress, production, tech, combat HP, and queued-unit continuation is in
   place; longer AI progression state remains for later skirmish work.
9. Editor workflow improvements. Initial scenario sidecar export/reload/run
   probe, env-gated editor Save As sidecar export, and the first visible
   Sovereign authoring tab are in place. Map-click placement now covers player
   starts, resource clusters, units, and buildings, including ownership/amount
   metadata and runtime pathability checks. Add/duplicate/remove controls and
   simple map-space placement markers are now in place. Validation issues now
   select the offending authoring slot and active markers distinguish the
   current placement target. Scenario metadata/export feedback and compact
   palette/validation summaries are implemented. Selected placement previews
   now expose authoring facts from the Sovereign registries. Palette
   filtering/category folding and scalable validation jump summaries are now in
   place. Saved Sovereign sidecars now import back into the authoring tab on
   editor map load. The larger authored-map stress fixture is now green with 4
   players, 16 resource clusters, 12 placed objects, 32 editor markers, and 68
   Metal runtime objects. Production-map seed, author notes, labeled victory
   mode, and sidecar export-report counts/validation status are now saved,
   reloaded, shown in the authoring tab, and checked by the Metal runtime
   scenario probe. Scenario metadata is now also actionable in gameplay through
   deterministic seed helpers, seeded skirmish setup checks, scenario victory
   dispatch, setup profile/resource preset resolution, victory-progress
   snapshots, session roundtrip coverage, and visible editor profile/preset
   authoring controls.
10. AI/skirmish loop. Initial deterministic two-player script, enemy
    economy-seed/train wave, walking animation check, facing combat proof,
    conquest-style winner check, resource/population/training/attack-readiness
    decisions, and a longer staged session/save-load probe are in place.
11. Performance, Retina clarity, and HD/4K polish.
