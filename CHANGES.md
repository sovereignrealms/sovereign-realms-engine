# Sovereign Realms Changes

## 2026-05-07

- Documented the single-repo early development model: engine, editor,
  Sovereign game package, and world packs stay together until the first
  vertical slice stabilizes.
- Replaced the upstream-first README with a Sovereign Realms README that keeps
  upstream attribution but removes misleading personal license/contact language.
- Added `games/` as the contribution boundary for independent world/game packs.
- Added `docs/modding/` notes for world-pack format and per-pack licensing.
- Added `games/example_world/` as a minimal MIT-licensed example pack.
- Extended publish preflight checks to require the world-pack documentation and
  example pack boundary.
- Added the first deterministic Sovereign AI build-order planner and Metal
  probe for resource recovery, house construction, wave training, priority
  target selection, combat/victory progress, and save/load continuation.
- Added tactical Sovereign AI scout/threat response coverage for nearby enemy
  classification, defender training, defense launch, and defender motion in
  Metal.
- Added scouting routes and threat memory so the AI can remember last-known
  threats after visibility is lost and adapt defender training toward the
  remembered position.
- Added AI memory save/load coverage so remembered threats survive native
  `.pfsave` reload and drive outnumbered regroup, resource recovery, house
  construction, defender training, and remembered-position response.
- Added adaptive AI strategy coverage: scheduled scout refresh, remembered
  military-threat unit choice, archer counter-training, regroup, response, and
  counterattack launch in Metal.
- Added macro AI strategy coverage: difficulty profiles, economy-vs-military
  weighting, second-base expansion, strategic archer training, and attack
  movement in Metal.
- Added map-control AI strategy coverage: named control-point evaluation,
  difficulty-tuned retreat/attack timing, resource/population recovery, archer
  counter-training, and map-control attack movement in Metal.
- Added branching AI strategy coverage: defense/harassment split decisions,
  multi-base expansion to three town centers, harassment training, and separate
  defense/harass movement in Metal.
- Added AI personality/cadence persistence coverage: difficulty-specific
  personality fields, harassment frequency controls, compact branch state,
  native `.pfsave` reload, cooldown hold, and second harassment-wave
  continuation in Metal.
- Added difficulty A/B skirmish evidence: standard, booming, and hard now
  prove distinct expansion targets, harassment frequency, target priority, and
  profile-driven militia/archer composition in Metal.
- Added strategic tech/unit-composition branching: profile-specific strategy
  research now drives militia, mixed, or archer army plans with matching attack
  target priorities in Metal.
- Added composition counter checks: standard, booming, and hard army plans now
  prove expected wins and losses against favorable and unfavorable enemy
  compositions in a native Metal probe.
- Added difficulty A/B save-load balance coverage: longer standard, booming,
  and hard branch reports now snapshot at a save point, continue from planner
  snapshots, and persist through native `.pfsave` reload.
- Added match-length build-order adaptation coverage: standard, booming, and
  hard now prove profile-specific opening economy duration, economy-to-military
  transition timing, expansion timing, preferred attack-unit counts, and attack
  launch timing in Metal.
- Added attrition recovery AI coverage: lost attack units are removed from the
  AI roster, live base pressure forces military priority over economy, and the
  hard profile now proves defense, regroup, retraining, and attack relaunch in
  Metal.
- Extended attrition AI coverage to repeated outcomes: a second failed push now
  escalates the relaunch army size, while a successful relaunch shifts the
  planner back toward economy and expansion.
- Added pressure-driven tech pacing to the attrition AI path: after repeated
  failed pushes, the hard profile now researches `ranger_fletching` before the
  next larger relaunch instead of only rebuilding unit count.
- Added multi-front army-control coverage: the AI can now assign disjoint
  militia/archer groups to home defense, villager harassment, and building
  attack fronts, with each front verified moving separately in Metal.
- Added larger AI-vs-player skirmish soak coverage: a composed Metal fixture
  now verifies player production, enemy economy income, multi-front activity,
  repeated attrition recovery with pressure tech, combat damage, conquest
  victory progress, and sustained runtime ticks together.
- Hardened the first larger-army scale soak to 96 units per side: 192 units
  are spawned, mass-moved, sampled for movement/animation activity, checked
  for representative combat damage, and kept alive through sustained Metal
  runtime ticks.
- Fixed the dense projectile-heavy 192-unit attack-move guard: near-vertical
  projectile shots now fail cleanly instead of producing NaN velocity math, and
  the 96-units-per-side attack-move soak now passes in Metal.
- Added larger-army budget telemetry and raised the attack-move scale evidence:
  250-unit and 500-unit mixed infantry/archer soaks now pass with phase timing,
  wall-time-per-tick, and per-100-unit budget output.
- Added a profiler-friendly 1000-unit exploratory scale gate with wide-zoom
  proof captures, p50/p95/max tick budget summaries, soft budget warnings, and
  classification hooks for future bottleneck reports.
- Added an attach-mode Instruments Time Profiler wrapper for the 1000-unit
  scale gate. The first captured trace exits cleanly and points the next
  optimization slice at ClearPath collision-avoidance geometry and Metal
  skinned-animation assembly.
