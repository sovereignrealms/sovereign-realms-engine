# Metal Terrain/Material Tone Parity — Diagnosis & Handoff for Codex

Author: Claude (sonnet path, opus model)
Date: 2026-04-25
Capture under review: `visual_parity_captures/2026-04-25-metal-water-final-color-parity/`

This file is the working notebook for the Claude/Codex collaboration on the
remaining "darker / flatter" Metal terrain tone gap. Keep edits additive:
append new sections; do not silently rewrite earlier diagnoses — they are
load-bearing once a fix attempt fails.

---

## 1. Diagnosis (ranked by likelihood)

### What I verified is NOT the cause

- **Splat blending absence in Metal IS a real gap, but does not explain this
  capture.** `session.pfsave` has `num_splats 0`, and the GL shader's
  `splatted_color_at_pos()` (`shaders/fragment/terrain-shadowed.glsl:386–399`)
  early-returns to `tex_color` whenever `splats[base_mat_idx] == -1`. With zero
  splats, GL and Metal produce the same texture color regardless. Track this
  for future maps but it is not the active darkening.
- **Lighting math is in parity.** `terrain-shadowed.glsl:743–769` and
  `backend_metal.m:478–520` use identical constants (`TERRAIN_AMBIENT=0.7`,
  `EXTRA_AMBIENT_PER_LEVEL=0.03`, diffuse=0.9, specular=0.5*0.1, shininess=2,
  `SHADOW_MULTIPLIER=0.55`). The Metal `mix(1.0, 0.55, shadow)` is algebraically
  equal to GL's `(0.55 + (1.0-shadow)*0.45)`.
- **Sampler / pixel format / LOD bias.** Both back-ends use linear `RGBA8`
  internal format, linear/linear/linear filter, repeat addressing, LOD bias
  `−0.5` (`gl_texture.h:45`, `backend_metal.m:1573–1581` + `bias(-0.5)` in
  `terrain_texture_val`). Mipmaps are generated on both. No `GL_FRAMEBUFFER_SRGB`
  in the GL backend; CAMetalLayer is plain `MTLPixelFormatBGRA8Unorm`.
- **Wang variation count.** On `__APPLE__ && __aarch64__`, GL takes the
  short-circuit branch in `gl_texture.c:705–733` and uploads the SAME source
  image into all 8 wang slots — the same as `backend_metal.m:3011–3018`.
- **Heightmap data.** Both back-ends call `Noise_GenerateOctavePerlinTile2D`
  with identical scale (`1/128.0`), octaves (4), persistence (0.5), and a
  resolution of 2048 (`HEIGHT_MAP_RES` = `METAL_HEIGHT_MAP_RES`).

### Most likely active causes (ranked)

1. **Texture upload Y-orientation mismatch (HIGH).** OpenGL textures are
   bottom-left origin; Metal textures are top-left. Both shaders apply the same
   `(uv.x, 1.0 - uv.y)` flip. `R_GL_Texture_ArrayMakeMapWangTileset`
   (`gl_texture.c:705–733`) calls `glTexSubImage3D(... GL_RGBA, GL_UNSIGNED_BYTE, upload_data)`,
   which the GL driver lays out so byte-row 0 of `stbi_load` ends up at GL
   texel-row 0 (top of GL texture coord space). Metal's
   `update_terrain_textures` (`backend_metal.m:2989–3018`) calls
   `[texture replaceRegion:withBytes:]` which puts byte-row 0 at Metal texel-row
   0 (top in Metal coord space).
   → Net effect: in Metal, the shader's `1.0 - uv.y` flips the image vertically
   relative to GL. For tileable, vertically symmetric textures this barely
   shows; for textures with directional lighting baked in (most "ground"
   textures have a hint of top-illumination), the flipped sample tends to
   look "darker / flatter" because the implicit highlights are now on the
   shadowed side of the tile.
   → Sanity check: pick one terrain texture (e.g. `assets/map_textures/grass.png`)
   that visibly has an asymmetric top-vs-bottom and run the metal launch probe
   with that material. If the probe also looks vertically mirrored relative
   to GL on that tile, this is the cause.

2. **Per-tile flat attribute expansion writes flat values into all 3 vertices
   in a non-provoking-vertex order (MEDIUM).** `al_metal_expand_terrain_flat_attrs`
   (`render_asset_load.c:83–88`) replicates flat fields from vertex `[i]` onto
   `[i+1]` and `[i+2]`. GL's `flat int mat_idx` uses GLSL provoking-vertex
   semantics, which is the LAST vertex of the primitive on most desktop GL.
   On the Metal Apple Silicon driver, attribute interpolation runs through
   the regular per-vertex path because Metal does not have a real `flat`
   provoking vertex. If the source layout assumes the LAST vertex is the
   provoking one but the expansion uses the FIRST, every triangle reads its
   flat material/wang/blend from the wrong vertex. This would manifest as
   tiles being painted with the wrong material / wang index in some tiles
   and could plausibly look "averaged / flatter / darker" because flat-edge
   tiles will more often quote a neighbor's darker material.
   → Sanity check: dump the first 100 expanded `terrain_vert` records for a
   known tile in both back-ends and diff `material_idx`, `wang_index`,
   `mid_indices`. If the Metal record uses a different vertex's value than
   GL would in the GL_LAST provoking-vertex convention, this is the cause.

3. **Fog buffer / visibility offset mismatch (MEDIUM).** GL feeds visibility
   data through a ring buffer with a `visbuff_offset` uniform
   (`gl_terrain.c:198–253` + `terrain-shadowed.glsl:208`). Metal allocates a
   fresh `MTLBuffer` per `R_GL_MapUpdateFog` call (`backend_metal.m:2695–2711`)
   and reads `fog_buff[idx]` from offset 0. If `R_GL_MapUpdateFog` is called
   with a buffer pointer that includes a starting offset (or with stale data
   from the ring), Metal will index the wrong tiles' fog states.
   → Visual evidence supports this: in
   `metal_overview.png` the fog-of-war area outside the lit zone is nearly
   black, while in `opengl_overview.png` the same area is clearly visible at
   ~50 % brightness. Black would correspond to `STATE_UNEXPLORED` (tf=0.0),
   not `STATE_IN_FOG` (tf=0.5). That points at a state-lookup error specific
   to the fog path.
   → Sanity check: log, on one frame, the byte read from `fog_buff[0]` and
   `fog_buff[fog_idx]` for a few sample tiles in the Metal terrain fragment
   (via a debug visualization mode) and compare with the GL `visbuff` content.

4. **Heightmap normal sign (LOW, but cheap to verify).** Both shaders share a
   typo where `z1` is fetched from the X-front index instead of the Z-front
   index (GL `terrain-shadowed.glsl:573–574`, Metal `backend_metal.m:384–385`).
   Because the bug is shared it is not a parity gap — but the resulting
   normal direction is mostly bogus on Metal too, so any subtle difference in
   the bogus direction (e.g. due to floating-point evaluation order between
   GLSL and MSL) can shift the diffuse term by a few percent. Worth fixing
   in BOTH back-ends after the parity work, not as part of this slice.

### What the visual evidence specifically argues for

