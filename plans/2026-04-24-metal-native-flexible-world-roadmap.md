# Metal-Native Flexible-World Roadmap

Created: 2026-04-24
Updated: 2026-05-01

## Directive (2026-04-26): GL stays as permanent parity reference

User directive: the OpenGL backend is **NOT** to be deleted. Metal becomes the gameplay default, but the GL build path is preserved indefinitely as a parity-comparison reference. The `RENDER_BACKEND=OPENGL` build target, the `PF_RENDER_BACKEND_*` guards, the `gl_*.c` implementations, and `scripts/macos/capture_visual_parity.sh` all stay live so that any future Metal regression can be A/B'd against a known-good GL render.

Historical note: when this directive was written, Slice 9 — the combat cluster cobble shadow residual at 1.82× ratio — was the key parity blocker. Later slices closed the shadow/material residuals, but the GL reference remains intentionally preserved so future Metal regressions can still be A/B'd against a known-good render.

The PBR/HD-graphics redesign (Cook-Torrance, AI-generated PBR maps, optional mesh redesign) still happens, but Phase 1 is revised: drop only the *default-target* assumption (Metal becomes the default build), not the GL backend itself. See `a.md` §25–§26 for the pivot history.

## Summary

This plan consolidates the Metal/OpenGL replacement work, the Age of Empires II: Definitive Edition Enhanced Graphics Pack clarity reference, the openage extensibility reference, and the longer-term HD/4K flexible-world graphics goal.

The immediate implementation track remains the Metal-native replacement of OpenGL. The HD/4K graphics platform is a post-port milestone: it should guide architecture choices now, but it should not block making Metal the default once functional and visual parity gates are met.

Related Apple sample-code notes: [2026-04-25 Apple Metal migration sample notes](2026-04-25-apple-metal-migration-sample-notes.md).
Related OpenGL-on-Metal reference notes: [2026-04-25 MGL OpenGL-on-Metal notes](2026-04-25-mgl-opengl-on-metal-notes.md).
Related current capability audit: [2026-04-30 macOS Metal capability equivalence audit](2026-04-30-macos-metal-capability-equivalence-audit.md).

## Milestone Chain

1. `Metal visual and smoothness parity`
   - Match the current OpenGL Apple Silicon baseline for runtime gameplay rendering.
   - Close color, gamma, terrain/material, fog, shadow, water, skybox, sampler/filtering, and frame-pacing differences using fixed-camera captures.
2. `Metal default`
   - DONE for the Apple Silicon runtime build: `make pf/run PLAT=MACOS_ARM64`
     now defaults to Metal.
   - Keep OpenGL available as the explicit parity/reference backend.
3. `OpenGL removal`
   - DONE for the first direct link decoupling: the default Metal Apple Silicon
     binary no longer compiles `backend_gl.c` or links `OpenGL.framework`.
   - Split or rename the remaining legacy `R_GL_*` render-command API and
     OpenGL helper-object dependencies.
   - Retire OpenGL-only assumptions from build/config/runtime paths after the Metal renderer owns the required game and editor flows.
4. `Metal-native HD/4K flexible-world graphics platform`
   - Add the higher-fidelity rendering and content pipeline needed for HD/4K-ready worlds, larger maps, dense vegetation, richer buildings, careful combat effects, and character-level zooms.
   - Preserve support for different worlds, rule systems, factions, art directions, and combat styles.

## Reference Guidance

- Age of Empires II: Definitive Edition Enhanced Graphics Pack is a clarity/readability benchmark, not a clone target.
  - Useful goals: sharper HD/4K assets, readable units at close zoom, large battlefield density, crisp terrain, strong building silhouettes, dense forests, and careful battlefield effects.
  - Pitfalls to avoid: input lag, fuzzy or soft visuals, over-smoothed motion that feels unnatural, difficult selection/click targets, and combat effects that lose fidelity.
- openage is an extensibility and modding architecture reference, not an implementation to copy wholesale.
  - Useful ideas: data-driven content, asset conversion/modpack thinking, configurable unit behavior, scripting hooks, and separation between simulation, renderer, input/presenter, events, world updates, and networking.
  - Non-goal: Age of Empires compatibility, rules, assets, civilizations, or exact gameplay replication.
- MGL is an OpenGL-on-Metal internals reference, not a dependency target.
  - Useful ideas: treat OpenGL as mutable state resolved at draw boundaries, make implicit GL state explicit in Metal pipeline/encoder state, and validate each renderer path with functional tests and fixed-camera image evidence.
  - Non-goal: shipping Permafrost through a generic OpenGL compatibility layer; the endpoint remains a native Metal renderer.

## Engine Platform Principles

- Keep simulation/game rules independent from renderer details.
- Keep renderer responsibilities focused on drawing world state, animation/material data, visibility, camera state, UI, and effects.
- Keep world/rule variation in scripts, data, maps, scenes, and assets wherever practical.
- Treat HFMP as one possible world built on the engine, not the engine's only target.
- Maintain the map/scene/object split as a practical content boundary for larger worlds.

## HD/4K Graphics Platform Goals

- At least HD output quality, with 4K-ready clarity as the long-term benchmark.
- Character-level zooms where units, banners, armor, weapons, animations, and health/combat feedback remain readable.
- Wide zoom-out that shows large map areas, dense armies, forests, buildings, terrain variation, and battle state without collapsing into visual noise.
- Better terrain richness: material blending, biome variation, road/cobble/grass/dirt transitions, cliffs, water edges, and large-map readability.
- Better vegetation and forests: varied tree/plant assets, dense stands, readable cutouts, depth/occlusion behavior, and performance-friendly batching.
- Better buildings: crisp silhouettes, readable faction identity, damage/burning states, construction states, and zoom-readable details.
- Careful combat rendering: arrows, fireballs, smoke, flames, impact effects, projectile trails, corpses/debris, and siege/burning feedback must remain readable without overwhelming army control.
- Metal-native performance should support larger maps and dense scenes without depending on OpenGL fallback paths.

## Active Parity Slice Queue (2026-04-25)

Run as a sequence; each slice is gated by a numerical or visual acceptance
test against a fresh `capture_visual_parity.sh` artifact, and may be
reverted independently. Working notebook: [a.md](../a.md).

1. **Shadow NDC-z parity** — DONE (2026-04-25). Metal `shadow_factor` and
   `mesh_shadow_factor` now use raw NDC z (`light_space_pos.z / w`) for
   the depth comparison while still mapping xy with `* 0.5 + 0.5` for
   sampling. Lit-terrain pixel ratio went from uniform 0.55× to ~1.00×.
   Artifact: `visual_parity_captures/2026-04-25-metal-shadow-ndc-z-fix/`.
2. **UI texpath images / inventory icons** — DONE (2026-04-25). Metal UI
   path now loads and binds textures referenced by
   `NK_COMMAND_IMAGE_TEXPATH` instead of dropping them. Adds a
   path → MTLTexture cache (`s_ui_texpath_cache`), a one-shot pending
   binding (`s_pending_ui_texture`), and per-command texture binding in
   `render_ui_draw_list`. Artifact:
   `visual_parity_captures/2026-04-25-metal-ui-texpath-fix/`.
3. **Unit appearance delta** — PARTIAL (2026-04-25). Bulk units
   now at ~1.00 ratio against GL across multiple cluster samples.
   One localized pocket near the bottom-center of the lit zone
   (3456×2234 px coords ~2050–2150, 1650–1750) shows Metal 1.32–
   1.78× brighter than GL, uniform across RGB. Tested NDC-z-clipping
   hypothesis with a Metal-friendly orthographic shadow projection;
   produced bit-identical output, hypothesis rejected. Static-mesh
   shadow path is the leading suspect, queued as follow-up. Not
   blocking remaining slices. See [a.md](../a.md) §10 for full record.
4. **Water shoreline + color delta** — DONE (2026-04-25). Removed the
   `water_state != 0u` hand-tuned blue/foam override from Metal's
   `terrain_fragment`. GL's terrain shader has no equivalent branch:
   water tiles render as terrain in both backends, and the standalone
   water surface mesh handles translucent scene-blended water on top.
   Metal water now shows a soft gray pool with terrain visible
   through, matching GL. Numeric ratios moved from saturated-blue
   (>1.5× B) to 0.85–1.06 across R, G, B at the bulk of water surface
   samples. Artifact:
   `visual_parity_captures/2026-04-25-metal-water-override-removed/`.
