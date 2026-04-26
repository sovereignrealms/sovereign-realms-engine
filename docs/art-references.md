# Art Reference Sources — Priority & Use

Reference-image strategy for the asset generation pipeline (Meshy image-to-3D → Blender).
Order matters: prefer earlier-listed sources when fetching references for a unit.

---

## Tier 1 — Public Domain / Open License (preferred)

**Why first:** zero IP risk, freely usable for commercial output.

- **Wikimedia Commons** — historical reenactor photography, museum artifacts, classical sculpture, book illustrations
- **Wikipedia (PD-licensed images only)** — many history articles use Commons-sourced images
- **Public-domain art collections** — Met Museum Open Access, Rijksmuseum, British Museum (where licensed openly), Smithsonian Open Access
- **PD historical illustrations** — 19th-century lithographs and engravings of Roman/Greek/Macedonian soldiery (often via Commons)
- **Classical sculpture** — Trajan's Column reliefs, Alexander Sarcophagus, Parthenon friezes, etc. — photos of these are usually Commons-licensed

## Tier 2 — Educational / Reenactor Sources

- Reenactment society websites and historical recreation photography
- Museum educational materials
- Academic illustrations (often free for non-commercial)

## Tier 3 — Japanese Historical Manga (style reference, with IP caveats)

**Why:** highest-quality character design for ancient warriors with consistent, gameable visual language. Used as **stylistic reference**, not direct copy.

| Manga | Author | Era / Setting | Best for |
|-------|--------|---------------|----------|
| [Ad Astra: Scipio and Hannibal](https://en.wikipedia.org/wiki/Ad_Astra:_Scipio_and_Hannibal) | Mihachi Kagano | Second Punic War (~218–202 BC) | Roman legionaries, Carthaginian forces, Numidian cavalry, war elephants |
| [Historie](https://en.wikipedia.org/wiki/Historie) | Hitoshi Iwaaki | Hellenistic / Macedonian (~340 BC) | Macedonian companions, Greek hoplites, Persian Achaemenid forces, Alexander's army |
| [Kingdom](https://en.wikipedia.org/wiki/Kingdom_(manga)) | Yasuhisa Hara | Warring States China (~245 BC) | Chinese infantry/cavalry, command armor, generals' regalia *(Chinese setting — see civ-roster note below)* |

## Tier 4 — Game / Concept Art (last resort, IP-heavy)

Use only when Tier 1–3 don't cover a specific need. Examples:
- Total War: Rome / Imperator concept art
- Age of Empires II: DE concept art
- Civilization VI character art

**IP caveat:** copyrighted. Acceptable as visual reference during development; not safe to ship anything that mirrors them too closely.

---

## IP & Licensing Notes

- **Tier 1 sources:** safe for commercial use — verify each image's specific license tag on Wikimedia (CC0, CC-BY, PD-old, etc.)
- **Tier 3 (manga):** copyrighted by the publisher (Shogakukan for *Ad Astra* and *Kingdom*; Kodansha for *Historie*). Using panel/promo art as **input** to AI 3D generation produces a **derivative work** — visually distinct outputs are typically fine for indie use, but avoid generating outputs that closely mimic specific characters or panel compositions.
- **General rule:** the more your final asset resembles a specific copyrighted source, the riskier it is to ship commercially. Lean Tier 1 → Tier 3 → Tier 4 in that priority.
- **Style ≠ copyright.** Anime/manga *style* itself isn't copyrightable — only specific character designs and panel art are.

---

## Civ-Roster Note (Kingdom-related)

*Kingdom* is set in **Warring States China**, not Mediterranean antiquity. It overlaps temporally with the existing primary civs (~3rd century BC) but introduces a different cultural roster (Qin, Zhao, Wei, Chu, Yan, Han, Qi).

Two ways to use it:
1. **Style reference only** — pull visual language (composition, proportions, dramatic poses, armor detail style) without adding Chinese civs to the game roster
2. **Add Chinese civ(s)** to the roster — would expand the setting beyond purely Mediterranean into a broader "ancient world" theme

*Decision pending — see [civilizations.md](civilizations.md).*

---

## Folder Layout

```
assets/refs/
  <civ>_<unit>/
    pd/              # Tier 1 — public domain
      front.jpg
      side.jpg
      reenactor.jpg
    manga/           # Tier 3 — style reference
      ad_astra_<character>.jpg
      historie_<character>.jpg
    concept/         # Tier 4 — game/concept art (last resort)
      <source>_<thing>.jpg
    SOURCES.md       # per-unit source list with URLs and licenses
```

Each `SOURCES.md` records: file name, source URL, license, date fetched, notes.
