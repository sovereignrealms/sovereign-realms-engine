# Permafrost macOS Port And Execution Plan

## Summary

- Status: `execution in progress`
- Current milestone: `Phase 2 - Native arm64 engine bring-up`
- Current milestone status: `in progress; native arm64 now links, launches, and responds to basic in-game input on Apple Silicon while Phase 1 remains blocked on Rosetta host setup`
- Current scope for this workstream:
  1. Rosetta `x86_64` demo bring-up on Apple Silicon
  2. native `MACOS_ARM64` engine bring-up with the existing scheduler model
  3. runtime modernization: `Python 2.7 -> Python 3.13`, `C99 -> gnu11`, native macOS GL loader
  4. custom Python pickler handled later, not in native arm64 v1

## Phase Status

- `Phase 0: Discovery and feasibility` - `completed`
- `Phase 1: Rosetta x86_64 demo bring-up` - `blocked`
- `Phase 2: Native arm64 engine bring-up` - `in progress with successful native launch, visible demo window, and degraded-renderer validation`
- `Phase 3: Python 3.13 migration` - `in progress enough to unblock the wider native build, with temporary feature gates for unsupported task/save paths`
- `Phase 4: Save/load and custom pickler follow-up` - `partial with a verified native Python 3 RTS-demo session roundtrip through probe, normal Session UI flow, and non-empty region/camera coverage on Apple Silicon`

## Current Implementation Notes

- Added `PLAT=MACOS_X86_64` Makefile support using host-installed x86_64 dependencies.
- Added `PLAT=MACOS_ARM64` dependency scaffolding and explicit build guards for the still-pending native phase.
- Added macOS dependency validation helpers for Rosetta and native arm64.
- Added a safe `git describe` fallback for archive-style source trees with no `.git` metadata.
- Kept the existing x86_64 scheduler, `C99`, Python `2.7`, and current runtime behavior for the first bring-up.
- Added an engine-owned macOS OpenGL loader in `src/render/gl_loader.[ch]` so the macOS path no longer depends on GLEW.
- Rewired renderer feature checks and fallbacks to use the new loader capabilities for debug output, compute support, timer queries, copy-image, buffer-storage, and multi-draw-indirect.
- Added macOS fallbacks for terrain buffer allocation and texture-array debug/copy paths when newer OpenGL helpers are unavailable.
- Added a first native Darwin arm64 scheduler/context-switch backend while keeping the existing stackful task model.
- Moved the native build to `gnu11`-style strictness cleanup across engine/gameplay code that now compiles under Apple clang.
- Started the Python 3.13 bridge migration far enough for the native arm64 build to move past the script layer and into core engine/render modules.
- The native arm64 build now links and produces `bin/pf-arm64`.
- The Python 3 path currently treats `pf.Task` as unsupported during bring-up instead of attempting a broken partial port of old CPython frame/thread-state internals.
- The only concrete Python-side helper still depending on `pf.Task` for the live codebase was `scripts/common/disappearing_text_task.py`; on Python 3 it now uses a module-level `EVENT_UPDATE_START` handler instead of task fibers.
- The deeper `src/script/py_task.c` fiber/task port remains deferred because the active RTS bring-up does not currently require engine-level `pf.Task` support.
- The Session window and RTS demo Session entry point are now re-enabled on Python 3 for the native path because the normal demo/UI save-load roundtrip is verified on Apple Silicon.
- The first native replacement step is now in place: `scripts/editor/scene.py` exposes a reusable Python-3-safe `save_scene_from_objects()` helper that can snapshot live RTS entities into a PFSCENE file without using `S_PickleObjgraph`.
- The native Python 3 session snapshot path now also preserves optional scene cameras and can re-wrap already-restored engine regions without colliding with `G_LoadGlobalState()`.
- That scene-snapshot foundation is verified end to end on Apple Silicon:
  - a native arm64 export run wrote `tmp_native_scene_snapshot_test.pfscene` from the live RTS scene with `EXPORTED_SCENE_OBJS=388`
  - a fresh native arm64 import run then loaded that snapshot back with `IMPORTED_SCENE_OBJS=388`
