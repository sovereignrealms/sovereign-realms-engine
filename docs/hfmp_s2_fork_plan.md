# HFMP S2 Fork Plan

## Status

- `execution in progress`
- Current phase: `stable Apple Silicon baseline accepted; first visible fork identity slice verified`
- Current package: [scripts/hfmp_s2](/Users/dev/Desktop/OpenGL%20RTS%20game%20engine/scripts/hfmp_s2)
- Baseline snapshot: [backups/2026-04-21-rts-baseline](/Users/dev/Desktop/OpenGL%20RTS%20game%20engine/backups/2026-04-21-rts-baseline)
- Apple Silicon baseline snapshot: [backups/2026-04-22-apple-silicon-final-validation](/Users/dev/Desktop/OpenGL%20RTS%20game%20engine/backups/2026-04-22-apple-silicon-final-validation)
- Fork slice backup: [backups/2026-04-22-hfmp-fork-start](/Users/dev/Desktop/OpenGL%20RTS%20game%20engine/backups/2026-04-22-hfmp-fork-start)

## Working Goal

Build a macOS-optimized RTS that keeps Permafrost's readable battlefield control, fog-of-war, formations, and economy foundation, while adding a hero-lite character layer inspired by Dota 2's role identity and power spikes.

## Engine Platform Boundary

- HFMP is one possible world built on the Permafrost/Metal-native engine, not the engine's only target.
- The shared engine should keep rules, factions, art direction, maps, scenes, assets, and combat presentation data/script-driven where practical so different kinds of RTS worlds can be built on the same core.
- The long-term graphics platform target is tracked in [plans/2026-04-24-metal-native-flexible-world-roadmap.md](/Users/dev/Desktop/OpenGL%20RTS%20game%20engine/plans/2026-04-24-metal-native-flexible-world-roadmap.md): Metal parity first, Metal default next, OpenGL removal after that, then the post-port HD/4K flexible-world graphics uplift.

## Source Influences

### Age of Empires II

- Empire growth depends on economy, technology, military production, and Age progression.
- Villagers are the backbone of the empire loop, and economic allocation changes with the plan.
- Advancing Ages is the clean power-progression spine: more buildings, more technologies, more unit access.
- Civilizations bonuses and unit availability create asymmetry without breaking the shared RTS ruleset.
- Readable counters, scouting, and map control matter as much as raw army size.
- Economy should be actively rebalanced instead of passively stockpiled; floating unused resources is considered a loss of tempo.

