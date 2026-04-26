# Permafrost Engine Notes

## Goal

- Understand Permafrost Engine well enough to evaluate it as a base for an HFMP S2-like RTS.
- Try the engine or demo locally on this Mac if practical.
- Capture architecture, build constraints, and reuse decisions as we go.

## Source

- Repo: <https://github.com/eduard-permyakov/permafrost-engine>
- License: GPLv3 with a special linking exception.
- Author contact: `edward.permyakov@gmail.com`

## Verified From Public README

- Permafrost Engine is an OpenGL 3.3 RTS engine written in C.
- The flagship game is EVERGLORY.
- The public gameplay/demo entrypoint is `./scripts/rts/main.py`.
- The editor entrypoint is `./scripts/editor/main.py`.
- Main dependencies called out by the repo:
  - SDL2 2.30.0
  - GLEW 2.2.0
  - Python 2.7.17
  - openal-soft 1.21.1
  - mi-malloc 2.2.3
- The documented build path is for Linux and Windows only.

## Early Build Notes

- The top-level `Makefile` builds vendored dependencies into `./lib` and then links the engine binary.
- The Linux target links against `-lGL`, `-ldl`, and `-lutil`, which are Linux-specific and likely need a macOS porting pass.
- The build uses an embedded Python 2.7 runtime, which is a major compatibility risk on modern macOS.
- Public repo structure from GitHub:
  - `src/`
  - `scripts/`
  - `assets/`
  - `shaders/`
  - `docs/`
  - `launcher/`
  - `deps/`

## Architecture Map

- `src/main.c`
  - Engine bootstrap and lifetime management.
  - Initializes settings, SDL, render thread, scheduler, session, asset loading, cursor, event, entity, animation, game, render, and UI subsystems.
- `src/render/`
  - OpenGL renderer, shader loading, batching, terrain, water, shadows, UI, minimap, swapchain, GPU movement helpers.
  - Uses SDL OpenGL context creation and targets OpenGL 3.3 core.
- `src/game/`
  - RTS gameplay simulation.
  - Includes movement, combat, fog of war, formation logic, builders/buildings, harvesting, storage, automation, selection, garrison, regions.
- `src/navigation/`
  - Map navigation context, layered pathfinding, flow fields, caches, debug overlays, land/water/air routing support.
- `src/script/`
  - Embedded Python bridge exposing engine/game/render/navigation/UI functionality into Python.
  - Session save/load includes Python-defined state.
- `src/map/`
  - Tile map representation, minimap, raycast support, map asset loading.
- `src/anim/`
  - Animation data loading, animation runtime, animation texture batching.
- `src/audio/`
  - OpenAL-backed audio/effects layer.
- `src/phys/`
  - Collision and projectile systems.
- `src/sched.c` + `src/context_switch.S`
  - Custom fiber/task scheduler with manual context switching and worker threads.
- `scripts/rts/`
  - Demo/gameplay layer.
  - `main.py` loads `assets/maps/demo.pfmap` and `assets/maps/demo.pfscene`, configures factions/cameras/UI, and drives the RTS demo.
- `scripts/editor/`
  - Map/editor UX layer built on the same engine API.
- `docs/python_api.txt`
  - Generated Python API reference for the exposed `pf` module.

## Gameplay / Scripting Split

- The engine core is in C.
- The gameplay shell is scriptable in Python 2.7 through the `pf` module.
- The demo entrypoint is thin and declarative: load map + scene, set diplomacy/control state, register UI/input handlers, then activate Python UI controllers.
- This suggests a good separation for a derivative game:
  - Reuse engine/runtime systems in C.
  - Replace the Python gameplay package, assets, maps, scenes, UI flow, and faction/unit definitions.

## Local Workspace Status

- Initial `git clone` stalled after remote setup in this environment.
- Preserved the incomplete checkout metadata as `.git.incomplete`.
- Downloaded and extracted the GitHub source archive into this workspace so the tree can be inspected locally.

## macOS Reality Check

- The repo documents only Linux and Windows builds.
- The Steam page for EVERGLORY currently lists Windows and SteamOS/Linux system requirements, not macOS.
- This Mac is:
  - `Darwin 25.3.0`
  - `arm64` Apple Silicon
- Native Apple Silicon is blocked immediately by the scheduler:
  - `src/sched.c` only supports `__x86_64__` or `_WIN64`.
  - `src/context_switch.S` ends with `#error "Unsupported platform"` outside those cases.
- Even if the architecture issue were solved, there is still no macOS platform target in `Makefile`; only `LINUX` and `WINDOWS` are defined.
- The renderer requests OpenGL 3.3 core via SDL, which macOS can potentially provide, but some higher-end features are optional:
  - Compute shaders are feature-gated in the engine and can be disabled if unsupported.

