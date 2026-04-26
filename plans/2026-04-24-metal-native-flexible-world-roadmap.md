# Metal-Native Flexible-World Roadmap

Created: 2026-04-24

## Summary

This plan consolidates the Metal/OpenGL replacement work, the Age of Empires II: Definitive Edition Enhanced Graphics Pack clarity reference, the openage extensibility reference, and the longer-term HD/4K flexible-world graphics goal.

The immediate implementation track remains the Metal-native replacement of OpenGL. The HD/4K graphics platform is a post-port milestone: it should guide architecture choices now, but it should not block making Metal the default once functional and visual parity gates are met.

Related Apple sample-code notes: [2026-04-25 Apple Metal migration sample notes](2026-04-25-apple-metal-migration-sample-notes.md).
Related OpenGL-on-Metal reference notes: [2026-04-25 MGL OpenGL-on-Metal notes](2026-04-25-mgl-opengl-on-metal-notes.md).

## Milestone Chain

1. `Metal visual and smoothness parity`
   - Match the current OpenGL Apple Silicon baseline for runtime gameplay rendering.
   - Close color, gamma, terrain/material, fog, shadow, water, skybox, sampler/filtering, and frame-pacing differences using fixed-camera captures.
2. `Metal default`
   - Make Metal the default Apple Silicon runtime after parity and smoke coverage are green.
   - Keep OpenGL available only as a fallback during the transition.
3. `OpenGL removal`
   - Remove temporary Metal dependence on linked OpenGL renderer symbols.
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
   been using 4x MSAA on scene pipelines. The parity path now defaults
   Metal to 1x and makes 2x/4x opt-in through `PF_METAL_MSAA_SAMPLES`
   so captures do not silently compare OpenGL no-MSAA against Metal
   4x MSAA. The "jagged edges in Metal" perception was the opposite
   of the objective measurement; the later HD/4K renderer can choose
   a higher-quality AA strategy intentionally. See [a.md](../a.md)
   §13 and §19 for data and follow-up.

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
9. **Ship-default MSAA flip (TODO before Metal default)** —
   `METAL_DEFAULT_MSAA_SAMPLES = 1` is correct for parity-test
   captures but becomes a quality regression once OpenGL is
   removed and Metal becomes the default renderer for end users.
   Before flipping the "Metal default" milestone, switch the
   shipping default back to 4× (or device max) and gate parity
   captures via a separate `PF_PARITY_MODE` flag. Also extend the
   accepted opt-in values to include 8 on M1+.
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

## Current Status

- Metal already verifies cold launch, startup UI, terrain, real terrain textures, the first terrain patch-command/material-adjacency pass, the first terrain sampler/mipmap parity pass, the first terrain texture-array LOD-bias parity fix, the first terrain height-map normal/lighting parity pass, the first material texture-array mipmap pass for static props/rocks, the first mesh material UV parity fix for units and rocks/static props, the first static-prop winding/culling parity fix, the first mesh normal-transform parity fix, the first unlit screen-space statusbar/healthbar tone fix plus the tighter GL-style healthbar outline/fill parity fix, the first mesh shadow formula parity fix, the first terrain shadow coverage parity fix, the first water/shore/fog parity foundation, the first water material/timing parity fix, the first water sampled-scene parity fix, the first offscreen water-scene color/tone fix, the first water final-color formula parity fix, static/skinned meshes, foliage cutouts, selection overlays, drag-box selection, terrain-conforming debug/vector overlays and debug primitives, healthbars, minimap, map overlays, fog, water foundations, the first skybox command path with skybox-fed water reflections, the first light-state/material-lighting parity slice, explicit MSAA parity state, frame pacing, main-frame depth, shadow-map parity, and the deterministic fixed-camera capture harness.
- The fixed-camera Metal magenta main-scene blocker is fixed.
- Still pending before Metal replaces OpenGL:
  - full visual/smoothness parity against the OpenGL Apple Silicon baseline
  - remaining water shoreline/color response, broader darker terrain/material tone, plus full skybox visual parity
  - richer material/color matching beyond the unlit statusbar/healthbar fix
  - localized combat unit/cobblestone material-lighting composition after the healthbar-edge fix
  - character/static-prop lighting parity at water/rock camera distances
  - broader normal gameplay validation
  - editor path
  - removal of temporary OpenGL renderer symbol dependence

## Validation

- Use the existing fixed-camera OpenGL/Metal capture harness for parity evidence.
- The capture harness now resolves the actual macOS game-window id before calling `screencapture -l`, so parity artifacts are window-scoped instead of full-desktop screenshots.
- Latest verified skybox/water-reflection artifact: `visual_parity_captures/2026-04-24-metal-skybox-water/`.
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