- The native Python 3 session replacement now also works for the current RTS demo roundtrip: the live scene is saved through the new PFSCENE-backed path, reloaded on arm64, and re-bootstrapped into the RTS runtime without using `S_PickleObjgraph`.
- The post-load continuation bug on Apple Silicon is now fixed:
  - task-context render flushing now swaps and drains the correct render workspace instead of deferring the entire session-load queue to the first resumed frame
  - task-context render flushing now restarts the render thread across `RSTAT_YIELD` boundaries during large restore batches instead of stalling mid-flush
  - movement render-state teardown no longer calls compute-shader cleanup unsafely on non-compute macOS paths, and the stale SSBO handle resets are corrected
- The remaining session work is now narrower:
  - broader manual/user-driven validation beyond the scripted UI roundtrip
  - the old custom Python pickler remains deferred
- Runtime validation of `bin/pf-arm64` on this Apple Silicon Mac is active and has now reached a stable early-launch smoke pass.
- Native Python 3 unit initialization on Apple Silicon now uses explicit RTS-side initialization instead of relying on the old cooperative `super()` chain across mixed Python/C extension bases.
- Common RTS/settings window constructors were updated for Python 3 integer division so `pf.Window` bounds no longer fail on float coordinates.
- Native Apple Silicon water rendering now runs through the full water path in `src/render/gl_water.c` again.
- The restored Apple Silicon water path now uses the regular reflection/refraction pipeline instead of the earlier simplified fallback:
  - the latest verified frame shows rippled/refractive water detail on arm64 instead of the earlier flat translucent surface
  - the fresh launch path remains quiet on stderr apart from the expected compute-shader skip
- A longer native gameplay smoke pass has now verified live camera motion, visible unit selection, a successful move order, fog-of-war reveal from unit movement, and a quiet 65-second stability hold on this Mac.
- Native Apple Silicon now also has two verified render-path fixes in place:
  - generic mesh draws only bind the animation pose buffer for animated assets instead of all meshes
  - terrain/generic mesh shaders now bind and use the real shadow-map path on macOS arm64 instead of the earlier degraded no-shadow path
- Native Apple Silicon now also has the batch-rendering path back on:
  - batched mesh shaders are no longer skipped during shader init on arm64
  - the default and current local config now both enable `pf.video.use_batch_rendering`
- Native Apple Silicon now also has three responsiveness/compatibility fixes in place:
  - the render-thread yield path now signals the main thread before `SDL_GL_SwapWindow` on Apple Silicon so loading-time swap waits do not deadlock the app
  - 2D/overlay line-width requests are clamped through a macOS-compatible path instead of tripping core-profile `GL_INVALID_VALUE`
  - map-texture Wang tileset generation uses a fast Apple Silicon fallback upload path instead of stalling startup in the expensive quilt generator
- Native Apple Silicon now also has two verified runtime-stability fixes in place:
  - `Sched_Tick()` now waits on `s_ready_cond` while actually holding `s_ready_lock`, fixing the sampled Apple Silicon hang where the main thread could wait forever after workers had already gone idle
  - minimap click/drag world conversion now uses the terrain diamond instead of the decorative outer minimap bounds, and the resulting world coordinate is clamped back into the playable map before camera movement
- `Settings_Create()` now correctly reuses existing settings slots when `pf.conf` is present, which removed the duplicate-registration assert seen on relaunch.
- The first visible native demo screenshot is saved at `macos_port_screenshot_2026-04-20.png`.
- Installed `cmake` and `pyenv` in `/opt/homebrew`.
- Installed native arm64 `openal-soft` and `mimalloc` in `/opt/homebrew`.

## Verified Results

