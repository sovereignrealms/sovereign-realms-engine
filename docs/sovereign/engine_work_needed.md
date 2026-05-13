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
- Every Sovereign unit registry entry must include readability metadata:
  silhouette class, far-view class, minimum pixel target, marker policy, and
  team-color strategy.

Use `tools/asset_validation/validate_pfobj.py` as the first validation gate.
Use `tools/asset_validation/validate_sovereign_readability.py` to track
team-color-mask and far-view silhouette readiness. Normal mode allows current
placeholder units to report pending masks; strict mode is the production gate
once final unit art is expected.

The current placeholder unit pack now has mask coverage for all three unit
entries:

- `militia`: `assets/models/knight/Knight_team_mask.png`
- `archer`: `assets/models/mage/Mage_team_mask.png`
- `villager`: `assets/models/cart/wood_team_mask.png`

Use `tools/asset_validation/validate_sovereign_readability.py --strict` as the
current pack-level gate. The cart mask is intentionally a placeholder
whole-texture mask because the cart asset has no separate team-color region.
Its filename follows the renderer lookup convention: a material texture named
`wood.jpg` uses a sibling mask named `wood_team_mask.png`. Final Sovereign
villager art still needs a purpose-built clothing/tool mask.

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
- `scripts/sovereign/systems/skirmish.py` now includes `BuildOrderPlanner`, a
  deterministic first build-order loop that gathers missing resources, adds a
  house when population is tight, trains a militia wave, chooses a priority
  target, and launches the attack.
- `scripts/macos/pf_sovereign_ai_build_order_probe.py` verifies that loop in
  Metal, then saves and reloads the session to prove scenario state, combat HP,
  victory progress, production queue state, research state, and queued-unit
  continuation survive restore.
- `scripts/sovereign/systems/skirmish.py` now includes tactical scout-report
  and threat-response helpers for classifying nearby enemy units around
  defended assets.
- `scripts/macos/pf_sovereign_ai_threat_response_probe.py` verifies a Metal
  fixture where an enemy scout detects a nearby player militia, recovers
  resources, builds population room, trains defenders, launches a defense
  response, and confirms defenders move toward the threat.
- `scripts/sovereign/systems/skirmish.py` now includes `ThreatMemory`,
  `ScoutingRoutePlanner`, and `MemoryResponsePlanner` so scouting can follow
  route waypoints, remember last-known threats after visibility is lost, and
  adapt response training toward remembered map positions.
- `scripts/macos/pf_sovereign_ai_scout_memory_probe.py` verifies route
  scouting, remembered threat persistence without current visibility,
  memory-driven income/house/defender training, defense launch, and scout plus
  defender motion in Metal.
- `scripts/sovereign/ai_memory_restore.py` restores saved AI threat memory
  after a native Python 3 session reload and re-drives the memory response
  planner from the saved state.
- `scripts/macos/pf_sovereign_ai_memory_save_load_probe.py` verifies native
  `.pfsave` persistence for AI memory, outnumbered regroup, resource/population
  recovery, defender training, and remembered-position defense response.
- `scripts/sovereign/systems/skirmish.py` now includes
  `AdaptiveMemoryStrategyPlanner`, which schedules scout-route refreshes,
  picks a response unit from remembered threat role, regroups while
  outnumbered, trains the selected counter unit, responds to the remembered
  position, and launches a counterattack when enough units are ready.
- `scripts/macos/pf_sovereign_ai_adaptive_strategy_probe.py` verifies that
  remembered military threats drive archer production, scheduled scouting,
  retreat/regroup, response launch, and counterattack motion in Metal.
- `scripts/sovereign/systems/skirmish.py` now includes macro-strategy
  difficulty profiles plus `StrategicMacroPlanner`, which scores economy versus
  military pressure, expands with a second base when economy wins, recovers
  military resources when threat pressure wins, trains the chosen unit type,
  and launches a strategic attack.