5. **"Rendering quality very less"** — CLOSED, NO BUG (2026-04-25).
   Two objective measurements (edge max-luminance-jump, local 61×61
   stdev) both report Metal **smoother** than GL across multiple
   sample points. GL renders without MSAA
   (no `SDL_GL_MULTISAMPLE*` set in `backend_gl.c`), while Metal had
   been using 4x MSAA on scene pipelines. The parity harness now uses
   `PF_PARITY_MODE=1` to force Metal to 1x so captures do not silently
   compare OpenGL no-MSAA against Metal 4x MSAA. The player-facing Metal
   default is back to 4x after item 9, with `PF_METAL_MSAA_SAMPLES`
   still available for explicit 1/2/4/8x override. The "jagged edges in
   Metal" perception was the opposite of the objective measurement; the
   later HD/4K renderer can choose higher-quality AA intentionally. See
   [a.md](../a.md) §13, §19, and §52 for data and follow-up.

6. **Animated mesh skin-weight normalization** — DONE (2026-04-25).
   Knight `vw` rows have weights summing to 0.5/1.9/3.0/4.0 in places;
   GL normalized in shader (`weight / tot_weight`), Metal CPU skinning
   was applying raw weights. Fixed in both
   `render_skinned_mesh_draw` and `append_skinned_anim_mesh`. After
   this, bulk lit-terrain pixel ratios in combat now sit at exact
   parity (1.00, 1.00, 1.00) and the helmet/silhouette mismatch
   collapsed. See [a.md](../a.md) §18.
7. **Capture harness SDL pump stall** — UNREPRODUCED (2026-04-26).
   Codex reported the OpenGL probe stalling in
   `SDL_PumpEventsInternal` before frames advance. Fresh paired-
   capture runs (`scripts/macos/capture_visual_parity.sh`) completed
   cleanly in foreground bash on 2026-04-26. The probe hardening
   (timeouts on osascript / swift / screencapture, full-screen
   fallback) is in place. Treating as transient/environmental for
   now; if it returns, drop the per-scene `_activate_own_window`
   AppleScript call from
   `scripts/macos/pf_visual_parity_probe.py:_capture` (it is not
   needed by `screencapture -l<window_id>` which captures by Quartz
   window ID regardless of focus stacking). Follow-up on 2026-04-26:
   the combat capture target is now deterministic because the visual
   parity probe pauses simulation before scene construction, and
   `capture_visual_parity.sh` now fails fast if OpenGL and Metal scene
   camera positions diverge by more than 0.1 world units. Artifact:
   `visual_parity_captures/2026-04-26-combat-deterministic/`. See
   [a.md](../a.md) §22.
8. **Static-mesh self-shadow parity (cliff face)** — DONE
   (2026-04-26). The winning hypothesis was a Metal shadow-pass
   front-facing winding mismatch. Xcode trace
   `visual_parity_captures/2026-04-26-cliff-shadow-trace/cliff-overview.gputrace`
   confirmed the first encoder was the shadow depth pass and that it
   used `setCullMode:Front` with clockwise front-facing winding before
   the fix. Changing only the shadow pass to
   `MTLWindingCounterClockwise` moved overview (1700, 900) from
   0.58, 0.58, 0.57 to 1.04, 1.04, 1.04. Artifact:
   `visual_parity_captures/2026-04-26-cliff-shadow-fix/`. See
   [a.md](../a.md) §21 for trace notes and ratios.
9. **Ship-default MSAA flip** — DONE (2026-04-27).
   `METAL_DEFAULT_MSAA_SAMPLES` is now 4 for the player-facing Metal path,
   `PF_PARITY_MODE=1` forces 1x for pixel/reference captures, and
   `PF_METAL_MSAA_SAMPLES` accepts explicit `1`, `2`, `4`, or `8` with
   device-support fallback to the nearest lower supported sample count.
   `pf.get_render_info()` now reports `msaa_samples`, so harness summaries
   can prove whether a run used the default smooth path or the parity path.
   Verification: normal Metal gameplay smoke reports `msaa_samples=4`,
   parity-mode Metal gameplay smoke reports `msaa_samples=1`, and
   `visual_parity_captures/2026-04-27-msaa-parity-gate/` keeps the
   five-scene fixed-camera parity capture at `msaa_samples=1` with cameras
   matched. See [a.md](../a.md) §52.
10. **Combat localized healthbar/material residual** — PARTIAL
    (2026-04-26). Full-pause capture is not usable because
    `G_PAUSED_FULL` stops the probe's UI/capture loop. The probe now
    resets animated entities to the start of their current clips after
    pausing and records `VISUAL_PARITY_ANIM_FREEZE count=59`, but this
    did not change the combat residual. The largest half=2 hot strip
    was confirmed as a Metal healthbar-outline mismatch and fixed by
    matching GL's effective 2 px border, outer-UV-space fill cutoff,
    and bottom-half darkening. Point (2074,1370) improved from
    2.40,3.80,2.54 to 1.11,1.28,1.08, but the half=60 block remains
    about 1.24,1.21,1.26. Next target: skinned/static mesh
    material-lighting or composition around the knight/cobblestone
    cluster, not broad terrain tone. Artifact:
    `visual_parity_captures/2026-04-26-combat-residual-fix/`. See
    [a.md](../a.md) §23.
11. **Lossless shadow dump + hidden-static caster policy + owner-map follow-up** — DONE
    (2026-04-26). Added float32 GL/Metal shadow dumps
    (`PF_GL_SHADOW_DUMP_F32_PATH`, `PF_METAL_SHADOW_DUMP_F32_PATH`),
    optional RGBA8 previews, caster-count logging, full-pass dump
    filters, and `scripts/macos/compare_shadow_depth_dumps.py`.
    Full-pass evidence shows GL and Metal shadow maps differ
    structurally, but terrain winding and GL-style depth-remap
    diagnostics were rejected because they either did not move the
    combat residual or regressed known-good control points. New
    hypothesis tested: explored-but-currently-fogged non-movable/static
    entities may be valid `light_visible` casters even when not
    camera-visible. The code now defaults to visible-only shadow
    casters; `PF_SHADOW_CASTERS_INCLUDE_UNREVEALED_STATIC=1`
    restores the old hidden-static behavior for A/B diagnosis. This
    closes the reported startup symptom where broad hidden-static
    shadows appear and then vanish after camera movement. Added the
    Metal owner-id shadow map as the next diagnostic:
    `PF_METAL_SHADOW_OWNER_DUMP_U32_PATH` emits a 2048x2048 `uint32`
    owner texture, `PF_SHADOW_CASTER_MANIFEST_PATH` emits UID/kind/
    flags/position CSV, and
    `scripts/macos/inspect_shadow_owner_dump.py` resolves shadow
    texels to caster UIDs. It did not move the combat cluster residual,
    as expected for a diagnostic-only slice. Added the Metal main-pass
    screen-pixel probe (`PF_METAL_SHADOW_SCREEN_PROBE`) so a bad PNG
    pixel can be mapped to Metal fragment coordinates, receiver world
    position, shadow texel, sampled owner UID, and depth comparison.
    For combat PNG `(2074,1500)`, the first Metal receiver witness
    mapped to fragment `(1037,750)`, shadow texel `(1115,1187)`,
    `owner=0`, and `closest_depth=1.0`, proving Metal was sampling
    clear shadow depth at the residual. Filtered main-pass dumps then
    identified OpenGL's caster as static UID `148`. The final fix flips
    Metal shadow receiver Y lookup to match Metal texture-space
    sampling and sets shadow-pass winding per caster type: terrain
    remains counter-clockwise for the cliff fix, while static/skinned
    meshes use clockwise to match their main-pass convention. Artifact:
    `visual_parity_captures/2026-04-26-shadow-yflip-winding-split/`.
    Combat `(2074,1500)` moved to `1.01,1.01,1.01` at half=30 and
    `1.03,1.03,1.03` at half=2. See [a.md](../a.md) §28, §29, §30,
    §31, and §32.
12. **Deterministic time-of-day lighting scaffold** — DONE
    (2026-04-26). Added script-space fixed phases
    `baseline`, `morning`, `afternoon`, `evening`, and `night`.
    Baseline exactly preserves the old lighting. The parity harness
    defaults to `baseline` and disables dynamic movement unless
    overridden with `PF_RTS_TIME_OF_DAY_PHASE`,
    `PF_RTS_TIME_OF_DAY_DYNAMIC`, and `PF_RTS_DAY_LENGTH_SEC`.
    Fixed-phase captures for morning/afternoon/evening/night all
    produced matching GL/Metal camera and lighting summaries. See
    [a.md](../a.md) §28.
