# Sovereign Realms Changes

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
