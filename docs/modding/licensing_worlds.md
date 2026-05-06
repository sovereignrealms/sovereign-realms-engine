# World And Game Pack Licensing

Sovereign Realms should support many worlds and game packs in the same engine
repository while the vertical slice is still evolving.

## Repository Boundary

Root engine code remains Permafrost-derived and follows `LICENSE.txt`: GPLv3
with the existing special linking exception. Engine, editor, renderer, runtime
API, and tool changes are engine changes.

World and game packs live under:

```text
games/<pack_id>/
```

Each pack must include its own:

```text
LICENSE
README.md
world.json
```

## Pack License Rule

A world pack can choose its own license for original pack content. Acceptable
examples include MIT, CC-BY, CC0, or another license selected by the
contributor.

That pack license applies to the pack's original:

- maps
- scenarios
- data files
- scripts
- art
- audio
- documentation

The pack license does not relicense Permafrost-derived engine code.

## Clean Boundary

To keep this separation clear:

- Put pack content only under `games/<pack_id>/`.
- Do not copy engine source into a pack.
- Do not modify engine files as part of a pack-only contribution.
- Declare every third-party asset source and license.
- Do not include Microsoft, Ensemble Studios, Age of Empires, or other
  proprietary assets without clear redistribution rights.

If a contribution changes engine/runtime/editor behavior outside
`games/<pack_id>/`, treat it as an engine contribution under the root engine
license.

This is project policy, not legal advice. Contributors with commercial or
dual-license plans should get their own legal review.