13. **Metal minimap fog-of-war parity** — DONE
    (2026-04-26). OpenGL bakes a full minimap texture but applies
    `visbuff` in `shaders/fragment/minimap.glsl` at HUD draw time:
    unexplored tiles are black, fogged explored tiles are half-bright,
    and visible tiles are full-bright. Metal was drawing the baked
    minimap through the generic UI texture path, which skipped the fog
    mask and made the minimap look revealed. Added a dedicated Metal
    minimap display pipeline that binds `s_fog_buffer` and reproduces
    the OpenGL visibility rules. Also added
    `scripts/macos/pf_metal_minimap_fog_probe.py`, which stages friendly
    units across spread-out pathable waypoints and captures minimap
    exploration evidence. Artifacts:
    `visual_parity_captures/2026-04-26-minimap-fog-metal/` and
    `visual_parity_captures/2026-04-26-minimap-fog-explore/`. See
    [a.md](../a.md) §33. Follow-up audit (2026-04-27) matched the
    OpenGL bake/update contract more closely by disabling live fog tint
    while Metal renders terrain into the baked minimap texture, leaving
    fog application in the final HUD minimap shader. Latest artifact:
    `visual_parity_captures/2026-04-27-minimap-bake-fog-clear/`. See
    [a.md](../a.md) §38.
14. **Rocks-edge fogged water composition parity** — DONE
    (2026-04-26). The remaining rocks `(1700,900)` watch item was
    reclassified from shadow to fogged water composition after crop
    evidence showed the sampled pixels sit on the water/fog boundary.
    Added `PF_RENDER_WATER_MOVE_FACTOR` so parity captures can pin
    water animation phase, then fixed the real Metal mismatch: GL
    computes water `view_dir` and `light_dir` per vertex and
    interpolates them, while Metal had been recomputing normalized
    directions per fragment. Metal now matches GL's water lighting data
    flow. Artifact:
    `visual_parity_captures/2026-04-26-rocks-water-dir-parity-final/`.
    Rocks `(1700,900)` is now `1.02,1.01,1.02` at half=60 and
    `0.98,0.99,1.00` at half=2. Re-validated after the skybox-fed
    water-reflection fix with the skybox-enabled GL reference:
    `visual_parity_captures/2026-04-27-post-reflection-allscene-skybox-validation/`,
    where rocks `(1700,900)` is `1.02,1.01,1.01` at half=60 and
    `1.00,1.00,1.00` at half=2. See [a.md](../a.md) §34 and §37.
15. **Main skybox parity + skybox-reflection follow-up** — DONE
    (2026-04-26). Added optional skybox coverage to the fixed-camera
    parity probe through `PF_VISUAL_PARITY_INCLUDE_SKYBOX=1`, and made
    the Apple Silicon OpenGL skybox reference explicitly opt-in via
    `PF_GL_ENABLE_APPLE_ARM64_SKYBOX=1` so ordinary parity captures stay
    on the long-running no-skybox Apple GL baseline. Main-frame skybox
    samples are now at exact GL/Metal parity in the skybox scene.
    The same capture exposed the next issue: skybox-fed water reflection
    was darker in Metal around water `(1700,900)`, about
    `0.70,0.73,0.70` at half=60. Added GL/Metal raw reflection texture
    dumps, proved Metal was sampling the reflection target's clear color
    because the scaled Metal skybox was 10x too small, and fixed the
    scaled skybox model scale to match Metal's `+/-1` cube vertices.
    Artifact:
    `visual_parity_captures/2026-04-27-water-reflection-scale-fix/`.
    Water `(1700,900)` is now `1.00,0.99,1.00` at half=60. See
    [a.md](../a.md) §35 and §36.
16. **Broader terrain/material/water tone audit** — BROAD TONE CLOSED,
    localized residuals split out
    (2026-04-27). Matched Metal water refraction offscreen shadow state
    to GL while keeping reflection shadows disabled. The skybox-enabled
    fixed-camera capture now shows median luma ratio at ~1.000 across
    overview, water, rocks, and combat central gameplay regions:
    `visual_parity_captures/2026-04-27-water-refraction-shadow-parity/`.
    The remaining outliers were localized static-prop cases, not a
    global terrain/water tone wash: rock material highlights around
    water `(2500,780)` / rocks `(2596,1020)`, plus smaller
    static-shadow composition blocks that moved under shadow
    diagnostics. See [a.md](../a.md) §39.
17. **Static-prop high-specular normal parity** — DONE
    (2026-04-27). The localized high-specular rock highlight outliers
    were traced to a mesh-lighting state mismatch: Metal normalized the
    interpolated static mesh normal before specular lighting, while the
    OpenGL textured mesh fragment path uses the interpolated normal
    directly. A broad GL-style normal change fixed rocks but regressed
    pine/static foliage near the staged water camera, so the landed fix
    keeps diffuse lighting normalized and uses the OpenGL-style
    interpolated normal only for opaque high-specular static material
    specular. Water `(2500,780)` moved from `1.12,1.12,1.14` to
    `1.05,1.05,1.05`, rocks `(2596,1020)` moved from
    `1.10,1.10,1.14` to `1.04,1.04,1.04`, combat controls stayed
    stable, and the known water-stage pine/static foliage watch point
    stayed at `0.95,0.95,0.92`. Artifact:
    `visual_parity_captures/2026-04-27-static-prop-highspec-normal-parity/`.
    See [a.md](../a.md) §40.
18. **Terrain shadow Poisson Y parity** — DONE
    (2026-04-27). The remaining rocks static-shadow composition
    residuals were traced to terrain shadow sampling rather than
    material tone. Metal flips shadow-map Y when projecting to texture
    space, but the terrain Poisson offsets still used OpenGL's Y signs.
    Flipping the four Poisson Y signs in Metal's terrain `shadow_factor`
    closed rocks `(2116,1164)` from `1.09,1.09,1.08` to
    `1.00,1.00,1.00` and rocks `(2212,780)` from `0.93,0.93,0.93` to
    `1.00,1.00,1.00`, while water and combat controls stayed stable.
    Artifact:
    `visual_parity_captures/2026-04-27-shadow-poisson-yflip-parity/`.
    See [a.md](../a.md) §41.
19. **Minimap dynamic water-update scissor pass** — FIRST PASS DONE
    (2026-04-27). Metal now mirrors OpenGL's per-chunk minimap update
    scissor when redrawing a changed chunk into the loaded minimap
    texture, with GL-bottom-left to Metal-top-left Y conversion. The
    dynamic probe also exposed and fixed a hidden Metal tile-update
    crash: `R_GL_TileUpdate` reached an unconditional `GL_ASSERT_OK()`
    after CPU-side Metal terrain vertex edits. The probe now supports
    `PF_MINIMAP_FOG_PROBE_DYNAMIC_WATER=1` plus optional target
    chunk/tile env vars for larger-map fixtures. Full exploration plus
    dynamic water update passes in
    `visual_parity_captures/2026-04-27-minimap-fog-dynamic-water-scissor-full/`.
    See [a.md](../a.md) §42.
20. **Terrain splat blending parity** — FIRST PASS DONE (2026-04-27).
    Metal now mirrors OpenGL's map-level `num_splats` path by generating the
    same procedural 1024x1024 float splat mask, maintaining a 256-entry
    base-material to accent-material table, and applying the OpenGL splat
    blend formula inside normal and adjacency-blended terrain texture sampling.
    The visual parity probe now supports
    `PF_VISUAL_PARITY_SPLAT_PAIRS=base:accent[;...]` for opt-in splat fixtures
    on the current demo map and future larger/custom maps. Verified artifacts:
    `visual_parity_captures/2026-04-27-terrain-splat-dormant-baseline/`,
    `visual_parity_captures/2026-04-27-terrain-splat-pair-0-1/`, and
    `visual_parity_captures/2026-04-27-terrain-splat-pair-0-9/`.
    See [a.md](../a.md) §43.
21. **Terrain-rich larger/custom-map fixture** — FIRST PASS DONE (2026-04-27).
    Added `scripts/macos/pf_terrain_custom_map_parity_probe.py` and
    `scripts/macos/capture_terrain_custom_map_parity.sh`. The probe generates
    a deterministic 10x10 in-memory map with multi-biome materials, splats, a
    cliff/ridge, road/cobble transitions, a depressed basin, and a dynamic tile
    update, then verifies matching OpenGL/Metal map metadata, updated-tile
    metadata, and camera positions. Final artifact:
    `visual_parity_captures/2026-04-27-terrain-custom-map-final/`. Stable
    terrain, splat, and tile-update controls are at 1.00, while the depressed
    basin exposes the next localized terrain side/depression/material residual.
    See [a.md](../a.md) §44.
22. **Custom-map minimap bake projection/map-state parity** — FIRST PASS DONE
    (2026-04-27). The custom-map fixture showed that the biggest apparent
    terrain/material residual was actually minimap contamination: Metal's
    minimap bake was using a perspective projection after an orthographic
    camera tick, lacked GL-to-Metal orthographic depth remap, and did not refresh
    map uniforms/water-mask state during the standalone minimap bake/update
    passes. Metal now uses an explicit orthographic minimap projection, correct
    Metal depth mapping, per-minimap map-state setup, and minimap water masking.
    Stable main-world terrain, splat, and dynamic tile-update controls remain at
    1.00 in `visual_parity_captures/2026-04-27-minimap-final/`. Remaining large
    ratios are now classified as minimap/background or localized water-edge
    samples, not broad terrain tone. See [a.md](../a.md) §45.
