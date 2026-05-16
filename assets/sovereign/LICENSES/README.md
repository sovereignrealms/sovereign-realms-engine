# Sovereign Asset License Manifest

`manifest.json` is the required provenance record for files under
`assets/sovereign/`.

New Sovereign-created assets default to MIT. Keep them separate from inherited
Permafrost, Glest, GPL, LGPL, or other third-party assets.

Every record must include:

- `path`: repository-relative asset path
- `name`: human-readable asset name
- `type`: asset category, such as `unit`, `building`, `terrain`, `scenario`
- `author`: author or contributor name
- `source`: `original`, `commissioned`, or a clear source reference
- `created_or_intake_date`: `YYYY-MM-DD`
- `license`: `MIT` for Sovereign-created assets
- `third_party_base`: `false` unless the asset derives from external material

Validate the manifest with:

```sh
python3 tools/asset_validation/validate_sovereign_asset_licenses.py --strict
```
