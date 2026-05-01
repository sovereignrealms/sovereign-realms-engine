# macOS Metal Capability Equivalence Audit

Date: 2026-04-30

Scope: assess whether the Apple Silicon Metal runtime is equivalent enough to the original Permafrost Engine capability list to start building a real RTS game on top of it.

## Bottom Line

The macOS Metal runtime is ready for real game prototyping and upstream PR presentation as a native Apple Silicon Metal port. It is not yet a complete equivalence claim for every historical engine feature.

The strongest evidence is that the default Metal binary launches without linking `OpenGL.framework`, five-scene OpenGL/Metal visual parity passes with matched cameras, and focused Metal probes cover launch, water, sprites/effects, minimap fog, settings, session roundtrip, editor feature surfaces, editor save/reload workflow plus deterministic editor screenshots, gameplay smoke, gameplay soak, forced GPU-movement smoke, dense movement, Python tasks, audio playback, core RTS gameplay systems, a larger mixed economy/combat scenario, and an 8x8 generated custom-world soak with a Metal session checkpoint.

The largest remaining unproven gameplay areas have moved from core RTS systems to longer manual/editor usability and future game-content scale. `pf.Task` now has a Python 3.13 cooperative generator runtime, OpenAL audio has generated WAV fixtures plus Metal/OpenGL playback smoke coverage, dense formation movement has Metal GPU plus CPU/reference sanity coverage, resource/building/transport/garrison systems have Metal/OpenGL smoke coverage, water/air transport and navigation-layer reshuffle edges have dedicated coverage, dynamic blocker insertion/avoidance is verified on Metal/OpenGL, production automation toggles and worker transport constraints are verified on Metal/OpenGL, a combined economy/fog/minimap/combat/effects scenario is verified on Metal/OpenGL, an 8x8 generated custom-world soak is verified on Metal/OpenGL, and editor terrain/object save plus fresh reload workflow is verified on Metal/OpenGL.

## Evidence Captured

Commands/results from the 2026-04-30 audit:

| Area | Evidence |
|---|---|
| Metal build | `make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL` passed |
| Native launch | `NATIVE_LAUNCH_READY ... pf.render.backend=METAL pf.render.renderer=Apple M2 Max` |
| OpenGL link removal | `otool -L bin/pf-arm64` showed Metal/QuartzCore/Foundation and no `OpenGL.framework` |
| GL symbol check | `nm -g bin/pf-arm64 | rg '(_pf_gl|_gl[A-Z]|OpenGL)'` returned no matches |
| Visual parity | `scripts/macos/capture_visual_parity.sh visual_parity_captures/2026-04-30-equivalence-audit` passed with `CAMERAS MATCH scenes=5 max_position_delta=0.000000` |
| Combat/rocks ratios | Fresh half=60 samples were effectively parity: combat key blocks `1.00-1.01`, rocks key blocks `1.00-1.01` |
| Gameplay smoke | `METAL_GAMEPLAY_SMOKE_PASS ... camera=1 selection=1 move=1 pause=1 attack=1` |
| Forced GPU movement smoke | `METAL_GAMEPLAY_SMOKE_PASS ... gpu_movement=1` |
| Dense GPU crowd movement | `GPU_CROWD_PASS backend=METAL movement_mode=gpu gpu_movement=1 units=64 moved=62 avg_progress=15.41`; Metal CPU and OpenGL CPU sanity also passed |
| Core RTS gameplay systems | `GAMEPLAY_SYSTEMS_PASS backend=METAL resource=1 building=1 builder=1 transport=1 automation=1 garrison=1`; OpenGL sanity also passed |
| Dynamic obstacle behavior | `DYNAMIC_OBSTACLE_PASS backend=METAL mode=gpu started=1 blocker=1 pathing=1 progress=1 clearance=1`; OpenGL CPU reference also passed the same route/blocker scenario |
| Production automation variants | `PRODUCTION_AUTOMATION_PASS backend=METAL toggle=1 idle=1 blocked=1 resumed=1 pickup=1 dropoff=1`; OpenGL reference also passed the same automation gate/resume scenario |
| Mixed economy/combat scenario | `MIXED_GAMEPLAY_SCENARIO_PASS backend=METAL move=1 fog=1 resource=1 building=1 transport=1 garrison=1 combat=1 effects=1`; OpenGL reference passed the same scenario |
| Large custom-world soak | `LARGE_WORLD_SOAK_RESTORE_PASS objs=18 regions=1 cameras=1` after `LARGE_WORLD_SOAK_PASS backend=METAL map=8x8 exploration=1 economy=1 combat=1 effects=1 session=1`; OpenGL reference passed the gameplay path with save skipped to avoid the generated-map session stall |
| Gameplay soak | `GAMEPLAY_SOAK_PASS backend=METAL stages=6 dynamic_water=0 combat=1` |
| Water | `METAL_WATER_PROBE_PASS backend=METAL water_x=228.00 water_z=-148.00 water_h=-12.00` |
| Sprite/VFX | `METAL_SPRITE_PROBE_PASS backend=METAL render_frames=24` and `METAL_GAMEPLAY_EFFECTS_PASS backend=METAL trail=1 impact=1 fire=1 smoke=1` |
| Minimap fog | `MINIMAP_FOG_PROBE_PASS captures=5` |
| Session roundtrip | `NATIVE_SESSION_RESTORED objs=388 regions=1 cameras=1 ...` |
| Settings | `NATIVE_SETTINGS_APPLIED ...` and `NATIVE_SETTINGS_RESTORED ...` |
| Editor | `EDITOR_FEATURE_AUDIT_READY backend=METAL renderer=Apple M2 Max factions=2`; `EDITOR_WORKFLOW_READY backend=METAL ... placed_objects=2 saved_objects=2`; `EDITOR_WORKFLOW_RELOAD_READY backend=METAL ... loaded_objects=2`; `EDITOR_VISUAL_READY backend=METAL renderer=Apple M2 Max captures=2 placed_objects=2 saved_objects=2`; macOS top-bar inset added after live screenshot showed the tab bar under the system menu; OpenGL sanity also passed |
| Python task runtime | `METAL_TASK_PROBE_PASS backend=METAL steps=start,yield,sleep,event`; OpenGL sanity also passed with the same steps |
| Legacy task sample | `PONG_TASK_PROBE_PASS backend=METAL`; OpenGL sanity also passed |
| Audio | `METAL_AUDIO_PROBE_PASS backend=METAL music=audio_probe_tone effect=audio_probe_beep`; OpenGL sanity also passed |
| Capability inventory | `METAL_CAPABILITY_INVENTORY_READY backend=METAL gpu_movement_after_request=True task_status=run_supported` |