- `completed` `make deps PLAT=MACOS_X86_64` now performs a real dependency validation pass for the Rosetta lane.
- `completed` `make deps PLAT=MACOS_ARM64` now performs a real dependency validation pass for the native arm64 lane.
- `completed` Helper scripts pass shell syntax validation.
- `completed` `make -n pf PLAT=MACOS_X86_64` expands to Rosetta `clang` compile commands with the new macOS target wiring.
- `completed` `make pf PLAT=MACOS_ARM64` now fails immediately with the explicit pending-phase message instead of falling through into a broken build.
- `completed` `make run_editor PLAT=MACOS_X86_64` now fails with the explicit unsupported-phase message.
- `completed` macOS dependency checks no longer require `glew`; `make deps PLAT=MACOS_X86_64` now reports only the missing x86_64 Homebrew libraries and Python 2.7 toolchain.
- `completed` `make -B obj/render/gl_loader.o obj/render/render.o obj/render/gl_batch.o PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 EXTRA_FLAGS='-Wno-deprecated-non-prototype -Wno-unused-but-set-variable'` succeeds.
- `completed` `make -B obj/render/gl_texture.o obj/render/gl_ringbuffer.o obj/render/gl_terrain.o PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 EXTRA_FLAGS='-Wno-deprecated-non-prototype -Wno-unused-but-set-variable'` succeeds.
- `completed` Native arm64 warning cleanup now covers typed vector comparators, SDL global-event registration signatures, and SDL window flag accumulation.
- `completed` `make -B obj/event.o obj/cursor.o obj/cam_control.o obj/main.o obj/audio/al_audio.o obj/map/raycast.o obj/render/render.o obj/render/gl_batch.o obj/game/clearpath.o obj/game/game.o obj/game/region.o PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1` now compiles through the prior `gnu11` warning blockers until it reaches the Python bridge.
- `completed` `make -B obj/script/py_console.o PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1` now succeeds because the interactive console is stubbed on Python 3.
- `completed` `make -B obj/script/py_pickle.o obj/script/py_script.o PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1` succeeds with the Python 3 compatibility layer, module registration changes, modern `sys.argv` handling, weakref updates, and save/load disabled on Python 3.
- `completed` `make -B obj/sched.o obj/context_switch.o PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1` succeeds with the new Darwin arm64 scheduler backend and AArch64 context-switch trampolines.
- `completed` `make -B obj/render/gl_image_quilt.o PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1` succeeds after fixing macOS header portability in the render path.
- `completed` `make -B pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1` now links successfully and produces `bin/pf-arm64`.
- `completed` The previous native blocker in `src/script/py_entity.c` is cleared; the current native frontier is runtime startup validation on Apple Silicon.
- `completed` `pf.Task` and Python-backed save/load are explicitly gated off on Python 3 for the current native macOS bring-up so the port fails clearly instead of depending on removed CPython internals.
- `completed` Native runtime launch blockers cleared so far include:
  - macOS GL loader fallback to framework symbols when `SDL_GL_GetProcAddress` omits core functions
  - skipping the early software loading-screen path on macOS OpenGL windows so SDL still creates a real GL window/context
  - removing unsupported GLSL `#if USE_GEOMETRY` dependency from the affected vertex shaders
  - fixing Python-2-era bare `METH_KEYWORDS` method flags that CPython 3 rejects during type registration
- `completed` `./bin/pf-arm64 ./ ./scripts/rts/main.py` now launches on this Apple Silicon Mac, reports only the expected missing `pf.conf` warning and compute-shader skip, and stays alive for an approximately 60-second smoke run without a new crash on stderr.
- `completed` Native arm64 scene loading now succeeds on this Mac after fixing Python 3 package imports, unit initializer chaining, and Python 2 integer-division assumptions in the RTS/common window scripts.
- `completed` Native arm64 now reaches a visible in-game frame with the RTS demo UI, minimap, action pad, terrain, and units rendered on screen; see `macos_port_screenshot_2026-04-20.png`.
- `completed` Native arm64 now reaches a real on-screen world render again after fixing the terrain/generic shadow-sampler conflict; the current screenshot shows playable scene content instead of the earlier blank background.
- `completed` Fresh Apple Silicon stack samples no longer show the previous minute-long startup stall in `R_GL_ImageQuilt_MakeTileset`; after the terrain fallback, the render thread spends its time in normal frame/render work.
- `completed` A fresh native Apple Silicon interaction smoke test now changes visible game state: the camera/view changed, a unit selection ring became visible, and the app stayed responsive during the test.
- `completed` A focused Apple Silicon freeze investigation found and fixed a real scheduler bug in `Sched_Tick()`, where the main thread was waiting on `s_ready_cond` without holding `s_ready_lock`.
- `completed` Minimap interaction on native Apple Silicon is now validated beyond the earlier camera-change smoke test: a stronger lower-left terrain click no longer sends the camera into the off-map black view, and the corrected scene remains stable after a short idle hold.
- `completed` The repeated `Unmatched perf marker: Task 00x [navigation_tick_task]` warning no longer reproduces in a verified 65-second native Apple Silicon idle run after suppressing frame-boundary false positives for worker-thread task stacks.
- `completed` Normal `GL_ASSERT_OK()` behavior is restored on Apple Silicon; the current native launch and idle-smoke path now survives with real OpenGL assertions enabled.
- `completed` A fresh `./bin/pf-arm64 ./ ./scripts/rts/main.py` launch with the restored full Apple Silicon water path again reports only the expected compute-shader skip on this Mac.
- `completed` Full water reflection/refraction rendering is now back on native Apple Silicon: the restored path launches cleanly, stays quiet on stderr after first render, and the latest verified frame shows rippled/refractive water detail instead of the earlier flat fallback.
- `completed` Real shadow-map rendering is now back on native Apple Silicon: after re-enabling the shadow-map bind path, the shadowed terrain shader, and the terrain shadow buffers, a fresh launch stayed quiet on stderr and a live frontmost screenshot showed projected world shadows again.
- `completed` Batch rendering is now back on native Apple Silicon: after re-enabling batched shader init and turning `pf.video.use_batch_rendering` back on, the native arm64 build launched cleanly, stayed quiet on stderr, and the live frame continued to show correct world/entity rendering.
- `completed` `python3 -m py_compile scripts/common/disappearing_text_task.py` now succeeds with the Python 3 compatibility shim for the old `pf.Task`-backed disappearing-text helper.
- `completed` A fresh `make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1` and `./bin/pf-arm64 ./ ./scripts/rts/main.py` relaunch after the disappearing-text compatibility patch still build and launch cleanly, with no new startup output beyond the expected compute-shader skip.
- `completed` `python3 -m py_compile scripts/common/views/session_window.py scripts/rts/view_controllers/demo_vc.py` succeeds after the native Python 3 session-window update.
- `completed` A fresh `make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1` after the session-path update still links successfully.
- `completed` A direct runtime probe through `./bin/pf-arm64 ./ /tmp/pf_session_api_check.py` now prints:
  - `PF_SAVE_SESSION_NOT_IMPLEMENTED: Session save is unavailable on Python 3 in the current macOS native port.`
  - `PF_LOAD_SESSION_NOT_IMPLEMENTED: Session load is unavailable on Python 3 in the current macOS native port.`