## Build Probes Run On This Mac

- `make deps`
  - First failed because GLEW's generator calls `python`, while this Mac only had `python3`.
- After adding a temporary `python -> python3` shim:
  - GLEW generation completed.
  - GLEW build then failed under Apple clang with generated symbol redefinition errors in `deps/GLEW/src/glew.c`.
- Local toolchain observations:
  - `clang` is present.
  - `make` is present.
  - `cmake` is not currently installed.
- Meaning:
  - We are blocked before even reaching the engine compile itself.
  - After that, native `arm64` would still fail in the custom scheduler/context-switch layer.

## macOS Port Spike Notes

- The macOS port path now has an engine-owned GL loader in `src/render/gl_loader.[ch]`.
- On macOS, the renderer no longer needs GLEW for capability discovery.
- The new loader exposes explicit feature checks for:
  - OpenGL 3.3 availability
  - `KHR_debug`
  - copy-image
  - buffer-storage
  - multi-draw-indirect
  - compute-shader support
  - timer queries
  - texture sub-image reads
- Renderer call sites now use those capability checks instead of direct `GLEW_*` or `GL_ARB_multi_draw_indirect` tests.
- Added macOS-friendly fallbacks:
  - terrain texture-buffer creation falls back from `glBufferStorage` to `glBufferData`
  - texture-array copies fall back from `glCopyImageSubData` to framebuffer blits
  - texture-array dumps fall back from `glGetTextureSubImage` to framebuffer reads
- macOS dependency validation no longer requires packaged `glew`.
- Native arm64 object-level verification succeeded for the touched renderer files when temporarily suppressing unrelated existing warnings:
  - `obj/render/gl_loader.o`
  - `obj/render/render.o`
  - `obj/render/gl_batch.o`
  - `obj/render/gl_texture.o`
  - `obj/render/gl_ringbuffer.o`
  - `obj/render/gl_terrain.o`
