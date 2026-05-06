# Sovereign Realms Repository And License Structure

## Recommended Repositories

Use `sovereignrealms/sovereign-realms-engine` as the first repository. It should
keep the Permafrost root layout so upstream fixes and the current Metal pull
request remain easy to compare.

Create `sovereignrealms/sovereign-realms-game` later, after the first skirmish
vertical slice proves which game-package boundary is actually needed.

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
  docs/
    sovereign/
  tools/
    asset_validation/
```

Do not publish local build outputs, captures, app bundles, notebooks, backup
folders, or temporary session saves as part of the public repository.

## License Policy

The engine fork remains GPLv3 with the existing special linking exception until
the upstream copyright holder grants different terms in writing.

Rules for this fork:

- Preserve original copyright headers.
- Preserve `LICENSE.txt`.
- Keep this notice file and `CHANGES.md` current.
- Mark Sovereign Realms modifications clearly.
- Keep original assets under `assets/sovereign/` with their own source/license
  records.
- Do not import proprietary Age of Empires assets.

If an Apache 2.0 or dual-license grant is received later, add the grant text and
new license files in a separate, reviewable commit. Do not pre-label existing
Permafrost-derived engine code as Apache 2.0 before that grant exists.