- `completed` `python3 -m py_compile scripts/rts/views/demo_window.py scripts/rts/view_controllers/demo_vc.py` succeeds after removing the native Python 3 Session entry point from the RTS demo.
- `completed` A fresh `make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1` and `./bin/pf-arm64 ./ ./scripts/rts/main.py` relaunch after the Session-entry cleanup still build and launch cleanly, with no new startup output beyond the expected compute-shader skip.
- `completed` `python3 -m py_compile scripts/editor/scene.py scripts/rts/units/__init__.py scripts/rts/units/anim_moveable.py scripts/rts/units/anim_combatable.py` succeeds after making the scene writer reusable from Python 3 and making RTS unit-class registration/import safe outside `rts/main.py`.
- `completed` `./bin/pf-arm64 ./ /tmp/pf_native_scene_export.py` now exports a live RTS scene snapshot on Apple Silicon and reports `EXPORTED_SCENE_OBJS=388`.
- `completed` `./bin/pf-arm64 ./ /tmp/pf_native_scene_import.py` now loads that exported snapshot on a fresh Apple Silicon run and reports `IMPORTED_SCENE_OBJS=388`.
- `completed` The native Python 3 RTS-demo session roundtrip now verifies end to end on Apple Silicon:
  - a fresh `./bin/pf-arm64 ./ /tmp/pf_native_session_save.py` writes `tmp_native_session_roundtrip.pfsave`
  - a fresh `./bin/pf-arm64 ./ /tmp/pf_native_session_load.py` now restores that save and writes `NATIVE_SESSION_RESTORED objs=388 regions=0 cameras=0`
- `completed` The re-enabled Python 3 Session UI and normal demo event flow now also verify on Apple Silicon:
  - `python3 -m py_compile scripts/rts/views/demo_window.py scripts/rts/view_controllers/demo_vc.py scripts/common/views/session_window.py /tmp/pf_native_session_ui_roundtrip.py` succeeds
  - a fresh `./bin/pf-arm64 ./ /tmp/pf_native_session_ui_roundtrip.py` now drives the normal demo/UI Session show-save-load flow and writes `NATIVE_SESSION_RESTORED objs=388 regions=0 cameras=0`
- `completed` Native Python 3 save/load now also verifies non-empty scene-region and scene-camera coverage on Apple Silicon:
  - `python3 -m py_compile scripts/editor/scene.py scripts/rts/main.py /tmp/pf_native_session_region_camera_roundtrip.py` succeeds
  - a fresh `./bin/pf-arm64 ./ /tmp/pf_native_session_region_camera_roundtrip.py` now restores `NATIVE_SESSION_RESTORED objs=388 regions=1 cameras=1 region_names=native_session_probe_region camera_names=native_session_probe_camera`