- The next native arm64 compile blockers are no longer renderer-loader-specific:
  - the first `gnu11` warning wave was fixable with small cleanups:
    - typed comparator signatures in `vec.h`
    - const-correct comparator helpers in gameplay code
    - SDL global-event registration widened to accept raw event codes
    - SDL window flag accumulation in `main.c` moved to a raw `Uint32` bitmask
  - the interactive Python console is now stubbed on Python 3 to avoid Python-2-only parser internals like `node.h`
  - the custom pickler is also stubbed on Python 3, matching the plan to disable save/load for native arm64 v1
  - the core Python bridge in `src/script/py_script.c` now compiles far enough on Python 3.13 with:
    - compatibility shims for `PyString_*` and `PyInt_*`
    - Python 3 module registration
    - Python 3 `sys.argv` setup
    - updated weakref handling
    - save/load disabled on the Python 3 path
  - a first Darwin arm64 scheduler/context-switch backend now compiles, preserving the existing stackful scheduler model with:
    - an AArch64 context record
    - an entry trampoline to pass task args correctly
    - an exit trampoline back into `sched_task_exit`
  - the current native arm64 frontier is no longer the scheduler or the early Python bridge; the full build now links successfully and produces `bin/pf-arm64`
  - the native arm64 runtime now launches on this Apple Silicon Mac, reaches a visible in-game frame, and exposes the RTS demo UI/minimap/action pad/units in a real macOS window
  - the first captured native arm64 visible-demo screenshot is saved in this workspace as `macos_port_screenshot_2026-04-20.png`
  - the latest verified native arm64 screenshots now show both the main world rendering and projected world shadows again after the generic mesh path stopped binding the animation pose buffer for every terrain/static draw and after the real shadow-map path was re-enabled on macOS arm64
  - launch blockers already cleared in the native macOS path include:
    - OpenGL loader fallback to framework symbols when SDL does not return core entrypoints like `glActiveTexture`
    - skipping the early SDL software-renderer loading screen on macOS OpenGL windows so `SDL_GL_CreateContext` sees a real GL window
    - removing the unsupported GLSL `#if USE_GEOMETRY` dependency from the affected vertex shaders
    - fixing Python-2-era bare `METH_KEYWORDS` call flags that CPython 3 rejects during type registration
    - switching RTS unit initialization away from Python-2-era cooperative `super()` chaining across mixed Python/C extension bases; Apple Silicon now uses explicit `pf.AnimEntity` / `pf.CombatableEntity` initialization in the RTS classes
    - fixing Python 3 integer-division breakage in common/settings window constructors so `pf.Window` receives integer bounds again
  - current Apple Silicon render bring-up status:
    - full water rendering is now back on native arm64; the current verified path uses the regular reflection/refraction pipeline again instead of the earlier simplified fallback
    - batch rendering is now back on native arm64 as well; batched mesh shaders are enabled again and the current verified frame still shows correct world/entity rendering with batching on
  - a focused freeze/launch diagnostic pass on Apple Silicon found and fixed three high-value runtime issues:
    - the render-thread yield path could still deadlock against `SDL_GL_SwapWindow` on macOS because `R_Yield()` swapped before waking the main thread; Apple Silicon now signals `RSTAT_YIELD` before the swap
    - selection/overlay rendering used `glLineWidth` values like `2`, `3`, and `5`, which core-profile macOS rejects; Apple Silicon now clamps those requests through a compatibility helper
    - map-texture Wang tileset generation was spending an extremely long time in `R_GL_ImageQuilt_MakeTileset`; Apple Silicon now uses a fast fallback that resizes the source terrain texture into the expected 8 slots instead of blocking startup in the quilt generator
  - a later live freeze investigation on Apple Silicon found and fixed two more runtime issues:
    - `Sched_Tick()` was waiting on `s_ready_cond` without holding `s_ready_lock`, which matched a sampled hang where the main thread stayed blocked after worker threads had already gone idle
    - minimap click/drag world conversion was using the decorative outer minimap diamond instead of the terrain footprint, which could send valid terrain clicks off-map; Apple Silicon now converts through the terrain diamond and clamps the resulting world coordinate back into the playable map
  - relaunches also exposed a settings bug unrelated to OpenGL:
    - `Settings_Create()` could re-register an existing key when `pf.conf` was already present
    - this triggered `sett_add_priv` assertions on relaunch until the setting-restore path was fixed to reuse existing slots
  - current verified runtime state on this Mac:
    - the native arm64 build now reaches a visible scene quickly without the previous terrain-generation stall
    - a basic smoke test now changes visible game state on screen: the camera/view changed, a unit-selection ring appeared after interaction, and stronger minimap edge clicks now stay on-map instead of dumping the camera into the off-map black view
    - stderr stayed quiet in a later verified 65-second idle run; the earlier `Unmatched perf marker: Task 00x [navigation_tick_task]` warning no longer reproduces after the worker-thread perf cleanup
    - normal `GL_ASSERT_OK()` behavior is restored on Apple Silicon; the current native launch and idle-smoke path survives with real OpenGL assertions enabled again
    - real shadow-map rendering is now back on Apple Silicon: the current verified frontmost screenshot shows projected world shadows again after re-enabling the shadow-map bind path and the shadowed terrain shader/buffers
    - full water reflection/refraction rendering is now back on Apple Silicon: the latest verified frame shows rippled/refractive water detail again instead of the earlier flat fallback
    - batch rendering is now back on Apple Silicon: the current verified frame still shows correct world/entity rendering after re-enabling batched shaders and turning `pf.video.use_batch_rendering` back on
    - with that restored full water path in place, a fresh native launch is quiet again apart from the expected compute-shader skip
    - a longer native gameplay smoke pass now also verifies live camera motion, visible unit selection on the blue formation, a successful move order, fog-of-war reveal from that movement, and a quiet 65-second post-interaction hold with no new stderr output
  - `pf.Task` is intentionally unsupported on Python 3 in the current native port because the old implementation depends on removed CPython frame/thread-state internals; RTS bring-up proceeds without pretending that path works
  - the only concrete helper in the live codebase still depending on `pf.Task` was `scripts/common/disappearing_text_task.py`; on Python 3 it now uses a module-level `EVENT_UPDATE_START` handler instead of task fibers, so the visible text-fade behavior no longer needs the old engine-level task internals
  - the deeper `src/script/py_task.c` fiber/task port is still deferred; active RTS bring-up does not currently require engine-level `pf.Task` support
  - the first native replacement step is now verified: `scripts/editor/scene.py` exposes a reusable Python-3-safe `save_scene_from_objects()` helper, and fresh native arm64 export/import runs proved a live 388-object RTS scene can round-trip through a PFSCENE snapshot without using `S_PickleObjgraph`
  - `rts.units` now eagerly imports/registers the RTS unit modules, so scene loading outside `rts/main.py` no longer fails just because custom classes were never imported
  - the native Python 3 RTS-demo session path now also round-trips on arm64: a fresh save is written through the new PFSCENE-backed path, the matching load completes, and the probe marker reports `NATIVE_SESSION_RESTORED objs=388 regions=0 cameras=0`
  - the Session UI is now re-enabled on Python 3 for the native demo path, and the normal demo/UI event flow also verified the same roundtrip marker through a scripted in-game save/load pass
  - the native save/load path now also preserves non-empty scene-region and scene-camera metadata on arm64: a fresh probe restored `NATIVE_SESSION_RESTORED objs=388 regions=1 cameras=1 region_names=native_session_probe_region camera_names=native_session_probe_camera`
  - the normal Python 3 Session UI flow now also preserves that richer metadata on arm64: a fresh scripted in-game save/load pass restored `NATIVE_SESSION_RESTORED objs=388 regions=1 cameras=1 region_names=native_ui_session_probe_region camera_names=native_ui_session_probe_camera`
  - the later Apple Silicon load crash after pressing Session -> Load is now fixed:
    - `Engine_FlushRenderWorkQueue()` now swaps and drains the correct workspace from task context and resumes the render thread across `RSTAT_YIELD` while large restore batches are flushing
    - `R_GL_MoveClearState()` no longer performs compute-shader-only cleanup unsafely on the non-compute macOS path, and the stale SSBO reset typos in `gl_movement.c` are corrected
    - a final clean scripted Session UI roundtrip again restored `NATIVE_SESSION_RESTORED objs=388 regions=1 cameras=1 region_names=native_ui_session_probe_region camera_names=native_ui_session_probe_camera` with no error file and only the expected compute-shader skip on stderr
  - the old custom Python pickler is still deferred; the remaining session work is mostly broader manual validation rather than basic entity reconstruction for the current RTS demo