23. **Minimap-hidden custom-map sampling** — DONE (2026-04-27). The
    terrain-rich custom-map probe now supports
    `PF_TERRAIN_CUSTOM_MAP_MINIMAP_MODE=default|hidden|offscreen`, and records
    that mode in the paired summary metadata. The hidden-minimap capture proves
    the old large overview ratios at `(700,1700)` and `(400,2000)` were HUD
    minimap contamination: both are now exact `1.00,1.00,1.00` while main
    terrain, splat, and dynamic tile-update controls remain clean. Latest
    artifact: `visual_parity_captures/2026-04-27-terrain-hidden-minimap/`.
    The remaining `0.00` ratios were isolated empty-background/no-geometry
    coverage, not terrain material tone, and are closed by item 24 below. See
    [a.md](../a.md) §46.
24. **Empty-skybox background coverage parity** — DONE (2026-04-27). The
    hidden-minimap custom-map residual was caused by `G_SetSkybox("", "")`
    loading an empty black fallback cube on Metal while Apple Silicon OpenGL
    left the frame clear visible because skybox drawing is disabled by default.
    `G_SetSkybox` now treats an empty directory or extension as "no skybox":
    it frees the current skybox and skips the load command. Empty/no-geometry
    background samples now match OpenGL at `1.00,1.00,1.00` in
    `visual_parity_captures/2026-04-27-empty-skybox-background-fix/`, and
    terrain/ridge/update controls remain at `1.00`. See [a.md](../a.md) §47.
25. **Basin water-edge fixture retarget** — DONE (2026-04-27). The custom-map
    probe now keeps the original off-center basin and adds a smaller central
    basin that the fixed isometric camera can frame. The `water_edge` scene now
    targets that basin at height `720.0`, producing a useful diagonal
    land/water/depression boundary instead of mostly clear background. The final
    paired artifact is
    `visual_parity_captures/2026-04-27-basin-water-edge-final/`; sampled
    water-edge, overview, ridge, and tile-update controls are all
    `1.00,1.00,1.00`. See [a.md](../a.md) §48.
26. **Normal-gameplay water/rocks skybox reference parity** — DONE
    (2026-04-27). The apparent `water (1700,900)` / `rocks (1700,900)` tone
    residual was a harness reference-mode mismatch: Metal honored
    `pf.set_skybox(...)`, while Apple Silicon OpenGL only drew skyboxes when
    `PF_GL_ENABLE_APPLE_ARM64_SKYBOX` was set. The visual parity harness now
    defaults `PF_VISUAL_PARITY_INCLUDE_SKYBOX=1`, exports that flag to the
    probe, and therefore compares Metal against the skybox-enabled OpenGL
    reference by default. The same slice also corrected Metal's reflection pass
    to render reflected terrain/entities with the mirrored camera. The full
    five-scene artifact is
    `visual_parity_captures/2026-04-27-water-rocks-default-skybox-full-5scene/`;
    water, rocks, overview, combat, and skybox watch points are all at
    `0.99-1.04` ratios. See [a.md](../a.md) §49.
27. **Paired normal-gameplay smoke validation** — FIRST PASS DONE
    (2026-04-27). Generalized the existing gameplay smoke probe so the same
    camera, selection, movement, pause/resume, and attack sequence can run under
    both OpenGL and Metal, then added
    `scripts/macos/capture_gameplay_smoke_parity.sh` as a paired gate. Artifact:
    `visual_parity_captures/2026-04-27-gameplay-smoke-parity/`; both backends
    report `camera=1 selection=1 move=1 pause=1 attack=1`, and the wrapper
    prints `GAMEPLAY SMOKE MATCH checks=5 selected=4`. See [a.md](../a.md) §50.
28. **Paired free-roam gameplay soak validation** — FIRST PASS DONE
    (2026-04-27). Added `scripts/macos/pf_gameplay_soak_probe.py` and
    `scripts/macos/capture_gameplay_soak_parity.sh` so OpenGL and Metal run the
    same longer live route: initial selection, four staged exploration
    waypoints across the map, a dynamic water-tile update, and a final combat
    contact. Artifact:
    `visual_parity_captures/2026-04-27-gameplay-soak-parity/`; both backends
    produced matching seven-record summaries and the wrapper printed
    `GAMEPLAY SOAK MATCH checks=5 records=7 selected=4`. See [a.md](../a.md)
    §51.
29. **Apple Silicon Metal-default runtime switch** — DONE (2026-04-27).
    `Makefile` now defaults `PLAT=MACOS_ARM64` to `RENDER_BACKEND=METAL` while
    preserving `RENDER_BACKEND=OPENGL` as the explicit reference/fallback.
    `make -n run PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1` now expands through
    the `obj/MACOS_ARM64-METAL` object tree and launches `./bin/pf-arm64`.
    Launch probes verified the default build reports `pf.render.backend=METAL`,
    and the explicit OpenGL reference build still reports
    `pf.render.backend=OPENGL`. The paired parity harnesses now rebuild Metal at
    the end so normal local runs are left on the default backend after evidence
    capture. See [a.md](../a.md) §53.
30. **First Metal/OpenGL link decoupling** — DONE (2026-04-27).
    The default Metal Apple Silicon build no longer compiles
    `src/render/backend_gl.c` and no longer links `OpenGL.framework`.
    `otool -L bin/pf-arm64` shows Metal/QuartzCore/Foundation without OpenGL,
    `nm -gU bin/pf-arm64 | rg "R_GL_Backend|SDL_GL_|OpenGL"` returns no
    output, and default Metal plus explicit OpenGL launch probes both still
    pass. Remaining cleanup is the larger split/rename of the legacy `R_GL_*`
    command API and OpenGL helper-object dependencies. See [a.md](../a.md) §54.
31. **First swapchain-command decoupling** — DONE (2026-04-27).
    Metal no longer queues or drops the OpenGL loading-screen swapchain-present
    command, and Metal `render.o` no longer references the OpenGL swapchain
    resize command. Default Metal and explicit OpenGL launch probes both pass,
    with the local binary restored to Metal afterward. See [a.md](../a.md) §55.
32. **Frame command identity split** — DONE (2026-04-28).
    `R_GL_BeginFrame` and `R_GL_EndFrame` now live as backend-neutral command
    identity stubs in the shared render object, while the OpenGL execution
    bodies moved to private `_Impl` functions dispatched by `backend_gl.c`.
    Metal still maps the same command IDs to Metal frame begin/end, explicit
    OpenGL still launches, and the local binary is restored to Metal afterward.
    See [a.md](../a.md) §56.
33. **View/projection/light command identity split** — DONE (2026-04-28).
    `R_GL_SetViewMatAndPos`, `R_GL_SetProj`, `R_GL_SetAmbientLightColor`,
    `R_GL_SetLightEmitColor`, and `R_GL_SetLightPos` now live as
    backend-neutral command identity stubs in the shared render object, while
    OpenGL state updates moved to private `_Impl` functions dispatched by
    `backend_gl.c`. Metal consumes the same command IDs through its existing
    dispatch path, explicit OpenGL still launches, and the local binary is
    restored to Metal afterward. See [a.md](../a.md) §57.
34. **Screenspace/box helper command identity split** — DONE (2026-04-28).
    `R_GL_SetScreenspaceDrawMode` and `R_GL_DrawBox2D` now live as
    backend-neutral command identity stubs in the shared render object, while
    OpenGL helper execution moved to private `_Impl` functions. OpenGL internal
    direct calls now target `_Impl`, Metal keeps consuming the public command
    IDs, explicit OpenGL still launches, and the local binary is restored to
    Metal afterward. See [a.md](../a.md) §58.
35. **Low-risk debug command identity split** — DONE (2026-04-28).
    `R_GL_DrawLine`, `R_GL_DrawQuad`, `R_GL_DrawOrigin`, `R_GL_DrawRay`, and
    `R_GL_DrawOBB` now live as backend-neutral command identity stubs in the
    shared render object, while OpenGL helper execution moved to private
    `_Impl` functions dispatched by `backend_gl.c`. Metal consumes the same
    command IDs, explicit OpenGL still launches, and the local binary is
    restored to Metal afterward. See [a.md](../a.md) §59.
36. **Selection/overlay command identity split** — DONE (2026-04-28).
    `R_GL_DrawSelectionCircle`, `R_GL_DrawSelectionRectangle`,
    `R_GL_DrawMapOverlayQuads`, `R_GL_DrawFlowField`, and
    `R_GL_DrawCombinedHRVO` now live as backend-neutral command identity stubs
    in the shared render object, while OpenGL overlay execution moved to
    private `_Impl` functions dispatched by `backend_gl.c`. Metal consumes the
    same command IDs, explicit OpenGL still launches, and the local binary is
    restored to Metal afterward. See [a.md](../a.md) §60.
