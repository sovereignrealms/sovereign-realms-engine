# macOS Metal Capability Equivalence Audit

Date: 2026-04-30

Scope: assess whether the Apple Silicon Metal runtime is equivalent enough to the original Permafrost Engine capability list to start building a real RTS game on top of it.

## Bottom Line

The macOS Metal runtime is ready for real game prototyping and upstream PR presentation as a native Apple Silicon Metal port. It is not yet a complete equivalence claim for every historical engine feature.

The strongest evidence is that the default Metal binary launches without linking `OpenGL.framework`, five-scene OpenGL/Metal visual parity passes with matched cameras, and focused Metal probes cover launch, water, sprites/effects, minimap fog, settings, session roundtrip, editor feature surfaces, editor save/reload workflow plus deterministic editor screenshots, gameplay smoke, gameplay soak, forced GPU-movement smoke, dense movement, Python tasks, audio playback, core RTS gameplay systems, a larger mixed economy/combat scenario, an 8x8 generated custom-world soak with a Metal session checkpoint, and historical ASCII map/scene/model/perf/Wang-tiling surfaces.

The largest remaining unproven gameplay areas have moved from core RTS systems to longer duration/game-content scale. `pf.Task` now has a Python 3.13 cooperative generator runtime, OpenAL audio has generated WAV fixtures plus Metal/OpenGL playback smoke coverage, dense formation movement has Metal GPU plus CPU/reference sanity coverage, resource/building/transport/garrison systems have Metal/OpenGL smoke coverage, water/air transport and navigation-layer reshuffle edges have dedicated coverage, dynamic blocker insertion/avoidance is verified on Metal/OpenGL, production automation toggles and worker transport constraints are verified on Metal/OpenGL, a combined economy/fog/minimap/combat/effects scenario is verified on Metal/OpenGL, an 8x8 generated custom-world soak is verified on Metal/OpenGL, and the packaged Metal editor now verifies feature audit, terrain/object editing, save, fresh reload, and deterministic Terrain/Objects visual captures from a self-contained `.app`.

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
| Large custom-world soak | Baseline restore passed with `LARGE_WORLD_SOAK_RESTORE_PASS objs=18 regions=1 cameras=1`. Scaled 10x10 run also passed with `LARGE_WORLD_SOAK_RESTORE_PASS objs=54 regions=5 cameras=4`. The longer repeated-loop 10x10 run now passes 3 extra gameplay loops before save/restore with `LARGE_WORLD_SOAK_RESTORE_PASS objs=54 regions=5 cameras=4`; OpenGL reference passed the same repeated-loop gameplay path with save skipped to avoid the generated-map session stall |
| Gameplay soak | `GAMEPLAY_SOAK_PASS backend=METAL stages=6 dynamic_water=0 combat=1` |
| Water | `METAL_WATER_PROBE_PASS backend=METAL water_x=228.00 water_z=-148.00 water_h=-12.00` |
| Sprite/VFX | `METAL_SPRITE_PROBE_PASS backend=METAL render_frames=24` and `METAL_GAMEPLAY_EFFECTS_PASS backend=METAL trail=1 impact=1 fire=1 smoke=1` |
| Minimap fog | `MINIMAP_FOG_PROBE_PASS captures=5` |
| Session roundtrip | `NATIVE_SESSION_RESTORED objs=388 regions=1 cameras=1 ...` |
| Settings | `NATIVE_SETTINGS_APPLIED ...` and `NATIVE_SETTINGS_RESTORED ...` |
| Editor | `EDITOR_FEATURE_AUDIT_READY backend=METAL renderer=Apple M2 Max factions=2`; `EDITOR_WORKFLOW_READY backend=METAL ... placed_objects=2 saved_objects=2`; `EDITOR_WORKFLOW_RELOAD_READY backend=METAL ... loaded_objects=2`; `EDITOR_VISUAL_READY backend=METAL renderer=Apple M2 Max captures=2 placed_objects=2 saved_objects=2`; `PACKAGED_EDITOR_QA_PASS ... backend=METAL feature=1 workflow=1 reload=1 visual=1`; self-contained `dist/Permafrost Editor.app` packaging verifies through macOS `open`, and the temp QA bundle verifies packaged editing through LaunchServices with nonblank Terrain/Objects screenshots; OpenGL sanity also passed |
| Python task runtime | `METAL_TASK_PROBE_PASS backend=METAL steps=start,yield,sleep,event`; OpenGL sanity also passed with the same steps |
| Legacy task sample | `PONG_TASK_PROBE_PASS backend=METAL`; OpenGL sanity also passed |
| Audio | `METAL_AUDIO_PROBE_PASS backend=METAL music=audio_probe_tone effect=audio_probe_beep`; OpenGL sanity also passed |
| Capability inventory | `METAL_CAPABILITY_INVENTORY_READY backend=METAL gpu_movement_after_request=True task_status=run_supported` |
| Historical feature surfaces | `HISTORICAL_FEATURES_READY backend=METAL status=pass` and `HISTORICAL_FEATURES_READY backend=OPENGL status=pass`; summaries saved under `qa-output/2026-05-02-historical-features-metal/` and `qa-output/2026-05-02-historical-features-opengl/` |

## Capability Matrix

Legend:

- `Verified`: exercised on this Mac Metal runtime with a probe or parity capture.
- `Smoke verified`: exercised in a representative but not exhaustive way.
- `Source verified`: source/fallback behavior is checked directly, but the full historical tooling path is not runtime-executed.
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
| Interactive Python console | Smoke verified | Python 3 console visibility is restored through the Nuklear console window; stdout/stderr capture, `flush()`, original-stream teeing, single-line execution, and multiline compound input are restored. The verifier runs a `for` block through the console path and records `PY_CONSOLE_SELFTEST_PASS multiline=1 total=3 len=3`. |
| Fiber-backed Python tasks (`pf.Task`) | Smoke verified | Python 3.13 supports cooperative generator tasks using `yield self.yield_()`, `yield self.sleep(ms)`, and `yield self.await_event(event)`. The legacy Pong sample has been migrated and runtime-probed on Metal/OpenGL. |
| Event system | Smoke verified | Probe event handlers, attack-start handlers, and UI/global events all execute. |
| Audio API / positional effects | Smoke verified | Generated WAV fixtures are indexed under `assets/music` and `assets/sounds`; Metal/OpenGL probes exercise `get_all_music`, `play_music`, `curr_music`, `play_global_effect`, and positional `play_effect`. |
| Map/scene editor | Smoke verified | Metal editor launch, feature audit, terrain/object save, fresh saved map/scene reload, deterministic screenshot verification, and full packaged app editing QA pass. The packaged visual harness paints a cobblestone patch, places animated/static objects, captures Terrain and Objects tabs with window-specific, full-screen, and display-specific screenshot fallbacks, validates the PNGs as nonblank, saves the edited map/scene inside the staged app runtime, and reloads that saved content. Deeper human usability polish remains a follow-up, but packaged editing correctness is now covered. |
| Debug/profiling instrumentation | Smoke verified | `scripts/macos/pf_macos_historical_features_probe.py` samples `pf.prev_frame_ms()`, `pf.prev_frame_perfstats()`, `pf.prev_frame_memstats()`, navigation perf stats, and constructs the PerfStatsWindow on Metal/OpenGL. Deep GPU timestamp equivalence is still not claimed: `R_Cmd_TimestampForCookie` is guarded for Metal and should stay out of parity requirements until a native Metal timestamp path exists. |
| Custom ASCII model/map import/export | Smoke verified | Historical probe verifies editor PFMap serialization/parser roundtrip, `pf.load_map_string`, empty PFScene serialization plus `pf.load_scene`, session export, representative static/animated PFOBJ structural counts, and `export_pfobj.py` syntax. Blender-driven export is not run without Blender, so that remains a tooling follow-up rather than a Metal runtime blocker. |
| Image quilting / Wang tiling | Source verified | Historical probe checks the original `R_GL_ImageQuilt_MakeTileset` source is present, terrain still calls `R_GL_Texture_ArrayMakeMapWangTileset`, and the Apple Silicon fallback uploads 8 Wang slices per material. The full Image Quilt generator remains OpenGL-owned historical tooling and is not executed in the Metal runtime audit. |
| HD/4K Retina/high-clarity text, character, and world platform | Partial / future phase | First Retina UI text hardening is in place through high-DPI SDL drawables, drawable-space mouse scaling, and higher-quality Nuklear font atlas oversampling. Runtime HUD, Settings, Session, Console, unhandled Python error-dialog, close characters, close terrain/props, normal fogged wide gameplay, revealed wide-world readability, and a staged HD/4K world-readability scaffold now have Metal high-DPI screenshot evidence at `3456x2234`. The new scaffold stages close heroes, dense army, dense forest/building content, VFX fixtures, and a wide large-map view with 108 temporary entities. The scene renderer is Retina-scale, but HD/4K characters, richer world assets, zoom-aware LOD/readability, terrain variation, dense vegetation/buildings, and AoE II DE-style asset-quality uplift remain post-port graphics-platform work. |
| Linux/Windows parity and Windows minidump launcher | Out of scope | This audit is only for macOS Apple Silicon Metal. |

## Build-Readiness Assessment

For starting a real game on top of this engine, the answer is **yes**, with constraints:

1. Use the current Metal runtime for active macOS gameplay prototyping.
2. Keep OpenGL as the reference backend until the upstream PR and early Sovereign Realms fork stabilize.
3. Treat Retina-ready text/UI, HD/4K visuals, larger maps, and character-level zoom as the next graphics-platform phase, not as already completed work.
4. New gameplay systems can use Python 3 `pf.Task` in the cooperative generator style; old stackful task scripts should be migrated before relying on them.
5. Keep audio fixtures small and replace them with richer original game audio when the real content pipeline begins.
6. Treat Blender-driven PFOBJ export, full Image Quilt generation, and native Metal GPU timestamp readback as non-blocking tooling/profiling follow-ups rather than gameplay-start blockers.

## Recommended Next Targets

1. Longer wall-clock soak: the generated-map checkpoint restore path now verifies at 10x10 with 54 objects, 5 regions, 4 cameras, longer post-combat settle, and 3 repeated gameplay loops; the next runtime stress target is an hour-scale run.
2. HD/4K graphics-platform uplift: the Metal path now has a repeatable five-scene readability scaffold for close characters, dense army, dense forest/building content, VFX combat, and wide large-map zoom-out. The next graphics-readability gap is a narrow asset/LOD pilot: one character family, one terrain/biome patch, and one vegetation/building cluster upgraded enough to compare against the current scaffold baseline.