## What Looks Reusable For An HFMP S2-Like RTS

- Strong candidates to reuse directly:
  - Tile map + scene loading
  - RTS camera/input scaffolding
  - Selection, minimap, fog of war, building, gathering, garrison, projectile, formation, diplomacy systems
  - Navigation/pathfinding stack
  - Renderer, terrain, shadows, water, animation, asset formats
  - Python-exposed gameplay API
- Likely replace heavily:
  - All game-specific Python scripts under `scripts/rts/`
  - Unit/building/faction data and behavior
  - Maps, scenes, assets, UI theme/UX
  - Campaign content and mission scripting
- Likely port/fix before a serious Mac-based workflow:
  - Build system
  - Embedded Python runtime strategy
  - Scheduler/context switching for Apple Silicon
  - Dependency strategy, especially GLEW and packaged libs

## Rules / Options / Stock Game Design Audit

- Terrain, scene, and model data are intentionally separate:
  - `PFMAP` stores terrain materials, splat mappings, and tile-level geometry/pathability data.
  - `PFSCENE` stores factions, entities, and optional regions/cameras layered over a map.
  - `PFOBJ` stores mesh/material data plus optional skeleton, animation, and collision bounds.
- The stock RTS demo is defined by [scripts/rts/main.py](/Users/dev/Desktop/OpenGL%20RTS%20game%20engine/scripts/rts/main.py), which:
  - loads `assets/maps/demo.pfmap`
  - loads `assets/maps/demo.pfscene`
  - sets the skybox
  - marks factions `1`, `2`, and `3` as mutually at war
  - leaves only faction `1` player-controllable by default
  - installs a main RTS camera plus a debug FPS camera
  - binds `C` to camera toggle and `P` to pause toggle
- The stock scene currently defines 4 factions:
  - `Mother Nature`
  - `Sinbad's Forces`
  - `Goblin Confederacy`
  - `Wild Barbarians`
- The stock scene currently has `388` entities total.
- Script-visible class counts in `assets/maps/demo.pfscene`:
  - `Goblin`: `16`
  - `Knight`: `12`
  - `Mage`: `10`
  - `Chicken`: `8`
  - `Berzerker`: `8`
  - `Sinbad`: `1`
- The demo shell in [scripts/rts/views/demo_window.py](/Users/dev/Desktop/OpenGL%20RTS%20game%20engine/scripts/rts/views/demo_window.py) exposes:
  - controlled faction switching
  - settings
  - performance
  - pause/resume
  - session save/load
  - console
  - exit
- The action pad in [scripts/rts/views/action_pad_window.py](/Users/dev/Desktop/OpenGL%20RTS%20game%20engine/scripts/rts/views/action_pad_window.py) is a `3 x 4` grid driven by the first selected controllable unit.
- Stock shared unit actions:
  - slot `0`: `Move`, hotkey `M`
  - slot `1`: `Stop`, hotkey `S`
  - slot `2`: `Hold Position`, hotkey `H`
  - slot `3`: `Attack`, hotkey `A`
- Orders are not hard-coded per click site; instead, scripts set engine-side left-click target modes like:
  - `pf.set_move_on_left_click()`
  - `pf.set_attack_on_left_click()`
  - other engine-supported target modes also exist for build, gather, pick-up, drop-off, garrison, rally, and transport