37. **Loading-screen/healthbar command identity split** — DONE (2026-04-28).
    `R_GL_DrawLoadingScreen` and `R_GL_DrawHealthbars` now live as
    backend-neutral command identity stubs in the shared render object, while
    OpenGL UI execution moved to private `_Impl` functions dispatched by
    `backend_gl.c`. Metal keeps consuming or intentionally ignoring the same
    command IDs, explicit OpenGL still launches, and the local binary is
    restored to Metal afterward. See [a.md](../a.md) §61.
38. **Skeleton/normals/model-preview command identity split** — DONE (2026-04-28).
    `R_GL_DrawSkeleton`, `R_GL_DrawNormals`, and `R_GL_DrawModelToTexture` now
    live as backend-neutral command identity stubs in the shared render object,
    while OpenGL debug/model-preview execution moved to private `_Impl`
    functions dispatched by `backend_gl.c`. Metal behavior is unchanged for
    these unsupported paths, explicit OpenGL still launches, and the local
    binary is restored to Metal afterward. See [a.md](../a.md) §62.
39. **Core scene draw command identity split** — DONE (2026-04-28).
    `R_GL_Draw` now lives as a backend-neutral command identity stub in the
    shared render object, while OpenGL mesh draw execution moved to
    `R_GL_Draw_Impl` dispatched by `backend_gl.c`. The two OpenGL helper direct
    calls in model-preview and minimap bake now target `_Impl`, Metal continues
    consuming the same command ID through its terrain/static/skinned draw path,
    explicit OpenGL still launches, and the local binary is restored to Metal
    afterward. See [a.md](../a.md) §63.
40. **Depth-pass command identity split** — DONE (2026-04-28).
    `R_GL_DepthPassBegin`, `R_GL_DepthPassEnd`, `R_GL_RenderDepthMap`,
    `R_GL_SetShadowsEnabled`, and `R_GL_Batch_RenderDepthMap` now live as
    backend-neutral command identity stubs in the shared render object, while
    OpenGL shadow/depth execution moved to private `_Impl` functions dispatched
    by `backend_gl.c`. The paired visual harness passes for five OpenGL/Metal
    scenes with matching cameras after routing the OpenGL terrain shadow-state
    helper call to `_Impl`. See [a.md](../a.md) §64.
41. **Map command identity split** — DONE (2026-04-28).
    `R_GL_MapInit`, `R_GL_MapShutdown`, `R_GL_MapBegin`, `R_GL_MapEnd`,
    `R_GL_MapUpdateFog`, and `R_GL_MapInvalidate` now live as backend-neutral
    command identity stubs in the shared render object, while OpenGL terrain/map
    execution moved to private `_Impl` functions dispatched by `backend_gl.c`.
    OpenGL minimap direct helper calls now target `_Impl`, and the five-scene
    paired visual harness passes with matching cameras. A fresh four-scene
    custom terrain-map harness retest also passes with matching cameras after
    an earlier transient SDL display initialization hiccup. See
    [a.md](../a.md) §65.
42. **Water command identity split** — DONE (2026-04-29).
    `R_GL_WaterInit`, `R_GL_WaterShutdown`, and `R_GL_DrawWater` now live as
    backend-neutral command identity stubs in the shared render object, while
    OpenGL water execution moved to private `_Impl` functions dispatched by
    `backend_gl.c`. The OpenGL minimap water-texture bake helper now calls
    `R_GL_DrawWater_Impl` directly. The five-scene visual harness and the
    four-scene custom terrain/water harness both pass with matching cameras
    after non-persistent vsync-off capture hardening for the Apple OpenGL
    swap/pump stall. See [a.md](../a.md) §66.
43. **Minimap command identity split** — DONE (2026-04-29).
    `R_GL_MinimapBake`, `R_GL_MinimapUpdateChunk`, `R_GL_MinimapRender`,
    `R_GL_MinimapRenderUnits`, and `R_GL_MinimapFree` now live as
    backend-neutral command identity stubs in the shared render object, while
    OpenGL minimap execution moved to private `_Impl` functions dispatched by
    `backend_gl.c`. The five-scene visual harness, four-scene custom
    terrain/minimap harness, and dedicated Metal minimap fog probe pass after
    the split. See [a.md](../a.md) §67.
44. **Tile command identity split** — DONE (2026-04-29).
    `R_GL_TileDrawSelected`, `R_GL_TileUpdate`,
    `R_GL_TilePatchVertsBlend`, and `R_GL_TilePatchVertsSmooth` now live as
    backend-neutral command identity stubs in the shared render object.
    OpenGL selected-tile drawing moved to `R_GL_TileDrawSelected_Impl`, while
    tile update and adjacency patch execution moved to neutral
    `R_Tile*Impl` helpers shared by OpenGL and Metal. The five-scene visual
    harness and four-scene custom terrain/tile-update harness pass after the
    split. See [a.md](../a.md) §68.
45. **Batch command identity split** — DONE (2026-04-29).
    `R_GL_Batch_Draw`, `R_GL_Batch_DrawWithID`,
    `R_GL_Batch_RenderDepthMap`, `R_GL_Batch_Reset`, and
    `R_GL_Batch_AllocChunks` now live as backend-neutral command identity
    stubs in the shared render object, while OpenGL batch execution moved to
    private `_Impl` functions dispatched by `backend_gl.c`. Metal keeps its
    native batch draw/depth paths and no-op reset/chunk-allocation behavior.
    The five-scene visual harness and four-scene custom terrain/chunk harness
    pass after the split. See [a.md](../a.md) §69.
46. **Animation command identity split** — DONE (2026-04-29).
    `R_GL_AnimAppendData` and `R_GL_AnimSetUniforms` now live as
    backend-neutral command identity stubs in the shared render object, while
    OpenGL animation pose-buffer upload/uniform execution moved to private
    `_Impl` functions dispatched by `backend_gl.c`. Metal continues to consume
    `R_GL_AnimSetUniforms` as native animated-entity state and ignores the
    OpenGL-only pose-buffer upload path. `R_GL_AnimInit`,
    `R_GL_AnimShutdown`, and `R_GL_AnimBindPoseBuff` remain OpenGL lifecycle
    helpers. The five-scene visual harness passes after the split. See
    [a.md](../a.md) §70.
47. **Sprite command identity split** — DONE (2026-04-29).
    `R_GL_SpriteRenderBatch` now lives as a backend-neutral command identity
    stub in the shared render object, while OpenGL world-sprite batch execution
    moved to `R_GL_SpriteRenderBatch_Impl` dispatched by `backend_gl.c`. Metal
    still explicitly drops the sprite batch command until a native sprite path
    is implemented, preserving the existing behavior without referencing
    OpenGL execution. The five-scene visual harness passes after the split; the
    gameplay smoke parity harness hit the known macOS SDL display-service
    startup failure before probe initialization and was not used as renderer
    evidence. See [a.md](../a.md) §71.
48. **Native Metal world-sprite batch path** — DONE (2026-04-29).
    Metal now handles `R_GL_SpriteRenderBatch` with a dedicated world-space
    billboard pipeline, sprite-sheet texture cache, row/column frame sampling,
    and alpha discard matching the OpenGL sprite shader. This restores the
    renderer-side foundation for projectile trails, impacts, fire, smoke, and
    other future sprite-sheet effects. At landing time the stock checkout had
    no `assets/sprites/` content, so the first probe exercised the
    command/pipeline path with a dummy sprite while the five-scene visual
    harness guarded against scene regressions. See [a.md](../a.md) §72.
49. **Real sprite effect assets and Metal probe coverage** — DONE
    (2026-04-29).
    Added the first loadable `assets/sprites/` fixtures for projectile trails,
    impact bursts, fire, and smoke. The Metal sprite probe now spawns all four
    effect classes and uses the env-gated `PF_METAL_SPRITE_STATS_PATH` renderer
    hook to fail unless the native Metal sprite batch path actually loads and
    draws every sheet. The OpenGL and Metal native launch probes and five-scene
    visual harness pass after the change. These sheets are probe fixtures, not
    final HD/4K production effects. See [a.md](../a.md) §73.
50. **Gameplay-driven projectile/fire/smoke effects probe** — DONE
    (2026-04-29).
    The default Mage fireball descriptor now uses the projectile-trail and
    impact-burst sprite sheets, and the new Metal gameplay-effects probe stages
    a Mage attack to prove trail/impact emission from `src/phys/projectile.c`
    and native Metal rendering of projectile trail, impact, fire, and smoke
    sheets in the same run. Fire and smoke are still controlled world fixtures,
    not burning-building gameplay integration. See [a.md](../a.md) §74.