References:
- [Getting Started with Age of Empires II: DE – PC](https://www.ageofempires.com/learn-to-play/getting-started-aoe2/)
- [Advancing to the Next Age](https://www.ageofempires.com/learn-to-play/advancing-aoe2/)
- [Military & Economy](https://www.ageofempires.com/learn-to-play/military-and-economy-aoe2/)
- [Civilizations & Game Modes](https://www.ageofempires.com/learn-to-play/civilizations-game-modes-aoe2/)

### Dota 2

- Heroes are the center of player identity.
- Roles matter because heroes contribute different battlefield value even before items or late-game scaling.
- Talent-style bonuses and curated item/build guidance create meaningful mid-game specialization.
- HUD and minimap readability are treated as core gameplay aids, not just presentation.
- Dota's HUD references are especially useful for Mac polish:
  - smaller top-bar footprint to preserve battlefield visibility
  - quick-read minimap options
  - in-game settings access
- Dota Plus is a good reference for non-magic hero depth:
  - role-aware suggestions
  - data-driven progression/help
  - hero-specific stat tracking and milestones

References:
- [Dota 2 Reborn - Hero Browser](https://www.dota2.com/reborn/part1?l=japanese)
- [Dota 2 7.00 - New Gameplay](https://www.dota2.com/700/gameplay/%3Fl%3Dtchinese)
- [Dota 2 7.00 - New HUD](https://www.dota2.com/700/hud/)
- [Dota Plus](https://www.dota2.com/plus/?l=english)

## Design Direction

### What We Keep From RTS

- Economy-first battlefield loop.
- Fog-of-war and scouting pressure.
- Territorial play through movement, army positioning, and map control.
- Clear unit classes and counters.
- Multi-unit control as the main skill expression.

### What We Borrow From Dota 2

- Named signature characters inside each faction.
- Character-specific bonus skills instead of spell-heavy magic systems.
- Role identity such as frontline bruiser, scout-captain, duelist, banner support, siege specialist.
- Power spikes through training, veterancy, tech unlocks, equipment, or talent-style bonuses.

### What We Avoid

- Mana-heavy spell design.
- Particle-dense magic readability problems.
- Mechanical complexity that fights RTS army control.

## Permafrost Audit

### Engine Rules And Formats

- Terrain and scene are separate assets by design.
- `PFMAP` stores terrain only: materials, optional splat mappings, and 32x32 tile chunks with height, ramp, material, and pathability data.
- `PFSCENE` stores factions, entities, optional regions, and optional cameras on top of a loaded map.
- `PFOBJ` stores mesh data, materials, optional skeletons, optional animation sets, and optional collision bounds.
- The scripting surface is the `pf` module, which already exposes the game-level verbs we care about:
  - factions and diplomacy
  - selection and left-click order modes
  - map loading and scene loading
  - minimap and cursor controls
  - regions and cameras
  - save/load
  - formation, combat, projectile, and resource helpers

### Stock Demo Design

- The public demo entrypoint is [scripts/rts/main.py](/Users/dev/Desktop/OpenGL%20RTS%20game%20engine/scripts/rts/main.py).
- The stock demo loads:
  - map: `assets/maps/demo.pfmap`
  - scene: `assets/maps/demo.pfscene`
- The demo scene defines 4 factions:
  - `Mother Nature`
  - `Sinbad's Forces`
  - `Goblin Confederacy`
  - `Wild Barbarians`
- The stock diplomacy setup makes factions `1`, `2`, and `3` mutually at war, while `Mother Nature` acts as the neutral environment faction.
- The stock scene has `388` entities total.
- The combat/unit roster currently present in the scene is:
  - `Goblin`: `16`
  - `Knight`: `12`
  - `Mage`: `10`
  - `Chicken`: `8`
  - `Berzerker`: `8`
  - `Sinbad`: `1`
- Cameras:
  - main RTS camera
  - debug FPS camera toggled with `C`
- Pause toggle is `P`.
- The stock left-side demo window lets the player:
  - switch controlled faction
  - open settings
  - open performance
  - pause/resume
  - open Session
  - open Console
  - exit

### Core RTS Interaction Rules In The Demo

- Unit control is faction-gated through `pf.set_faction_controllable(...)`.
- The action pad is selection-driven and only shows actions from the first selected controllable unit.
- The stock shared action grid is `3 x 4`.
- Current default action-pad verbs are:
  - `Move` on slot `0`, hotkey `M`
  - `Stop` on slot `1`, hotkey `S`
  - `Hold Position` on slot `2`, hotkey `H`
  - `Attack` on slot `3`, hotkey `A`
- These actions switch the engine into left-click target modes instead of directly resolving every order in UI code.
- Fog-of-war is part of the core game loop and should stay.
- The stock demo already depends on:
  - unit selection
  - minimap navigation
  - formation-aware movement
  - faction diplomacy
  - ranged and melee combat
  - session save/load

### Stock Unit Design

- `Knight`
  - melee
  - `max_hp=150`
  - `base_dmg=50`
  - `base_armour=0.5`
- `Goblin`
  - melee
  - `max_hp=120`
  - `base_dmg=40`
  - `base_armour=0.30`
  - rotates through multiple attack clips
- `Mage`
  - ranged projectile attacker
  - `max_hp=100`
  - `base_dmg=80`
  - `base_armour=0.10`
  - `attack_range=50.0`
- `Berzerker`
  - heavy melee
  - `max_hp=220`
  - `base_dmg=80`
  - `base_armour=0.25`
- `Sinbad`
  - hero-like showcase unit
  - `max_hp=250`
  - `base_dmg=80`
  - `base_armour=0.50`
  - has an extra action on slot `8` to toggle idle style
- `Chicken`, `Deer`, `Doe`
  - mobile ambient wildlife
  - no combat layer in the stock scripts

### Player-Facing Options

- Visible in the stock Settings UI:
  - aspect ratio
  - resolution
  - window mode
  - window always on top
  - vsync
  - shadows
  - water reflections
  - health bars
- Visible in the stock demo shell:
  - controlled faction
  - pause/resume
  - performance panel
  - session save/load
  - Python console

### Engine/Config Options Worth Preserving

- `pf.audio.*`
  - master volume
  - music volume
  - effect volume
  - music playback mode
  - mute on focus loss
- `pf.game.*`
  - healthbar mode
  - fog of war enabled
  - camera zoom
  - movement tick rate
  - combat tick rate
  - movement use GPU
  - storage-site UI mode
- `pf.video.*`
  - aspect ratio
  - resolution
  - display mode
  - always-on-top
  - vsync
  - shadows enabled
  - batch rendering
  - water reflection
  - water refraction
- `pf.debug.*`
  - render log mask
  - Python trace
  - GPU trace
  - pathfinding, formation, combat, automation, hearing, and faction-vision overlays

### Fork Constraints From The Audit

- Keep the map/scene split.
- Keep fog-of-war and minimap as first-class mechanics.
- Keep faction-controllability and diplomacy as engine concepts, not ad-hoc script state.
- Keep the left-click target-mode model for actions so the action pad stays readable.
- Keep unit actions small and icon-driven; do not turn the first vertical slice into a spell bar.
- Keep hero-like uniqueness grounded in stats, passives, stance changes, veterancy, equipment, and battlefield roles before adding any heavy FX layer.
- Keep the Mac shipping baseline aligned with the current Apple Silicon path:
  - no compute requirement for core gameplay
  - readable action icons
  - high-contrast minimap/HUD
  - batch-friendly content and restrained material complexity

## Mac Optimization Rules

- Keep the current Apple Silicon path as the shipping baseline.
- Avoid compute-shader dependencies for core gameplay systems.
- Prefer batched world rendering, limited material variety, and readable terrain overlays.
- Keep HUD/minimap high-contrast and legible on Retina displays.
- Build hero bonuses around gameplay state and existing systems before adding renderer-heavy effects.

## Execution Tracker

- `completed` Create a dated backup snapshot of the original RTS Python layer.
- `completed` Fork the RTS package into [scripts/hfmp_s2](/Users/dev/Desktop/OpenGL%20RTS%20game%20engine/scripts/hfmp_s2).
- `completed` Give the new package its own visible prototype identity and entrypoint wiring.
- `completed` Audit the engine docs, settings, and stock RTS scripts for actual rules, options, and design constraints.
- `completed` Launch the new package on Apple Silicon and confirm the forked entrypoint reaches the native runtime path cleanly.
- `completed` Replace the most obvious stock demo shell wording in the HFMP prototype window without changing gameplay rules.
- `completed` Treat the Apple Silicon RTS port as the stable branch baseline before expanding the fork.
- `completed` Replace stock faction framing and prototype naming with HFMP-specific terminology without breaking the proven Mac baseline.
- `completed` Define the first placeholder faction roster and 3-5 signature characters with non-magic bonus skills for the fork shell.
- `completed` Add a dedicated Mac launch path for the fork through `make run_hfmp PLAT=MACOS_ARM64`.
- `completed` Verify the HFMP fork launches on native Apple Silicon with its own faction identities.
- `completed` Re-verify that the stock Apple Silicon RTS baseline still launches unchanged after the fork slice.
- `pending` Replace the remaining stock faction roster, unit presentation, and scene framing with HFMP-specific content while keeping the same map/scene assets.
- `pending` Build the first real vertical slice with one player faction, one enemy faction, and curated signature-unit behavior differences.

## Verified Results

- `completed` `python3 -m py_compile scripts/hfmp_s2/main.py scripts/hfmp_s2/factions.py scripts/hfmp_s2/views/demo_window.py scripts/macos/pf_hfmp_launch_probe.py`
- `completed` `make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1`
- `completed` `make -n run_hfmp PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1`
  - expands to `./bin/pf-arm64 ./ ./scripts/hfmp_s2/main.py`
- `completed` `./bin/pf-arm64 ./ ./scripts/macos/pf_hfmp_launch_probe.py`
  - reports `HFMP_LAUNCH_READY factions=Frontier Wilds,Sentinel Compact,Rime Covenant,Ashen Raiders`
- `completed` `./bin/pf-arm64 ./ ./scripts/macos/pf_native_launch_probe.py`
  - still reports the stable stock Apple Silicon baseline marker after the HFMP fork slice

## Current Placeholder Faction Roster

- `Frontier Wilds`
  - neutral environment layer
  - ambient wildlife and map dressing
- `Sentinel Compact`
  - disciplined player-facing command faction
  - `Captain Rowan`: rally radius bonus
  - `Shield Knight`: brace stance bonus
  - `Trail Ranger`: faster fog reveal
- `Rime Covenant`
  - heavy assault rival faction
  - `Line Breaker`: charge impact bonus
  - `War Banner Bearer`: morale aura
  - `Iron Vanguard`: armour spike under focus fire
- `Ashen Raiders`
  - fast pressure/flanking rival faction
  - `Dust Scout`: wider sight arc
  - `Hook Duelist`: pursuit bonus
  - `Marauder Chief`: kill-chain damage ramp
- `pending` Build the first playable vertical slice on top of the new package.

## Immediate Next Slice

1. Replace the stock faction names and visible prototype framing with HFMP-specific terminology.
2. Define the first HFMP faction roster against the proven stock action model: move, stop, hold, attack, fog-of-war, minimap, save/load.
3. Start the first playable vertical slice on top of the already-verified Mac launch path.