- `completed` The normal Python 3 Session UI flow now also verifies non-empty region/camera coverage on Apple Silicon:
  - `python3 -m py_compile /tmp/pf_native_session_ui_region_camera_roundtrip.py scripts/rts/main.py` succeeds
  - a fresh `./bin/pf-arm64 ./ /tmp/pf_native_session_ui_region_camera_roundtrip.py` now drives the normal demo/UI Session show-save-load flow and restores `NATIVE_SESSION_RESTORED objs=388 regions=1 cameras=1 region_names=native_ui_session_probe_region camera_names=native_ui_session_probe_camera`
- `completed` The previous native Session UI load crash on Apple Silicon is fixed:
  - after repairing task-context render flushing and the macOS movement cleanup path, a fresh `./bin/pf-arm64 ./ /tmp/pf_native_session_ui_region_camera_roundtrip.py` cleanly reaches `NATIVE_SESSION_RESTORED objs=388 regions=1 cameras=1 region_names=native_ui_session_probe_region camera_names=native_ui_session_probe_camera`
  - the final clean stderr for that verification contains only the expected compute-shader skip and no save/load failure output
- `completed` A live native gameplay smoke pass now verifies:
  - keyboard camera movement changes the visible in-game view
  - the selected blue formation shows visible selection rings and activates the action pad
  - a move order executes successfully and visibly repositions the selected formation
  - the move order reveals additional fog-of-war terrain during movement
  - a 65-second hold after the interaction pass produced no new stderr output
- `completed` The current native Apple Silicon RTS smoke-coverage milestone is considered done for this tracker.
- `blocked` Rosetta host dependencies are not available under the expected x86_64 prefix on this Mac.
- `blocked` Installing Rosetta Homebrew under `/usr/local` failed because this account does not have the required macOS admin privileges.
- `blocked` Vendored `GLEW` still fails on macOS even without regeneration, with duplicate typedef and symbol definitions in `deps/GLEW/include/GL/glew.h` and `deps/GLEW/src/glew.c`.
- `blocked` Building x86_64 Python `2.7.18` under `pyenv` hit a modern dependency failure because the current python-build flow expects `openssl@1.1`.
- `completed` Native arm64 dependency validation is now green on this Mac.
- `partial` The Python 3 migration is no longer the immediate native-build blocker; the current native frontier has moved from basic launch into deeper functional validation.

## Verification Checklist

- `completed` Save the plan into the repo and track execution status here.
- `completed` Implement `make deps PLAT=MACOS_X86_64`.
- `completed` Implement `make deps PLAT=MACOS_ARM64`.
- `partial` Implement `make pf PLAT=MACOS_X86_64`.
  - The target and compiler wiring exist, but the machine is still missing the Rosetta dependency/toolchain pieces needed for a real link.
- `completed` Verify the demo on this Mac or record the exact remaining blockers.
- `completed` Remove macOS GLEW dependency from the renderer and dependency checks.
- `completed` Verify the new macOS GL loader and renderer fallbacks at object-build level.
- `completed` Clear the first native-arm64 `gnu11` warning wave that blocked renderer and game objects.
- `completed` Start the Python 3.13 migration enough to keep the arm64 compile moving.
  - The embedded console and custom pickler are stubbed on Python 3 where planned, and the core bridge now compiles far enough for the wider native build to proceed.
- `completed` Implement the first Darwin arm64 scheduler/context-switch backend and verify it compiles.
- `completed` Link a full native `bin/pf-arm64` build on this Apple Silicon Mac.
- `completed` Launch the native arm64 build and clear the first startup/runtime blockers through an early smoke run.
- `completed` Validate deeper functional behavior beyond early launch stability.
  - Visible native demo window and world rendering are confirmed, and a basic interaction pass now shows camera/view change plus unit selection on Apple Silicon.
  - Minimap interaction validation is now green and the old worker perf warning is gone in the latest 65-second idle verification run.
  - A later smoke pass also verified a successful move order, fog-of-war reveal, and a quiet 65-second post-interaction hold.
  - The remaining RTS smoke-coverage milestone is now marked done for the current bring-up tracker.
- `completed` Update this file with the verified implementation status.
- `completed` Build the first native scene-snapshot foundation that avoids `S_PickleObjgraph` and verify export/import in fresh arm64 runs.