51. **UI command identity split** — DONE (2026-04-29).
    `R_GL_UI_Init`, `R_GL_UI_Shutdown`, `R_GL_UI_Render`, and
    `R_GL_UI_UploadFontAtlas` now live as shared render-command identities.
    OpenGL execution moved to private `R_GL_UI_*_Impl` functions dispatched by
    `backend_gl.c`, while `backend_metal.m` dispatches the same command
    identities directly to the native `R_Metal_UI_*` implementation. The Metal
    object no longer references `R_GL_*_Impl`, both backend launch probes pass,
    and the five-scene parity harness passes with matched cameras. See
    [a.md](../a.md) §75.
52. **Metal GL perf/query wrapper cleanup** — DONE (2026-04-29).
    Debug `GL_PERF_*` instrumentation is now OpenGL-only, so Metal builds no
    longer inherit `pf_glGenQueries`, `pf_glQueryCounter`, or GL debug-group
    references from split OpenGL source files. `R_GL_TimestampForCookie` also
    has a Metal guard, leaving the GL query readback implementation active only
    for OpenGL. Both backend launch probes and the five-scene parity harness
    pass after the change. See [a.md](../a.md) §76.
53. **Metal loader-root split for mesh init and skybox commands** — DONE
    (2026-04-29).
    Metal macOS links now use dead stripping, `R_GL_Init` is a shared command
    identity with OpenGL execution in `R_GL_Init_Impl`, and the skybox command
    family is split into shared command IDs plus OpenGL `R_GL_*_Impl` bodies.
    `-why_live,_pf_glBindBuffer` no longer reports mesh init or skybox load as
    GL-loader roots; the remaining roots are position/movement upload/readback.
    Both backend launch probes and the five-scene parity harness pass. See
    [a.md](../a.md) §77.
54. **Metal position/movement loader-root split** — DONE (2026-04-29).
    The optional GPU movement and position-buffer commands are now shared
    command identities with OpenGL execution behind private `_Impl` functions.
    `-why_live,_pf_glBindBuffer` now emits no liveness chain, and `nm` no
    longer finds the GL buffer upload/readback symbols or movement `_Impl`
    bodies in the Metal binary. The next live GL-loader root is texture loading
    through `R_GL_Texture_GetOrLoad`. Both backend launch probes and the
    five-scene parity harness pass. See [a.md](../a.md) §78.
55. **Metal texture-loader root split** — DONE (2026-04-29).
    `R_GL_Texture_GetOrLoad` is now a shared render command identity with
    OpenGL texture loading behind `R_GL_Texture_GetOrLoad_Impl`; OpenGL-only UI,
    sprite, and loading-screen callers use the `_Impl` path directly. A stray
    audio `glGetError()` typo was also corrected to `alGetError()`. The Metal
    binary now has no live `_pf_gl*` loader symbols and still does not link
    `OpenGL.framework`. Both backend launch probes and the five-scene parity
    harness pass. See [a.md](../a.md) §79.
56. **Backend-neutral command API rename** — DONE (2026-04-29).
    The shared render-command identity surface has moved from legacy
    `R_GL_*` names to backend-neutral `R_Cmd_*` names. OpenGL execution bodies
    remain explicitly owned by `R_GL_*_Impl` functions, and true OpenGL helpers
    such as framebuffer dumps, shadow diagnostics, GL position texture
    readback, and OpenGL-only swapchain/viewport resize helpers keep their GL
    names. This left macOS editor launch as explicit follow-up work rather than
    a hidden part of the command-rename slice. Metal/OpenGL launch probes, the
    five-scene parity harness, old-command source checks, and Metal linkage
    checks pass. See [a.md](../a.md) §80.

57. **macOS Metal editor launch bring-up** — DONE (2026-04-29).
    The Apple Silicon editor path now starts on the native Metal runtime:
    Python 3 `basestring` and float-rectangle startup blockers were fixed,
    `make run_editor PLAT=MACOS_ARM64` is enabled, and a dedicated editor
    launch probe reports `EDITOR_LAUNCH_READY backend=METAL`. This closes the
    startup blocker only; full editor feature parity remains a later audit. See
    [a.md](../a.md) §81.

58. **macOS Metal editor feature-surface audit** — DONE (2026-04-30).
    A new feature audit probe drives the Metal editor through Terrain, Objects,
    Diplomacy, Menu, Settings, Performance, Session, and Load/Save As cancel
    flows. The audit found and fixed an animated placement-preview lifetime
    crash when switching Objects from Place to Select. Direct Metal launch and
    `make run_editor PLAT=MACOS_ARM64` both report
    `EDITOR_FEATURE_AUDIT_READY backend=METAL`; Metal linkage remains free of
    OpenGL framework and live GL-loader symbols. See [a.md](../a.md) §82.

59. **Python 3 cooperative `pf.Task` runtime** — DONE (2026-04-30).
    `pf.Task.run()` no longer raises `NotImplementedError` on Python 3.13.
    The macOS runtime supports generator-style cooperative tasks using
    `yield self.yield_()`, `yield self.sleep(ms)`, and
    `yield self.await_event(event)`. Both Metal and OpenGL task probes pass
    with `steps=start,yield,sleep,event`. Legacy Python 2 stackful task scripts
    that call blocking task methods without `yield` still need migration. See
    [a.md](../a.md) §83.

60. **Legacy Pong `pf.Task` migration** — DONE (2026-04-30).
    `scripts/pong.py` now preserves the original Python 2 stackful task path
    while using Python 3 generator-yield task methods on the macOS runtime.
    The migration also fixes Python 3 range/division startup blockers in the
    Pong field setup. A new probe validates that the Pong ball advances through
    the task-driven `EVENT_30HZ_TICK` loop on both Metal and OpenGL. See
    [a.md](../a.md) §84.

61. **OpenAL audio fixture/probe coverage** — DONE (2026-04-30).
    Added tiny original generated WAV fixtures under `assets/music` and
    `assets/sounds`. A new audio probe verifies music indexing/playback state,
    global effect playback, and positional effect playback on both Metal and
    OpenGL. See [a.md](../a.md) §85.

62. **Dense GPU movement/crowd stress probe** — DONE (2026-04-30).
    Added a synthetic-but-real 64-unit animated Knight formation stress probe.
    The Metal GPU movement run passed with `gpu_movement=1`, 62/64 units moved,
    and average forward progress `15.41`. Metal CPU and OpenGL CPU sanity runs
    also passed. See [a.md](../a.md) §86.

63. **Core RTS gameplay systems probe** — DONE (2026-04-30).
    Added a controlled Metal/OpenGL gameplay-systems probe for resource
    gathering/drop-off, direct building lifecycle, builder orders, storage
    transport, automatic transport, and garrison. The slice also fixed Python 3
    constructor forwarding for gameplay entity mixins and corrected the Python
    garrison binding argument order. See [a.md](../a.md) §87.

64. **macOS Metal editor save/reload workflow probe** — DONE (2026-04-30).
    Added a focused editor workflow probe that mutates terrain, places one
    animated object and one static object, drives the editor Save As path,
    validates the written `.pfmap`/`.pfscene`, and then verifies a fresh editor
    launch can reload that saved pair. Metal and OpenGL both pass the save and
    reload phases. The slice also fixed Python 3 editor scene-save module
    lookup and the editor's stale two-value `pf.load_scene()` unpack. See
    [a.md](../a.md) §88.

65. **macOS Metal editor deterministic visual harness** — DONE (2026-05-01).
    Added a focused visual editor probe that paints terrain, places animated
    and static objects, captures Terrain and Objects tab screenshots through
    window-specific macOS capture, validates the screenshots as nonblank, and
    saves the edited map/scene. This closes the first deterministic screenshot
    gate after the top-bar usability fix. Computer Use could not attach to the
    raw SDL `pf-arm64` process, so direct desktop automation remains follow-up
    packaging work. See [a.md](../a.md) §90.

66. **macOS gameplay edge probe for water/air pathing and water transport** —
    DONE (2026-05-01). Added `pf_metal_gameplay_edge_probe.py` to exercise
    land, water, and air nearest-pathable queries, water and air move-order
    startup, and water-only resource transport restrictions including
    `do_not_take_water`. The probe passes on both the Metal runtime and the
    OpenGL reference backend, upgrading the capability matrix's land/water/air
    pathfinding row to verified and adding deeper coverage for transport edge
    behavior.

67. **macOS navigation-layer and formation reshuffle probe** — DONE
    (2026-05-01). Added `pf_metal_nav_formation_probe.py` to create mixed
    1x1/3x3/5x5/7x7 ground units, verify preferred-formation resolution,
    issue a rank formation move, then force a column reshuffle. The probe
    passes on the Metal GPU movement path and the OpenGL CPU reference,
    closing the dedicated navigation-layer/Hungarian reshuffle matrix gap.

