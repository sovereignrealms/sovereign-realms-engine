# Apple Metal Migration Sample Notes

Created: 2026-04-25

## Local Sample Archives Reviewed

- `/Users/dev/Downloads/MixingMetalAndOpenGLRenderingInAView.zip`
- `/Users/dev/Downloads/MigratingOpenGLCodeToMetal.zip`

## Relevant Lessons For This Port

- Treat OpenGL/Metal interop as a temporary migration aid, not the end state. The final Permafrost path should be native Metal, with OpenGL removed after parity gates are met.
- When comparing a migrated draw path, keep the OpenGL and Metal versions structurally aligned: vertex layout, texture coordinates, normal transforms, sampler state, render-target formats, depth state, culling, and alpha behavior should be checked together.
- Metal pipeline state bakes more assumptions than an OpenGL program object. Pixel formats, depth formats, vertex layout, and shader entry points need to be explicit per pipeline.
- Texture-origin differences must be handled deliberately. For this engine, Metal mesh UV parity should stay matched to the existing OpenGL material shaders rather than applying ad hoc flips per asset.
- Metal clip-space depth differs from OpenGL. Any migrated projection, shadow, reflection, or offscreen path should be validated with actual captures instead of assuming matrix parity from visual similarity.
- Mipmaps and sampler choices matter for static props. Rocks/buildings/foliage should use the same intended filtering class as the OpenGL baseline before judging art quality.
- Dynamic per-frame data should be protected from CPU/GPU overlap with bounded in-flight buffering or equivalent lifetime discipline. This matters later for smoothness parity and larger RTS scenes.
- Offscreen render targets need explicit usage, load/store actions, depth attachments, and restore paths. This applies to water, minimap, shadows, reflections, and future high-clarity effects.

## Application To The Next Rock/Static-Prop Slice

- First inspect static mesh material sampling and alpha handling against the OpenGL `textured-phong-shadowed` path.
- Confirm normals and light vectors are in the same space as OpenGL for rocks/static props.
- Confirm sampler/mipmap behavior is appropriate for material texture arrays at the rocks camera distance.
- Keep the change narrow: fix one visible parity gap, verify with the rocks fixed-camera capture, and preserve the OpenGL fallback.

## Naming Note

- The project folder name `OpenGL RTS game engine` no longer matches the long-term goal. A future cleanup can rename the folder to `RTS game engine`, but that should be a separate small change after checking scripts, docs, local captures, and app workspace assumptions for absolute path references.
