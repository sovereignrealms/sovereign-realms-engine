# Sovereign Unit Art And Readability Guide

This guide defines the first production rules for Sovereign Realms unit art.
It is intentionally practical: the engine can already render and measure unit
readability, but the current villager/cart, militia/Knight, and archer/Mage
entries are placeholders. New art should improve silhouettes and animation
clarity without depending on broad shader tinting or thick selection markers.

## Goals

- Make units readable at normal RTS zoom and still identifiable at wide zoom.
- Keep close-zoom characters clear enough for HD/Retina screenshots.
- Preserve AoE-style readability: strong faction color belongs on the minimap
  and command UI; world units should use shape, motion, equipment, and small
  authored accents.
- Keep OpenGL as the visual reference while Metal remains the macOS production
  target.

## Non-Goals

- Do not replace the renderer to solve asset readability.
- Do not use whole-material dynamic team-color tinting in the world view.
- Do not thicken selection rings or use saturated selection colors to make up
  for weak unit silhouettes.
- Do not import or trace Age of Empires, Microsoft, or Ensemble assets.

## Core Readability Rules

1. The silhouette must identify the unit role before texture detail is visible.
2. The attack pose must show the weapon/action direction.
3. The walk pose must read as locomotion, not sliding.
4. The idle pose must not collapse into a dark blob at gameplay zoom.
5. Health bars stay compact and should not carry identity by themselves.
6. Selection rings stay neutral white and thin.
7. Any faction accent in the world must be authored into the asset, such as
   cloth trim, shield markings, banners, flags, saddle cloth, roof trim, or
   tool wrappings.

## First Unit Classes

| Class | Required Read | Close-View Expectation | Wide-View Expectation |
|---|---|---|---|
| Worker/villager | human worker with tool/carry state | gather, carry, build, repair silhouettes | small upright worker, not a cart blob |
| Melee infantry | shield/weapon/frontline shape | clear idle, walk, attack, die poses | heavier silhouette than worker/ranged |
| Ranged infantry | bow/crossbow/projectile stance | weapon points toward target in attack | thinner line with ranged posture |
| Cavalry | mounted mass and rider profile | horse/rider separation at close zoom | larger fast unit silhouette |
| Siege | large machine with firing direction | projectile origin/socket is obvious | readable as high-value equipment |
| Animal/resource | non-military shape | natural movement or harvest state | distinct from units and props |

## Required Animation Set

Production unit models should provide these clips where applicable:

- `Idle`
- `Walk`
- `Attack`
- `Die`
- `Gather`
- `Carry`
- `Build`
- `Repair`
- `Shoot`

If a clip does not apply, document that in the unit registry. A production
villager should not rely on a static cart placeholder for walk, gather, build,
or carry proof scenes.

## PFOBJ Intake Checklist

Before a unit enters a production scenario:

- PFOBJ parses with `tools/asset_validation/validate_pfobj.py`.
- All textures referenced by materials exist.
- Bounds, selection radius, and collision footprint are documented.
- Bone weights are normalized and within engine-supported limits.
- Required animation clips exist or have a written exception.
- Attack frame and projectile/socket origin are documented for ranged units.
- Texture scale supports close-zoom Retina screenshots.
- Far-view silhouette target is recorded in `scripts/sovereign/data/units.py`.
- Source file, author, and license are recorded with the asset pack.

## Texture And Material Rules

- Use original or clearly licensed textures only.
- Keep albedo readable under both Metal and OpenGL lighting.
- Avoid making the whole unit faction-colored.
- Prefer small authored faction accents over runtime tinting.
- Avoid noisy high-frequency detail that disappears into shimmer at wide zoom.
- Use alpha carefully; hair, foliage, banners, and cloth should not produce
  distracting edge flicker.

## Proof Gates

Every production unit should pass these proof views:

- Close idle pose at the unit's preferred close camera height.
- Close walk pose.
- Close attack or work pose.
- Wide silhouette view with no healthbar identity crutch.
- Selected view with neutral thin selection ring.
- Damaged view with compact healthbar.

Current proof command:

```sh
./bin/pf-arm64 ./ ./scripts/macos/pf_metal_hd_world_readability_probe.py \
  --output-dir visual_parity_captures/<dated-unit-proof> \
  --expect-backend METAL
```

Metadata validation:

```sh
python3 tools/asset_validation/validate_sovereign_readability.py --strict
```

PFOBJ validation:

```sh
python3 tools/asset_validation/validate_pfobj.py <path/to/unit.pfobj> --strict
```

## First Replacement Order

1. Real villager/worker, because economy readability is central and the
   current cart placeholder is not production-representative.
2. Melee infantry, because it anchors early combat and selection feedback.
3. Ranged unit, because projectile origin, facing, and attack pose must line up.
4. Cavalry or siege, once the infantry/ranged baseline is reliable.

## Acceptance For A New Unit

A new unit is ready to enter the skirmish vertical slice when:

- It passes PFOBJ validation.
- It has complete unit registry metadata.
- Its close/wide proof images are nonblank and visually readable.
- Its `production_asset.status` is `production_ready`.
- It does not depend on broad world-material team tinting.
- It works with neutral thin selection rings and compact healthbars.
