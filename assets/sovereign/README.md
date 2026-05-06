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
