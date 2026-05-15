# Sovereign Realms Assets

This folder is reserved for original Sovereign Realms game assets. Every asset
added here must include source and license metadata before it is used in a
public build.

Recommended layout:

```text
assets/sovereign/
  models/
    units/
    buildings/
    siege/
    resources/
    animals/
    trees/
    props/
  terrain/
  sprites/
    projectiles/
    impacts/
    fire_smoke/
  icons/
  maps/
  scenes/
  scenarios/
  sounds/
  music/
  LICENSES/
```

`scenarios/` stores Sovereign-specific JSON sidecars for player starts,
diplomacy, starting resources, victory rules, and editor palettes. Terrain
still lives in PFMAP files and engine object placement can continue to use
PFSCENE.

Do not place Microsoft, Ensemble Studios, or Age of Empires assets in this
tree. Use original, commissioned, or clearly licensed assets only.

## Unit Readability Requirements

Every production unit must have readability metadata in
`scripts/sovereign/data/units.py`:

- a far-view silhouette class
- a minimum pixel target for wide zoom
- a marker policy for when healthbars or other UI indicators may appear
- an explicit world-material team-color policy

World materials do not use a dynamic team-color tint path. OpenGL has no
equivalent mask shader, so Metal also keeps this disabled for parity. Strong
team identity belongs on the minimap and other deliberate UI surfaces; world
unit readability should come from authored silhouettes, animation, equipment,
small built-in costume accents, and compact health/status UI.

The historical mask proof assets may remain in the tree while older notes are
kept for auditability, but they are not part of the active renderer contract.
Final Sovereign unit art should replace the placeholder Knight/Mage/cart assets
with purpose-built models and textures that are readable without runtime tinting.