68. **macOS dynamic obstacle blocker/avoidance probe** — DONE
    (2026-05-01). Added `pf_metal_dynamic_obstacle_probe.py` to create a
    known-moving mixed-radius formation, insert a founded blocking buildable
    after pre-blocker progress is proven, verify the navigation field shifts
    away from the blocker, and confirm the group continues moving with blocker
    clearance preserved. The probe passes on the Metal GPU movement path and
    the OpenGL reference backend, upgrading dynamic obstacle behavior from
    smoke coverage to verified in the capability matrix.

69. **macOS production automation variant probe** — DONE (2026-05-01).
    Added `pf_metal_production_automation_probe.py` to verify automatic
    worker transport toggles, idle behavior while automatic transport is
    disabled, worker `do_not_transport` blocking, automatic pickup/dropoff
    after the gate is cleared, and post-delivery idle settling. The probe
    passes on the Metal runtime and the OpenGL reference backend, closing the
    production automation variant matrix target.

70. **macOS mixed economy/combat scenario probe** — DONE (2026-05-01).
    Added `pf_metal_mixed_gameplay_scenario_probe.py` to verify a longer
    combined scenario on both Metal and OpenGL: camera movement, selection,
    fog/minimap setup, resource gather/drop-off, building lifecycle and builder
    order, automatic storage transport, garrison, Mage projectile combat, and
    projectile trail/impact plus fire/smoke sprite effects on the Metal path.
    This closes the larger mixed economy/combat matrix target.

71. **macOS large generated-world soak probe** — DONE (2026-05-01).
    Added `pf_metal_large_world_soak_probe.py` to load an 8x8 generated custom
    map with varied terrain/materials, fog/minimap, skybox, splats, dynamic tile
    update, custom content placement, exploration, economy/build/transport/
    garrison, combat, battlefield sprite effects, and a Metal session
    checkpoint. The Metal run writes and restores the generated custom-map
    checkpoint; the OpenGL reference run verifies the gameplay path and skips the
    custom-map save because it can stall in this generated-map path. The restore
    hardening added importable probe entity classes plus per-object scene
    metadata so the Python 3 scene snapshot recreates movable/resource/storage/
    buildable/garrisonable probe entities before native movement/resource state
    is loaded. The follow-up scale pass adds opt-in map/content/duration knobs
    and verifies a 10x10 Metal generated-world run with 54 restored objects,
    5 regions, 4 cameras, and a longer post-combat soak; the OpenGL reference
    passes the same scaled gameplay path. The long-duration follow-up adds
    repeated gameplay-loop coverage before save/restore; Metal now verifies
    three extra camera/exploration/combat/effects/tile-update loops before
    restoring the same 54-object, 5-region, 4-camera generated world, and
    OpenGL passes the same looped gameplay path.

72. **macOS editor app packaging and Computer Use attach smoke** — DONE
    (2026-05-01). Added `scripts/macos/build_editor_app_bundle.sh`, `make
    editor_app`, and `make run_editor_app` so the Metal editor can be staged as
    `dist/Permafrost Editor.app` with a normal bundle identifier
    (`org.permafrostengine.editor.dev`). The package now stages `pf-arm64`,
    `assets/`, `scripts/`, and `shaders/` under
    `Contents/Resources/permafrost`, avoiding macOS privacy failures when a
    launched app reads a Desktop checkout. macOS `open` presents it as
    `Permafrost Editor`; Computer Use lists the app/window and sees the real
    editor UI. The existing editor launch, feature, save, reload, and visual
    probes still pass on Metal after packaging.

## Current Status

- Metal already verifies cold launch, startup UI, paired normal-gameplay smoke coverage, paired free-roam gameplay soak coverage, Apple Silicon editor launch, first editor feature-surface audit, editor terrain/object save plus fresh reload workflow, deterministic Terrain/Objects editor screenshots on the Metal runtime, Python 3 cooperative `pf.Task` scheduling plus the migrated Pong task sample, OpenAL music/global-effect/positional-effect smoke coverage, dense 64-unit GPU movement/crowd stress, core RTS resource/building/transport/automation/garrison smoke coverage, water/air pathing and water-transport edge behavior, navigation-layer formation movement and rank-to-column reshuffle coverage, dynamic blocker insertion/avoidance coverage, production automation variant coverage, larger mixed economy/combat scenario coverage, larger generated custom-world soak coverage with Metal session checkpoint restore, the Apple Silicon default runtime build, the first Metal/OpenGL link decoupling, the first swapchain-command decoupling, the frame command identity split, the view/projection/light command identity split, the screenspace/box helper command identity split, the low-risk debug command identity split, the selection/overlay command identity split, the loading-screen/healthbar command identity split, the skeleton/normals/model-preview command identity split, the core scene draw command identity split, the depth-pass command identity split, the map command identity split, the water command identity split, the minimap command identity split, the tile command identity split, the batch command identity split, the animation command identity split, the sprite command identity split, the UI command identity split, the Metal GL perf/query wrapper cleanup, the Metal mesh-init/skybox loader-root split, the Metal position/movement loader-root split, the Metal texture-loader root split, the native Metal world-sprite batch path, real sprite effect fixture/probe coverage for projectile trails/impacts/fire/smoke, gameplay-driven Mage projectile trail/impact coverage, terrain, real terrain textures, the first terrain patch-command/material-adjacency pass, the first terrain sampler/mipmap parity pass, the first terrain texture-array LOD-bias parity fix, the first terrain height-map normal/lighting parity pass, the first terrain splat blending parity pass, the first terrain-rich larger/custom-map fixture, the first custom-map minimap bake projection/map-state pass, minimap-hidden custom-map sampling, empty-skybox background coverage parity, basin water-edge/depression fixture coverage, normal-gameplay water/rocks skybox-reference parity, the first material texture-array mipmap pass for static props/rocks, the first mesh material UV parity fix for units and rocks/static props, the first static-prop winding/culling parity fix, the first high-specular static-prop normal/specular parity fix, the first mesh normal-transform parity fix, the first unlit screen-space statusbar/healthbar tone fix plus the tighter GL-style healthbar outline/fill parity fix, the first mesh shadow formula parity fix, the first terrain shadow coverage parity fix, the first terrain shadow Poisson Y parity fix, the first shadow-map Y-lookup and per-caster winding split, the first water/shore/fog parity foundation, the first water material/timing parity fix, the first water sampled-scene parity fix, the first offscreen water-scene color/tone fix, the first water final-color formula parity fix, static/skinned meshes, foliage cutouts, selection overlays, drag-box selection, terrain-conforming debug/vector overlays and debug primitives, healthbars, minimap fog-of-war HUD display, the first minimap dynamic water-update/scissor pass, map overlays, fog, water foundations, the first skybox command path with skybox-fed water reflections, main-frame skybox visual parity with the default Apple Silicon OpenGL skybox reference, skybox-fed water reflection scale parity, the first light-state/material-lighting parity slice, explicit MSAA parity state, ship-default 4x MSAA with parity-mode 1x captures, frame pacing, main-frame depth, shadow-map parity, lossless shadow-map diagnostics, deterministic fixed-time lighting phases, and the deterministic fixed-camera capture harness.
- The fixed-camera Metal magenta main-scene blocker is fixed.
- Still pending after the Apple Silicon Metal-default switch:
  - continue visual/smoothness regression checks against the OpenGL Apple Silicon baseline
  - polish any concrete remaining material/color residuals found by review
  - deeper manual editor editing QA through the packaged app/window
  - finish any remaining OpenGL helper-object dependency isolation

## Validation

