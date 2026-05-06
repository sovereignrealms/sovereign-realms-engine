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