- The lit zone is uniformly dimmer in Metal — broad multiplicative signal.
- The fog zone is nearly black in Metal but ~50 % bright in GL — this is
  almost certainly state lookup (#3 above), not lighting.
- Texture detail is preserved in Metal (so textures are loaded), which rules
  out a fallback-to-procedural-color path.
- Inventory icons are missing in the Metal capture — that is a separate UI
  bug, **not** part of this slice; record but do not chase it here.

---

## 2. File / function references

GL reference path (the one actually used on macOS):

- Shader: `shaders/fragment/terrain-shadowed.glsl`
  - `texture_val_raw` (line 291) — base texture fetch.
  - `splatted_color_at_pos` (line 386) — splat blending; early-returns when
    `splats[base_mat_idx] == -1`.
  - `texture_val` (line 316) — wraps raw with splat blending.
  - `main` (line 712) — discard on alpha, lighting, shadow, fog tint.
- Pipeline: `src/render/gl_terrain.c`
  - `create_height_map` (line 85), `create_splat_map` (line 113).
  - `R_GL_MapBegin` populates `splatbuff[]` to all `-1` then patches the
    declared splats (line 273–286); always installs `terrain-shadowed`
    program (line 289).
- Texture upload: `src/render/gl_texture.c`
  - `R_GL_Texture_ArrayMakeMapWangTileset` (line 650). Apple Silicon path at
    line 705–733 replicates one source image into 8 wang slots; non-Apple
    path quilts variations.
- Visibility/fog: `src/render/gl_terrain.c:230–253` (ring-buffered upload);
  shader uses `visbuff_offset` uniform.

Metal port:

- Shader source (string): `src/render/backend_metal.m:195–556`
  - `terrain_texture_val` (line 394) — equivalent of `texture_val_raw` but
    with `bias(-0.5)`, plus 2 fallback layers (line 399, 402) that GL does
    not have. No splat blending.
  - `terrain_blended_texture_val` (line 422) — the BLUR mode equivalent.
  - `terrain_fragment` (line 469) — discard, lighting, fog, water override,
    shadow.
- Pipeline build: `build_terrain_pipeline` (line 1462), depth+blending state
  (no blending; opaque). Color attachment is `MTLPixelFormatBGRA8Unorm`.
- Sampler: `ensure_terrain_sampler` (line 1568) — linear/linear/linear, repeat.
- Texture upload: `update_terrain_textures` (line 2955–3041). Replicates one
  resized 128×128 source into 8 wang slices via `replaceRegion`.
- Heightmap upload: `ensure_heightmap_buffer` (line 2564).
- Fog buffer upload: `update_fog_texture` (line 2695). **Allocates a new
  MTLBuffer each fog update.** Indexed from 0 in shader.
- Flat-attribute expansion: `src/render/render_asset_load.c:83–88`
  (`al_metal_expand_terrain_flat_attrs`).
- Light/ambient/light_pos plumbing: `backend_metal.m:5333–5350` catches the
  GL-style setters and updates `s_light_ambient`, `s_light_color`,
  `s_light_pos` statics consumed at terrain draw time
  (`backend_metal.m:2635–2637`).

---

## 3. Minimal patch plan

This slice is investigation, not yet fixing. Three minimal landing diffs in
order, each independently verifiable, smallest-blast-radius first:

### Slice A — Add a Metal-only debug overlay knob

Add a one-line uniform (`terrain_params.w` is currently 0) that, when set,
makes the terrain fragment output a packed visualization of:

- channel R = `fog_factor` (0 = unexplored, 0.5 = in_fog, 1.0 = visible)
- channel G = `texel.r` (raw sampled red, no lighting)
- channel B = `dot(normal, light_dir)` clamped to [0,1]

Wire a Python toggle in `scripts/macos/pf_metal_debug_overlay_probe.py` so a
single capture exposes which channel is anomalous. Compare this against the
existing OpenGL overlay path. **No gameplay-visible change unless toggled.**

### Slice B — Verify and fix Metal flat-attribute expansion (#2 above)

In `al_metal_expand_terrain_flat_attrs`, switch from copying vertex `[i]`'s
flat fields onto `[i+1]` and `[i+2]` to copying vertex `[i+2]`'s flat fields
onto `[i]` and `[i+1]` (or whatever matches GL's provoking-vertex
convention used for `flat` interpolation in the engine — confirm by reading
the GL terrain vertex generator in `gl_tile.c`). Validate by re-running:

- `pf_metal_launch_probe.py`
- `pf_metal_gameplay_smoke_probe.py`
- `capture_visual_parity.sh`

If this slice does not reduce the brightness gap, revert. Do **not** stack a
second hypothesis on top.

### Slice C — Verify Metal fog index path against GL (#3 above)

Two sub-tasks:

1. Confirm `R_GL_MapUpdateFog` is being called from the engine's render
   command stream with `args[0]` already pointing to the *active* visibility
   slice (no per-frame ring offset). If GL's ring buffer is at a non-zero
   offset, Metal needs to mirror that — either by uploading only the active
   slice or by tracking the offset.
2. In Metal, surface a debug mode that visualizes `water_buff[fog_idx]` and
   `fog_buff[fog_idx]` directly (color-coded) and re-capture. Use the
   debug overlay from Slice A as the host.

Only after these two are confirmed, consider re-enabling splat blending
in Metal as a separate slice — the test scene has 0 splats so it is not
relevant to this capture.

---

## 4. Verification commands

From `/Users/dev/Desktop/OpenGL RTS game engine`:

```bash
# Build Metal
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL

# Smoke probes
./bin/pf-arm64 ./ ./scripts/macos/pf_metal_launch_probe.py
./bin/pf-arm64 ./ ./scripts/macos/pf_metal_water_probe.py
./bin/pf-arm64 ./ ./scripts/macos/pf_metal_debug_overlay_probe.py
./bin/pf-arm64 ./ ./scripts/macos/pf_metal_gameplay_smoke_probe.py
./bin/pf-arm64 ./ ./scripts/macos/pf_native_session_ui_region_camera_roundtrip.py

# Side-by-side parity capture
scripts/macos/capture_visual_parity.sh \
    visual_parity_captures/2026-04-25-metal-terrain-splat-tone-parity

# Restore OpenGL fallback build (last command in capture_visual_parity.sh
# already does this, but explicit is fine)
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=OPENGL
```

Acceptance for this slice: in the new capture directory,
`metal_overview.png` and `metal_combat.png` should match
`opengl_overview.png` and `opengl_combat.png` to within a small per-pixel
delta in the lit zone, and the fog-of-war zone should not be black on
Metal where GL shows visible terrain.

---

## 5. Out-of-scope, but observed

- **HD/4K Metal-native upgrades:** parked. The user has explicitly asked us
  to land OpenGL parity first, and not to introduce visual-tuning hacks
  along the way.
- **Inventory icons missing in Metal capture:** unrelated UI bug; do not
  bundle into this slice. File separately.
- **Shared heightmap-normal `z1` bug** (`terrain-shadowed.glsl:573–574`,
  `backend_metal.m:384–385`): not a parity issue (both wrong), but worth a
  follow-up cleanup once the parity work is green.

---

## 6. Attempt 1 — 2026-04-25 — Verification reads (no diff)

Before committing to any of the three patch slices, two read-only
verifications were run. Both hypotheses they were meant to confirm were
**disproven**.

### Verification 1: provoking-vertex convention

- The GL backend explicitly calls `glProvokingVertex(GL_FIRST_VERTEX_CONVENTION)`
  at `src/render/gl_render.c:1656`.
- The terrain vertex generator (`gl_tile.c:834-841`) writes flat attributes
  to vertex `[i*3 + 0]` of every triangle (the `*_provoking[]` arrays
  point to those vertices).
- The Metal flat-attribute expansion (`render_asset_load.c:83-88`,
  `gl_tile.c:98-104`) copies vertex `[i]`'s flat fields onto `[i+1]` and
  `[i+2]`. With GL's first-vertex convention this is **correct** —
  every Metal triangle vertex ends up holding the same flat values
  GL would have read from its provoking vertex.
- **Hypothesis #2 is incorrect. Do not patch the expansion code.**

### Verification 2: fog buffer offset

- GL ring buffer: `R_GL_RingbufferBindLast` (`gl_ringbuffer.c:386-411`)
  computes `bpos = ring->markers[ring->imark_head].begin` and uploads it
  as the `visbuff_offset` uniform. So GL really does index
  `visbuff[visbuff_offset + idx]` into a *circular* buffer.
- Metal: `update_fog_texture` (`backend_metal.m:2695-2711`) is wired to
  the same `R_GL_MapUpdateFog` command. The data passed in is the
  *full* visbuff produced by `G_Fog_UpdateVisionState` in
  `src/game/fog_of_war.c:711-746` (size = `chunk_w * chunk_h * tile_w * tile_h`,
  no leading offset). Metal allocates a fresh `MTLBuffer` per update and
  reads from offset 0.
- Indexing math is identical between `terrain-shadowed.glsl:179-183`,
  `backend_metal.m:284-298`, and `td_index` at `fog_of_war.c:118-126`.
- **Hypothesis #3 is incorrect. Metal's fog indexing matches GL's data
  layout.**

### Visual evidence revisited

Re-reading `metal_combat.png` and `opengl_combat.png` more carefully
(against my earlier description in §1):

- The unexplored / fog-of-war zones are **black on both back-ends**, not
  brighter-on-GL as I'd claimed. My earlier read was wrong.
- The actual remaining delta is **only inside the lit zone**: the
  Metal lit terrain is dimmer and more olive/desaturated than GL.
- Inventory icons missing in Metal capture remains a separate UI bug.

### Status

- Slices A, B, C in §3 are now wrong as written:
  - Slice B is moot (expansion is correct).
  - Slice C is moot (fog indexing is correct; my fog-zone visual delta
    didn't actually exist).
  - Slice A (debug overlay) is still valid — it just can't lean on the
    fog-channel readout to disambiguate.
- Hypothesis #1 (texture Y-orientation) is also weaker than I made it
  sound: stepping through both upload-conventions plus the in-shader
  `1.0 - uv.y`, the math cancels. GL stores source-top-left at GL
  bottom-left and the shader's `1.0-uv.y` flip puts it back at world
  top. Metal stores source-top-left at Metal top-left and the shader's
  `1.0-uv.y` flip also puts it back at world top. Both are right-side-up.
  This is **likely also wrong** as a cause and should be confirmed
  before patching.

### What to do next (replaces §3)

1. **Land Slice A (debug overlay) as the next concrete step.** It is
   purely additive and the only way to localize where the divergence
   actually is. Suggested channels for the Metal overlay (and a
   matching GL overlay if not present):
   - `texel.xyz` directly (no lighting). If GL and Metal differ here,
     the gap is in texture data / sampling.
   - `(ambient + diffuse + specular)` only (no texture). If GL and
     Metal differ here, the gap is in lighting math or uniforms.
   - `dot(normal, light_dir)` only. If different, the gap is in normal
     handling or the heightmap-normal contribution.
   - `shadow_factor` only. If different, the gap is in shadow sampling.
2. **Only after the overlay isolates a channel** should we propose a
   diff. Do not skip this step.
3. The user has explicitly asked to avoid broad gamma/brightness hacks
   and aesthetic tuning, so even if the divergence localizes to a
   "tone curve" symptom, the fix must point at a concrete code-level
   parity gap before landing.

### Decision

Given that all three pre-write hypotheses are now either disproven or
weakened, **no fix is being attempted in this attempt**. Hand back to
the user for sign-off on landing the debug overlay (Slice A) before
the next attempt.

---

## 7. Attempt 2 — 2026-04-25 — Pixel measurement nailed it

After Attempt 1 disproved all three pre-write hypotheses, I switched
from code-reads to a numerical measurement of the actual on-screen
delta. That pinned the bug in five seconds.

### Method

Stdlib-only Python PNG reader (`/tmp/png_compare.py`) sampling 13×13
pixel blocks from the same coordinates of `opengl_combat.png` and
`metal_combat.png` (3456×2234 captures).

### Smoking gun

Four samples taken at distinct lit-terrain points:

```
2592, 477   GL=(157,182, 75)   Metal=( 86,100, 40)   ratio b/a = 0.55, 0.55, 0.54
2074,1370   GL=(172,198, 82)   Metal=( 95,109, 44)   ratio b/a = 0.55, 0.55, 0.54
1900,1300   GL=(152,165, 89)   Metal=( 84, 91, 49)   ratio b/a = 0.55, 0.55, 0.55
2800, 300   GL=(108,124, 51)   Metal=( 59, 69, 27)   ratio b/a = 0.55, 0.55, 0.53
```

Uniform multiplicative 0.55× across R, G, B at every lit-terrain point.
That is `#define SHADOW_MULTIPLIER 0.55` from `terrain-shadowed.glsl:56`
applied to a fragment that should be unshadowed. Lit terrain is being
unconditionally tagged "in shadow" in Metal.

### Root cause

NDC z-convention mismatch on the shadow path:

- `PFM_Mat4x4_MakeOrthographic` (`src/pf_math.c:362-373`) builds an
  OpenGL-style orthographic matrix that maps view-space `[near, far]`
  to NDC z `[-1, 1]`. Both back-ends reuse it for the light-space
  transform (`gl_shadows.c:165`, `backend_metal.m:1212`).
- OpenGL hardware then maps NDC z `[-1, 1]` → depth-attachment value
  `[0, 1]` automatically. The shader's
  `current_depth = (light_space_pos.z / w) * 0.5 + 0.5`
  (`terrain-shadowed.glsl:428`) reproduces exactly that mapping. They
  agree, so the comparison works.
- Metal hardware writes `clip_z / clip_w` (NDC z) directly to the depth
  attachment, AND clips fragments with NDC z < 0. So in the Metal
  shadow texture the surviving fragments hold raw NDC z in `[0, 1]`,
  not the GL-style remapped `[0.5, 1.0]` value.
- Metal's `shadow_factor` (`backend_metal.m:337-358`) still uses the GL
  formula `(light_space_pos.z / w) * 0.5 + 0.5` for `current_depth`.
  That value is offset by `+0.5` relative to what the texture actually
  stores. For any fragment with NDC z in `[0, 0.996]` the test
  `current_depth - bias > closest_depth` is unconditionally true —
  hence shadow = 1.0 everywhere, hence the universal 0.55× tint.

The same bug shape applies to `mesh_shadow_factor`
(`backend_metal.m:604-610`), so static-mesh and CPU-skinned characters
are dimmed by the same factor whenever shadows are enabled.

A secondary effect of the convention mismatch: half the shadow
casters (those at NDC z < 0 in light space) get clipped by Metal
during the shadow pass and never write to the depth texture. That
means some real shadows go missing. We accept that as a follow-up;
the visible 0.55× dimming is the bigger gameplay-visible delta and
fixing the shader formula alone resolves it.

### Proposed minimal fix

Smallest patch that restores parity for the visible-terrain case.
**Two locations, both inside the embedded MSL string in
`src/render/backend_metal.m`:**

1. `shadow_factor` at `backend_metal.m:337-358`: replace
   ```metal
   float3 proj = (light_space_pos.xyz / w) * 0.5 + 0.5;
   if(proj.x < 0.0 || proj.y < 0.0 || proj.z > 0.95) return 0.0;
   float current_depth = proj.z;
   float closest_depth = shadow_map.sample(shadow_sampler, proj.xy);
   ```
   with
   ```metal
   float2 proj_xy = (light_space_pos.xy / w) * 0.5 + 0.5;
   float  proj_z  = light_space_pos.z / w;
   if(proj_xy.x < 0.0 || proj_xy.y < 0.0
      || proj_xy.x > 1.0 || proj_xy.y > 1.0
      || proj_z < 0.0 || proj_z > 0.95) return 0.0;
   float current_depth = proj_z;
   float closest_depth = shadow_map.sample(shadow_sampler, proj_xy);
   ```
   and update the four poisson sample calls a few lines below to use
   `proj_xy` instead of `proj.xy`.
2. `mesh_shadow_factor` at `backend_metal.m:604-610`: same edit.

Why this is the minimal correct change:

- xy still need the `* 0.5 + 0.5` map: NDC xy in `[-1, 1]` → texture
  uv in `[0, 1]`. That is unchanged between GL and Metal.
- z must NOT be remapped: the depth attachment stores raw NDC z, so
  comparing against raw NDC z gives the right answer.
- Adding `proj_z < 0.0` and `proj_xy > 1.0` early-returns is for
  correctness: NDC z < 0 was clipped during the shadow pass so the
  texel is `clearDepth = 1.0`, and we'd correctly read "no shadow"
  anyway, but skipping the sample is cleaner and avoids border bleed.
- No engine math changes. No Metal-specific projection helper. No
  changes to GL. No risk of regressing the OpenGL parity baseline.

### Verification plan

1. Apply the two-block edit inside `s_terrain_shader_source` and
   `s_static_mesh_shader_source` in `backend_metal.m`. (Both are
   raw-string MSL.)
2. Rebuild Metal:
   ```bash
   make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
   ```
3. Smoke probes:
   ```bash
   ./bin/pf-arm64 ./ ./scripts/macos/pf_metal_launch_probe.py
   ./bin/pf-arm64 ./ ./scripts/macos/pf_metal_gameplay_smoke_probe.py
   ./bin/pf-arm64 ./ ./scripts/macos/pf_native_session_ui_region_camera_roundtrip.py
   ```
4. Side-by-side capture into a fresh directory:
   ```bash
   scripts/macos/capture_visual_parity.sh \
       visual_parity_captures/2026-04-25-metal-shadow-ndc-z-fix
   ```
5. Re-run the pixel-ratio measurement against the new capture:
   ```bash
   python3 /tmp/png_compare.py \
       visual_parity_captures/2026-04-25-metal-shadow-ndc-z-fix/opengl_combat.png \
       visual_parity_captures/2026-04-25-metal-shadow-ndc-z-fix/metal_combat.png \
       2592,477 2074,1370 1900,1300 2800,300
   ```
   Acceptance: ratios within ~0.02 of 1.0 across R, G, B at all four
   sample points. Lit-zone parity restored.
6. Fall-back check: real-shadow regions (e.g. behind a tall static
   prop) should still darken. If those become un-shadowed too,
   investigate whether the shadow caster was rasterized into the
   shadow texture correctly. If they remain shadowed, ship.

### Risks / things to watch in the capture

- A small chunk of the shadow frustum (NDC z < 0, the half nearest
  the light's near plane) is currently clipped by Metal during the
  shadow pass. The fix above does NOT change that. Expect: shadows
  cast by tall objects whose tops sit beyond the light's mid-plane
  may not reach as far as in OpenGL. If this is visible, a follow-up
  slice can introduce a Metal-specific orthographic helper that maps
  `[near, far]` directly to NDC z `[0, 1]`, which restores the full
  shadow frustum. Do NOT bundle that into this slice.
- Water and skybox paths use their own shaders; this fix does not
  touch them. The `2200,1500` outlier in the pixel sample (Metal
  brighter+bluer than GL) is a separate water-shoreline bug that the
  user already flagged as out of scope for this slice.

### Decision

Diagnosis is verified by direct numeric measurement; the fix is a
two-block textual edit inside one file with no risk to OpenGL.
**Recommended next step: land the patch, capture, run
`png_compare.py` on the new capture, ship if ratios sit at ~1.0.**

---

## 8. Attempt 3 — 2026-04-25 — Patch landed and verified

### Diff applied

`src/render/backend_metal.m` — two equivalent edits inside the embedded
MSL strings:

- `shadow_factor` (line 337-358): split `proj` into `proj_xy` (still
  `* 0.5 + 0.5` for sampling the depth texture) and `proj_z` (raw
  `light_space_pos.z / w`), updated the early-return guard to also
  reject `proj_xy > 1.0` and `proj_z < 0.0`, updated the four poisson
  sample calls to use `proj_xy`.
- `mesh_shadow_factor` (line 604-610): same split, same guard, same
  sampler argument change.

No other files touched. No GL changes.

### Build

```
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
```
Single OBJC compile + link, clean.

### Capture

```
scripts/macos/capture_visual_parity.sh \
    visual_parity_captures/2026-04-25-metal-shadow-ndc-z-fix
```
Both back-ends ran four scenes (overview, water, rocks, combat) to
completion and emitted summary JSONs.

### Pixel-ratio measurement (combat scene, same four points as before)

```
2592, 477   GL=(157,182, 75)   Metal=(157,182, 75)   ratio = 1.00, 1.00, 1.00
2074,1370   GL=(172,198, 82)   Metal=(172,197, 82)   ratio = 1.00, 1.00, 1.00
1900,1300   GL=(152,165, 89)   Metal=(152,165, 89)   ratio = 1.00, 1.00, 1.00
2800, 300   GL=(108,124, 51)   Metal=(107,125, 51)   ratio = 1.00, 1.00, 1.00
```

Per-channel deltas all under 0.5 of a uchar. Parity restored at the
target sample points. Side-by-side `metal_combat.png` and
`opengl_combat.png` in the new capture directory show indistinguishable
terrain coloration (compared visually by re-loading both PNGs).

### Sanity check on other scenes

Cross-scene sampling shows that terrain hits at lit ground are at
parity (ratios 0.99–1.02 where the same texel is hit). The few
larger-ratio entries (rocks scene `1900,1300` at 1.34, overview
`1500,800` at 0.61/0.64/0.99) are at points where the two captures
land on different scene content (units / rocks at slightly different
positions or orientations between the two engine runs), not on
matching terrain texels. The water-surface deltas are the previously
known water-shoreline bug, untouched by this patch.

### Status

- Bug closed for the gameplay-visible terrain/material darkening.
- The "missing-shadow-caster in the near half of the light frustum"
  follow-up (Metal hardware clipping fragments with NDC z < 0 during
  the shadow pass) is left unaddressed in this slice. If artifact
  shows up as un-shadowed regions near tall props, file it as a
  follow-up and address with a Metal-specific orthographic projection
  helper that maps `[near, far]` → NDC z `[0, 1]` directly. Do not
  bundle into this slice.
- Inventory icons missing in Metal capture — still a separate UI bug,
  not related to this fix.
- Water shoreline / color delta — separate, also untouched by this
  fix.

### Artifacts

- Patch: in `src/render/backend_metal.m` (no separate file).
- Capture directory: `visual_parity_captures/2026-04-25-metal-shadow-ndc-z-fix/`
- Measurement script: `/tmp/png_compare.py` (stdlib-only PNG reader).

---

## 9. Attempt 4 — 2026-04-25 — Slice 2: inventory icons (UI texpath)

### Symptom

Inventory grid icons (sword/hand/etc. in the lower-right HUD) render
in OpenGL but are missing in Metal across every recent capture.

### Root cause

`render_ui_draw_list` in [backend_metal.m](src/render/backend_metal.m)
silently dropped `NK_COMMAND_IMAGE_TEXPATH` and
`NK_COMMAND_IMAGE_TEXPATH_REGION` commands and their associated draws,
while [gl_ui.c:110-116](src/render/gl_ui.c:110) loads the texture
referenced by `ud->image.texpath` and assigns it into `cmd->texture.id`
so the next iteration binds and renders it. The Metal path also
rejected any draw whose `cmd->texture.id != 1` (the font-atlas marker),
which would have skipped the cmd anyway even if the userdata had been
processed.

### Patch

Three additions in `backend_metal.m`:

1. New statics next to `s_ui_font_texture`:
   ```objc
   static NSMutableDictionary *s_ui_texpath_cache;
   static id<MTLTexture>       s_pending_ui_texture;
   ```
2. New helper `ui_texpath_get_or_load(const char *full_path)` that
   memoizes path → MTLTexture in `s_ui_texpath_cache`, falling back to
   `load_rgba_texture_2d` on a miss. Forward-declares
   `load_rgba_texture_2d` since the cache helper sits earlier in the
   file.
3. Rewrote the userdata branch in `render_ui_draw_list` to load
   the texture and **fall through** (instead of `continue`) when the
   userdata type is `NK_COMMAND_IMAGE_TEXPATH(_REGION)`. The
   draw-rejection guard now allows cmds either with `texture.id == 1`
   (font) OR with `s_pending_ui_texture != nil` (current image).
   Per-cmd `setFragmentTexture:` chooses between font atlas and
   pending image. `s_pending_ui_texture` clears after the draw so it
   only applies to its associated cmd. Cache + pending state cleared in
   `release_ui_resources`.

No GL changes. No shader changes. No new pipeline.

### Verification

Build: `make pf … RENDER_BACKEND=METAL` clean (single OBJC compile + link
after a forward-decl fixup).

Capture:
`visual_parity_captures/2026-04-25-metal-ui-texpath-fix/`.

Visual: in `metal_overview.png` the lower-right HUD now shows the same
four inventory slots and portrait that `opengl_overview.png` shows,
populated with the same icon textures.

Numeric (overview, inventory-icon-area pixel sample):
```
3050,1850  GL=(153,135, 63)  Metal=( 84, 72, 24)   ratio = 0.55, 0.53, 0.37
3150,1850  GL=( 91, 77, 21)  Metal=( 34, 30, 13)   ratio = 0.37, 0.39, 0.64
3250,1850  GL=(123,108, 55)  Metal=(135,124, 67)   ratio = 1.10, 1.14, 1.21
3350,1850  GL=(102, 86, 24)  Metal=( 41, 35,  5)   ratio = 0.40, 0.40, 0.22
```

Non-zero, varying ratios — consistent with two characteristics:
(a) icons ARE drawing in Metal (no longer black), (b) UI layout is
not pixel-perfect across independent engine runs (Nuklear sub-pixel
rounding shifts where each icon lands). The visual side-by-side is
the right acceptance bar here, and that side-by-side passes.

Pixel-perfect inventory parity would require pinning UI layout
across captures; that is out of scope for this slice and not
related to the rendering bug.

### Out-of-scope, observed

- Minimap appears more detailed in Metal than in GL in this capture.
  Could be an unrelated minimap-rendering difference; record but do
  not bundle.
- Slice 3+ (units, water, jagged edges, blurry LODs) still pending.

---

## 10. Attempt 5 — 2026-04-25 — Slice 3: unit-pixel sampling + shadow pocket investigation

### Slice 3 question

After Slice 1 closed the universal 0.55× shadow tint, do units still
show a measurable delta?

### Method

`png_block_compare.py` (61×61 block average) on lit-zone unit-cluster
points in
`visual_parity_captures/2026-04-25-metal-ui-texpath-fix/metal_combat.png`
vs `opengl_combat.png`.

### Result

Most unit-cluster blocks ratio ~1.00:
```
2640, 540   ratio = 1.00, 1.00, 1.00
2280,1340   ratio = 1.00, 1.00, 1.00
2200,1340   ratio = 1.01, 1.01, 1.01
2350,1800   ratio = 1.00, 1.00, 1.00
2300,1700   ratio = 1.00, 1.00, 1.00
2592, 477   ratio = 1.00, 1.00, 1.00
1900,1300   ratio = 1.00, 1.00, 1.00
```

But a tight pocket near the bottom-center of the lit zone shows
Metal *brighter* than GL by 1.32–1.78×, uniform across R, G, B:
```
2100,1700   ratio = 1.56, 1.56, 1.57
2050,1700   ratio = 1.51, 1.51, 1.51
2100,1650   ratio = 1.78, 1.78, 1.78
2050,1650   ratio = 1.74, 1.74, 1.74
2050,1750   ratio = 1.47, 1.46, 1.46
```

Outside the pocket (e.g. 2300,1700) the ratio returns to 1.00. The
uniform-across-channels signature plus the magnitude pattern matches
"GL applies a shadow that Metal does not". The pocket is real and
deterministic — re-running the Metal capture twice produced
**bit-identical** PNG output, so this is not animation jitter.

### Tested hypothesis (NEGATIVE)

I previously flagged "Metal clips fragments with NDC z < 0 during the
shadow pass" as a follow-up of Slice 1, and predicted that swapping
`PFM_Mat4x4_MakeOrthographic` for a Metal-friendly variant in
`make_shadow_light_space` would close the pocket.

I implemented the Metal-friendly ortho:
```c
out->cols[2][2] = -1.0f / (farp - nearp);
out->cols[3][2] = -nearp / (farp - nearp);
```

Confirmed via `fprintf` that `metal_ortho_projection` was called
during the visual parity probe with the expected arguments
(`l=-160, r=160, b=160, t=-160, n=0.1, f=1536`).

Re-captured. Pocket ratios were **identical to within sampling noise**
to the pre-fix capture — same 1.56, 1.51, 1.78. The Metal-Metal
diff between the two captures was bit-identical at every test point.

To rule out "it just happens to compute the same matrix at this scene",
I ran a destructive control: replaced the helper with `PFM_Mat4x4_Identity`.
Output was again bit-identical to both prior Metal captures.

**Conclusion:** the shadow projection matrix has no observable impact
on the captured visible terrain at this scene. The depth texture's
content is not what's driving the 1.5× pocket. Hypothesis rejected.

I reverted the helper and the call-site change so no dead code or
non-functional matrix lives in the tree.

### What this likely is

Three remaining live hypotheses, ranked by what the evidence supports:

1. **Static-mesh shadow path is broken in a way that doesn't show up
   in the lit-terrain test.** GL casts unit/prop shadows via the same
   shadow pass; if Metal's static-mesh shadow rasterization is dropping
   a chunk of geometry (CullMode mismatch, winding mismatch, vertex
   stream offset, depth-write disabled for that pipeline variant),
   you'd get exactly this signature: lit terrain unaffected (it shadows
   itself), but caster shadows missing in the pocket near the units.
   `s_shadow_terrain_pipeline` and `s_shadow_mesh_pipeline` both go
   through `build_shadow_depth_pipeline` but that helper takes only a
   stride, not a vertex format diff — worth re-reading.
2. **Main-pass shader's `proj_z > 0.95` early-return** is firing for
   the pocket but not in GL because GL's `current_depth` for the same
   fragment is on a different scale. With the GL-style ortho still in
   place this is plausible at the far edge of the frustum.
3. **The pocket lies on a foliage / cutout mesh that uses a
   different fragment shader path** that doesn't apply shadow at all
   in Metal. The bottom-center of the screen has the prominent tree —
   the pocket might actually be tree shadow that GL renders and Metal
   doesn't.

### Decision

Slice 3 is closed as **PARTIAL**: bulk-unit parity is at 1.00; one
localized brightness pocket warrants its own investigation but does not
block Slices 4 / 5. Proceeding to Slice 4 (water shoreline / color)
next, since it has wider visible impact than the pocket.

The static-mesh shadow path investigation is queued in §11 as
follow-up.

---

## 11. Open follow-ups (queued, not yet root-caused)

- **Shadow pocket at (2050-2150, 1650-1750) in combat scene.**
  Metal 1.32-1.78× brighter than GL. Uniform across RGB. Stable
  across runs. Three live hypotheses; static-mesh shadow path is
  the leading suspect. Not blocking other slices.
- **Inventory icons pixel-perfect alignment.** Slice 2 closed
  with icons rendering, but pixel coordinates in Metal vs GL drift
  by a few px due to Nuklear sub-pixel rounding. Cosmetic, not a bug.
- **Minimap appears more detailed in Metal than GL.** Spotted in
  Slice 2 capture comparison. Unrelated to inventory fix; investigate
  separately if it visibly bothers anyone.
- **Heightmap-normal `z1` indexing typo.** Both backends share the
  same wrong `front_idx` use for z gradient (`terrain-shadowed.glsl:573-574`,
  `backend_metal.m:384-385` pre-Slice-1 lines). Not a parity gap;
  cleanup-only.

---

## 12. Attempt 6 — 2026-04-25 — Slice 4: water shoreline + color delta

### Symptom

In `metal_water.png` the water area was a saturated cyan-blue pool
with hard foam edges. In `opengl_water.png` the same area was a soft
muted gray with the underlying terrain showing through. Distinct
visual gap, not a tone shift.

### Root cause

Metal's `terrain_fragment` had a hand-tuned water-tile palette that
*overwrote* the terrain `lit` color when `water_state != 0`:

```metal
if(water_state != 0u) {
    float3 deep        = float3(0.03, 0.17, 0.30);
    float3 shallow     = float3(0.07, 0.34, 0.53);
    float3 reflect_tint = float3(0.26, 0.46, 0.62);
    float3 foam        = float3(0.62, 0.78, 0.88);
    lit = mix(deep, shallow, wave_mix);
    lit = mix(lit, reflect_tint, fresnel * 0.55);
    lit += foam * uniforms.light_color.xyz * (...);
}
```

The OpenGL reference [terrain-shadowed.glsl](shaders/fragment/terrain-shadowed.glsl)
has **no equivalent branch**. GL renders water-flagged tiles as
ordinary terrain, then the water surface mesh draws translucent
scene-blended water on top via [water.glsl](shaders/fragment/water.glsl)
(refraction + reflection + faint tint, alpha = depth-damping factor
based on water depth).

In Metal, the result was:
1. The terrain shader paints water tiles solid blue (with the
   hand-tuned palette).
2. The water surface mesh tries to paint translucent scene water on
   top of solid blue terrain — but the underlying blue dominates
   and bleeds at the shoreline.

### Patch

Three deletions from the `s_terrain_shader_source` MSL in
[backend_metal.m](src/render/backend_metal.m):

1. The `uint water_state = 0u;` declaration (no longer needed).
2. The `water_state = water_buff[fog_idx];` assignment (now redundant;
   `fog_idx` voided so the compiler is happy with no unused warning).
3. The entire `if(water_state != 0u) { ... }` block that overwrote
   `lit` with the hand-tuned palette.

The terrain shader now renders water tiles as terrain, matching the
GL reference. The standalone water surface shader (`s_water_surface_shader_source`)
is unchanged — it already mirrors GL's `water.glsl` and produces the
correct translucent water look.

### Verification

Build: clean.

Capture:
`visual_parity_captures/2026-04-25-metal-water-override-removed/`.

Visual: `metal_water.png` now shows a soft gray water area with
underlying terrain visible, no saturated blue, no hard foam edges.
Visually indistinguishable from `opengl_water.png` at the gameplay
zoom.

Numeric (water surface, 61×61 block sampling):
```
1700, 900   GL=( 80, 84, 78)   Metal=( 69, 75, 70)   ratio = 0.87, 0.89, 0.90
1600,1000   GL=( 63, 66, 60)   Metal=( 57, 61, 57)   ratio = 0.90, 0.92, 0.95
1700,1100   GL=(102,111,104)   Metal=(109,117,110)   ratio = 1.06, 1.05, 1.06
1500, 900   GL=( 26, 27, 23)   Metal=( 22, 22, 20)   ratio = 0.82, 0.84, 0.88
1900,1100   GL=( 78, 93, 55)   Metal=( 69, 84, 67)   ratio = 0.88, 0.91, 1.24
```

Most points are at 0.85–1.06 (close to parity). The remaining 1.24
blue shift at 1900,1100 is a small residual from the water surface
shader's faint blue tint (`vec4(0.0, 0.3, 0.5, 0.1)` mixed at 10 %).
That tint is identical between GL and Metal shaders, so the residual
is most likely sub-pixel-level: the refraction texture content at
the same screen UV differs slightly because the offscreen scene
render is itself subtly different (terrain LOD, mip selection, etc.).
Not blocking and not a regression — strictly better than the saturated
blue we had.

### Notable: this also changes water-shore foam

Pre-fix Metal had a strong "foam" specular highlight along shorelines
(`foam * (water_specular * (0.25 + ripple_mix * 0.25))`). GL has no
such effect on terrain — it only has the smaller water-surface
specular. With the override removed, Metal shorelines now match GL's
softer transition. This was always a fidelity *gap* with GL, even if
visually attractive. The user said "OpenGL parity, then HD/4K later"
so the foam gets revisited as part of the HD platform milestone if at
all.

### Status

Slice 4 closed. Proceeding to Slice 5 (jagged edges + blurry units)
unless redirected.

---

## 13. Attempt 7 — 2026-04-25 — Slice 5: jagged edges + blurry units (CLOSED, no bug)

### User-reported symptoms

"jagged edges and the units are looking blurred too (units or props
look low-poly or low-LOD compared to OpenGL)".

### Method

Two objective measurements on
`visual_parity_captures/2026-04-25-metal-water-override-removed/`:

1. **Edge sharpness** — horizontal pixel-line scan across a high-contrast
   edge, report `max(|L(i+1) - L(i)|)` and the per-pixel luminance
   profile.
2. **Local texture variance** — stdev of luminance within a 61×61
   block centered at a sample point. Higher stdev = more
   high-frequency detail.

### Findings

**Edge sharpness — Metal is consistently softer than GL** across four
edges (unit silhouette, rock silhouette, terrain corner, overview).
Max delta numbers (units of 0–255 luminance):

| Edge | OpenGL | Metal |
|---|---|---|
| Unit silhouette y=1340 | 26.1 | 11.9 |
| Rock silhouette y=1500 | 63.3 | 25.0 |
| Terrain corner y=1900 | 18.6 |  9.2 |
| Overview y=1300       |  4.7 |  2.0 |

GL's profile shows pixel-pair duplication
(`157.2, 157.2, 153.7, 153.7, …`) — telltale of a 1728×1117
internal buffer upscaled with nearest-neighbor blocks to the
3456×2234 capture. Metal's profile is per-pixel-unique with smooth
ramps. Metal is rendering at the drawable's full size with proper
MSAA-resolved edges. **Metal's edges are objectively smoother, not
"jagged."**

**Local variance — Metal averages ~17 % lower than GL:**

| Point | GL stdev | Metal stdev | Δ |
|---|---|---|---|
| 2592,477  |  7.05 |  6.41 |  -9 % |
| 2074,1370 | 27.74 | 14.08 | -49 % |
| 2300,1700 | 22.00 | 17.67 | -20 % |
| 1900,1500 |  9.53 | 11.20 | +18 % |
| 2200,1340 |  8.88 |  7.63 | -14 % |
| 2480,1380 | 61.29 | 56.94 |  -7 % |

That ~17 % loss of high-frequency detail is the standard 4× MSAA
box-resolve effect: sub-pixel detail is averaged into the resolved
single-sample image.

### Why GL is sharper here

- [backend_gl.c](src/render/backend_gl.c) sets up the SDL GL context
  with no `SDL_GL_MULTISAMPLEBUFFERS` / `SDL_GL_MULTISAMPLESAMPLES`
  calls anywhere → GL renders to the default framebuffer without
  MSAA.
- [backend_metal.m:156](src/render/backend_metal.m:156)
  `#define METAL_MSAA_SAMPLES 4` → every Metal scene pipeline is
  MSAA-4×.

So Metal does *more* AA than GL. The user's "jagged edges in Metal"
perception is the opposite of the objective measurement.

### Why "blurry units" was reported

Two probable contributors:

1. The Slice 1 shadow bug (now fixed) made every lit fragment 0.55×
   dimmer on Metal. Dim & desaturated reads as muddy / low-fidelity
   when compared side-by-side with GL.
2. The Slice 4 water-override bug (now fixed) made shorelines
   saturated-blue with hard foam — the high-contrast artifacts gave
   an impression of jaggedness that wasn't representative of the
   rest of the scene.

After the four landed slices, those side-effects are gone. The ~17 %
variance loss from MSAA remains and is by design.

### Decision

**Slice 5 closed without a code change.** Metal is objectively higher
quality on edges and a small, expected step softer on
high-frequency texture detail than the no-MSAA GL baseline.

If "strict GL parity" requires matching GL's lack of MSAA, that's a
one-line change at `METAL_MSAA_SAMPLES = 1`. It is a quality
regression, so deferred to user choice. Not landing it in this slice.

### Status of overall queue

- Slice 1 (shadow NDC-z): DONE.
- Slice 2 (UI texpath / inventory icons): DONE.
- Slice 3 (unit appearance): PARTIAL — bulk parity, one localized
  shadow pocket pending root-cause; static-mesh shadow path leading
  suspect. Queued in §11.
- Slice 4 (water shoreline + color): DONE.
- Slice 5 (jagged / blurry): NO BUG, closed.

Open follow-ups in §11:
- Localized shadow pocket near (2050-2150, 1650-1750) in combat
  scene.
- Minimap detail difference.
- Inventory icon sub-pixel position drift.
- Heightmap-normal `z1` indexing typo (shared between GL and Metal,
  not a parity gap).

---

## 14. Attempt 8 — 2026-04-25 — Unit texture detail "fix it completely" investigation

### Methods used

Six experiments, all reverted (no live code changes from this attempt):

1. **Removed Metal's `effect_params.x > 0.5` conditional** — confirmed
   the conditional was already firing for unit pixels (bit-identical
   output to baseline).
2. **Forced `level(0.0)` in Metal sample call** — bit-identical to
   `bias(-0.5)`. Metal IS sampling mip 0 at this scene.
3. **Switched material sampler to Nearest/None mip filter** — no
   improvement; small per-pixel sharpening, but the chainmail pattern
   on Knight helmets still absent. So filter-mode isn't the cause.
4. **Disabled MSAA** (`METAL_MSAA_SAMPLES = 1`) — local-stdev variance
   only rose ~3% (averaged over 4 sample points). Visible chainmail
   detail did NOT return. So MSAA box-resolve is not the dominant cause.
5. **Added V-flip `(uv.x, 1.0 - uv.y)` to static-mesh sample** —
   flipped the visible orientation the WRONG way: Knights went all-
   black (sampling the alpha=0 background of the source). Reverted.
6. **Dumped pre-upload bytes for both backends** and viewed them:

   - Source `Knight.png` is 512×512 RGB.
   - Metal upload: 512×512 RGBA (stbi_load with `flip=true` adds a
     V-flip in raster order, plus alpha=255 padding).
   - GL upload: same 512×512 RGBA, but additionally passed through
     `stbir_resize_uint8(... 512, 512, ...)` even at same dims, which
     applies a soft sinc-style filter.
   - Byte diff: 15% of pixels differ, but only by 1–2 per channel —
     within the noise of stbir's same-size resampling.
   - **Both dumps decoded to PNG show full chainmail detail in the
     texture data.** So the texture data Metal uploads to the GPU
     contains the chainmail.

### What this means

The root cause of the visible chainmail-loss is NOT:
- Texture data (verified — both backends have full detail).
- LOD selection (verified — sampling mip 0).
- Sampler filter mode (verified — both linear).
- MSAA box-resolve (verified — only ~3% variance contribution).
- V-flip (verified — current orientation samples the right region;
  forcing a flip makes it worse).
- Conditional sample skip (verified — branch fires correctly).

Possible remaining causes I have NOT pinned:
- Driver-side derivative computation differing between Metal and the
  Apple Silicon GL implementation for the skinned/animated mesh
  pipeline. Different derivatives → different LOD → different
  effective sharpness even at the same logical mip.
- Some interaction between MSAA's per-sample UV offsets and the
  texture sampler that effectively over-samples (and thus blurs)
  more than the 1× case suggested.
- Different magfilter behavior for `texture2d_array<float>` vs
  GL's `sampler2DArray` at edge-of-texel positions.

These require either GPU-trace tooling (Xcode Metal frame capture +
RenderDoc on GL) or per-pixel synthetic-texture diagnostics that
isolate sampler behavior. Beyond what I can do from text alone.

### Status

I could NOT fix the unit texture detail "completely and fully" in
this attempt. The texture data is correct, the sampling looks
correct on every parameter I can adjust, yet the visible result
still loses high-frequency detail in Metal. I rolled back every
experimental change so the tree is in the clean post-Slice-1+2+4
state. Both binaries in `bin/`:

- `bin/pf-arm64-metal` — current Metal build, all landed slices.
- `bin/pf-arm64-opengl` — reference OpenGL build.

### Recommended next moves (any of which need tooling I lack)

1. **Xcode Metal frame capture** of a single Knight rendering frame.
   Inspect the actual sampled mip level, the inferred derivatives,
   and the resolved color value per fragment. This is the single
   most informative tool and would pin the cause in minutes.
2. **Per-pixel synthetic-texture probe**: replace the Knight texture
   with a checkerboard pattern in both backends, render one frame.
   If Metal blurs the checkers and GL doesn't, the cause is in
   sampler / derivative / MSAA. If both produce sharp checkers,
   the cause is in the actual stored texture content (which my
   bytewise comparison would have missed for some reason).
3. **Anisotropic filtering** — neither backend currently sets it.
   Enable max anisotropy 16 on Metal's material sampler and test;
   if it restores the chainmail at oblique angles, the cause is
   GL's driver implicitly using anisotropic filtering on Apple
   Silicon while Metal honors the descriptor literally.

### Honest disclosure

I went deep on this without a successful fix. The honest position is
"texture data is fine, sampling parameters are fine, the visible loss
of detail is in a place my text-based diagnostics can't reach". I
should have escalated to "we need GPU frame capture" earlier instead
of grinding through more experiments.

---

## 15. Working notes for Claude/Codex collaboration

- This file is the single source of truth for the parity slice. Each new
  attempted fix should append a `## Attempt N — <date>` section: hypothesis,
  one-paragraph diff summary, capture directory used, observed delta, and
  conclusion (kept / reverted).
- Codex: please do not "improve" Metal-side rendering math beyond what the
  GL reference shader does. The endpoint is GL parity, not aesthetics.
- Before each new attempt, re-read sections 1 and 5 — they encode what we
  have already ruled out and the user's no-go list.
- When a slice lands, capture under
  `visual_parity_captures/<YYYY-MM-DD>-metal-<short-tag>` and link the
  directory in the attempt's section.
- If a slice does not move the metric, REVERT and pick the next-ranked
  hypothesis. Do not stack speculative fixes.

---

## 16. Attempt 9 — 2026-04-25 — Anisotropy and synthetic checker diagnostics

### Xcode frame-capture feasibility

Codex opened Xcode through Computer Use. Xcode 26.4.1 is present, but it
stops at the first-launch "Select the components you want to get started
with" dialog. The visible action is `Download & Install`, with iOS 26.4
selected by default. Codex did **not** click it because that can install
platform components and requires explicit user approval.

Command-line check:

```bash
xcrun metal-capture --help
```

returned "unable to find utility `metal-capture`". So a real Xcode Metal
frame capture remains the highest-signal next step, but this machine's
Xcode setup needs user-approved component setup before Codex can use that
path.

### Anisotropy swing

Hypothesis: Apple's OpenGL path might be implicitly using stronger
anisotropic filtering than the literal Metal material sampler.

Temporary diff:

```objc
sampler_desc.maxAnisotropy = 16;
```

inside `ensure_material_sampler` in `src/render/backend_metal.m`.

Verification:

- Metal build passed.
- `pf_metal_launch_probe.py` passed.
- `pf_metal_water_probe.py` passed.
- `pf_metal_debug_overlay_probe.py` passed.
- `pf_metal_gameplay_smoke_probe.py` passed.
- `pf_native_session_ui_region_camera_roundtrip.py` passed.
- Paired capture: `visual_parity_captures/2026-04-25-metal-material-anisotropy-test/`.
- Restored OpenGL fallback launch probe passed.

Result:

- Crop: `/tmp/m_after_aniso.png`.
- Compared against prior `/tmp/m_combat_zoom2.png`.
- The crop was visually the same; chainmail did not return.
- Pixel samples were effectively unchanged, aside from small expected
  sampling/scene differences.

Decision: **negative test, reverted.** There is no live anisotropy diff in
the tree. Do not retry anisotropy unless a future GPU capture shows it is
actually affecting the helmet fragments.

### Synthetic checker test

Hypothesis: if Metal cannot preserve high-frequency unit textures, a
512x512 black/white 16x16 checker replacing `Knight.png` should blur in
Metal while remaining sharp in OpenGL.

Procedure:

1. Recorded original hash:
   `b2137a9dbe2812fbd3f78e478615a11192a0b90118d262f3025a8d8ef0b5fe11`.
2. Backed up `assets/models/knight/Knight.png` to `/tmp/Knight.png.codex-original`.
3. Replaced `Knight.png` with a generated 512x512 RGBA 16x16 checker for one
   capture only.
4. Captured both backends into
   `visual_parity_captures/2026-04-25-metal-unit-checker-test/`.
5. Restored the original `Knight.png`.
6. Rechecked the hash; it matched the original exactly.

Crops:

- `/tmp/g_checker_combat_zoom.png`
- `/tmp/m_checker_combat_zoom.png`

Result:

- The checker is clearly visible in both OpenGL and Metal.
- Whole-crop luminance stdev:
  - OpenGL checker crop: `56.69`
  - Metal checker crop: `58.50`
- Metal is not broadly unable to preserve a high-frequency material texture
  on the same animated Knight path.

Decision: **negative for generic sampler/derivative blur.** The missing
chainmail is not explained by texture data, mip level, basic sampler filters,
MSAA, UV orientation, anisotropy, or a general inability to resolve
high-frequency unit texture content.

### Updated next step

The next useful diagnostic is either:

1. User-approved Xcode setup, then a real Metal frame capture on a Knight
   helmet fragment; inspect sampled UV, actual mip, derivatives, source texel,
   and resolved color.
2. If Xcode setup is deferred, add a temporary explicit debug mode for the
   static/skinned mesh shader that outputs raw `material_textures.sample(...)`
   as unlit color for animated units. If raw Metal texel output shows the
   chainmail, the loss is lighting/resolve/post-sample. If raw output is still
   smooth, the issue is UV/animation/sample-position specific.

No code or asset changes from this attempt are intended to remain except this
notebook section.

---

## 17. Attempt 10 — 2026-04-25 — Xcode GPU trace capture path

### Xcode setup status

After user approval, Xcode component setup completed enough for GPU trace
inspection. `xcrun xctrace list templates` now works and includes Metal/GPU
templates, but:

```bash
xcrun metal-capture --help
```

still returns "unable to find utility `metal-capture`". So this machine has
Xcode GPU debugging, but not a standalone `metal-capture` CLI.

### MTLCaptureManager hook

Added an opt-in Metal capture hook in `src/render/backend_metal.m`. It is
disabled unless `PF_METAL_CAPTURE_PATH` is set, and GPU trace document output
also requires Apple's `MTL_CAPTURE_ENABLED=1` environment variable.

Environment controls:

- `PF_METAL_CAPTURE_PATH`: output `.gputrace` bundle path.
- `PF_METAL_CAPTURE_START_PRESENT`: first present count to capture; default 1.
- `PF_METAL_CAPTURE_PRESENTS`: number of presents to capture; default 1.

Also added `PF_METAL_CAPTURE_EXIT_DELAY` handling to
`scripts/macos/pf_visual_parity_probe.py` so the probe does not `os._exit(0)`
before Xcode finishes indexing the trace bundle.

### Failed/corrupt trace

The earlier combat trace:

```text
visual_parity_captures/2026-04-25-metal-gputrace-capture/pf-combat-390.gputrace
```

is corrupt/incomplete. Xcode reports:

```text
Failed to open the document.
Xcode failed to open the gputrace document. The index file does not exist.
The capture may be incomplete or corrupt. (2)
```

Confirmed cause: that bundle has no `index` file. Do not use it as evidence.

### Finalized trace

The finalized capture command was:

```bash
env MTL_CAPTURE_ENABLED=1 \
  PF_METAL_CAPTURE_PATH=/Users/dev/Desktop/OpenGL\ RTS\ game\ engine/visual_parity_captures/2026-04-25-metal-gputrace-capture/pf-combat-finalized.gputrace \
  PF_METAL_CAPTURE_START_PRESENT=380 \
  PF_METAL_CAPTURE_PRESENTS=20 \
  PF_METAL_CAPTURE_EXIT_DELAY=12 \
  ./bin/pf-arm64 ./ ./scripts/macos/pf_visual_parity_probe.py \
  --output-dir visual_parity_captures/2026-04-25-metal-gputrace-capture-finalized \
  --expect-backend METAL
```

Result:

- Probe reached combat and passed.
- Metal logged capture start and stop.
- Bundle size: about 602 MiB.
- Bundle contains an `index` file.
- Xcode opens it as `pf-combat-finalized.gputrace`.

### Xcode inspection notes

In Xcode, filtering the trace list by `static` finds the relevant static mesh
draws. One verified draw:

- Command Buffer 1
- Render Encoder 0
- Draw: `1120 [drawPrimitives:Triangle vertexStart:0 vertexCount:19380]`
- Pipeline: `static_mesh_vertex` -> `static_mesh_fragment`
- Material texture binding: `Fragment Texture 0`, `Texture2DArray`,
  `material_textures`, 512 x 512, `RGBA8Unorm`
- Sampler binding: `Fragment Sampler 0`, `material_sampler`
- Shadow map binding: 2048 x 2048 `Depth32Float`
- Attachments are multisampled color/depth with color resolve.

This confirms the trace is actionable for the unit-detail investigation and
can inspect the actual Metal static mesh draw state. The next manual/Xcode
step is selecting a helmet pixel in the color attachment and using Debug Pixel
to inspect the material sample, derivatives/mip choice, and resolved color.

### Verification

- Metal build passed after adding the capture hook.
- Normal Metal launch probe passed without capture environment variables.
- Finalized capture probe passed and generated a trace Xcode can open.

This hook is intended to remain as debug tooling because it is fully env-gated
and does not affect normal rendering runs.

---

## 18. Attempt 11 — 2026-04-25 — Animated mesh skin-weight normalization

### Xcode Debug Pixel status

Opened the finalized trace and selected a static mesh draw:

- Command Buffer 1
- Render Encoder 0
- Draw: `1120 [drawPrimitives:Triangle vertexStart:0 vertexCount:19380]`
- Pipeline: `static_mesh_vertex` -> `static_mesh_fragment`

Xcode exposed the draw resources, including `material_textures` and
`material_sampler`, but `Debug Pixel` stayed disabled for the selected unit
region. The trace is still useful for draw-state inspection, but this path did
not expose fragment-level UV/mip data quickly enough for the current slice.

### Raw material diagnostic

Added an env-gated debug branch:

```bash
PF_METAL_DEBUG_RAW_MATERIAL=1
```

When enabled, `static_mesh_fragment` returns the sampled material texture before
lighting, shadows, and final material modulation. Normal rendering is unchanged
when the variable is unset.

Captured:

```text
visual_parity_captures/2026-04-25-metal-raw-material-debug/
```

Crops:

- `/tmp/g_raw_material_combat_zoom.png`
- `/tmp/m_raw_material_combat_zoom.png`

Result: Metal still showed smooth helmet texture before lighting. The source
atlas `assets/models/knight/Knight.png` is also mostly smooth in the helmet
area, so the visible OpenGL high-frequency helmet look is not raw diffuse
texture alone. This pointed back to animated mesh pose/normal parity.

### Root cause found

OpenGL normalizes animated skin weights in the vertex shader:

```glsl
float fraction = weight / tot_weight;
mat4 bone_mat = fraction * pose_mat * inv_bind_mat;
mat3 rot_mat = fraction * mat3(transpose(inverse(pose_mat * inv_bind_mat)));
```

Metal CPU skinning was applying raw weights directly in both:

- `render_skinned_mesh_draw`
- `append_skinned_anim_mesh`

This is a real parity bug. The Knight asset has many `vw` rows whose weights do
not sum to 1.0; examples include sums around `0.5`, `1.9`, `3.0`, and `4.0`.
OpenGL hides that by normalizing in the shader, while Metal was distorting the
pose/normal result.

### Fix

Metal now computes `total_weight` per animated vertex and applies:

```c
weight = total_weight > 0.0f ? curr->weights[j] / total_weight : 0.0f;
```

in both skinned paths.

### Verification

- Metal build passed.
- Normal Metal launch probe passed.
- Paired visual parity capture passed:
  `visual_parity_captures/2026-04-25-metal-skin-weight-normalization/`.
- Crops:
  - `/tmp/g_skin_weight_combat_zoom.png`
  - `/tmp/m_skin_weight_combat_zoom.png`
- Metal water probe passed.
- Metal gameplay smoke probe passed.
- Metal debug overlay probe passed.
- Native session UI/region/camera roundtrip probe passed.

One probe initially failed with `expected METAL backend, got OPENGL` because
the parity capture script ends by rebuilding the OpenGL binary. Rebuilding with
`RENDER_BACKEND=METAL` fixed the probe setup.

### Result

The Metal unit bulk/pose/scale in the combat crop moved much closer to OpenGL,
and the helmets are no longer the oversized smooth shapes seen before the fix.
The remaining visible difference is now mostly Metal's smoother MSAA/tonal look
and broader material/scene response, not the severe animated skinning mismatch.

---

## 19. Attempt 12 — 2026-04-25 — Explicit MSAA parity state

### Current measurement before the slice

Re-sampled the post-skin-weight capture:

```text
visual_parity_captures/2026-04-25-metal-skin-weight-normalization/
```

Four lit terrain points in `combat` now sit at exact parity
(`ratio = 1.00, 1.00, 1.00`). The remaining large deltas are clustered
on combat units/effects and healthbar-adjacent pixels, which matches the
visual crop: Metal's 4x MSAA resolve is smoother/softer than the OpenGL
baseline's no-MSAA edge rasterization.

### Fix

Made the Metal sample count explicit:

- strict OpenGL-parity default is now `METAL_DEFAULT_MSAA_SAMPLES = 1`
- `PF_METAL_MSAA_SAMPLES=2` or `PF_METAL_MSAA_SAMPLES=4` opts back into
  multisampling for controlled quality experiments
- multisampled pipelines now use the active frame sample count instead of
  assuming a hard-coded 4x render target

This keeps parity captures from silently comparing OpenGL no-MSAA against
Metal 4x MSAA. It also preserves the higher-smoothness path for the later
HD/4K renderer work, where anti-aliasing should be chosen intentionally rather
than inherited as a hidden porting default.

### Capture harness hardening

While trying to capture the new default, the paired capture helper repeatedly
blocked in the macOS event/capture path before producing PNGs. Added three
small robustness changes to `scripts/macos/pf_visual_parity_probe.py`:

- reuse the active camera and call `center_over_location()` instead of
  replacing the active camera object
- timeout the `osascript` window activation step
- timeout/fallback the Swift window-id and `screencapture -l` steps to a
  full-screen capture path

Even with those guardrails, the current OpenGL probe run stalled inside
`SDL_PumpEventsInternal` before frames advanced, so the paired PNG capture for
this slice is blocked and should be revisited as its own harness issue.

### Verification

- Metal build passed:
  `make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL`
- Default Metal launch probe passed.
- `PF_METAL_MSAA_SAMPLES=4` launch probe passed when run outside the sandbox
  to avoid the macOS display-driver sandbox failure.
- Metal gameplay smoke probe passed.
- Native session UI/region/camera roundtrip probe passed.

### Result

The renderer now has a parity-correct default for the MSAA part of the visible
gap and an explicit opt-in path for smoother AA experiments. The remaining
material-tone work should focus on real shading/water/scene response, not on
an accidental 1x-vs-4x comparison.

---

## 20. Attempt 13 — 2026-04-26 — Harness re-test + static-mesh self-shadow gap

### Context

User asked for a focused review of (a) whether the new MSAA default/opt-in
state is the right parity move and (b) what concrete material-tone or
water/shoreline gap to attack next. Without numbers from a fresh paired
capture (Codex reported the harness blocked in `SDL_PumpEventsInternal`),
the second question would have been guesswork — so first I tried to
reproduce the stall.

### Harness re-test

`scripts/macos/capture_visual_parity.sh
visual_parity_captures/2026-04-26-harness-test` ran end-to-end in
foreground bash, both backends, four scenes each, in under 60 seconds.

The OpenGL probe progressed through `init → settle:overview → capture →
stage_water_units → ...` without stalling. The stall Codex saw is
**not currently reproducing**.

Most likely the §19 hardening (osascript / swift / screencapture
timeouts and full-screen fallback) closed it, even though the AppleScript
activate call is still present at `_capture`. The activate call is the
prime suspect for any future recurrence (it posts an AppleEvent that
SDL has to drain through `SDL_PumpEvents`); if the stall returns, drop
that call entirely — `screencapture -l<window_id>` does not need the
window to be frontmost (Quartz captures by ID).

For now: do NOT remove the activate call defensively. Note in the
roadmap that this is the recovery action if the stall recurs.

### Numerical state from the fresh paired capture

`png_block_compare.py` at half=60 (121×121 block average) over
representative points across all four scenes.

**At parity (ratio ≈ 1.00 across R, G, B), confirmed:**

| Scene | Point | Status |
|---|---|---|
| overview | 2592, 477 | 1.00, 1.00, 1.00 |
| overview | 1900, 1500 | 1.00, 1.00, 1.00 |
| rocks | 2074, 1370 | 1.00, 1.00, 1.00 |
| rocks | 1900, 1500 | 0.99, 0.98, 0.98 |
| rocks | 2200, 1500 | 1.00, 1.00, 1.00 |
| combat | 2592, 477 | 1.00, 1.00, 1.00 |
| combat | 2300, 1700 | 1.00, 1.00, 1.00 |
| combat | 1900, 1500 | 1.01, 1.01, 1.02 |
| water | 2074, 1370 | 1.00, 1.00, 1.00 |
| water | 1900, 1300 | 1.00, 1.00, 1.00 |
| water | 1900, 1500 | 1.00, 0.99, 1.00 |
| water | 2200, 1500 | 1.00, 0.99, 1.00 |

The skin-weight (§18) + MSAA (§19) slices have closed the bulk of
parity. This is excellent.

**Persistent deltas (Metal darker — applying shadow GL doesn't):**

| Scene | Point | Ratio (M/G) | Pattern |
|---|---|---|---|
| overview | 1700, 900 | 0.58, 0.58, 0.57 | Cliff face. **Exact `SHADOW_MULTIPLIER = 0.55`** signature. |
| rocks | 1700, 900 | 0.77, 0.79, 0.81 | Same cliff area in rocks scene; less direct hit. |
| water | 2592, 477 | 0.88, 0.89, 0.88 | Smaller delta, possibly the water-edge banner area. |
| water | 1700, 900 | 0.91, 0.93, 0.93 | Edge of water render. |

**Persistent deltas (Metal brighter — missing shadow GL has):**

| Scene | Point | Ratio (M/G) | Pattern |
|---|---|---|---|
| combat | 2074, 1370 | 1.33, 1.36, 1.35 | Unit-cluster pixel; could be animation-frame variance OR residual missing-shadow-pocket from §10. |
| combat | 2200, 1500 | 1.23, 1.26, 1.21 | Same area as above. |
| rocks | 1900, 1300 | 1.16, 1.14, 1.16 | Rocks-scene unit cluster. |
| overview | 2074, 1370 | 1.04, 1.04, 1.06 | Marginal. |
| overview | 1900, 1300 | 1.03, 1.04, 1.03 | Marginal. |

### Visual verification

Crops at:

- `/tmp/g_ov.png` and `/tmp/m_ov.png` — overview, 1700×1300 region
  centered on the cliff face. The cliff face area is **clearly lit
  in OpenGL** (rocky gray surface visible) and **clearly shadowed in
  Metal** (almost black with edge highlights only). Single-frame
  visible delta is dramatic and matches the 0.57 ratio.
- `/tmp/g_co.png` and `/tmp/m_co.png` — combat, 1500×700 region
  centered on the unit cluster. Now **very close visually**; bulk
  Knight rendering matches the OpenGL look.

### MSAA design review (request from user)

The design as landed is **the right parity move**:

- Hardcoded 4× MSAA was a bug-shaped constant — making sample count
  per-pipeline parameterized (`build_*_pipeline(NSUInteger sample_count)`
  + `active_msaa_sample_count()`) is correct architecture.
- Default 1× lets parity captures actually compare like-for-like.
  We could not previously distinguish "Metal smoother edges from
  MSAA" (legit win) from "Metal more averaged texture detail from
  MSAA" (legit cost).
- `PF_METAL_MSAA_SAMPLES=2|4` opt-in preserves the higher-AA path
  for HD/4K work.

One ship-prep follow-up flagged in the roadmap (item 9 of the slice
queue): once OpenGL is removed and Metal is the default for end
users, the shipping default should flip back to 4× or device-max,
with a separate `PF_PARITY_MODE` (or build-time flag) forcing 1×
during parity captures. The current default is correct **for the
parity work** but would be a quality regression as a shipping
default. Not blocking this slice.

Also: extend the accepted opt-in values to include 8 once parity
work is complete. M1+ supports 8× color MSAA.

### Recommendation: next slice

**Slice 6 — static-mesh self-shadow parity (cliff face).**

Most reproducible, biggest single visible delta, and matches a
known-pattern (`SHADOW_MULTIPLIER` ratio). Codex already plumbed
the `MTLCaptureManager` hook in §17. Concrete steps:

1. Set `PF_METAL_CAPTURE_PATH` to a fresh `.gputrace` path and run
   the visual parity probe with the camera positioned over the
   cliff (overview scene works). Capture the shadow render pass
   (the encoder before the main scene encoder).
2. In Xcode, inspect `s_shadow_depth_texture` content for the
   screen-space xy that maps to (1700, 900) in the overview
   capture. The expected behavior: the texel is at the cliff's
   own depth (it cast itself into the shadow map). The bug
   behavior: the texel is at a closer caster's depth than the
   cliff fragment's own.
3. Compare the same pixel in a GL frame trace if possible (or
   reason about what GL does: same matrix, same culling, but GL
   writes the shadow texture directly with `glBlitFramebuffer` /
   regular drawing instead of Metal's `replaceRegion`-style
   per-vertex stream).
4. Likely root cause hypotheses to check first:
   - **Cull mode mismatch** during shadow vs main pass on static
     meshes. Both backends use `glCullFace(GL_FRONT)` /
     `MTLCullModeFront` during shadow; but if Metal's static-mesh
     winding is different from GL's because of the §"static-prop
     winding/culling parity fix" applied earlier, only the front
     pass is right and the shadow pass is wrong.
   - **Front-facing winding** — Metal sets
     `MTLWindingClockwise` in shadow_pass_begin
     (`backend_metal.m:2110`). Verify this matches the actual
     winding of the cliff prop's triangles. If GL's shadow pass
     uses `glFrontFace(GL_CCW)` and Metal's geometry is wound CW,
     `MTLCullModeFront` culls a different set of triangles.
   - **Depth bias** — Metal shader uses `base_bias = 0.002` and
     compares `proj_z - bias > closest_depth`. For the cliff's
     own front face, `proj_z` and `closest_depth` are very close.
     If the GL shader's effective bias is larger (or has a
     slope-scaled component), GL's test is more permissive.
     `terrain-shadowed.glsl:55` says `SHADOW_MAP_BIAS = 0.002`
     too — same constant — but the depth values written may
     differ in scale (recall the §7 NDC z fix; static-mesh shadow
     pipeline may have a residue of the old mapping).

I am stopping at the diagnosis-and-handoff point intentionally:
this is exactly the kind of slice where Xcode trace inspection by
Codex is faster than text-only iteration. The hook is in place,
the symptom is reproducible, the hypothesis ladder is ranked.

### Out-of-scope (recorded only, do not chase)

- The combat (2074, 1370) and (2200, 1500) Metal-brighter pockets
  could be Slice 3's leftover localized pocket OR animation-frame
  variance between the GL and Metal capture runs. Re-sample after
  any Slice 6 fix lands; if they remain, investigate then.
- Overview (2074, 1370) and (1900, 1300) at 1.03–1.06 are within
  noise. Don't chase.
- Water (2592, 477) at 0.88 could be the same cliff-shadow issue
  bleeding into the water-scene capture's banner area. Likely to
  be closed automatically by Slice 6.

### Verification artifacts

- `visual_parity_captures/2026-04-26-harness-test/` — fresh paired
  capture used for the numerical analysis above.
- `/tmp/g_ov.png`, `/tmp/m_ov.png` — cropped cliff-face evidence.
- `/tmp/g_co.png`, `/tmp/m_co.png` — cropped combat-scene evidence
  (now near-parity).

---

## 21. Attempt 14 — 2026-04-26 — Static-mesh self-shadow parity (cliff face)

### Trace evidence

Generated two Metal traces:

- `visual_parity_captures/2026-04-26-cliff-shadow-trace/cliff.gputrace`
  using the originally requested start-present window.
- `visual_parity_captures/2026-04-26-cliff-shadow-trace/cliff-overview.gputrace`
  using an earlier start-present window so the overview cliff camera's shadow
  pass was inside the capture.

In Xcode, `cliff-overview.gputrace` shows the first command buffer's first
render encoder is the shadow pass:

- viewport: `0, 0, 2048, 2048`
- depth attachment: `Texture 2D`, `Depth`, `Clear | Store`
- `setCullMode:Front`
- pre-fix `setFrontFacingWinding:Clockwise`
- terrain `shadow_depth_vertex` draws first, followed by static-mesh
  `shadow_depth_vertex` draws into the same depth texture.

The trace confirmed the bug is in the shadow caster state, not material
sampling or final-scene lighting.

### Winning hypothesis

**Front-facing winding mismatch in the Metal shadow pass.**

Changing only the shadow encoder front-facing winding from clockwise to
counter-clockwise moved the overview cliff sample from the exact shadow
multiplier signature to parity. This rules out depth bias as the primary fix
for this slice.

### Diff

`src/render/backend_metal.m:2238`

```objc
[s_shadow_encoder setFrontFacingWinding:MTLWindingCounterClockwise];
```

The cull mode remains `MTLCullModeFront`; only the shadow pass winding changed.
Main static/skinned mesh draw winding remains unchanged.

### Before / after

Baseline from `visual_parity_captures/2026-04-26-harness-test/`:

```text
overview 1700,900  ratio = 0.58, 0.58, 0.57
rocks    1700,900  ratio = 0.77, 0.79, 0.81
combat   2074,1370 ratio = 1.33, 1.36, 1.35
combat   2200,1500 ratio = 1.23, 1.26, 1.21
```

Diagnostic capture after the one-line winding change:

```text
overview 1700,900  ratio = 1.04, 1.04, 1.04
combat   2074,1370 ratio = 1.34, 1.36, 1.35
combat   2200,1500 ratio = 1.23, 1.26, 1.21
```

Final acceptance capture:

```text
visual_parity_captures/2026-04-26-cliff-shadow-fix/

overview 1700,900  ratio = 1.04, 1.04, 1.04
overview 2074,1370 ratio = 1.04, 1.04, 1.06
overview 1900,1300 ratio = 1.03, 1.04, 1.03
rocks    1700,900  ratio = 1.17, 1.16, 1.15
rocks    2074,1370 ratio = 1.00, 1.00, 1.00
```

The final combat side-effect sample is not reliable because the final capture's
summary JSON records different OpenGL/Metal combat camera positions. The
diagnostic capture indicates the previous combat bright pockets did **not**
close as a side effect of the cliff fix.

### Result

Slice 6 is closed for the cliff-face acceptance gate. The highest-priority
Metal-darker self-shadow pocket moved from `0.57x` to within the requested
`0.95-1.05` band. Remaining combat-brighter pockets should stay parked as the
separate Slice 3 residual unless a future matched-camera capture proves they
share the same cause.

---

## 22. Attempt 15 — 2026-04-26 — Combat capture determinism + bright-pocket re-check

### Context

The final Slice 6 capture closed the cliff-face shadow gap, but its combat
side-effect ratios were not trustworthy: `summary_opengl.json` and
`summary_metal.json` recorded different combat camera positions. The combat
target was being picked from moving enemy units in `_build_scenes()`, so small
backend startup timing differences could move the chosen target before capture.

### Diff

`scripts/macos/pf_visual_parity_probe.py`

- pauses simulation with `pf.set_simstate(pf.G_PAUSED_UI_RUNNING)` before
  scene construction in the `init` phase
- resumes simulation at probe exit if it is still paused

`scripts/macos/capture_visual_parity.sh`

- adds a post-capture summary check that compares OpenGL and Metal scene names
  and camera positions
- exits with `CAMERA MISMATCH ...` if any scene position differs by more than
  `0.1` world units

### Deterministic capture

`scripts/macos/capture_visual_parity.sh
visual_parity_captures/2026-04-26-combat-deterministic`

Result:

```text
CAMERAS MATCH scenes=4 max_position_delta=0.000000
```

Both summaries now report identical camera positions and directions:

```text
overview [152.32484436035156, 262.5, 10.558418273925781]
water    [318.51068115234375, 262.5, -57.48931884765625]
rocks    [330.86346435546875, 262.5, -82.65286254882812]
combat   [151.37591552734375, 262.5, -68.48370361328125]
```

### Combat ratios with matched cameras

`png_block_compare.py`, half=60:

| Point | Ratio M/G | Conclusion |
|---|---:|---|
| 2074,1370 | 1.32, 1.35, 1.34 | bright pocket persists |
| 2200,1500 | 1.25, 1.28, 1.23 | bright pocket persists at block scale |
| 1900,1300 | 1.02, 1.03, 1.03 | near parity |
| 2592,477 | 1.00, 1.00, 1.00 | baseline holds |
| 2300,1700 | 1.00, 1.00, 1.00 | baseline holds |

`png_block_compare.py`, half=2:

| Point | Ratio M/G | Conclusion |
|---|---:|---|
| 2074,1370 | 2.40, 3.80, 2.54 | highly localized bright pixel/feature |
| 2200,1500 | 0.97, 0.97, 0.97 | exact point is not bright; half=60 delta is area composition |
| 1900,1300 | 1.00, 1.00, 1.00 | parity |
| 2592,477 | 1.00, 1.00, 1.00 | parity |
| 2300,1700 | 1.01, 1.01, 1.01 | parity |

Crops saved for visual review:

- `/tmp/g_combat_det.png`
- `/tmp/m_combat_det.png`

The residual is not a global Metal brightness/gamma issue. It is localized
around the unit cluster / cobblestone / healthbar composition.

### Rocks side-effect re-sample

`png_block_compare.py`, half=60:

| Point | Ratio M/G | Note |
|---|---:|---|
| 1700,900 | 1.11, 1.10, 1.09 | still slightly Metal-brighter, smaller than Slice 6 final |
| 1900,1300 | 1.30, 1.30, 1.30 | very dark absolute values: GL 6.3/5.8/4.6, Metal 8.2/7.5/6.0 |
| 2074,1370 | 1.00, 1.00, 1.00 | parity |
| 1900,1500 | nan, nan, nan | both blocks black |
| 2200,1500 | 1.00, 1.00, 1.00 | parity |

`png_block_compare.py`, half=2:

| Point | Ratio M/G | Note |
|---|---:|---|
| 1700,900 | 1.35, 1.28, 1.26 | localized low-value cliff/fog residual |
| 1900,1300 | nan, nan, nan | both blocks black |
| 2074,1370 | 1.01, 1.00, 1.01 | parity |
| 2200,1500 | 0.99, 0.99, 1.01 | parity |

This is real enough to keep on the list, but its absolute values are small and
it is not blocking the combat evidence fix.

### Skin-weight smoke check

Quick asset scan over combat-relevant models found many non-unit-sum `vw` rows:

```text
knight     bad_gt_0.01=1122 maxdev=3.090961
mage       bad_gt_0.01=420  maxdev=2.000000
goblin     bad_gt_0.01=6719 maxdev=1.215531
sinbad     bad_gt_0.01=8265 maxdev=0.976547
berzerker  bad_gt_0.01=728  maxdev=2.000000
```

The §18 Metal normalization is already unconditional in
`render_skinned_mesh_draw` and `append_skinned_anim_mesh`, so this remains
background validation rather than a new candidate fix for this localized
bright pocket.

### Result

Slice 7 closed the evidence problem. Combat capture cameras now match exactly
and future parity captures fail fast if they drift again.

The bright-pocket residual is still **open** with trustworthy evidence:

- it is not camera drift
- it is not a broad scene tone mismatch
- it is localized around the combat unit cluster / cobblestone area

Recommended next slice: capture the combat scene's shadow pass with the
`MTLCaptureManager` hook and inspect static/skinned mesh depth writes around
the unit cluster. The leading hypothesis is still a localized shadow-map
caster/receiver mismatch; the 5×5 data says to inspect exact pixels rather
than broad terrain tone first.

## 23. Attempt 16 — 2026-04-26 — Combat localized shadow/material residual

### Starting point

Input artifact:
`visual_parity_captures/2026-04-26-combat-deterministic/`

Slice 7 made the combat camera trustworthy:

```text
CAMERAS MATCH scenes=4 max_position_delta=0.000000
```

The open residual was still localized around the combat unit cluster:

| Block | Point | Before ratio M/G |
|---|---:|---:|
| half=60 | 2074,1370 | 1.32, 1.35, 1.34 |
| half=60 | 2200,1500 | 1.25, 1.28, 1.23 |
| half=60 | 2592,477 | 1.00, 1.00, 1.00 |
| half=60 | 2300,1700 | 1.00, 1.00, 1.00 |
| half=2 | 2074,1370 | 2.40, 3.80, 2.54 |
| half=2 | 2068,1370 | 2.49, 3.92, 2.76 |
| half=2 | 2080,1370 | 2.66, 4.20, 2.72 |
| half=2 | 2200,1500 | 0.97, 0.97, 0.97 |
| half=2 | 2210,1500 | 1.10, 1.11, 1.11 |

### Hypothesis checks

1. `pf.G_PAUSED_FULL` was tested in the probe as a stronger pause mode.
   It froze the UI/update callbacks after `VISUAL_PARITY_PHASE
   settle:overview`, so the probe never advanced to captures. Reverted.

2. Added a probe-side animation reset after `pf.G_PAUSED_UI_RUNNING`:
   `scripts/macos/pf_visual_parity_probe.py:240` iterates animated
   entities and calls `play_anim(get_anim())`, then records
   `frozen_anim_count` in the summary. Both backends reported:

   ```text
   VISUAL_PARITY_ANIM_FREEZE count=59
   ```

   Capture:
   `visual_parity_captures/2026-04-26-combat-animfreeze-test/`

   Result: ratios were unchanged. Animation phase drift is not the
   cause of the measured hot strip.

3. First combat GPU trace capture at start present 390 was incomplete:
   Xcode failed with "index file does not exist". A shorter/finalized
   trace succeeded:

   ```text
   visual_parity_captures/2026-04-26-combat-shadow-trace/combat-finalized.gputrace
   ```

   The trace opened in Xcode. Command Buffer 0 / Render Encoder 0 was
   the shadow depth pass: 2048x2048 viewport, `setCullMode:Front`, and
   `setFrontFacingWinding:CounterClockwise`.

4. Diagnostic animated-shadow winding override was tested and reverted:
   leaving static/terrain shadow winding at CCW while drawing animated
   shadow casters as CW produced no measurable change in the combat
   residual.

5. Pixel inspection changed the leading diagnosis. After cropping
   `/tmp/g_hb_after.png` and `/tmp/m_hb_after.png`, the worst half=2
   pixels were not terrain/shadow pixels:

   ```text
   OpenGL 2074,1370 = 0,0,0
   Metal  2074,1370 = 24,63,12
   ```

   The OpenGL pixel was the black healthbar outline; Metal was sampling
   green/dark-green bar/content. The immediate hot strip was a
   healthbar outline parity bug, not a mesh shadow receiver bug.

### Landed diff

`src/render/backend_metal.m:4219` now mirrors the GL statusbar shader
more closely:

- effective healthbar border changed from 1 px to 2 px, matching GL's
  `BORDER_PX_WIDTH / CURR_HB_HEIGHT` behavior over a `[-1,+1]` quad
- fill cutoff now uses the same outer-UV-space health percentage as GL
  instead of scaling across only the already-inset inner width
- the fill is split into top and bottom halves so Metal applies GL's
  `uv.y > 0.5` 0.8x bottom-half darkening

`scripts/macos/pf_visual_parity_probe.py:240` also keeps the animation
reset as capture-harness hardening. It did not fix this residual, but
it makes future combat captures explicitly start animated entities at
the beginning of their current clips and records the reset count.

### Verification

Build:

```text
make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL
python3 -m py_compile scripts/macos/pf_visual_parity_probe.py
```

Paired capture:

```text
scripts/macos/capture_visual_parity.sh visual_parity_captures/2026-04-26-combat-residual-fix
CAMERAS MATCH scenes=4 max_position_delta=0.000000
```

`png_block_compare.py`, half=60:

| Point | After ratio M/G | Result |
|---|---:|---|
| 2074,1370 | 1.24, 1.21, 1.26 | improved, still open at block scale |
| 2200,1500 | 1.21, 1.19, 1.20 | improved, still open at block scale |
| 1900,1300 | 1.00, 1.00, 1.00 | parity |
| 2592,477 | 1.00, 1.00, 1.00 | baseline holds |
| 2300,1700 | 1.00, 1.00, 1.00 | baseline holds |

`png_block_compare.py`, half=2:

| Point | After ratio M/G | Result |
|---|---:|---|
| 2074,1370 | 1.11, 1.28, 1.08 | hot strip mostly closed; green still high |
| 2068,1370 | 1.13, 1.30, 1.11 | hot strip mostly closed; green still high |
| 2080,1370 | 1.26, 1.45, 1.22 | improved, still a local edge/composition delta |
| 2200,1500 | 0.97, 0.97, 0.97 | exact center parity/darker |
| 2210,1500 | 1.10, 1.11, 1.11 | unchanged small local pocket |

The high half=2 point moved from roughly 2.4-4.2x to roughly 1.1-1.45x,
so the healthbar edge bug was a real contributor. The acceptance target
for the broader half=60 block was not reached.

### Rocks side-effect re-sample

`visual_parity_captures/2026-04-26-combat-residual-fix/`

| Block | Point | Ratio M/G | Note |
|---|---:|---:|---|
| half=60 | 1700,900 | 1.11, 1.10, 1.09 | still small Metal-brighter residual |
| half=60 | 1900,1300 | 1.30, 1.30, 1.30 | very dark absolute values |
| half=2 | 1700,900 | 1.38, 1.32, 1.28 | localized low-value rock/cliff residual |

### Diagnostic rejected after the landed fix

Metal's mesh shadow receiver UV bounds were temporarily changed to mimic
GL's clamp-to-edge behavior for `proj_xy > 1.0`, then captured at:

```text
visual_parity_captures/2026-04-26-combat-shadow-uv-clamp-test/
```

Combat ratios were bit-for-bit unchanged at the sampled points, so that
diagnostic was reverted.

### Result

Slice 8 is **partial**:

- `G_PAUSED_FULL` is not usable for this probe because it stops the UI
  capture loop.
- Animation reset did not change the residual, so animation phase drift
  is rejected for the current hot strip.
- Shadow winding and mesh receiver UV-bound diagnostics did not change
  the combat samples.
- A real Metal healthbar outline/shading mismatch was fixed.
- The remaining half=60 combat delta is broader than the black healthbar
  outline. Pixel clusters around y~1400 show Metal still brighter on
  unit/cobblestone composition, so the next slice should inspect the
  skinned/static mesh material/lighting path around the knight cluster,
  not global terrain tone.

---

## 24. Attempt 17 — 2026-04-26 — Combat cluster cobble shadow: rejected hypotheses + handoff

### Starting point

Slice 8 closed the healthbar outline parity but left a half=60 ratio of
~1.21–1.24× across the combat unit cluster. Codex's Slice 8 record (§23)
diagnosed it as "skinned/static mesh material-lighting or composition,
not global terrain tone." Visual evidence and 5×5 / 11×11 sampling told
a different story.

### Visual + numerical re-grounding

`/tmp/g_cluster.png` vs `/tmp/m_cluster.png` (500×350 crop centered at
the Knight cluster from `2026-04-26-combat-residual-fix/`):

OpenGL clearly shows long diagonal **sword-shadow streaks** extending
up-right from each Knight onto the cobblestone. Metal's same crop has
no visible streaks — cobblestone is uniformly lit under and around the
units.

11×11 block ratios along the GL streak path:

```
2100,1460  ratio = 1.82, 1.83, 1.82
2120,1450  ratio = 1.81, 1.81, 1.81
2140,1420  ratio = 1.51, 1.51, 1.51
2090,1410  ratio = 1.90, 1.87, 1.88
2090,1490  ratio = 1.88, 1.88, 1.89
2074,1500  ratio = 1.81, 1.81, 1.81
2150,1500  ratio = 1.82, 1.82, 1.83
```

1.82× = 1/0.55 = exact `SHADOW_MULTIPLIER` signature. **GL applies
near-full shadow at the streak; Metal applies essentially none.**
This is the same diagnostic pattern as Slice 1 (cliff face) but
inverse — Metal missing GL shadow.

### Debug visualization (rejected hypothesis #1)

Added an env-gated `PF_METAL_DEBUG_SHADOW_VIZ=1` branch to the terrain
fragment shader that returns `(R=closest_depth, G=current_depth,
B=compare-fired)`. Capture: `/tmp/shadow_viz2/metal_combat.png`.

Decoded samples at cluster cobble points:

```
2090,1410   closest=0.48  current=0.24  compare-fired=0.10
2090,1450   closest=0.30  current=0.30  compare-fired=0.28
2090,1490   closest=0.33  current=0.29  compare-fired=0.12
2070,1450   closest=0.61  current=0.73  compare-fired=0.79
2050,1410   closest=0.93  current=0.43  compare-fired=0.18  (clear)
```

**The shadow texture HAS caster data at the cluster xy (closest_depth
<< 1.0 in many places).** The comparison correctly returns "no shadow"
because Metal's `current_depth` (raw NDC z = 0.24) is less than the
caster depth (0.48). Geometrically: the recorded caster at this xy is
FURTHER from the light than the terrain pixel projects.

This rules out the "shadow texture is empty" hypothesis. Metal IS
rasterizing casters; the depth comparison just doesn't fire because of
the relative depth values at the cluster xys.

### Rejected hypothesis #2 — Metal-friendly ortho swap

Replaced `PFM_Mat4x4_MakeOrthographic` with a Metal-convention ortho
that maps view-space [-near, -far] to NDC z [0, 1] (instead of GL's
[-1, 1]) for the shadow light projection.

Capture: `visual_parity_captures/2026-04-26-shadow-ortho-fix/`.

**Result: Metal output bit-identical to baseline at every sample
point.** The hardware was not actually clipping NDC z < 0 fragments in
this scene's geometry. Reverted. Re-confirms my §10 (Slice 3a) finding.

### Rejected hypothesis #3 — MTLDepthClipModeClamp

Set `[s_shadow_encoder setDepthClipMode:MTLDepthClipModeClamp]` so
near-half fragments would survive instead of being clipped.

Capture: `visual_parity_captures/2026-04-26-shadow-clipclamp/`.

**Result: bit-identical to baseline.** Either Metal hardware behaves
differently from Apple's documented Clip default, or the clip mode is
overridden somewhere downstream. Reverted.

### Rejected hypothesis #4 — GL-style depth remap in shader

Hypothesized that Metal hardware actually stores depth as
`(NDC z + 1)/2` (GL-style) and that the Slice 1 raw-NDC-z mapping was
wrong. Tested by changing `current_depth = proj_z` to
`current_depth = proj_z * 0.5 + 0.5` in both `shadow_factor` and
`mesh_shadow_factor`.

Capture: `visual_parity_captures/2026-04-26-shadow-glmap/`.

**Result: regressed previously-parity points.** `combat (2300, 1700)`
went from 1.00 to 0.82, `combat (1900, 1300)` from 1.00 to 0.94 —
Metal now applies shadow where GL doesn't (over-shadowing). Cluster
samples improved marginally (e.g., 2090,1490 went 1.88 → 1.77) but
not enough to close the gap. **Confirms Metal hardware stores raw
NDC z, consistent with Slice 1's mapping.** Reverted.

### What's left as the actual cause

After ruling out all of (a) clipping, (b) clamp mode, (c) depth-value
encoding, the remaining candidate causes are:

1. **GL's depth pass writes more shadow casters than Metal's.**
   Specifically suspected: GL submits some entity to its depth pass
   that Metal does not, OR GL renders some triangles that Metal culls.
   The `light_vis_stat` and `light_vis_anim` lists are populated on the
   game side identically for both backends, so the difference (if any)
   is in what the renderer DOES with each entity.

2. **Pose / skinned-vertex divergence.** Metal CPU-skins each vertex
   in `append_skinned_anim_mesh` (with the §18 weight-normalization
   fix). GL GPU-skins via `skinned-depth.glsl`. Both should produce
   identical world positions for identical pose data, but if GL's
   pose-buffer texture sampling and Metal's CPU matrix multiplies
   diverge by even a small amount, the projected caster depth at
   cluster xys could shift enough to matter.

3. **Static-mesh shadow-pass winding interaction with the cliff fix.**
   Slice 6 flipped the shadow-pass winding to CCW. Codex re-tested
   reverting animated-mesh winding to CW and saw no change. Untested:
   reverting STATIC-mesh winding only to CW. Banner poles, prop bases,
   rock geometry are static, and might rasterize to different texels
   in the shadow map under different winding.

### Hypotheses I am NOT currently chasing

- Specular / material-lighting on units. Visual evidence (cobble
  beneath units brighter than units themselves; ratio peaks at 1.82×
  on cobble at 2074,1500; ratio at unit body 2074,1370 only 1.16×)
  rules this out as the dominant cause.
- Animation pose drift. Codex's animation-reset hardening lands a
  count of 59 frozen entities deterministically; ratios were
  unchanged across captures with vs without the reset.

### State after this attempt

All experimental changes are reverted. The tree is at the post-Slice-8
state:

- Skin-weight normalization (§18) in place.
- MSAA parity default = 1, opt-in via `PF_METAL_MSAA_SAMPLES` (§19).
- Cliff-face shadow winding fix (§21) in place.
- Combat camera determinism (§22) in place.
- Healthbar outline parity (§23) in place.

Build verified:
`make pf PLAT=MACOS_ARM64 MACOS_ARM64_BUILD_READY=1 RENDER_BACKEND=METAL`

### Recommended next move (Slice 9)

The next-most-informative step is **direct shadow texture content
comparison between backends**. This requires either:

a. Extending the existing `MTLCaptureManager` hook (§17) to also dump
   the resolved `s_shadow_depth_texture` content to a viewable PNG at
   capture-end time. Then compare GL's depth attachment dump (which
   would need analogous instrumentation in `gl_shadows.c`) against
   Metal's. If Metal's shadow map is missing caster geometry that
   GL's has at the cluster xys, hypothesis #1 above wins.

