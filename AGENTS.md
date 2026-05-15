# Local Project Notes

- When `pf-arm64` is frozen or half-responsive on macOS, prefer a force kill over a normal kill. Use `killall -9 pf-arm64`.
- Before pushing the HFMP-style game fork forward, first read and document the engine rules, gameplay options, and current game design so the next changes match how Permafrost actually works.
- If the user narrows scope to Apple Silicon polish for the existing game, keep HFMP fork work and Metal support deferred until that polish phase is explicitly complete.
- In the Metal migration, prefer the smallest visible gameplay-feedback slice first; wire world selection overlays before attempting drag-box or minimap work.
- For Metal visual parity captures, keep staged water-edge units and rocks/static props in the evidence loop; do not judge water or mesh parity from empty scenery-only screenshots.
- Keep player selection rings neutral white and thin; do not make them saturated team-colored or thick for readability. Wide-zoom readability should come from small zoom-scaled healthbars, silhouettes, LOD/icon rules, and subtle asset-side accents.
- Follow AoE-style team readability: minimap markers may use strong faction colors, but main-world materials should not be broadly tinted. Only small authored accents such as shields, banners, cloth trim, flags, or building trim should use team-color masks.