- `scripts/macos/pf_sovereign_ai_macro_strategy_probe.py` verifies `booming`
  economy expansion, `hard` military weighting, second-base placement,
  strategic archer training, and attack movement in Metal.
- `scripts/sovereign/systems/skirmish.py` now includes `MapControlEvaluator`
  and `MapControlStrategyPlanner`, which score named control points, apply
  difficulty-profile attack/retreat thresholds, retreat/regroup when control is
  poor, recover through income/population, train the preferred counter unit,
  and attack when army and timing scores are ready.
- `scripts/macos/pf_sovereign_ai_map_control_probe.py` verifies map-control
  summaries, `hard` profile thresholds, retreat timing, resource/population
  recovery, archer training, map-control attack timing, and attack movement in
  Metal.
- `scripts/sovereign/systems/skirmish.py` now includes
  `BranchingStrategyPlanner`, which splits strategic branches across defense,
  multi-base expansion, harassment training, and harassment launch without
  rewriting engine combat or pathing.
- `scripts/macos/pf_sovereign_ai_branching_strategy_probe.py` verifies a
  longer Metal branch sequence: militia defense against a nearby threat,
  resource recovery, two additional town centers, archer harassment training,
  and separate defense/harassment movement.
- `scripts/sovereign/systems/skirmish.py` difficulty profiles now carry
  personality IDs, expansion target counts, harassment cadence, max harassment
  waves, and target-role priorities. `BranchingStrategyPlanner.from_snapshot()`
  restores that branch state after native session load.
- `scripts/sovereign/ai_branching_restore.py` and
  `scripts/macos/pf_sovereign_ai_personality_save_load_probe.py` verify a hard
  pressure personality launching harassment, saving during its cadence window,
  restoring the cooldown hold, and continuing into a second harassment wave.
- `BranchingStrategyPlanner` now defaults harassment composition from the
  difficulty profile's `preferred_military_unit`, and
  `scripts/macos/pf_sovereign_ai_difficulty_ab_probe.py` compares standard,
  booming, and hard over the same extended Metal branch fixture. It verifies
  different expansion counts, harassment wave counts, target-role priorities,
  and militia-vs-archer pressure composition.
- `scripts/sovereign/data/technologies.py` now includes strategy technologies
  for infantry, expansion, and archer pressure. `CompositionStrategyPlanner`
  researches the profile-specific strategy tech, trains toward the target unit
  mix, and attacks the profile's preferred target role.
- `scripts/macos/pf_sovereign_ai_composition_strategy_probe.py` verifies that
  standard researches infantry drills and builds militia, booming researches
  settlement logistics and builds a mixed militia/archer force, and hard
  researches ranger fletching and builds archer pressure.
- `scripts/sovereign/systems/combat_rules.py` now includes deterministic
  composition-duel checks, and
  `scripts/macos/pf_sovereign_ai_composition_counter_probe.py` verifies in
  Metal that the standard, booming, and hard army plans win favorable matchups
  and lose clearly unfavorable matchups.
- `scripts/macos/pf_sovereign_ai_difficulty_balance_save_load_probe.py` now
  runs a longer standard/booming/hard A/B balance fixture, snapshots each
  branch at a save point, continues from planner snapshots, and verifies the
  compact comparison report survives native `.pfsave` reload.
- `scripts/sovereign/systems/skirmish.py` now includes
  `MatchLengthBuildOrderPlanner`, which gives each difficulty profile a
  deterministic opening-economy window before moving into expansion,
  military-transition, and attack timing.
- `scripts/macos/pf_sovereign_ai_match_length_adaptation_probe.py` verifies
  standard, booming, and hard in one Metal scene, including opening duration,
  transition step, expansion step, preferred attack-unit count, and attack
  launch timing.
- `scripts/sovereign/systems/skirmish.py` now includes
  `AttritionRecoveryPlanner`, and `ScriptedSkirmishAI` tracks live rosters plus
  explicit unit-loss records so failed attacks can trigger regroup/rebuild
  behavior instead of counting lost units as ready attackers.