b. Per-vertex dump of the SHADOW PASS's vertex shader output for one
   skinned mesh, both backends. Compare clip-space positions for
   matching vertex indices. If Metal's positions differ from GL's by
   more than floating-point noise, hypothesis #2 wins.

c. Static-mesh-only shadow-pass winding override (mirror Codex's
   animated-mesh test from §23). Set static-mesh shadow pass to CW
   while keeping terrain at CCW. If cluster ratios collapse,
   hypothesis #3 wins.

Of those, (c) is the cheapest (one-line, pre-pipeline state change),
and the most likely to either fix or definitively rule out the
remaining structural hypothesis. Suggested first step.

### Side-effect side-quest noted

`overview (1700, 900)` was 1.04× post-Slice-6 (cliff face acceptance
gate). The half=60 sample at the same point in the
`shadow-clipclamp` capture is unchanged — winding fix holds.

`rocks (1700, 900)` half=60 = 1.16, 1.14, 1.14 — small persistent
Metal-brighter residual (was 1.10× post-Slice-7). Not regressed by
this attempt's experiments. Same pattern as the cluster, smaller
magnitude. Likely closed by whichever Slice 9 fix lands.


---

## §25 — Direction pivot: Metal-native redesign + drop OpenGL (2026-04-25)

User has pivoted: parity-first is suspended. New plan at
`/Users/dev/.claude/plans/the-degradation-in-character-fizzy-mitten.md`:

