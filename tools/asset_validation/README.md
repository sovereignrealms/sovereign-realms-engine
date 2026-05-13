# Asset Validation Tools

These tools are the first gate for Sovereign Realms art and gameplay assets.

## PFOBJ Validation

Validate a single model:

```sh
python3 tools/asset_validation/validate_pfobj.py assets/models/knight/knight.pfobj
```

Validate every PFOBJ in a tree:

```sh
find assets/models -name '*.pfobj' -print0 | xargs -0 -n 1 python3 tools/asset_validation/validate_pfobj.py
```

The validator checks header structure, vertex/material counts, material
references, texture existence, animation frame counts, collision blocks, and
skinning-weight sanity.

Use `--strict` in CI or intake gates when warnings should fail the asset.
Use `--verbose` when you need every warning line.

## Sovereign Readability Validation

Validate the Sovereign unit readability metadata:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py
```

The readability gate checks that every unit has a far-view silhouette class,
minimum pixel target, marker policy, and team-color strategy. Current
placeholder units are allowed to report `pending_mask` in the normal gate so
gameplay probes can continue to run while production art is incomplete.

Use `--strict` when a production asset pack is expected to have real texture
masks instead of pending placeholders:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py --strict
```

For incremental asset work, scope strict validation to a single unit:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py --unit militia --strict
```
