# MGL OpenGL-On-Metal Notes

Created: 2026-04-25

## Scope

This note captures lessons from `openglonmetal/MGL` for the Permafrost Apple Silicon renderer migration.

MGL is useful as an OpenGL internals reference because it maps OpenGL state and draw calls onto Metal. It is not a runtime dependency target for this project. The Permafrost goal remains a native Metal backend that eventually replaces OpenGL, not an OpenGL compatibility layer running through Metal.

## Relevant MGL Lessons

- OpenGL works like a large mutable state machine. Most API calls validate parameters, update context state, and mark pieces of that state dirty; the real resolution happens when a draw, copy, or compute command reaches the GPU-facing path.
- Metal makes many of those states explicit earlier: pipeline pixel/depth formats, blend factors, vertex descriptors, depth/stencil state, front-face winding, cull mode, depth bias, scissor/viewport, texture/sampler bindings, render-pass load/store actions, and command encoders.
- MGL's `processGLState` idea is the important conceptual bridge: before a draw call, collect the current OpenGL state, rebuild or reuse the Metal pipeline/encoder state that depends on it, bind buffers/textures/samplers, then issue the Metal draw.
- Permafrost should keep applying that idea at the engine command level. Instead of implementing all OpenGL 4.6, map the existing `R_GL_*` renderer commands and known shader/material paths directly into stable Metal pipelines.
- The recent static-prop winding fix is a concrete example of this lesson. OpenGL's global `glFrontFace(GL_CW)` was implicit state; Metal needed the matching `MTLWindingClockwise` set explicitly in mesh and shadow draw paths.
- Render targets are another critical state boundary. OpenGL framebuffer and implicit load/store behavior must become explicit Metal render-pass descriptors, including color/depth formats, MSAA store/resolve rules, and offscreen reflection/refraction usage.
- Shader bindings should be audited as typed layout contracts, not loose names. Vertex attributes, material texture arrays, terrain texture arrays, uniform buffers, water textures, and shadow maps should each have clear Metal binding slots that match the source GLSL intent.
- Pipeline caching matters for smoothness. MGL notes that immutable Metal objects should be created up front where practical; this matches Permafrost's ongoing work to cache persistent buffers, samplers, textures, and render pipeline states instead of doing avoidable per-frame setup.
- Feature-by-feature tests are the safest migration pattern. MGL's functional test approach maps well to the current Permafrost probes and fixed-camera OpenGL/Metal capture harness.

## Porting Guidance For Permafrost

- Treat every OpenGL parity bug as a missing explicit Metal state until proven otherwise.
- For each renderer path, audit:
  - source GLSL inputs and texture/sampler bindings
  - material/light/fog/shadow uniforms
  - front-face winding, cull mode, depth write/test, blend state, and alpha discard
  - render target pixel formats, depth formats, MSAA store/resolve, and load/store behavior
  - texture orientation, mipmap generation, address mode, filtering, and gamma/color-space assumptions
- Keep the OpenGL fallback stable while Metal closes visual and smoothness parity.
- Do not route the final engine through a generic OpenGL-on-Metal shim. The desired endpoint is a clean Metal renderer that owns terrain, water, skybox, shadows, meshes, foliage, UI overlays, editor views, and future HD/4K graphics features natively.

## Latest Applied Target

The first follow-up implementation slice from this note is now applied: a Metal mesh normal-transform parity fix for characters, buildings, and rocks/static props at the existing water/rocks capture distances.

That slice compared the OpenGL `textured-phong-shadowed` and skinned/static vertex shader assumptions against the Metal mesh path, then made Metal normal transforms explicit at the draw boundary. This follows directly from the MGL lesson that implicit OpenGL draw state must be made explicit and verified at the Metal draw boundary.

Current code-read anchors:

- OpenGL static mesh normals use `mat3(model) * in_normal`; Metal now passes that draw-level normal transform explicitly.
- OpenGL skinned mesh normals use the engine-provided `anim_normal_mat` after skinning; Metal now preserves that normal-space contract for the CPU-skinned path.
- The OpenGL and Metal mesh fragment formulas are now close enough that remaining differences are likely in state and data feeding: material values, texture/sampler behavior, alpha discard, shadow state, scene light inputs, or broader terrain/water tone.

Applied result:

- `src/render/backend_metal.m` now passes an explicit mesh normal transform in `StaticMeshUniforms`.
- CPU-skinned Metal normals now use inverse-transpose pose/bind transforms, then the draw-level normal transform.
- Verification artifact: `visual_parity_captures/2026-04-25-metal-mesh-normal-parity/`.
- Remaining target: broader scene color/material response and water shoreline/color matching.

## References

- <https://github.com/openglonmetal/MGL>
- <https://github.com/openglonmetal/MGL#mapping-opengl-onto-metal>
- <https://github.com/openglonmetal/MGL#processglstate-does-all-the-state-mapping-from-opengl-to-metal>