- Use the existing fixed-camera OpenGL/Metal capture harness for parity evidence.
- The capture harness now resolves the actual macOS game-window id before calling `screencapture -l`, so parity artifacts are window-scoped instead of full-desktop screenshots.
- Latest default skybox-reference all-scene artifact: `visual_parity_captures/2026-04-27-water-rocks-default-skybox-full-5scene/`.
- Latest paired normal-gameplay smoke artifact: `visual_parity_captures/2026-04-27-gameplay-smoke-parity/`.
- Latest paired free-roam gameplay soak artifact: `visual_parity_captures/2026-04-27-gameplay-soak-parity/`.
- Latest MSAA default/parity-gate artifacts: `visual_parity_captures/2026-04-27-metal-msaa-default-smoke/`, `visual_parity_captures/2026-04-27-metal-msaa-parity-smoke/`, and `visual_parity_captures/2026-04-27-msaa-parity-gate/`.
- Latest verified main-skybox parity artifact: `visual_parity_captures/2026-04-26-skybox-reflection-cull-fix/`.
- Latest skybox-fed water-reflection parity artifact: `visual_parity_captures/2026-04-27-water-reflection-scale-fix/`.
- Latest skybox-enabled all-scene post-reflection validation artifact: `visual_parity_captures/2026-04-27-post-reflection-allscene-skybox-validation/`.
- Latest broader terrain/material/water tone audit artifact: `visual_parity_captures/2026-04-27-water-refraction-shadow-parity/`.
- Latest static-prop high-specular normal parity artifact: `visual_parity_captures/2026-04-27-static-prop-highspec-normal-parity/`.
- Latest terrain shadow Poisson Y parity artifact: `visual_parity_captures/2026-04-27-shadow-poisson-yflip-parity/`.
- Latest minimap dynamic water-update/scissor artifact: `visual_parity_captures/2026-04-27-minimap-fog-dynamic-water-scissor-full/`.
- Latest terrain splat parity artifacts: `visual_parity_captures/2026-04-27-terrain-splat-dormant-baseline/`, `visual_parity_captures/2026-04-27-terrain-splat-pair-0-1/`, and `visual_parity_captures/2026-04-27-terrain-splat-pair-0-9/`.
- Latest terrain-rich custom-map fixture artifact: `visual_parity_captures/2026-04-27-terrain-custom-map-final/`.
- Latest custom-map minimap bake projection/map-state artifact: `visual_parity_captures/2026-04-27-minimap-final/`.
- Latest minimap-hidden custom-map terrain sampling artifact: `visual_parity_captures/2026-04-27-terrain-hidden-minimap/`.
- Latest UI command identity split artifact: `visual_parity_captures/2026-04-29-ui-command-split/`.
- Latest GL perf/query cleanup artifact: `visual_parity_captures/2026-04-29-metal-gl-perf-cleanup/`.
- Latest Metal loader-root split artifact: `visual_parity_captures/2026-04-29-metal-loader-root-split/`.
- Latest Metal position/movement loader-root split artifact: `visual_parity_captures/2026-04-29-metal-position-movement-loader-root-split/`.
- Latest Metal texture-loader root split artifact: `visual_parity_captures/2026-04-29-metal-texture-loader-root-split/`.
- Latest verified light-state/material-lighting artifact: `visual_parity_captures/2026-04-24-metal-light-state/`.
- Latest verified debug primitive artifact: `visual_parity_captures/2026-04-24-metal-debug-primitives/`.
- Latest verified terrain patch-command/material-adjacency artifact: `visual_parity_captures/2026-04-24-metal-terrain-patch-final-pair/`.
- Latest verified terrain sampler/mipmap parity artifact: `visual_parity_captures/2026-04-24-metal-terrain-mipmaps-windowid-final/`.
- Latest deterministic camera plus texture-array LOD-bias artifact: `visual_parity_captures/2026-04-25-metal-terrain-water-tone-lodbias/`.
- Latest verified terrain height-map normal/lighting artifact: `visual_parity_captures/2026-04-24-metal-terrain-heightmap-normal/`.
- Latest water-with-units and rocks artifact: `visual_parity_captures/2026-04-24-metal-water-units-rocks/`.
- Latest mesh material UV parity artifact: `visual_parity_captures/2026-04-24-metal-mesh-uv-parity/`.
- Latest static-prop winding/culling parity artifact: `visual_parity_captures/2026-04-25-metal-static-prop-winding/`.
- Latest mesh normal-transform parity artifact: `visual_parity_captures/2026-04-25-metal-mesh-normal-parity/`.
- Latest unlit statusbar/healthbar tone artifact: `visual_parity_captures/2026-04-25-metal-unlit-statusbar-tone/`.
- Latest combat healthbar/material residual artifact: `visual_parity_captures/2026-04-26-combat-residual-fix/`.
- Latest shadow-map Y-lookup and mesh winding split artifact: `visual_parity_captures/2026-04-26-shadow-yflip-winding-split/`.
- Latest minimap fog parity artifact: `visual_parity_captures/2026-04-26-minimap-fog-metal/`.
- Latest minimap unit-exploration probe artifact: `visual_parity_captures/2026-04-27-minimap-bake-fog-clear/`.
- Latest rocks-edge fogged water composition artifact: `visual_parity_captures/2026-04-27-post-reflection-allscene-skybox-validation/`.
- Latest native sprite effects fixture artifact:
  `visual_parity_captures/2026-04-29-metal-sprite-effects-assets/`.
- Latest gameplay-driven sprite effects artifact:
  `visual_parity_captures/2026-04-29-metal-gameplay-effects-parent-verified/`.
- Latest post-gameplay-effects five-scene parity artifact:
  `visual_parity_captures/2026-04-29-metal-gameplay-effects-parity/`.
- Latest gameplay edge probe artifacts:
  `visual_parity_captures/2026-05-01-gameplay-edge-metal/` and
  `visual_parity_captures/2026-05-01-gameplay-edge-opengl/`.
- Latest navigation-layer/formation reshuffle probe artifacts:
  `visual_parity_captures/2026-05-01-nav-formation-metal/` and
  `visual_parity_captures/2026-05-01-nav-formation-opengl/`.
- Latest dynamic obstacle blocker/avoidance probe artifacts:
  `visual_parity_captures/2026-05-01-dynamic-obstacle-metal-final/` and
  `visual_parity_captures/2026-05-01-dynamic-obstacle-opengl/`.
- Latest production automation variant probe artifacts:
  `visual_parity_captures/2026-05-01-production-automation-metal-final/` and
  `visual_parity_captures/2026-05-01-production-automation-opengl/`.
- Latest mixed economy/combat scenario probe artifacts:
  `visual_parity_captures/2026-05-01-mixed-gameplay-scenario-metal-final/` and
  `visual_parity_captures/2026-05-01-mixed-gameplay-scenario-opengl/`.
- Latest large generated-world soak probe artifacts:
  baseline restore at `visual_parity_captures/2026-05-01-large-world-soak-restore-metal/`
  and `visual_parity_captures/2026-05-01-large-world-soak-restore-opengl/`;
  scaled 10x10 soak at `visual_parity_captures/2026-05-01-large-world-soak-scale-metal-final/`
  and `visual_parity_captures/2026-05-01-large-world-soak-scale-opengl/`;
  repeated-loop 10x10 soak at `visual_parity_captures/2026-05-01-large-world-soak-loop-metal/`
  and `visual_parity_captures/2026-05-01-large-world-soak-loop-opengl/`.
- Latest packaged editor app smoke: `make editor_app PLAT=MACOS_ARM64
  MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL` stages a self-contained
  `dist/Permafrost Editor.app`; `scripts/macos/build_editor_app_bundle.sh
  --skip-build --verify` reports `EDITOR_APP_LAUNCH_READY`, and Computer Use
  sees the rendered `Permafrost Editor — org.permafrostengine.editor.dev`
  window instead of a blank clear-color surface.
- Latest mesh shadow formula parity artifact: `visual_parity_captures/2026-04-24-metal-mesh-shadow-parity/`.
- Latest terrain shadow coverage parity artifact: `visual_parity_captures/2026-04-24-metal-terrain-shadow-coverage/`.
- Latest water/shore/fog parity artifact: `visual_parity_captures/2026-04-24-metal-water-fog-parity/`.
- Latest water material/timing parity artifact: `visual_parity_captures/2026-04-24-metal-water-material-timing/`.
- Latest water sampled-scene parity artifact: `visual_parity_captures/2026-04-24-metal-water-scene-sampling/`.
- Latest offscreen water-scene color/tone artifact: `visual_parity_captures/2026-04-25-metal-water-offscreen-color/`.
- Latest water final-color formula parity artifact: `visual_parity_captures/2026-04-25-metal-water-final-color-parity/`.
- Latest MGL migration-reference notes: `plans/2026-04-25-mgl-opengl-on-metal-notes.md`.
- Latest direct debug-overlay probe: `scripts/macos/pf_metal_debug_overlay_probe.py` reports `METAL_DEBUG_OVERLAY_PASS backend=METAL render_frames=8 chunk_boundaries=1 flow_field=1 combat_targets=1`.
- Add future capture scenarios for:
  - close character-level zoom
  - wide large-map zoom-out
  - dense forests and vegetation
  - dense army/battle scenes
  - arrows, fire, smoke, impacts, and burning buildings
- Do not mark the HD/4K platform complete from existing stock assets alone; it is a post-port graphics/content uplift.

## References

- [AoE II DE review](https://www.dedoimedo.com/games/age-of-empires-definitive-edition.html)
- [openage](https://github.com/SFTtech/openage/)
- [openage engine core modules](https://blog.openage.dev/engine-core-modules.html)
- [MGL OpenGL 4.6 and ES 3.x on Metal](https://github.com/openglonmetal/MGL)
