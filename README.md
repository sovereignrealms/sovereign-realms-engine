# Sovereign Realms Engine

Sovereign Realms Engine is a Permafrost Engine-derived RTS engine fork focused
on macOS Apple Silicon, native Metal rendering, and flexible world/game-pack
creation.

The first production goal is an Age of Empires II-style skirmish vertical slice:
resource economy, buildings, unit production, formations, combat, fog of war,
minimap, editor-authored scenarios, save/load, and large-map readiness. The
project is not a clone of Age of Empires and does not include Microsoft,
Ensemble Studios, or Age of Empires assets.

## Repository Role

This repository intentionally keeps the engine, editor, first Sovereign game
package, and early world-pack examples together while the vertical slice is
still evolving. That keeps engine/API/editor fixes close to gameplay and
scenario work.

```text
sovereign-realms-engine/
  src/                         # Permafrost-derived engine code
  scripts/sovereign/           # Sovereign gameplay/data systems
  assets/sovereign/            # Sovereign original assets and asset notes
  games/                       # World/game packs with their own licenses
  docs/sovereign/              # Engine, repo, and roadmap notes
  docs/modding/                # World-pack and licensing policy
  tools/asset_validation/      # Asset validation tools
```

Later, once the vertical slice stabilizes, game-only content may split into a
separate `sovereign-realms-game` repository. Until then, `games/<pack_id>/`
is the contribution boundary for independent worlds.

## World Packs And Licensing

Root engine code remains under the upstream Permafrost license: GPLv3 with the
existing special linking exception in `LICENSE.txt`.

World/game packs under `games/<pack_id>/` may use their own license for original
pack content, including MIT, CC-BY, CC0, or another license chosen by the
contributor. A pack license applies only to that pack's original scripts, maps,
data, art, audio, and documentation. It does not relicense Permafrost-derived
engine code.

Every pack must include:

```text
LICENSE
README.md
world.json
```

See:

- `docs/modding/licensing_worlds.md`
- `docs/modding/world_pack_format.md`
- `games/example_world/`

## Upstream

This project is derived from Permafrost Engine by Eduard Permyakov, the engine
behind EVERGLORY. Upstream copyright notices and `LICENSE.txt` are preserved.

Sovereign Realms modifications are documented in:

- `NOTICE.md`
- `CHANGES.md`
- `docs/sovereign/repo_license_structure.md`

Alternate licensing of Permafrost-derived engine code, such as Apache 2.0 or a
dual-license grant, requires explicit written permission from the upstream
copyright holder. This repository does not grant that permission by itself.

## Current Status

The macOS Apple Silicon runtime has a native Metal backend, with OpenGL retained
as a visual/reference backend while parity and scale checks continue.

Sovereign Realms currently has verified scaffolding for:

- data-driven units, buildings, resources, technologies, ages, and civilizations
- runtime factory spawning
- resource economy and drop-off behavior
- production queues and population
- age advancement and technology state
- combat counters
- projectile/VFX origin and facing checks
- save/load roundtrip for Sovereign gameplay state
- deterministic skirmish probes and first AI decision-depth checks
- editor scenario sidecars, placement, validation, reload, and export reports
- world-pack licensing and metadata boundaries

The project is not production-game-ready yet. Main remaining areas are real
production assets, deeper AI/build-order planning, performance and large-map
benchmarks, HD/Retina presentation polish, and broader gameplay content.

The active plan is tracked in:

- `plans/2026-05-05-sovereign-realms-engine-work-needed.md`
- `docs/sovereign/engine_work_needed.md`

## Engine Features

Permafrost Engine provides the RTS foundation this fork builds on:

- OpenGL 3.3 reference renderer
- native Metal renderer for macOS Apple Silicon runtime builds
- custom PFOBJ mesh/animation format and Blender export path
- skeletal animation with GPU skinning
- directional light shadow mapping
- terrain texture splatting
- water rendering
- skybox support
- RTS and FPS cameras
- tile-based map loading
- Nuklear-based UI
- map/scene editor
- selection, movement, formations, and pathfinding
- land/water/air navigation layers
- fog of war and minimap
- resource gathering, base building, combat, projectiles, garrison/transport
- save/load of engine sessions and Python-defined state
- multithreaded simulation/render pipeline

## macOS Apple Silicon Build

Install host dependencies:

```sh
brew install cmake pkg-config sdl2 openal-soft mimalloc python@3.13
```

Build the native Metal runtime:

```sh
make deps PLAT=MACOS_ARM64
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
./bin/pf-arm64 ./ ./scripts/rts/main.py
```

Build the OpenGL reference backend:

```sh
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
./bin/pf-arm64 ./ ./scripts/rts/main.py
```

Launch the editor:

```sh
make run_editor PLAT=MACOS_ARM64
```

## Validation

Before publishing or pushing packaging changes:

```sh
python3 scripts/macos/verify_sovereign_publish_ready.py --strict
```

Useful Sovereign probes include:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_factory_probe.py
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_economy_probe.py
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_skirmish_probe.py
./bin/pf-arm64 ./ ./scripts/macos/pf_sovereign_long_skirmish_probe.py
```

OpenGL/Metal visual parity capture:

```sh
scripts/macos/capture_visual_parity.sh visual_parity_captures/<tag>
```

## Contributing

Contributions should keep the boundary clear:

- engine/editor/runtime changes follow the root engine license
- world/game packs belong under `games/<pack_id>/`
- every world pack needs `LICENSE`, `README.md`, and `world.json`
- all assets need clear source/license metadata
- no proprietary Age of Empires, Microsoft, Ensemble, or other third-party
  assets without redistribution rights

For the current repository and license plan, read:

- `docs/sovereign/repo_license_structure.md`
- `docs/sovereign/repo_publish_handoff.md`
- `docs/modding/licensing_worlds.md`

## License

Engine code is distributed under GPLv3 with the Permafrost special linking
exception, as preserved in `LICENSE.txt`.

Sovereign Realms changes are recorded in `CHANGES.md` and attributed in
`NOTICE.md`.

World/game packs under `games/` carry their own local license files for original
pack content. Pack licenses do not relicense the engine.