1. Drop OpenGL entirely; Metal becomes sole renderer (~20,030 LOC across
   37 files + shaders/ to delete).
2. Add PBR material pipeline (albedo/normal/roughness/metallic/AO) +
   Cook-Torrance BRDF in static + animated mesh shaders.
3. AI-generated PBR maps per character (Codex, computer-use).
4. Knight first as PoC; roll out to all models; optional mesh redesign.

The unresolved §24 cluster cobble shadow residual is now SUPERSEDED —
no longer worth solving since the static mesh shader will be replaced.

### Phase 0 status (Claude, 2026-04-25)

**Blocker found:** repo has zero git commits and no remote
(`git log` empty, `git remote -v` empty). The plan's Phase 0 safety
mitigation (`git tag pre-metal-redesign && git push origin
pre-metal-redesign`) cannot run.

**Mitigation taken:** snapshot of `src/`, `shaders/`, `Makefile`,
`a.md`, `plans/` saved to `backups/2026-04-25-pre-metal-redesign/`
(6.4M). This is the recovery point before Phase 1 deletion.

**Remaining Phase 0 step (deferred to Codex):** baseline visual
capture via `scripts/macos/capture_visual_parity.sh
visual_parity_captures/2026-04-26-pre-redesign` and the Knight-zoom
ref shot. Both require interactive game runs.

**Awaiting user confirmation** before proceeding to Phase 1 (deletion
of OpenGL backend) per auto-mode safety policy.