- Stock unit role/stat design in the demo scripts:
  - `Knight`: melee, `150 HP`, `50 dmg`, `0.50 armour`
  - `Goblin`: melee, `120 HP`, `40 dmg`, `0.30 armour`
  - `Mage`: ranged projectile, `100 HP`, `80 dmg`, `0.10 armour`, `50` range
  - `Berzerker`: heavy melee, `220 HP`, `80 dmg`, `0.25 armour`
  - `Sinbad`: hero-like showcase unit, `250 HP`, `80 dmg`, `0.50 armour`, extra idle-toggle action
  - `Chicken` / `Deer` / `Doe`: ambient mobile wildlife
- Player-facing settings currently wired through the stock UI:
  - video: aspect ratio, resolution, window mode, always-on-top, vsync, shadows, water reflections
  - game: health bars
  - runtime shell: controlled faction, performance, pause/resume, session, console
- Additional engine/config settings currently available through `pf.conf` / settings registration:
  - audio:
    - `pf.audio.master_volume`
    - `pf.audio.music_volume`
    - `pf.audio.effect_volume`
    - `pf.audio.music_playback_mode`
    - `pf.audio.mute_on_focus_loss`
  - game:
    - `pf.game.fog_of_war_enabled`
    - `pf.game.camera_zoom`
    - `pf.game.movement_hz`
    - `pf.game.combat_hz`
    - `pf.game.movement_use_gpu`
    - `pf.game.storage_site_ui_mode`
  - video:
    - `pf.video.use_batch_rendering`
    - `pf.video.water_refraction`
  - debug:
    - `pf.debug.render_log_mask`
    - `pf.debug.trace_python`
    - `pf.debug.trace_gpu`
    - navigation, formation, combat, automation, hearing, and faction-vision overlays
- The most important fork constraints from this audit:
  - keep the `PFMAP + PFSCENE` split
  - keep fog-of-war and minimap as core mechanics
  - keep faction controllability and diplomacy as real engine concepts
  - keep the action pad small and icon-driven
  - keep hero differentiation grounded in role, passives, equipment, veterancy, and battlefield bonuses before adding any spell-heavy layer
  - keep the current Apple Silicon path as the practical Mac shipping baseline: no compute dependency for core gameplay, readable HUD/minimap, and batch-friendly content

## Current Best Assessment

- Understanding the engine locally is very feasible.
- Running the stock game/demo natively on this Apple Silicon Mac is now good enough for real game-polish work, not just bring-up.
- The current Apple Silicon baseline is now aligned in the repo itself:
  - `pf.video.vsync`, `pf.video.use_batch_rendering`, shadows, and full water are on
  - `pf.game.movement_use_gpu` remains off
  - `pf.game.combat_hz` is back to `1.0`
  - hard-coded local resolution/aspect overrides were removed from `pf.conf` so startup again uses the native desktop size
- `make run PLAT=MACOS_ARM64` now launches the real native game path.
- Repo-backed validation now exists under `scripts/macos`:
  - `pf_native_launch_probe.py` verifies the current Mac runtime settings after a real launch
  - `pf_native_session_ui_region_camera_roundtrip.py` verifies the normal Session UI save/load roundtrip with non-empty region/camera metadata
  - `pf_native_settings_apply_probe.py` plus `pf_native_settings_verify_restore_probe.py` verify that settings changed through the existing controllers persist across relaunch and can be restored to the baseline
- The settings path is cleaner now too:
  - `pf.game.healthbar_mode` is no longer written as a bool from the Game settings page; the controller now applies explicit `HB_MODE_DAMAGED` / `HB_MODE_NEVER` values
- The current Apple Silicon polish work is now mostly about repeatable validation and broader manual gameplay/settings confidence, not first-port renderer/runtime rescue.
- That final broader manual validation has now passed too:
  - camera, minimap, selection, move, attack, pause/resume, fog-of-war reveal, Session save/load, and live settings checks all succeeded in the real game UI
  - for the existing game, the Apple Silicon OpenGL path is now in a good enough state to treat as the working Mac baseline
- The Metal-native fork work has now started from that stable baseline:
  - a pre-Metal backup snapshot is saved at `backups/2026-04-22-metal-fork-start/`
  - Makefile now supports `RENDER_BACKEND=OPENGL` and `RENDER_BACKEND=METAL`
  - backend builds now use backend-specific `obj/` directories so `OPENGL` and `METAL` artifacts no longer collide
  - `make run` now rebuilds the selected backend before launch
  - the default repo path remains `OPENGL`
- The first backend split is now in place:
  - shared renderer control/settings/workspace logic stays in `src/render/render.c`
  - OpenGL bootstrap/context/present logic moved into `src/render/backend_gl.c`
  - the first Metal bootstrap lives in `src/render/backend_metal.m`
  - shared window flags, drawable-size queries, and present hooks now go through backend wrappers instead of assuming `SDL_GL_*`
