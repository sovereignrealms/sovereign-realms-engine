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
- a team-color strategy

The preferred production team-color strategy is a texture mask stored beside
the unit texture and referenced by the unit's `readability.team_color.mask`
field. Current placeholder assets may use `pending_mask`, but that is not
production-ready.