- `scripts/macos/pf_sovereign_ai_attrition_recovery_probe.py` verifies a
  hard-profile archer opening that loses two archers, defends against live base
  pressure, regroups, retrains archers, and relaunches the attack in Metal.
- `AttritionRecoveryPlanner` now records post-launch outcomes. A second failed
  push escalates the next relaunch target from three to four archers, while a
  successful relaunch clears recovery state and lets the planner shift back
  toward economy/expansion.
- `AttritionRecoveryPlanner` now also supports pressure-driven technology
  pacing: after repeated failed pushes, the hard-profile probe researches
  `ranger_fletching` through the existing `ResearchQueue` before the larger
  second relaunch.
- `MultiFrontArmyPlanner` now proves the first split-force control layer:
  selected militia/archer subsets can be assigned to separate defense,
  harassment, and building-attack fronts without reusing the same units.
- `scripts/macos/pf_sovereign_ai_skirmish_soak_probe.py` composes the AI
  layers into a larger Metal AI-vs-player soak: player production, enemy
  income, multi-front activity, repeated attrition recovery, pressure-triggered
  `ranger_fletching`, combat damage, conquest progress, and sustained runtime
  ticks are checked together.
- `scripts/macos/pf_sovereign_ai_large_army_scale_probe.py` adds the first
  larger-army Metal scale gates. It now supports mass movement and attack-move
  modes, records phase timing, sampled p50/p95/max wall-clock tick budgets, and
  wide-zoom proof captures, and verifies mixed infantry/archer soaks up through
  the first 1000-unit exploratory gate.
- `scripts/macos/profile_sovereign_large_army_scale.sh` wraps that 1000-unit
  gate with an attach-mode Instruments Time Profiler run and writes a compact
  hotspot summary. The first trace shows the dominant CPU cost in ClearPath
  collision-avoidance geometry (`inside_pcr`, `C_RayRayIntersection2D`,
  `compute_vo_xpoints`) plus Metal skinned-animation assembly
  (`append_skinned_anim_mesh`).
- `src/game/clearpath.c` now avoids duplicate pairwise ray intersections in
  `compute_vo_xpoints()`. This keeps the same unordered ray-pair candidate set
  while cutting redundant dense-formation collision-avoidance work.
- The post-change Time Profiler trace confirms that `compute_vo_xpoints`
  inclusive samples dropped from the first-trace hotspot tier. The remaining
  scale candidates are now `inside_pcr` work inside ClearPath and
  `append_skinned_anim_mesh` in the Metal animation stream path.
- `src/render/backend_metal.m:append_skinned_anim_mesh()` now precomposes the
  entity model matrix with each joint skin matrix once per animated entity, so
  CPU-side batch assembly skins directly into world space instead of applying a
  second model transform to every skinned vertex. The 1000-unit profiled gate
  now sits around a 351 ms p95 tick budget.
- `src/game/clearpath.c` now has opt-in ClearPath diagnostic counters behind
  `PF_CLEARPATH_STATS_PATH`, and the large-army probe can flush them before its
  fast `os._exit()` path. The 1000-unit diagnostic run shows the next collision
  bottleneck is not just raw ray count: it is repeated no-solution fallback
  attempts, with roughly 1.12 million fallback removals, 2.15 billion xpoint
  ray-pair tests, and 680 million `inside_pcr()` checks in that run.
- `src/game/clearpath.c` now uses a guarded dense-fallback policy by default:
  after a no-solution ClearPath attempt, it removes up to four furthest
  neighbours only while 40 or more neighbours remain. This reduces repeated
  dense retry work while leaving smaller formations close to prior behavior.
- The post-fallback attach-mode Time Profiler trace shows the next primary CPU
  lane is Metal animated mesh batch assembly (`append_skinned_anim_mesh`,
  roughly 25.9% inclusive), followed by remaining ClearPath geometry
  (`inside_pcr`, roughly 22.9% inclusive, and `compute_vo_xpoints`, roughly
  11.8% inclusive). This makes animation batching the next clean scale target,
  with ClearPath still close behind.
