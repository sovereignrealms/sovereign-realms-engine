# HD/4K World Readability Targets

Created: 2026-05-02

## Purpose

This plan turns the HD/4K graphics goal into a concrete Metal validation target. It is not a declaration that the current stock assets are final HD/4K quality. The current milestone is to prove the Metal renderer, capture path, and staged scenes can expose close-zoom and wide-zoom readability gaps repeatably.

## Current Evidence

- Probe: `scripts/macos/pf_metal_hd_world_readability_probe.py`
- Latest artifact: `visual_parity_captures/2026-05-02-hd-world-readability-metal/`
- Pass marker: `HD_WORLD_READABILITY_PASS backend=METAL captures=5 highdpi=1 staged=108 sprite_sheets=fire_loop.png,impact_burst.png,projectile_trail.png,smoke_puff.png`
- Capture scale: `3456x2234` screenshots from a `1728x1117` Metal window, `retina_scale=[2.0, 2.0]`
- Staged coverage: close hero characters, dense army, dense forest/building/prop cluster, projectile/fire/smoke/impact fixtures, and wide large-map zoom-out.

## Readability Targets

### Close Character Zoom

- Characters should remain sharp and identifiable at character-level zoom on Retina and 4K displays.
- Team color, armor/cloth panels, weapons, faces/helmets, and animation silhouettes should read without fuzzy scaling.
- Healthbars, selection rings, and combat overlays must not hide the character details being inspected.
- Future content work should add higher-resolution materials, stronger mesh silhouettes, and explicit close/mid/far LOD rules.

### Dense Army Views

- Large formations should remain readable as organized groups, not visual clutter.
- Unit silhouettes, team colors, selection rings, healthbars, and weapons should survive dense overlap.
- Formation readability should be tested at close tactical zoom and at wide battlefield zoom.

### Terrain, Forests, And Buildings

- Large maps need macro terrain variation so grass/cobble/dirt/water do not read as repeated tiles at wide zoom.
- Dense forests need species, height, canopy, color, and silhouette variation.
- Buildings should retain strong roof/wall silhouettes, readable player color, and clear shadow grounding.
- Cliffs, shorelines, roads, and water edges need material transitions that stay crisp at close zoom and coherent at wide zoom.

### Combat Effects

- Projectile trails, impact bursts, fire, smoke, and burning structures must remain readable without overdraw clutter.
- Effects should be visible at wide battlefield zoom while preserving smaller detail at close zoom.
- Current fixture sheets prove the Metal sprite path and capture coverage only; they are not final production effects.

### Wide Large-Map Zoom-Out

- Wide zoom should show large areas with useful strategic readability: terrain regions, forests, buildings, unit clusters, water routes, and roads.
- LOD/impostor rules should reduce clutter while preserving important gameplay signals.
- Minimap, fog-of-war, and world rendering should agree on what is visible, explored, and strategically important.

## Next Pilot Slice

The next graphics-platform implementation should be a narrow asset/LOD pilot, not a broad renderer rewrite:

1. Pick one character family, one terrain/biome patch, and one vegetation/building cluster.
2. Add or swap higher-clarity materials/assets for that small set.
3. Add the minimum LOD/readability rule needed to keep those assets clean at close and wide zoom.
4. Re-run `pf_metal_hd_world_readability_probe.py` and compare the five fixed scenes against the current baseline.

## Non-Goals For This Slice

- Do not clone Age of Empires II art, rules, or assets.
- Do not bundle a PBR renderer redesign into the first pilot.
- Do not remove OpenGL parity/reference capture workflows solely because this Metal-only readability probe passes.
- Do not mark HD/4K complete until production-quality assets and zoom-aware LOD/readability rules are present.
