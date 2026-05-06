# World Pack Format

World packs are folder-based content packages loaded by the Sovereign runtime
and tooling conventions.

## Folder Layout

```text
games/<pack_id>/
  LICENSE
  README.md
  world.json
  scripts/
  assets/
  maps/
  scenarios/
```

Only `LICENSE`, `README.md`, and `world.json` are required for the first
placeholder pack. Runtime folders should be added as the pack becomes playable.

## Metadata

`world.json` should use this shape:

```json
{
  "id": "example_world",
  "name": "Example World",
  "version": "0.1.0",
  "license": "MIT",
  "entry": {
    "scenario": null,
    "script": null
  },
  "authors": [
    "Sovereign Realms contributors"
  ],
  "description": "Small example pack showing the required metadata boundary."
}
```

Rules:

- `id` should match the folder name.
- `license` should match the local `LICENSE` file.
- `entry.scenario` and `entry.script` may stay `null` until the pack is
  runnable.
- Pack-specific assets should stay inside the pack unless they are promoted to
  shared Sovereign assets with source/license records.

## Validation Goals

Future validation should check:

- required files exist
- metadata parses
- metadata `id` matches folder name
- local `LICENSE` exists
- referenced scripts, maps, scenarios, and assets exist
- no blocked proprietary assets are included