- `src/render/backend_metal.m` now keeps a per-frame skinned-mesh cache for
  animated Metal draws. The shadow pass can seed CPU-skinned vertices and the
  main pass can reuse them for the same UID/model pair instead of assembling the
  same mesh twice. The latest 1000-unit profiled gate drops from a 356.499 ms
  p95 tick to 193.387 ms, with the 500-unit regression at 90.064 ms p95.
- `src/game/clearpath.c` now uses direct squared-length determinant tests in
  `inside_pcr()` and a ClearPath-local cross-product ray intersection in
  `compute_vo_xpoints()`. This removes the generic slope-based ray-intersection
  helper from the hot list and lowers ClearPath's profile share, though the
  wall-clock p95 is effectively neutral at the current scale.
- `src/phys/projectile.c` now checks projectile `sprite_flags` before spawning
  trail sprites. This fixes a hidden dense-combat crash where collision flag
  `PROJ_ONLY_HIT_ENEMIES` overlapped the sprite flag bit for
  `PROJ_HAS_TRAIL_SPRITE`.
- `src/render/backend_metal.m` now has an env-gated
  `PF_METAL_GPU_SKINNING=1` prototype for batched animated main-pass and
  shadow-pass draws. It keeps the default path unchanged, preserves per-caster
  shadow owner diagnostics on the CPU path, and moves the 1000-unit opt-in p95
  to about 69 ms in the normal gate and 54 ms in the Time Profiler run. The
  leading hotspot becomes ClearPath again rather than CPU skinning.
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
  attack-readiness decisions are in place. Deterministic build-order planning
  now covers resource recovery, house construction, militia wave training,
  priority target selection, and attack launch. Tactical scouting and nearby
  threat response are now in place for defended assets. Scouting route
  waypoints and threat memory now preserve last-known enemy positions after
  visibility is gone. AI threat memory now also survives native save/load and
  can drive outnumbered regroup, resource/population recovery, defender
  training, and remembered-position response after restore. Adaptive strategy
  now schedules scout refreshes, chooses archers against remembered military
  threats, and launches counterattacks once the response force is ready. Macro
  strategy now adds difficulty profiles, economy-vs-military weighting, and
  second-base expansion. Map-control strategy now scores contested control
  points, uses difficulty-tuned attack/retreat timing, recovers through
  economy/population, trains archers, and launches a timed counterattack.
  Branching strategy now splits militia defense from archer harassment, expands
  to three town centers, and proves a longer branch sequence in Metal.
  Difficulty-specific personalities, composition branching, balance save/load
  comparisons, and match-length opening-to-military transition timing are now
  covered by native Metal probes. Failed-attack recovery now handles a first
  attrition case by recording unit loss, defending under live pressure,
  regrouping survivors, rebuilding the preferred unit count, and relaunching.
  Repeated attrition outcome tracking now distinguishes a second failed push
  from a successful relaunch: the failed path escalates army size, and the
  success path shifts back into economy/expansion. Repeated failed pressure can
  now also trigger `ranger_fletching` before the larger second relaunch.
  Multi-front control now splits disjoint groups across home defense, villager
  harassment, and building attack fronts. Naval/air reactions remain later
  slices.

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
The first larger-army probe now covers 192-unit, 250-unit, 500-unit, and a
1000-unit exploratory mixed infantry/archer attack-move soak in Metal with
wall-clock budget telemetry and wide-zoom captures. The 1000-unit run proves
functional survival. After the first ClearPath duplicate-pair optimization, the
1000-unit exploratory run clears the current 500 ms soft p95 tick budget. After
the ClearPath stats and guarded fallback slices, the no-stats 1000-unit default
regression passed at roughly 310 ms p95, compared with roughly 340 ms before the
fallback policy. After the per-frame Metal skinned-mesh cache, the latest
profiled 1000-unit p95 is 193.387 ms and the 500-unit regression p95 is
90.064 ms. After the ClearPath fast-math slice, the 1000-unit gate remains
green at 196.212 ms p95 with no warnings, and the Time Profiler no longer shows
the generic `C_RayRayIntersection2D()` helper as a hotspot. The next scale
target returned to Metal animated rendering. The first env-gated
`PF_METAL_GPU_SKINNING=1` prototype now skins batched animated main/shadow
draws on the GPU, drops the opt-in 1000-unit gate to about 69 ms p95, and drops
the profiled p95 to about 54 ms. This is not the default yet; it needs visual
parity and longer gameplay checks before promotion. The next scale target is
ClearPath dense-candidate pressure under this new baseline. The first
post-GPU-skinning ClearPath policy probe confirmed repeated no-solution
fallback remains the pressure point, but no default fallback-policy change
landed because the tested batch-removal variants were either too aggressive or
unstable across verification runs. A 500-unit GPU-skinning capture-proof pass
now records before/engage/soak/wide-zoom screenshots at 3456x2234 for visual
hardening. The HD world readability probe now adds Retina-scale close/wide
proof captures, centered review crops, and luma/edge metrics for close
characters, dense armies, world props, VFX combat, and wide-map readability.
The first production-readability overlay rule is also in place: selected
player-owned units keep neutral white thin rings, the Metal backend renders
world-color overlays through the native color pipeline, and healthbars shrink
as the camera zooms out so large army views are not dominated by UI bars.
These are regression evidence gates; real production HD/4K asset quality still
requires new character, building, terrain, and UI content.

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
| AI build-order probe | `pf_sovereign_ai_build_order_probe.py` verifies deterministic gather, house, militia training, priority target selection, attack launch, combat HP delta, victory progress, save/load, and queued-unit continuation after restore |
| AI threat-response probe | `pf_sovereign_ai_threat_response_probe.py` verifies scouting, nearby threat classification, resource recovery, population recovery, defender training, defense launch, and defender motion toward the threat |
| AI scout-memory probe | `pf_sovereign_ai_scout_memory_probe.py` verifies scouting route steps, remembered threats after current visibility is gone, memory-driven income/house/defender training, defense launch to a last-known position, and scout/defender motion |
| AI memory save/load probe | `pf_sovereign_ai_memory_save_load_probe.py` verifies restored threat memory after native `.pfsave` load, outnumbered regroup, memory-driven income/house/training, and response to the remembered threat position |
| AI adaptive strategy probe | `pf_sovereign_ai_adaptive_strategy_probe.py` verifies scheduled scout refresh, remembered-threat unit choice, archer counter-training, retreat/regroup, remembered-position response, counterattack launch, and movement |
| AI macro-strategy probe | `pf_sovereign_ai_macro_strategy_probe.py` verifies difficulty profiles, economy-vs-military scoring, second-base expansion, military recovery, archer training, strategic attack launch, and movement |
| AI map-control strategy probe | `pf_sovereign_ai_map_control_probe.py` verifies control-point scoring, difficulty thresholds, retreat/regroup timing, resource/population recovery, archer training, map-control attack launch, and movement |
| AI branching strategy probe | `pf_sovereign_ai_branching_strategy_probe.py` verifies defense/harassment split decisions, expansion income, three-base planning, harassment training, harassment launch, and separate defense/harass movement |
| AI personality save/load probe | `pf_sovereign_ai_personality_save_load_probe.py` verifies difficulty personality fields, hard-profile harassment cadence, compact native save/load state, restored cooldown hold, and a second harassment wave after reload |
| AI difficulty A/B probe | `pf_sovereign_ai_difficulty_ab_probe.py` compares standard, booming, and hard over an extended branch fixture, proving expansion targets, harassment frequency, target priority, and profile-driven militia/archer composition diverge as intended |
| AI composition strategy probe | `pf_sovereign_ai_composition_strategy_probe.py` verifies profile-specific strategy research, target unit mixes, profile attack-role priorities, and composition attack launch for standard, booming, and hard |
| AI composition counter probe | `pf_sovereign_ai_composition_counter_probe.py` verifies standard, booming, and hard army plans against favorable and unfavorable enemy compositions, including expected wins, expected losses, and damage-bonus rule checks |
| AI difficulty balance save/load probe | `pf_sovereign_ai_difficulty_balance_save_load_probe.py` verifies longer profile comparisons, save-point snapshots, post-snapshot continuation, balance tuning, compact state tagging, and native `.pfsave` reload of the A/B report |
| AI match-length adaptation probe | `pf_sovereign_ai_match_length_adaptation_probe.py` verifies profile-specific opening economy duration, economy-vs-military transition timing, expansion timing, preferred attack-unit counts, and attack launch timing for standard, booming, and hard |
| AI attrition recovery probe | `pf_sovereign_ai_attrition_recovery_probe.py` verifies failed attack detection, live-pressure defense, survivor regrouping, replacement training, military-over-economy pressure scoring, repeated failed-push escalation, pressure-triggered `ranger_fletching` research before the larger second relaunch, successful outcome tracking, post-success expansion, and attack relaunch after casualties |
| AI multi-front probe | `pf_sovereign_ai_multi_front_probe.py` verifies disjoint unit assignments for defense, harassment, and building attack fronts, plus separate movement toward each front in Metal |
| AI skirmish soak probe | `pf_sovereign_ai_skirmish_soak_probe.py` verifies a larger AI-vs-player fixture with player production, enemy economy income, disjoint multi-front activity, attrition recovery, pressure tech, relaunch, combat damage, victory progress, and sustained Metal ticks |
| AI large-army scale probe | `pf_sovereign_ai_large_army_scale_probe.py` verifies 96/125/250/500 units per side, mass movement or attack-move orders, movement distance, active Walk/Attack animations, representative combat/projectile-heavy damage, sustained Metal ticks, sampled p50/p95/max wall-clock budgets, soft budget warnings, and optional wide-zoom proof captures; `profile_sovereign_large_army_scale.sh` records an attach-mode Time Profiler trace and hotspot summary for the 1000-unit gate |
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
    decisions, deterministic build-order planning, priority target selection,
    tactical threat response, scouting route waypoints, threat memory,
    macro-strategy expansion, map-control scoring, difficulty-tuned
    attack/retreat timing, branching defense/harassment behavior, three-base
    expansion sequencing, difficulty-specific personality/cadence tuning,
    branch-state save/load continuation, difficulty A/B behavior comparison,
    profile-driven harassment composition, strategy research, target unit-mix
    branching, composition counter checks, longer difficulty balance
    save/load coverage, match-length opening-to-military transition timing,
    failed-attack attrition recovery under live pressure, repeated attrition
    outcome tracking, pressure-triggered tech pacing, multi-front army control,
    a larger AI-vs-player skirmish soak, a first 192-unit scale soak, and a
    longer staged session/save-load probe are in place.
11. Performance, Retina clarity, and HD/4K polish. The current Metal scale
    floor includes a green 500-unit regression and a green 1000-unit
    exploratory gate with Time Profiler evidence. ClearPath fallback policy and
    animated mesh affine assembly have been tuned, and the Metal skinned-mesh
    cache now avoids duplicate CPU skinning across shadow/main passes for
    cacheable animated draws. Shadow-side animated casters now batch by shared
    render data while the owner-id shadow diagnostic path remains per-caster.
    The first env-gated GPU-skinning prototype now moves batched animated
    main-pass and shadow-pass work to Metal for the 1000-unit scale gate,
    lowering the opt-in p95 from about 181 ms to about 69 ms. It is not default
    yet. A follow-up ClearPath dense-policy probe rejected broader fallback
    batch defaults as unstable, while a GPU-skinning capture-proof run saved
    before/engage/soak/wide-zoom evidence. Remaining work is visual parity and
    longer-session hardening before promotion, with ClearPath `inside_pcr` and
    no-solution fallback pressure still the leading scale lane.