- Reduced duplicate ClearPath collision-avoidance geometry work by intersecting
  each velocity-obstacle ray pair once instead of twice. The 500-unit
  attack-move regression still passes and the 1000-unit exploratory gate now
  clears the 500 ms soft p95 tick budget without warnings.
- Captured the post-change 1000-unit Time Profiler trace. `compute_vo_xpoints`
  inclusive samples dropped sharply, leaving remaining `inside_pcr` checks and
  `append_skinned_anim_mesh` as the next scale tuning candidates.
- Reduced Metal skinned-animation assembly cost by precomposing model and skin
  matrices once per animated entity before CPU-side batch assembly. The
  1000-unit profiled p95 tick time drops to roughly 351 ms with no soft budget
  warnings.
- Added env-gated ClearPath diagnostics and scale-probe reporting for
  `inside_pcr`, ray-pair candidate counts, fallback removals, projection
  candidates, and no-solution attempts. Disabled diagnostics keep the 500-unit
  and 1000-unit no-stats scale gates passing.
- Added a guarded ClearPath fallback policy: dense retries now remove up to
  four furthest neighbours only when at least 40 neighbours remain, cutting
  repeated no-solution work in the 1000-unit scale gate while preserving the
  500-unit regression gate.
- Refreshed the 1000-unit attach-mode Time Profiler after the guarded fallback
  policy. The trace now points first at Metal skinned-animation batch assembly,
  with ClearPath `inside_pcr` / `compute_vo_xpoints` still the second major CPU
  lane. Disabled ClearPath diagnostics no longer leave a helper-call hotspot in
  normal profiles.
- Tuned the Metal animated-mesh assembly loop to use direct column-major affine
  point/vector transforms after world-skin matrix precomposition, removing
  `PFM_Mat4x4_Mult4x1` from the 1000-unit profile hot list. The 500-unit and
  1000-unit gates still pass, but `append_skinned_anim_mesh` remains the
  dominant CPU hotspot and needs a structural follow-up.
- Added a per-frame Metal skinned-mesh cache so animated vertices assembled for
  the shadow pass can be reused by the main pass when the same UID/model pair is
  drawn again. The 1000-unit profiled p95 tick drops from 356.499 ms to
  193.387 ms, with the 500-unit regression green at 90.064 ms p95.
- Cleaned up ClearPath candidate math by replacing per-test vector
  normalization in `inside_pcr()` with an equivalent squared-length determinant
  check and by using a ClearPath-local cross-product ray intersection in
  `compute_vo_xpoints()`. The 500/1000-unit scale gates stay green, and generic
  `C_RayRayIntersection2D()` no longer appears in the 1000-unit hot list.
- Fixed a dense-projectile crash in trail spawning: projectile trail playback
  now checks sprite descriptor flags rather than collision behavior flags, whose
  bit values overlap.
- Batched Metal animated shadow casters by shared render data while preserving
  per-caster owner-id shadow diagnostics. The 1000-unit no-stats gate remains
  green and the p95 tick baseline improves from roughly 196 ms to about 181 ms.
- Added an opt-in `PF_METAL_GPU_SKINNING=1` Metal animated rendering prototype
  for batched main-pass and shadow-pass skinning. The 500-unit and 1000-unit
  gates stay green, the 1000-unit opt-in p95 drops to roughly 69 ms, and the
  profiler now points back to ClearPath as the leading scale lane.
- Probed ClearPath dense fallback policy against the GPU-skinning baseline and
  rejected broader default batch-removal settings after verification showed
  unstable movement/budget tradeoffs. Added GPU-skinning capture-proof evidence
  for before/engage/soak/wide-zoom large-army scenes.

## 2026-05-06

- Expanded the Sovereign runtime scaffold into verified Metal probes for
  factory spawning, economy, production/population, age/technology,
  combat-counter rules, projectile/VFX alignment, save/load, skirmish flow,
  editor scenario authoring, metadata persistence, and AI decision depth.
- Added the first packaged-editor Sovereign authoring path for sidecar scenario
  metadata, player starts, resources, placed objects, setup profiles, resource
  presets, validation navigation, import/reload, and larger-map stress checks.
- Added `scripts/macos/verify_sovereign_publish_ready.py` to make
  `sovereignrealms/sovereign-realms-engine` publishing checks repeatable.
- Updated artifact ignore rules for local save files and Metal capture traces.

## 2026-05-05

- Added the Sovereign Realms planning and bootstrap scaffold for building an
  AoE2-like RTS vertical slice on top of Permafrost Engine.
- Added a dedicated `scripts/sovereign/` package skeleton for data-driven game
  definitions and future gameplay systems.
- Added a dedicated `assets/sovereign/` layout document for original game
  assets and per-asset licensing records.
- Added PFOBJ asset validation tooling under `tools/asset_validation/`.
- Preserved the upstream GPLv3 with special linking exception as the default
  engine license until an alternate grant is received from the upstream
  copyright holder.
