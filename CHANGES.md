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