- The first verified Metal result is now a little deeper than cold launch:
  - `make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL` succeeds
  - `./bin/pf-arm64 ./ ./scripts/macos/pf_metal_launch_probe.py` survives engine startup and reports `pf.render.backend=METAL`
  - the current Metal runtime now executes real frame begin/end/present work plus Nuklear font-atlas upload and UI draw-list rendering
  - a live Metal run now shows the stock startup menu/UI on-screen, and the next slice now also draws a simplified version of the real terrain chunk mesh instead of leaving the whole world black
  - the first world-render milestone is intentionally narrow: Metal now consumes the real camera matrices plus terrain `R_GL_Draw` calls and shades the terrain geometry with a simple material-index palette, while meshes/minimap/selection/world parity are still pending
  - the next slice now also preserves CPU copies of non-animated mesh vertices and shades them from their CPU-side material diffuse colors on Metal
  - the next slice now also preserves CPU copies of animated `anim_vert` streams, marks pose-buffer usage during asset load, and software-skins the first visible units on Metal from live joint matrices; the current screenshot is saved at `backups/2026-04-22-metal-fork-slice-6/pf_metal_skinned_mesh_live.png`
  - the next slice now also routes `R_GL_DrawSelectionCircle` and `R_GL_DrawSelectionRectangle` through the Metal backend, using the same CPU-side selection radius, OBB, color, and terrain-height sampling as the OpenGL path; the current screenshot is saved at `backups/2026-04-22-metal-fork-slice-7/pf_metal_selection_overlay_probe_live.png`
  - the next slice now also routes `R_GL_DrawBox2D` through the Metal backend, using the same top-left drawable coordinates and signed-size semantics as the OpenGL path; the current screenshot is saved at `backups/2026-04-22-metal-fork-slice-8/pf_metal_dragbox_live.png`
  - the next slice now also routes the first minimap path through the Metal backend: it bakes a top-down terrain minimap texture, renders the rotated minimap diamond on-screen, overlays unit dots using the same normalized minimap-space math as the OpenGL path, and now also draws the camera-frustum overlay through the same CPU-side frustum math with explicit minimap-local clipping before screen transform; the current screenshot is saved at `backups/2026-04-22-metal-fork-slice-11/pf_metal_minimap_frustum_live.png`
  - the next slice now also routes `R_GL_DrawHealthbars` through the Metal backend, using the same camera/world-to-screen placement math and size rules as the OpenGL path with a simple bordered fill-bar draw; the current screenshot is saved at `backups/2026-04-22-metal-fork-slice-13/pf_metal_healthbar_live.png`
  - the next slice now also routes `R_GL_DrawMapOverlayQuads` through a dedicated blended Metal world-color pipeline, so terrain-conforming fog/debug tile overlays can render as translucent filled quads plus outlines on top of the Metal scene; the current screenshot is saved at `backups/2026-04-22-metal-fork-slice-14/pf_metal_map_overlay_probe.png`
  - the next slice now also adds a repeatable Metal gameplay smoke probe at `scripts/macos/pf_metal_gameplay_smoke_probe.py`; the current pass marker is `METAL_GAMEPLAY_SMOKE_PASS backend=METAL camera=1 selection=1 move=1 pause=1 attack=1`, so the Metal path now proves camera, selection, move, pause/resume, and an attack/contact step in the live RTS demo
  - the next slice now also proves the richer Python 3 Session UI save/load roundtrip on Metal without extra code changes: `scripts/macos/pf_native_session_ui_region_camera_roundtrip.py` restored `NATIVE_SESSION_RESTORED objs=388 regions=1 cameras=1 region_names=native_ui_session_probe_region camera_names=native_ui_session_probe_camera` on a `RENDER_BACKEND=METAL` build with an empty error marker
  - the next slice now also restores live terrain fog-of-war shading on Metal: `R_GL_MapUpdateFog` now stays resident as a Metal fog buffer, the terrain uniforms are bound on both the vertex and fragment stages, and the terrain fragment path now shades against the same chunk-major fog state layout as the OpenGL runtime; the current screenshot is saved at `backups/2026-04-22-metal-fork-slice-17/pf_metal_fog_live.png`
  - the next slice now also restores visible water areas on Metal through the terrain path: `R_GL_MapBegin` now uploads a per-tile water mask built from real map tiles, and the Metal terrain fragment path uses that mask for a first wave-tinted water pass over actual ponds/lakes; this is intentionally still below full OpenGL water parity because reflection/refraction are not ported yet, and the current screenshot is saved at `backups/2026-04-22-metal-fork-slice-18/pf_metal_water_live.png`
  - the next slice now also restores first-pass real terrain texturing on Metal: `R_GL_MapInit` now loads the map's source terrain textures into a Metal texture array, and the Metal terrain shader samples that array through the existing terrain UV/material-index path instead of only shading from the temporary flat material palette; the current screenshot is saved at `backups/2026-04-22-metal-fork-slice-19/pf_metal_textured_terrain_live.png`
  - the next slice now also restores first-pass real textured static/skinned meshes on Metal: mesh asset `base_path` is now preserved in `render_private`, the Metal backend lazily builds a per-mesh material texture array from the same `texname` list the OpenGL path already uses, and both static and software-skinned animated draws now sample those textures through the existing UV/material-index path; the current screenshot is saved at `backups/2026-04-22-metal-fork-slice-20/pf_metal_textured_meshes_live.png`
  - the next slice now also restores the first real Metal foliage/tree cutout path: after sampling mesh material textures the Metal fragment shader now premultiplies sampled RGB by alpha before applying the existing alpha-test discard, the material upload path marks meshes whose source textures carry real alpha as cutout meshes, and those meshes now render with backface culling disabled so foliage planes do not collapse into missing or dark silhouettes; known vegetation textures like `assets/models/pine_tree/pino.png`, `assets/models/shrub/planta.png`, `assets/models/fern/fern_leaf.png`, and the bush textures under `assets/models/bushes/` now route through that cutout-safe path automatically
  - the next slice now also restores the first Metal batch-rendering compatibility path: `pf.video.use_batch_rendering` is no longer forced back off when the backend is `METAL`, and the Metal backend now accepts `R_GL_Batch_Draw` / `R_GL_Batch_DrawWithID` by replaying the already-prepared animated/static visible lists through the current Metal draw helpers instead of dropping batched runtime scene draws entirely; this is intentionally functional parity first, not batch-performance parity yet, because chunk allocation/reset stay as safe no-ops and the depth-map batch path is still deferred with Metal shadow work
  - the next slice now also restores the first true Metal batch-performance path for runtime static meshes: when Metal receives the batch draw commands, it now groups opaque static entities by shared `render_private`, CPU-transforms those mesh vertices into world space, and submits merged vertex streams through the existing Metal static-mesh path with an identity model matrix; animated meshes and translucent static meshes intentionally stay on the safe per-entity replay path for now so we get a real first draw-call/setup reduction without risking ordering regressions
  - the next slice now also extends that true Metal batch-performance path to opaque animated meshes: when Metal receives the batch draw commands, it now groups non-translucent animated entities by shared `render_private`, CPU-skins each entity from its live joint pose into world-space vertices, and submits those merged animated streams through the same Metal static-mesh path with an identity model matrix; translucent animated and translucent static meshes still intentionally stay on the per-entity replay path because blended ordering remains the last risky batch-parity gap
  - the next slice now also restores conservative translucent Metal batch parity: translucent mesh draws now use a dedicated blended Metal pipeline that mirrors the current OpenGL mesh blend mode, translucent static and animated batches only merge consecutive entities with the same `render_private` so draw order stays intact, the merged-stream helper now draws the full combined vertex count instead of a single-entity count, and the translucent animated fallback now redraws the full failed run instead of silently dropping later entities after a partial merge failure
  - the next slice now also restores the first real Metal MSAA path: the main on-screen Metal frame now renders into a multisampled color target and resolves into the CAMetalLayer drawable during present, while offscreen passes like minimap bake/update keep their single-sample pipelines so the first anti-aliasing slice improves the visible game frame without regressing the already-working auxiliary render paths
  - the next slice now also restores the first real Metal frame-pacing / CPU-GPU synchronization path: the main on-screen Metal frame no longer blocks the CPU on every present with `waitUntilCompleted`, but instead uses a small in-flight semaphore plus command-buffer completion handlers to keep at most a bounded number of frames in flight, while the CAMetalLayer setup now keeps display sync enabled, disables drawable timeouts, and requests up to three drawables when supported
  - the next slice now also upgrades the current Metal water path without pretending full OpenGL water parity is done: `R_GL_WaterInit` now loads the real DUDV and normal maps, the Metal terrain shader uses those resources plus the current scene camera position for animated distortion, fresnel-style view response, and highlights over true water tiles, and `scripts/macos/pf_metal_water_probe.py` verifies the path with `METAL_WATER_PROBE_PASS backend=METAL water_x=228.00 water_z=-148.00 water_h=-12.00`; the separate `R_GL_DrawWater` reflection/refraction texture stack is now partially in place through offscreen reflection/refraction targets plus a first clipped/entity scene pass, but full skybox-inclusive and refraction-depth-aware parity is still deferred
  - the next slice now also establishes the first Metal main-frame depth-buffer foundation: the on-screen Metal frame creates and clears a `Depth32Float` attachment that matches the drawable size and MSAA sample count, terrain and opaque mesh draws now write depth, translucent mesh draws depth-test without writing, and UI/selection/minimap/debug overlays explicitly keep depth disabled so existing gameplay feedback remains visible; the launch/gameplay/session/water probes still pass after this depth slice
  - the next slice now also restores first-pass Metal shadow-map parity: the backend handles the engine's existing `R_GL_DepthPassBegin` / depth-draw / `R_GL_Batch_RenderDepthMap` / `R_GL_DepthPassEnd` flow, renders terrain/static/animated casters into a `Depth32Float` shadow map, then samples that depth texture from the regular terrain and mesh shaders through the computed light-space transform; this is functional parity first, with bias/filtering and visual tuning still available as later quality work
  - the next slice now also applies the first Metal shadow-quality tuning pass: terrain and mesh shaders use a small 3x3 PCF-style manual filter instead of a one-tap hard comparison, add slope-aware bias from normal/light direction, and soften the shadow multiplier slightly while keeping the existing launch/gameplay/session/water probes green
  - the next slice now also routes `R_GL_DrawWater` through Metal as a first post-scene water-surface foundation: it builds a dedicated blended water pipeline, draws the same map-sized water quad shape as the OpenGL path, uses the live water mask plus DUDV/normal resources, and depth-tests without writing depth so water does not paint over foreground terrain/units; full offscreen reflection/refraction texture parity remains the next water step
  - the next slice now also adds the first real Metal offscreen water-texture stack: the backend allocates reflection/refraction color targets plus matching depth targets, rerenders terrain into those textures between the main scene and the resumed water-surface pass, and the Metal water shader now samples those textures for a first real scene-driven reflection/refraction response; this is still terrain-only and does not yet match the OpenGL path's clipped above/below-water scene separation, reflected skybox, or reflected/refracted entity parity
  - the next slice now also adds the first clipped/entity Metal water-scene pass: the offscreen reflection/refraction passes now carry a simple water clip mode, terrain and mesh shaders discard fragments on the wrong side of the water plane during those passes, and the existing Metal static/skinned/batched entity helpers now render real scene entities into the offscreen water textures instead of leaving that first scene-texture path terrain-only
  - the next slice now also removes one of the current Metal backend's biggest avoidable smoothness costs: terrain and non-animated mesh draws cache persistent Metal vertex buffers instead of allocating fresh `MTLBuffer` objects from CPU-side vertex copies every frame
  - the current Apple guidance fit for this project is to finish smooth playable-scene parity first, then add anti-aliasing and stronger frame pacing, then restore richer scene features like skybox/shadows/full water, and only after that spend time on HDR, MetalFX upscaling, indirect command buffers, and faster asset-streaming paths
  - the current world-feedback slice is still intentionally narrow: unit/building selection shapes, drag-box UI, healthbars, a first minimap with terrain, unit dots, and clipped camera-frustum overlay, a first translucent map-overlay/faction-vision slice, a first scripted gameplay smoke pass, the richer Session UI roundtrip, live terrain fog-of-war shading, a first visible water slice plus richer DUDV/normal-driven terrain-path water, a depth-backed post-scene water-surface foundation, a first offscreen reflection/refraction texture stack, and a first clipped/entity water-scene pass, a first real terrain-texturing pass, a first real textured static/skinned-mesh pass, a first real foliage/tree cutout-material path, a first Metal batch-rendering compatibility path, first true batch-performance paths for opaque static, opaque animated, and conservative translucent meshes, a first on-screen MSAA pass, a first bounded in-flight frame-pacing slice, a main-frame depth-buffer foundation, first functional shadow-map parity, and first shadow-filter/bias tuning all render on Metal, but broader gameplay validation, full skybox-inclusive/refraction-depth-aware water parity, richer terrain-material parity, and later parity features are still pending
  - the Metal build still links the existing OpenGL renderer symbols for now while the draw-path migration is incomplete
- The most realistic near-term options are now:
  - Keep the Apple Silicon OpenGL baseline stable as the fallback while the Metal backend advances through startup UI, playable runtime scene, then editor support.
  - Continue the Metal renderer migration incrementally instead of mixing it with HFMP gameplay redesign right now.
  - Use the existing OpenGL path for normal game validation until Metal reaches scene-rendering parity.
- Quick local shortcut check:
  - No existing Steam, Wine, Whisky, or CrossOver installation was found on this Mac.

## Questions To Answer Next

- Which `src/` subsystems own rendering, simulation, pathfinding, scripting, and save/load?
- Are the gameplay systems mostly in Python scripts or split deeply across C and Python?
- What are the concrete blockers for building on Apple Silicon/macOS?
- Is there a faster path to "trying the game" on Mac via a packaged demo, Wine/CrossOver, or a source port?
- For an HFMP S2-like game, what should be reused directly versus replaced?