## Capability Matrix

Legend:

- `Verified`: exercised on this Mac Metal runtime with a probe or parity capture.
- `Smoke verified`: exercised in a representative but not exhaustive way.
- `API/source present`: visible in the Python API/source, but not fully gameplay-proven in this audit.
- `Gap`: known not equivalent yet.
- `Out of scope`: not a macOS Metal runtime requirement.

| Engine capability group | macOS Metal status | Notes |
|---|---|---|
| Native graphics backend | Verified | Default Apple Silicon runtime is Metal, no `OpenGL.framework` link in the Metal binary. |
| OpenGL reference backend | Verified | Preserved for parity captures; five-scene harness builds both backends and compares cameras. |
| Skeletal animation / GPU skinning visual path | Verified | Character texture/detail and animation parity slices are closed; combat parity blocks are now effectively 1.00. |
| Static meshes / props / rocks | Verified | Rock/static-prop residuals sampled at parity in the latest capture. |
| Directional light and shadow mapping | Verified | Prior shadow slices closed owner/depth/Y-lookup issues; latest parity capture shows combat/rocks parity. |
| Terrain texture splatting / material tone | Verified | Broader tone parity closed in roadmap; latest overview/water/rocks parity passed. |
| Water reflection/refraction/soft edges | Verified | Dedicated water probe and five-scene parity pass. |
| Skybox | Verified | Included in five-scene visual parity harness. |
| Sprites/projectile trails/impacts/fire/smoke | Verified | Real sprite assets and gameplay-effects probe pass. |
| UI / Nuklear rendering | Smoke verified | Settings/session/menu/editor audit and live screenshot render through Metal. |
| RTS minimap | Verified | Minimap fog probe passes; fog-of-war now applies to minimap instead of showing a revealed map. |
| Fog of war | Verified | Native launch setting true; minimap and live screenshot confirm dark unexplored regions. |
| RTS selection/move/pause/attack | Verified | Gameplay smoke, soak, and mixed scenario probes pass. |
| Pathfinding land/water/air query APIs | Verified | Capability inventory and the gameplay edge probe confirm land, water, and air nearest-pathable queries return valid values on both Metal and OpenGL. |
| GPU movement / crowd compute path | Smoke verified | Metal forced-GPU smoke passes and dense 64-unit formation stress passes with GPU movement enabled; Metal CPU and OpenGL CPU sanity runs also pass. |
| Formation movement / navigation-layer reshuffle | Verified | New navigation/formation edge probe covers 1x1/3x3/5x5/7x7 ground pathing, preferred-formation resolution, rank formation move, and column reshuffle on Metal GPU movement and the OpenGL CPU reference. |
| Dynamic obstacle behavior | Verified | Dynamic obstacle probe inserts a blocking founded buildable after mixed-radius formation movement starts, verifies the pathable field shifts away from the blocker, then confirms the group continues moving while preserving blocker clearance on Metal and OpenGL. |
| Resource gathering / base-building / garrison / transport / automation | Smoke verified | Gameplay-systems probe creates controlled workers, resources, storage sites, build sites, transport jobs, automatic transport, and garrison orders on both Metal and OpenGL. The gameplay edge probe additionally covers water transport and `do_not_take_water` source restrictions, while the production automation probe verifies automatic-transport toggles, idle-with-auto-off behavior, worker `do_not_transport` blocking, resume after clearing the gate, pickup/dropoff, and post-delivery idle settling on both backends. The mixed scenario now exercises selection, fog/minimap setup, resource flow, building, transport, garrison, Mage projectile combat, and sprite effects in one run. |
| Ranged combat projectile physics | Verified | Gameplay-effects probe saw projectile trail and impact events; the mixed scenario also verifies combat/projectile effects after economy and garrison stages. |
| Configurable graphics settings | Verified | Settings apply/restore probes pass; restore probe now accounts for UI On/Off healthbar granularity and restores the exact original value through the API. |
| Save/restore whole session | Verified | Session UI region/camera roundtrip passes on the default map. The large custom-world soak now writes and restores a generated custom-map Metal checkpoint after preserving probe entity scene metadata and importable probe classes. |
| Embedded Python scripting | Verified | All probes are Python-driven under Python 3.13. |
| Interactive Python console | Smoke verified | `pf.show_console()` succeeds in the capability inventory probe; manual typing/execution in the console is not yet scripted. |
| Fiber-backed Python tasks (`pf.Task`) | Smoke verified | Python 3.13 supports cooperative generator tasks using `yield self.yield_()`, `yield self.sleep(ms)`, and `yield self.await_event(event)`. The legacy Pong sample has been migrated and runtime-probed on Metal/OpenGL. |
| Event system | Smoke verified | Probe event handlers, attack-start handlers, and UI/global events all execute. |
| Audio API / positional effects | Smoke verified | Generated WAV fixtures are indexed under `assets/music` and `assets/sounds`; Metal/OpenGL probes exercise `get_all_music`, `play_music`, `curr_music`, `play_global_effect`, and positional `play_effect`. |
| Map/scene editor | Smoke verified | Metal editor launch, feature audit, terrain/object save, fresh saved map/scene reload, and deterministic screenshot verification pass. The visual harness paints a cobblestone patch, places animated/static objects, captures Terrain and Objects tabs with window-specific screenshots, validates the PNGs as nonblank, and saves/reloads the edited map/scene. Computer Use could not attach to the raw SDL `pf-arm64` process, so desktop verification remains screenshot/probe based. |
| Debug/profiling instrumentation | API/source present | Debug/perf UI surfaces are touched by editor/game probes, but deep profiling/timestamp equivalence is not part of this audit. |
| Custom ASCII model/map import/export | API/source present | Runtime loads the existing assets/maps; exporter/importer workflows were not revalidated here. |
| Image quilting / Wang tiling | API/source present | Historical engine features; not exercised in this Mac Metal audit. |
| HD/4K high-clarity character/world platform | Gap / future phase | Explicitly post-port. Current work is parity with the existing asset/rendering baseline, not an AoE II DE-style asset-quality uplift. |
| Linux/Windows parity and Windows minidump launcher | Out of scope | This audit is only for macOS Apple Silicon Metal. |

## Build-Readiness Assessment

For starting a real game on top of this engine, the answer is **yes**, with constraints:

1. Use the current Metal runtime for active macOS gameplay prototyping.
2. Keep OpenGL as the reference backend until the upstream PR and early Sovereign Realms fork stabilize.
3. Treat HD/4K visuals, larger maps, and character-level zoom as the next graphics-platform phase, not as already completed work.
4. New gameplay systems can use Python 3 `pf.Task` only in the cooperative generator style; old stackful task scripts should be migrated before relying on them.
5. Keep audio fixtures small and replace them with richer original game audio when the real content pipeline begins.

## Recommended Next Targets

1. Longer manual editor usability QA once the editor is packaged as a normal macOS app/window that Computer Use can attach to directly.
2. Broader large-map soak duration and content scale-up: the generated-map checkpoint restore path is now verified, so the next useful stress target is longer runtime plus more objects/regions.
