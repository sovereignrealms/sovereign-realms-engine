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
minimum pixel target, marker policy, and explicit world-material team-color
policy. The active parity rule is `not_applicable`: world unit materials do not
receive dynamic team-color tinting because the OpenGL reference renderer has no
matching shader path.

Use `--strict` for metadata validation in CI or intake gates:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py --strict
```

For incremental asset work, scope strict validation to a single unit:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py --unit militia --strict
```

The current placeholder Sovereign unit pack is expected to pass strict metadata
validation while still reporting `placeholder_needs_replacement` for production
asset status. New production unit entries should move to `production_ready`
only after the close/wide proof captures are visually readable.

Strong team colors remain a minimap/UI concern; world readability should come
from authored silhouettes, animation, equipment, and compact status UI. See
`docs/sovereign/unit_art_readability.md` for the production unit art checklist.
