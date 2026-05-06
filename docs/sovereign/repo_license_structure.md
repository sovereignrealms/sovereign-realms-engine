# Sovereign Realms Repository And License Structure

## Recommended Repositories

Use `sovereignrealms/sovereign-realms-engine` as the first repository. It should
keep the Permafrost root layout so upstream fixes and the current Metal pull
request remain easy to compare.

Create `sovereignrealms/sovereign-realms-game` later, after the first skirmish
vertical slice proves which game-package boundary is actually needed.

Current decision snapshot:

```text
Engine repo name: sovereign-realms-engine
Engine repo URL:  https://github.com/sovereignrealms/sovereign-realms-engine
Later game repo:  https://github.com/sovereignrealms/sovereign-realms-game
```

The first repository is an engine fork plus the initial Sovereign game package.
The second repository should wait until the vertical slice proves which content,
asset, and release boundaries are actually useful.

For now, keep engine work and the first game/world packages together. This is
intentional: the vertical slice still needs engine, editor, renderer, gameplay,
asset-pipeline, and scenario changes to move together without submodule or
version-pinning friction.

## Engine Fork Layout

```text
sovereign-realms-engine/
  LICENSE.txt
  NOTICE.md
  CHANGES.md
  README.md
  src/
  scripts/
    sovereign/
  assets/
    sovereign/
  games/
    README.md
    example_world/
      LICENSE
      README.md
      world.json
  docs/
    modding/
    sovereign/
  tools/
    asset_validation/
```

Do not publish local build outputs, captures, app bundles, notebooks, backup
folders, or temporary session saves as part of the public repository.

## License Policy

The engine fork remains GPLv3 with the existing special linking exception until
the upstream copyright holder grants different terms in writing.

License files and notices:

- `LICENSE.txt`: upstream Permafrost Engine GPLv3 plus special linking
  exception.
- `NOTICE.md`: Sovereign Realms fork notice, upstream attribution, and
  alternate-license caveat.
- `CHANGES.md`: dated Sovereign modification history.
- `assets/sovereign/README.md`: original Sovereign asset/source/license
  tracking policy.
- `games/<pack>/LICENSE`: license for each contributed world or game pack.
- `games/<pack>/world.json`: pack metadata, including license identifier and
  pack boundaries.

Rules for this fork:

- Preserve original copyright headers.
- Preserve `LICENSE.txt`.
- Keep this notice file and `CHANGES.md` current.
- Mark Sovereign Realms modifications clearly.
- Keep original assets under `assets/sovereign/` with their own source/license
  records.
- Keep community worlds and game packs under `games/`, each with a local
  `LICENSE` and metadata.
- Do not import proprietary Age of Empires assets.

World/game pack policy:

- Engine/core code remains under the root engine license.
- Engine/editor/runtime API changes remain under the root engine license.
- World packs loaded as data/scripts through the public runtime conventions may
  use their own license, including MIT, CC-BY, CC0, or another compatible
  content license chosen by the contributor.
- A world pack's license applies only to that pack's original scripts, maps,
  data, and assets. It does not relicense Permafrost-derived engine code.
- If a pack copies engine code or modifies files outside its pack boundary,
  those changes are engine modifications and follow the root engine license.
- This repository should not accept packs that include proprietary Age of
  Empires, Microsoft, Ensemble, or other third-party assets without clear
  redistribution rights.

If an Apache 2.0 or dual-license grant is received later, add the grant text and
new license files in a separate, reviewable commit. Do not pre-label existing
Permafrost-derived engine code as Apache 2.0 before that grant exists.
