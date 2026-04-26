/*
 *  This file is part of Permafrost Engine.
 *  Copyright (C) 2017-2023 Eduard Permyakov
 *
 *  Permafrost Engine is free software: you can redistribute it and/or modify
 *  it under the terms of the GNU General Public License as published by
 *  the Free Software Foundation, either version 3 of the License, or
 *  (at your option) any later version.
 *
 *  Permafrost Engine is distributed in the hope that it will be useful,
 *  but WITHOUT ANY WARRANTY; without even the implied warranty of
 *  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 *  GNU General Public License for more details.
 */

#include <SDL.h>
#include <SDL_metal.h>
#include <dispatch/dispatch.h>

#import <Metal/Metal.h>
#import <QuartzCore/CAMetalLayer.h>
#import <simd/simd.h>

#include "backend_local.h"
#include "public/render.h"
#include "gl_material.h"
#include "render_private.h"
#include "gl_vertex.h"
#include "../anim/public/anim.h"
#include "../anim/public/skeleton.h"
#include "../phys/public/collision.h"
#include "../map/public/map.h"
#include "../map/public/tile.h"
#include "../camera.h"
#include "../main.h"
#include "../game/public/game.h"
#include "../lib/public/pf_nuklear.h"
#include "../lib/public/stb_image.h"
#include "../lib/public/stb_image_resize.h"
#include "../lib/public/mem.h"
#include "../config.h"

#include <assert.h>
#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>


extern bool g_trace_gpu;

static SDL_Window               *s_window;
static struct render_sync_state *s_rstate;
static SDL_MetalView             s_metal_view;
static id<MTLDevice>             s_device;
static id<MTLCommandQueue>       s_queue;
static CAMetalLayer             *s_layer;

static id<MTLRenderPipelineState> s_ui_pipeline;
static id<MTLRenderPipelineState> s_ui_msaa_pipeline;
static id<MTLRenderPipelineState> s_terrain_pipeline;
static id<MTLRenderPipelineState> s_terrain_msaa_pipeline;
static id<MTLRenderPipelineState> s_terrain_depth_pipeline;
static id<MTLRenderPipelineState> s_terrain_depth_msaa_pipeline;
static id<MTLRenderPipelineState> s_static_mesh_pipeline;
static id<MTLRenderPipelineState> s_static_mesh_msaa_pipeline;
static id<MTLRenderPipelineState> s_static_mesh_blend_pipeline;
static id<MTLRenderPipelineState> s_static_mesh_blend_msaa_pipeline;
static id<MTLRenderPipelineState> s_static_mesh_depth_pipeline;
static id<MTLRenderPipelineState> s_static_mesh_depth_msaa_pipeline;
static id<MTLRenderPipelineState> s_static_mesh_blend_depth_pipeline;
static id<MTLRenderPipelineState> s_static_mesh_blend_depth_msaa_pipeline;
static id<MTLRenderPipelineState> s_world_color_pipeline;
static id<MTLRenderPipelineState> s_world_color_msaa_pipeline;
static id<MTLRenderPipelineState> s_shadow_terrain_pipeline;
static id<MTLRenderPipelineState> s_shadow_mesh_pipeline;
static id<MTLRenderPipelineState> s_water_surface_pipeline;
static id<MTLRenderPipelineState> s_water_surface_msaa_pipeline;
static id<MTLDepthStencilState>   s_depth_write_state;
static id<MTLDepthStencilState>   s_depth_read_state;
static id<MTLSamplerState>       s_ui_sampler;
static id<MTLSamplerState>       s_scene_sampler;
static id<MTLSamplerState>       s_shadow_sampler;
static id<MTLTexture>            s_ui_font_texture;
static id<MTLTexture>            s_minimap_texture;
static id<MTLTexture>            s_terrain_texture_array;
static id<MTLTexture>            s_water_dudv_texture;
static id<MTLTexture>            s_water_normal_texture;
static id<MTLTexture>            s_frame_msaa_texture;
static id<MTLTexture>            s_frame_depth_texture;
static id<MTLTexture>            s_shadow_depth_texture;
static id<MTLTexture>            s_water_reflection_texture;
static id<MTLTexture>            s_water_reflection_depth_texture;
static id<MTLTexture>            s_water_refraction_texture;
static id<MTLTexture>            s_water_refraction_depth_texture;
static id<MTLBuffer>             s_fog_buffer;
static id<MTLBuffer>             s_water_buffer;

static id<CAMetalDrawable>       s_frame_drawable;
static id<MTLCommandBuffer>      s_frame_command_buffer;
static id<MTLRenderCommandEncoder> s_frame_encoder;
static id<MTLCommandBuffer>      s_shadow_command_buffer;
static id<MTLRenderCommandEncoder> s_shadow_encoder;
static id<MTLRenderCommandEncoder> s_water_scene_encoder;
static dispatch_semaphore_t      s_inflight_semaphore;

static char s_info_vendor[128];
static char s_info_renderer[128];
static char s_info_version[128];
static char s_info_sl_version[128];
static matrix_float4x4 s_scene_view;
static matrix_float4x4 s_scene_proj;
static matrix_float4x4 s_shadow_light_space;
static matrix_float4x4 s_shadow_view;
static matrix_float4x4 s_shadow_proj;
static vector_float3   s_scene_view_pos;
static bool            s_have_scene_view;
static bool            s_have_scene_proj;
static bool            s_shadow_pass_active;
static bool            s_water_scene_pass_active;
static bool            s_shadow_map_valid;
static bool            s_shadows_enabled;
static int             s_water_scene_clip_mode;
static NSUInteger      s_frame_sample_count;
static bool            s_frame_inflight_reserved;
static uint32_t        s_curr_anim_uid;
static bool            s_have_anim_uid;
static vector_float2   s_map_pos;
static vector_float2   s_map_tile_world_size;
static vector_uint2    s_map_chunk_size;
static vector_uint2    s_map_tiles_per_chunk;
static uint32_t        s_terrain_texture_count;

#define METAL_MAX_JOINTS 256
#define METAL_MINIMAP_RES 1024
#define METAL_MSAA_SAMPLES 4
#define METAL_LIGHT_EXTRA_HEIGHT 300.0f
#define METAL_WATER_LEVEL (-1.0f * Y_COORDS_PER_TILE + 2.0f)
#define METAL_WATER_DUDV_PATH "assets/water_textures/dudvmap.png"
#define METAL_WATER_NORMAL_PATH "assets/water_textures/normalmap.png"
#define METAL_WATER_CLIP_NONE 0
#define METAL_WATER_CLIP_KEEP_BELOW 1
#define METAL_WATER_CLIP_KEEP_ABOVE 2

static const char *s_ui_shader_source =
"#include <metal_stdlib>\n"
"using namespace metal;\n"
"struct UIUniforms {\n"
"    float2 view_size;\n"
"};\n"
"struct VertexIn {\n"
"    float2 position [[attribute(0)]];\n"
"    float2 uv [[attribute(1)]];\n"
"    float4 color [[attribute(2)]];\n"
"};\n"
"struct VertexOut {\n"
"    float4 position [[position]];\n"
"    float2 uv;\n"
"    float4 color;\n"
"};\n"
"vertex VertexOut ui_vertex(VertexIn in [[stage_in]], constant UIUniforms &uniforms [[buffer(1)]]) {\n"
"    VertexOut out;\n"
"    float2 ndc;\n"
"    ndc.x = (in.position.x / uniforms.view_size.x) * 2.0 - 1.0;\n"
"    ndc.y = 1.0 - (in.position.y / uniforms.view_size.y) * 2.0;\n"
"    out.position = float4(ndc, 0.0, 1.0);\n"
"    out.uv = in.uv;\n"
"    out.color = in.color;\n"
"    return out;\n"
"}\n"
"fragment float4 ui_fragment(VertexOut in [[stage_in]], texture2d<float> tex [[texture(0)]], sampler tex_sampler [[sampler(0)]]) {\n"
"    return in.color * tex.sample(tex_sampler, in.uv);\n"
"}\n";

static const char *s_terrain_shader_source =
"#include <metal_stdlib>\n"
"using namespace metal;\n"
"struct TerrainVertexIn {\n"
"    float3 position [[attribute(0)]];\n"
"    float2 uv [[attribute(1)]];\n"
"    float3 normal [[attribute(2)]];\n"
"    int material_idx [[attribute(3)]];\n"
"};\n"
"struct TerrainUniforms {\n"
"    float4x4 model;\n"
"    float4x4 view;\n"
"    float4x4 proj;\n"
"    float4 view_pos;\n"
"    float2 map_pos;\n"
"    float2 tile_world_size;\n"
"    uint2 chunk_size;\n"
"    uint2 tiles_per_chunk;\n"
"    float4 terrain_params;\n"
"    float4 water_params;\n"
"    float4x4 light_space_transform;\n"
"    float4 shadow_params;\n"
"    float4 clip_params;\n"
"};\n"
"struct TerrainVertexOut {\n"
"    float4 position [[position]];\n"
"    float3 normal;\n"
"    uint material_idx;\n"
"    float2 uv;\n"
"    float3 world_pos;\n"
"    float2 world_xz;\n"
"    float4 light_space_pos;\n"
"};\n"
"static float3 terrain_material_color(uint idx) {\n"
"    switch (idx % 8u) {\n"
"    case 0u: return float3(0.36, 0.55, 0.26);\n"
"    case 1u: return float3(0.44, 0.62, 0.30);\n"
"    case 2u: return float3(0.58, 0.54, 0.32);\n"
"    case 3u: return float3(0.41, 0.45, 0.27);\n"
"    case 4u: return float3(0.64, 0.60, 0.37);\n"
"    case 5u: return float3(0.29, 0.43, 0.24);\n"
"    case 6u: return float3(0.50, 0.49, 0.31);\n"
"    default: return float3(0.48, 0.57, 0.34);\n"
"    }\n"
"}\n"
"vertex TerrainVertexOut terrain_vertex(TerrainVertexIn in [[stage_in]], constant TerrainUniforms &uniforms [[buffer(1)]]) {\n"
"    TerrainVertexOut out;\n"
"    float4 world_pos = uniforms.model * float4(in.position, 1.0);\n"
"    out.position = uniforms.proj * uniforms.view * world_pos;\n"
"    out.normal = normalize(in.normal);\n"
"    out.material_idx = (uint)max(in.material_idx, 0);\n"
"    out.uv = in.uv;\n"
"    out.world_pos = world_pos.xyz;\n"
"    out.world_xz = world_pos.xz;\n"
"    out.light_space_pos = uniforms.light_space_transform * float4(out.world_pos, 1.0);\n"
"    return out;\n"
"}\n"
"static float terrain_fog_factor(uint state) {\n"
"    if(state == 0u) return 0.05;\n"
"    if(state == 1u) return 0.45;\n"
"    return 1.0;\n"
"}\n"
"static bool clip_water_world_y(float world_y, float4 clip_params) {\n"
"    uint mode = uint(clip_params.x + 0.5);\n"
"    if(mode == 1u) return world_y > clip_params.z;\n"
"    if(mode == 2u) return world_y < clip_params.z;\n"
"    return false;\n"
"}\n"
"static float shadow_factor(float4 light_space_pos, float3 normal, float3 light_dir, depth2d<float> shadow_map, sampler shadow_sampler, float base_bias, float texel_radius) {\n"
"    float w = max(abs(light_space_pos.w), 0.0001);\n"
"    float3 proj = (light_space_pos.xyz / w) * 0.5 + 0.5;\n"
"    if(proj.x < 0.0 || proj.x > 1.0 || proj.y < 0.0 || proj.y > 1.0 || proj.z < 0.0 || proj.z > 0.98) return 0.0;\n"
"    float slope_bias = base_bias + (1.0 - max(dot(normalize(normal), normalize(light_dir)), 0.0)) * base_bias * 2.0;\n"
"    float2 texel = texel_radius / float2(shadow_map.get_width(), shadow_map.get_height());\n"
"    float shadow = 0.0;\n"
"    for(int y = -1; y <= 1; y++) {\n"
"    for(int x = -1; x <= 1; x++) {\n"
"        float2 uv = clamp(proj.xy + float2(x, y) * texel, float2(0.0), float2(1.0));\n"
"        float closest_depth = shadow_map.sample(shadow_sampler, uv);\n"
"        shadow += (proj.z - slope_bias > closest_depth) ? 1.0 : 0.0;\n"
"    }}\n"
"    return shadow / 9.0;\n"
"}\n"
"fragment float4 terrain_fragment(TerrainVertexOut in [[stage_in]], constant TerrainUniforms &uniforms [[buffer(1)]], device const uchar *fog_buff [[buffer(2)]], device const uchar *water_buff [[buffer(3)]], texture2d_array<float> terrain_textures [[texture(0)]], texture2d<float> water_dudv_map [[texture(1)]], texture2d<float> water_normal_map [[texture(2)]], depth2d<float> shadow_map [[texture(3)]], sampler terrain_sampler [[sampler(0)]], sampler shadow_sampler [[sampler(1)]]) {\n"
"    if(clip_water_world_y(in.world_pos.y, uniforms.clip_params)) discard_fragment();\n"
"    float3 light_dir = normalize(float3(0.35, 0.85, 0.20));\n"
"    float diffuse = max(dot(normalize(in.normal), light_dir), 0.18);\n"
"    float3 ambient = float3(0.18, 0.20, 0.16);\n"
"    float3 color = terrain_material_color(in.material_idx);\n"
"    float fog_factor = 1.0;\n"
"    uint water_state = 0u;\n"
"    if(uniforms.chunk_size.x > 0u && uniforms.chunk_size.y > 0u) {\n"
"        float field_w = uniforms.tile_world_size.x * uniforms.tiles_per_chunk.x;\n"
"        float field_h = uniforms.tile_world_size.y * uniforms.tiles_per_chunk.y;\n"
"        int chunk_c = int(fabs(uniforms.map_pos.x - in.world_xz.x) / field_w);\n"
"        int chunk_r = int(fabs(uniforms.map_pos.y - in.world_xz.y) / field_h);\n"
"        chunk_c = clamp(chunk_c, 0, int(uniforms.chunk_size.x) - 1);\n"
"        chunk_r = clamp(chunk_r, 0, int(uniforms.chunk_size.y) - 1);\n"
"        float chunk_base_x = uniforms.map_pos.x - (chunk_c * field_w);\n"
"        float chunk_base_z = uniforms.map_pos.y + (chunk_r * field_h);\n"
"        int tile_c = int(fabs(chunk_base_x - in.world_xz.x) / uniforms.tile_world_size.x);\n"
"        int tile_r = int(fabs(chunk_base_z - in.world_xz.y) / uniforms.tile_world_size.y);\n"
"        tile_c = clamp(tile_c, 0, int(uniforms.tiles_per_chunk.x) - 1);\n"
"        tile_r = clamp(tile_r, 0, int(uniforms.tiles_per_chunk.y) - 1);\n"
"        uint tiles_per_chunk = uniforms.tiles_per_chunk.x * uniforms.tiles_per_chunk.y;\n"
"        uint fog_idx = uint(chunk_r) * (uniforms.chunk_size.x * tiles_per_chunk)\n"
"                     + uint(chunk_c) * tiles_per_chunk\n"
"                     + uint(tile_r) * uniforms.tiles_per_chunk.x\n"
"                     + uint(tile_c);\n"
"        if(uniforms.water_params.z > 0.5) {\n"
"            uint fog_state = fog_buff[fog_idx];\n"
"            fog_factor = terrain_fog_factor(fog_state);\n"
"        }\n"
"        if(uniforms.water_params.y > 0.5) {\n"
"            water_state = water_buff[fog_idx];\n"
"        }\n"
"    }\n"
"    if(uniforms.terrain_params.x > 0.5) {\n"
"        uint texture_count = uint(uniforms.terrain_params.x + 0.5);\n"
"        if(in.material_idx < texture_count) {\n"
"            float4 texel = terrain_textures.sample(terrain_sampler, float2(in.uv.x, 1.0 - in.uv.y), in.material_idx);\n"
"            color = texel.xyz;\n"
"        }\n"
"    }\n"
"    float3 lit = color * diffuse + ambient * color;\n"
"    if(water_state != 0u) {\n"
"        float2 tile_world = max(uniforms.tile_world_size, float2(1.0, 1.0));\n"
"        float2 water_uv = float2(in.world_xz.x / (tile_world.x * 12.0), in.world_xz.y / (tile_world.y * 12.0));\n"
"        float2 dudv_uv = water_uv + float2(uniforms.water_params.x * 0.08, -uniforms.water_params.x * 0.05);\n"
"        float2 dudv = float2(0.0, 0.0);\n"
"        float3 water_normal = float3(0.0, 1.0, 0.0);\n"
"        if(uniforms.water_params.w > 0.5) {\n"
"            dudv = water_dudv_map.sample(terrain_sampler, dudv_uv).rg * 2.0 - 1.0;\n"
"            float2 normal_uv = water_uv + dudv * 0.12 + float2(uniforms.water_params.x * 0.03, uniforms.water_params.x * 0.02);\n"
"            float3 sampled_normal = water_normal_map.sample(terrain_sampler, normal_uv).rgb * 2.0 - 1.0;\n"
"            water_normal = normalize(float3(sampled_normal.r, max(sampled_normal.b, 0.35), sampled_normal.g));\n"
"        } else {\n"
"            float wave = 0.5 + 0.5 * sin((in.world_xz.x * 0.055) + uniforms.water_params.x * 4.0 + (in.world_xz.y * 0.040));\n"
"            float ripple = 0.5 + 0.5 * sin((in.world_xz.x * 0.035) - uniforms.water_params.x * 2.5 + (in.world_xz.y * 0.060));\n"
"            dudv = float2(wave - 0.5, ripple - 0.5);\n"
"            water_normal = normalize(float3(dudv.x * 0.8, 1.0, dudv.y * 0.8));\n"
"        }\n"
"        float3 view_dir = normalize(uniforms.view_pos.xyz - in.world_pos);\n"
"        float fresnel = pow(clamp(1.0 - max(dot(view_dir, water_normal), 0.0), 0.0, 1.0), 2.0);\n"
"        float specular = pow(max(dot(reflect(-light_dir, water_normal), view_dir), 0.0), 24.0);\n"
"        float wave_mix = clamp(0.5 + dudv.x * 0.5, 0.0, 1.0);\n"
"        float ripple_mix = clamp(0.5 + dudv.y * 0.5, 0.0, 1.0);\n"
"        float3 deep = float3(0.03, 0.17, 0.30);\n"
"        float3 shallow = float3(0.07, 0.34, 0.53);\n"
"        float3 reflect_tint = float3(0.26, 0.46, 0.62);\n"
"        float3 foam = float3(0.62, 0.78, 0.88);\n"
"        lit = mix(deep, shallow, wave_mix);\n"
"        lit = mix(lit, reflect_tint, fresnel * 0.55);\n"
"        lit += foam * (specular * (0.25 + ripple_mix * 0.25));\n"
"    }\n"
"    if(uniforms.shadow_params.x > 0.5) {\n"
"        float shadow = shadow_factor(in.light_space_pos, in.normal, light_dir, shadow_map, shadow_sampler, uniforms.shadow_params.y, uniforms.shadow_params.w);\n"
"        lit *= mix(1.0, uniforms.shadow_params.z, shadow);\n"
"    }\n"
"    return float4(lit * fog_factor, 1.0);\n"
"}\n";

static const char *s_static_mesh_shader_source =
"#include <metal_stdlib>\n"
"using namespace metal;\n"
"#define METAL_MAX_MATERIALS 16\n"
"struct StaticMeshVertexIn {\n"
"    float3 position [[attribute(0)]];\n"
"    float2 uv [[attribute(1)]];\n"
"    float3 normal [[attribute(2)]];\n"
"    int material_idx [[attribute(3)]];\n"
"};\n"
"struct StaticMeshUniforms {\n"
"    float4x4 model;\n"
"    float4x4 view;\n"
"    float4x4 proj;\n"
"    float4x4 light_space_transform;\n"
"    float4 material_diffuse[METAL_MAX_MATERIALS];\n"
"    float4 effect_params;\n"
"    float4 shadow_params;\n"
"    float4 clip_params;\n"
"};\n"
"struct StaticMeshVertexOut {\n"
"    float4 position [[position]];\n"
"    float3 normal;\n"
"    float2 uv;\n"
"    uint material_idx;\n"
"    float3 world_pos;\n"
"    float4 light_space_pos;\n"
"};\n"
"vertex StaticMeshVertexOut static_mesh_vertex(StaticMeshVertexIn in [[stage_in]], constant StaticMeshUniforms &uniforms [[buffer(1)]]) {\n"
"    StaticMeshVertexOut out;\n"
"    float4 world_pos = uniforms.model * float4(in.position, 1.0);\n"
"    out.position = uniforms.proj * uniforms.view * world_pos;\n"
"    out.normal = normalize((uniforms.model * float4(in.normal, 0.0)).xyz);\n"
"    out.uv = in.uv;\n"
"    out.material_idx = (uint)max(in.material_idx, 0);\n"
"    out.world_pos = world_pos.xyz;\n"
"    out.light_space_pos = uniforms.light_space_transform * float4(world_pos.xyz, 1.0);\n"
"    return out;\n"
"}\n"
"static float mesh_shadow_factor(float4 light_space_pos, float3 normal, float3 light_dir, depth2d<float> shadow_map, sampler shadow_sampler, float base_bias, float texel_radius) {\n"
"    float w = max(abs(light_space_pos.w), 0.0001);\n"
"    float3 proj = (light_space_pos.xyz / w) * 0.5 + 0.5;\n"
"    if(proj.x < 0.0 || proj.x > 1.0 || proj.y < 0.0 || proj.y > 1.0 || proj.z < 0.0 || proj.z > 0.98) return 0.0;\n"
"    float slope_bias = base_bias + (1.0 - max(dot(normalize(normal), normalize(light_dir)), 0.0)) * base_bias * 2.0;\n"
"    float2 texel = texel_radius / float2(shadow_map.get_width(), shadow_map.get_height());\n"
"    float shadow = 0.0;\n"
"    for(int y = -1; y <= 1; y++) {\n"
"    for(int x = -1; x <= 1; x++) {\n"
"        float2 uv = clamp(proj.xy + float2(x, y) * texel, float2(0.0), float2(1.0));\n"
"        float closest_depth = shadow_map.sample(shadow_sampler, uv);\n"
"        shadow += (proj.z - slope_bias > closest_depth) ? 1.0 : 0.0;\n"
"    }}\n"
"    return shadow / 9.0;\n"
"}\n"
"static bool clip_water_world_y(float world_y, float4 clip_params) {\n"
"    uint mode = uint(clip_params.x + 0.5);\n"
"    if(mode == 1u) return world_y > clip_params.z;\n"
"    if(mode == 2u) return world_y < clip_params.z;\n"
"    return false;\n"
"}\n"
"fragment float4 static_mesh_fragment(StaticMeshVertexOut in [[stage_in]], constant StaticMeshUniforms &uniforms [[buffer(1)]], texture2d_array<float> material_textures [[texture(0)]], depth2d<float> shadow_map [[texture(1)]], sampler material_sampler [[sampler(0)]], sampler shadow_sampler [[sampler(1)]]) {\n"
"    if(clip_water_world_y(in.world_pos.y, uniforms.clip_params)) discard_fragment();\n"
"    float3 light_dir = normalize(float3(0.35, 0.85, 0.20));\n"
"    float diffuse = max(dot(normalize(in.normal), light_dir), 0.18);\n"
"    uint diffuse_idx = min(in.material_idx, uint(METAL_MAX_MATERIALS - 1));\n"
"    float4 base_rgba = uniforms.material_diffuse[diffuse_idx];\n"
"    if(uniforms.effect_params.x > 0.5 && in.material_idx < uint(uniforms.effect_params.x + 0.5)) {\n"
"        float4 texel = material_textures.sample(material_sampler, float2(in.uv.x, 1.0 - in.uv.y), in.material_idx);\n"
"        base_rgba *= texel;\n"
"        base_rgba.xyz *= base_rgba.w;\n"
"        if(base_rgba.a <= 0.5) discard_fragment();\n"
"    }\n"
"    float3 base = base_rgba.xyz;\n"
"    float3 ambient = base * 0.18;\n"
"    float3 lit = base * diffuse + ambient;\n"
"    if(uniforms.shadow_params.x > 0.5) {\n"
"        float shadow = mesh_shadow_factor(in.light_space_pos, in.normal, light_dir, shadow_map, shadow_sampler, uniforms.shadow_params.y, uniforms.shadow_params.w);\n"
"        lit *= mix(1.0, uniforms.shadow_params.z, shadow);\n"
"    }\n"
"    return float4(lit, base_rgba.w);\n"
"}\n";

static const char *s_shadow_depth_shader_source =
"#include <metal_stdlib>\n"
"using namespace metal;\n"
"struct ShadowVertexIn {\n"
"    float3 position [[attribute(0)]];\n"
"};\n"
"struct ShadowUniforms {\n"
"    float4x4 model;\n"
"    float4x4 view;\n"
"    float4x4 proj;\n"
"};\n"
"struct ShadowVertexOut {\n"
"    float4 position [[position]];\n"
"};\n"
"vertex ShadowVertexOut shadow_depth_vertex(ShadowVertexIn in [[stage_in]], constant ShadowUniforms &uniforms [[buffer(1)]]) {\n"
"    ShadowVertexOut out;\n"
"    out.position = uniforms.proj * uniforms.view * uniforms.model * float4(in.position, 1.0);\n"
"    return out;\n"
"}\n";

static const char *s_water_surface_shader_source =
"#include <metal_stdlib>\n"
"using namespace metal;\n"
"struct WaterVertexIn {\n"
"    float3 position [[attribute(0)]];\n"
"};\n"
"struct WaterUniforms {\n"
"    float4x4 model;\n"
"    float4x4 view;\n"
"    float4x4 proj;\n"
"    float4 view_pos;\n"
"    float2 map_pos;\n"
"    float2 tile_world_size;\n"
"    uint2 chunk_size;\n"
"    uint2 tiles_per_chunk;\n"
"    float4 water_params;\n"
"    float4 water_texture_params;\n"
"};\n"
"struct WaterVertexOut {\n"
"    float4 position [[position]];\n"
"    float3 world_pos;\n"
"    float2 world_xz;\n"
"};\n"
"vertex WaterVertexOut water_surface_vertex(WaterVertexIn in [[stage_in]], constant WaterUniforms &uniforms [[buffer(1)]]) {\n"
"    WaterVertexOut out;\n"
"    float4 world_pos = uniforms.model * float4(in.position, 1.0);\n"
"    out.position = uniforms.proj * uniforms.view * world_pos;\n"
"    out.world_pos = world_pos.xyz;\n"
"    out.world_xz = world_pos.xz;\n"
"    return out;\n"
"}\n"
"static float terrain_fog_factor(uint state) {\n"
"    if(state == 0u) return 0.05;\n"
"    if(state == 1u) return 0.45;\n"
"    return 1.0;\n"
"}\n"
"static uint map_tile_index(float2 world_xz, constant WaterUniforms &uniforms) {\n"
"    float field_w = uniforms.tile_world_size.x * uniforms.tiles_per_chunk.x;\n"
"    float field_h = uniforms.tile_world_size.y * uniforms.tiles_per_chunk.y;\n"
"    int chunk_c = int(fabs(uniforms.map_pos.x - world_xz.x) / field_w);\n"
"    int chunk_r = int(fabs(uniforms.map_pos.y - world_xz.y) / field_h);\n"
"    chunk_c = clamp(chunk_c, 0, int(uniforms.chunk_size.x) - 1);\n"
"    chunk_r = clamp(chunk_r, 0, int(uniforms.chunk_size.y) - 1);\n"
"    float chunk_base_x = uniforms.map_pos.x - (chunk_c * field_w);\n"
"    float chunk_base_z = uniforms.map_pos.y + (chunk_r * field_h);\n"
"    int tile_c = int(fabs(chunk_base_x - world_xz.x) / uniforms.tile_world_size.x);\n"
"    int tile_r = int(fabs(chunk_base_z - world_xz.y) / uniforms.tile_world_size.y);\n"
"    tile_c = clamp(tile_c, 0, int(uniforms.tiles_per_chunk.x) - 1);\n"
"    tile_r = clamp(tile_r, 0, int(uniforms.tiles_per_chunk.y) - 1);\n"
"    uint tiles_per_chunk = uniforms.tiles_per_chunk.x * uniforms.tiles_per_chunk.y;\n"
"    return uint(chunk_r) * (uniforms.chunk_size.x * tiles_per_chunk)\n"
"         + uint(chunk_c) * tiles_per_chunk\n"
"         + uint(tile_r) * uniforms.tiles_per_chunk.x\n"
"         + uint(tile_c);\n"
"}\n"
"fragment float4 water_surface_fragment(WaterVertexOut in [[stage_in]], constant WaterUniforms &uniforms [[buffer(1)]], device const uchar *fog_buff [[buffer(2)]], device const uchar *water_buff [[buffer(3)]], texture2d<float> dudv_map [[texture(0)]], texture2d<float> normal_map [[texture(1)]], texture2d<float> reflect_tex [[texture(2)]], texture2d<float> refract_tex [[texture(3)]], sampler water_sampler [[sampler(0)]]) {\n"
"    if(uniforms.water_params.y < 0.5 || uniforms.chunk_size.x == 0u || uniforms.chunk_size.y == 0u) discard_fragment();\n"
"    uint idx = map_tile_index(in.world_xz, uniforms);\n"
"    if(water_buff[idx] == 0u) discard_fragment();\n"
"    float2 screen_uv = clamp(in.position.xy / max(uniforms.water_texture_params.xy, float2(1.0, 1.0)), float2(0.001, 0.001), float2(0.999, 0.999));\n"
"    float fog_factor = 1.0;\n"
"    if(uniforms.water_params.z > 0.5) fog_factor = terrain_fog_factor(fog_buff[idx]);\n"
"    float2 tile_world = max(uniforms.tile_world_size, float2(1.0, 1.0));\n"
"    float2 uv = float2(in.world_xz.x / (tile_world.x * 12.0), in.world_xz.y / (tile_world.y * 12.0));\n"
"    float2 dudv_uv = uv + float2(uniforms.water_params.x * 0.08, -uniforms.water_params.x * 0.05);\n"
"    float2 dudv = float2(0.0, 0.0);\n"
"    float3 water_normal = float3(0.0, 1.0, 0.0);\n"
"    if(uniforms.water_params.w > 0.5) {\n"
"        dudv = dudv_map.sample(water_sampler, dudv_uv).rg * 2.0 - 1.0;\n"
"        float2 normal_uv = uv + dudv * 0.12 + float2(uniforms.water_params.x * 0.03, uniforms.water_params.x * 0.02);\n"
"        float3 sampled_normal = normal_map.sample(water_sampler, normal_uv).rgb * 2.0 - 1.0;\n"
"        water_normal = normalize(float3(sampled_normal.r, max(sampled_normal.b, 0.35), sampled_normal.g));\n"
"    }\n"
"    float2 distortion = dudv * 0.025;\n"
"    float2 refract_uv = clamp(screen_uv + distortion, float2(0.001, 0.001), float2(0.999, 0.999));\n"
"    float2 reflect_uv = clamp(float2(screen_uv.x, 1.0 - screen_uv.y) + distortion * 0.65, float2(0.001, 0.001), float2(0.999, 0.999));\n"
"    float scene_mix = clamp(uniforms.water_texture_params.z + uniforms.water_texture_params.w, 0.0, 1.0);\n"
"    float3 refract_color = float3(0.04, 0.18, 0.28);\n"
"    float3 reflect_color = float3(0.35, 0.54, 0.68);\n"
"    float water_depth = 1.0;\n"
"    if(scene_mix > 0.0) {\n"
"        refract_color = refract_tex.sample(water_sampler, refract_uv).rgb;\n"
"        reflect_color = reflect_tex.sample(water_sampler, reflect_uv).rgb;\n"
"    }\n"
"    float3 light_dir = normalize(float3(0.35, 0.85, 0.20));\n"
"    float3 view_dir = normalize(uniforms.view_pos.xyz - in.world_pos);\n"
"    float fresnel = pow(clamp(1.0 - max(dot(view_dir, water_normal), 0.0), 0.0, 1.0), 2.0);\n"
"    float specular = pow(max(dot(reflect(-light_dir, water_normal), view_dir), 0.0), 32.0);\n"
"    float wave = clamp(0.5 + dudv.x * 0.5, 0.0, 1.0);\n"
"    float3 deep = float3(0.02, 0.12, 0.24);\n"
"    float3 shallow = float3(0.05, 0.30, 0.46);\n"
"    float3 reflect_tint = float3(0.35, 0.54, 0.68);\n"
"    float3 color = mix(deep, shallow, wave);\n"
"    float3 scene_color = mix(refract_color, reflect_color, fresnel * uniforms.water_texture_params.z);\n"
"    color = mix(color, scene_color, 0.55 * scene_mix);\n"
"    color = mix(color, reflect_tint, fresnel * 0.70);\n"
"    color = mix(color, shallow, (1.0 - water_depth) * 0.15 * uniforms.water_texture_params.w);\n"
"    color += float3(0.70, 0.86, 0.95) * specular * 0.45;\n"
"    float alpha = 0.42 + fresnel * 0.25;\n"
"    return float4(color * fog_factor, alpha * fog_factor);\n"
"}\n";

static const char *s_world_color_shader_source =
"#include <metal_stdlib>\n"
"using namespace metal;\n"
"struct WorldColorVertexIn {\n"
"    float3 position [[attribute(0)]];\n"
"    float4 color [[attribute(1)]];\n"
"};\n"
"struct WorldColorUniforms {\n"
"    float4x4 view;\n"
"    float4x4 proj;\n"
"};\n"
"struct WorldColorVertexOut {\n"
"    float4 position [[position]];\n"
"    float4 color;\n"
"};\n"
"vertex WorldColorVertexOut world_color_vertex(WorldColorVertexIn in [[stage_in]], constant WorldColorUniforms &uniforms [[buffer(1)]]) {\n"
"    WorldColorVertexOut out;\n"
"    out.position = uniforms.proj * uniforms.view * float4(in.position, 1.0);\n"
"    out.color = in.color;\n"
"    return out;\n"
"}\n"
"fragment float4 world_color_fragment(WorldColorVertexOut in [[stage_in]]) {\n"
"    return in.color;\n"
"}\n";

struct metal_ui_uniforms{
    float view_size[2];
    float _padding[2];
};

struct metal_terrain_uniforms{
    matrix_float4x4 model;
    matrix_float4x4 view;
    matrix_float4x4 proj;
    vector_float4   view_pos;
    vector_float2   map_pos;
    vector_float2   tile_world_size;
    vector_uint2    chunk_size;
    vector_uint2    tiles_per_chunk;
    vector_float4   terrain_params;
    vector_float4   water_params;
    matrix_float4x4 light_space_transform;
    vector_float4   shadow_params;
    vector_float4   clip_params;
};

struct metal_static_mesh_uniforms{
    matrix_float4x4 model;
    matrix_float4x4 view;
    matrix_float4x4 proj;
    matrix_float4x4 light_space_transform;
    vector_float4 material_diffuse[MAX_MATERIALS];
    vector_float4 effect_params;
    vector_float4 shadow_params;
    vector_float4 clip_params;
};

struct metal_world_color_uniforms{
    matrix_float4x4 view;
    matrix_float4x4 proj;
};

struct metal_shadow_uniforms{
    matrix_float4x4 model;
    matrix_float4x4 view;
    matrix_float4x4 proj;
};

struct metal_water_surface_uniforms{
    matrix_float4x4 model;
    matrix_float4x4 view;
    matrix_float4x4 proj;
    vector_float4   view_pos;
    vector_float2   map_pos;
    vector_float2   tile_world_size;
    vector_uint2    chunk_size;
    vector_uint2    tiles_per_chunk;
    vector_float4   water_params;
    vector_float4   water_texture_params;
};

static bool append_skinned_anim_mesh(const struct render_private *priv,
                                     uint32_t uid,
                                     const mat4x4_t *model,
                                     struct vertex *dst,
                                     size_t *dst_idx);
static void render_static_mesh_draw(const struct render_private *priv, const mat4x4_t *model, bool translucent);
static void render_skinned_mesh_draw(const struct render_private *priv, const mat4x4_t *model, bool translucent);
static void render_batched_stat_entities(const vec_rstat_t *ents);
static void render_batched_anim_entities(const vec_ranim_t *ents);

static bool render_wait_cmd(struct render_sync_state *rstate)
{
    SDL_LockMutex(rstate->sq_lock);
    while(!rstate->start && !rstate->quit)
        SDL_CondWait(rstate->sq_cond, rstate->sq_lock);

    if(rstate->quit) {
        rstate->quit = false;
        SDL_UnlockMutex(rstate->sq_lock);
        return true;
    }

    assert(rstate->start == true);
    rstate->start = false;
    SDL_UnlockMutex(rstate->sq_lock);
    return false;
}

static void render_signal_done(struct render_sync_state *rstate, enum render_status status)
{
    SDL_LockMutex(rstate->done_lock);
    rstate->status = status;
    SDL_CondSignal(rstate->done_cond);
    SDL_UnlockMutex(rstate->done_lock);
}

static void render_dispatch_cmd(struct rcmd cmd)
{
    switch(cmd.nargs) {
    case 0:  ((void(*)(void))cmd.func)(); break;
    case 1:  ((void(*)(void*))cmd.func)(cmd.args[0]); break;
    case 2:  ((void(*)(void*, void*))cmd.func)(cmd.args[0], cmd.args[1]); break;
    case 3:  ((void(*)(void*, void*, void*))cmd.func)(cmd.args[0], cmd.args[1], cmd.args[2]); break;
    case 4:  ((void(*)(void*, void*, void*, void*))cmd.func)(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3]); break;
    case 5:  ((void(*)(void*, void*, void*, void*, void*))cmd.func)(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4]); break;
    case 6:  ((void(*)(void*, void*, void*, void*, void*, void*))cmd.func)(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4], cmd.args[5]); break;
    case 7:  ((void(*)(void*, void*, void*, void*, void*, void*, void*))cmd.func)(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4], cmd.args[5], cmd.args[6]); break;
    case 8:  ((void(*)(void*, void*, void*, void*, void*, void*, void*, void*))cmd.func)(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4], cmd.args[5], cmd.args[6], cmd.args[7]); break;
    case 9:  ((void(*)(void*, void*, void*, void*, void*, void*, void*, void*, void*))cmd.func)(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4], cmd.args[5], cmd.args[6], cmd.args[7], cmd.args[8]); break;
    case 10: ((void(*)(void*, void*, void*, void*, void*, void*, void*, void*, void*, void*))cmd.func)(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4], cmd.args[5], cmd.args[6], cmd.args[7], cmd.args[8], cmd.args[9]); break;
    default: assert(0);
    }
}

static void update_drawable_size(void)
{
    int width = 0, height = 0;
    SDL_Metal_GetDrawableSize(s_window, &width, &height);
    s_layer.drawableSize = CGSizeMake(width, height);
}

static void release_ui_resources(void)
{
    s_ui_font_texture = nil;
    s_ui_sampler = nil;
    s_ui_pipeline = nil;
    s_ui_msaa_pipeline = nil;
}

static void release_scene_resources(void)
{
    s_minimap_texture = nil;
    s_frame_msaa_texture = nil;
    s_frame_depth_texture = nil;
    s_shadow_depth_texture = nil;
    s_water_reflection_texture = nil;
    s_water_reflection_depth_texture = nil;
    s_water_refraction_texture = nil;
    s_water_refraction_depth_texture = nil;
    s_terrain_texture_array = nil;
    s_water_dudv_texture = nil;
    s_water_normal_texture = nil;
    s_fog_buffer = nil;
    s_water_buffer = nil;
    s_scene_sampler = nil;
    s_shadow_sampler = nil;
    s_depth_write_state = nil;
    s_depth_read_state = nil;
    s_terrain_pipeline = nil;
    s_terrain_msaa_pipeline = nil;
    s_terrain_depth_pipeline = nil;
    s_terrain_depth_msaa_pipeline = nil;
    s_static_mesh_pipeline = nil;
    s_static_mesh_msaa_pipeline = nil;
    s_static_mesh_blend_pipeline = nil;
    s_static_mesh_blend_msaa_pipeline = nil;
    s_static_mesh_depth_pipeline = nil;
    s_static_mesh_depth_msaa_pipeline = nil;
    s_static_mesh_blend_depth_pipeline = nil;
    s_static_mesh_blend_depth_msaa_pipeline = nil;
    s_world_color_pipeline = nil;
    s_world_color_msaa_pipeline = nil;
    s_shadow_terrain_pipeline = nil;
    s_shadow_mesh_pipeline = nil;
    s_water_surface_pipeline = nil;
    s_water_surface_msaa_pipeline = nil;
    s_terrain_texture_count = 0;
    s_shadow_map_valid = false;
}

static void reset_frame_state(void)
{
    s_frame_encoder = nil;
    s_frame_command_buffer = nil;
    s_frame_drawable = nil;
    s_frame_sample_count = 0;
}

static bool reserve_inflight_frame(void)
{
    if(s_frame_inflight_reserved)
        return true;
    if(!s_inflight_semaphore)
        s_inflight_semaphore = dispatch_semaphore_create(3);
    if(!s_inflight_semaphore)
        return false;
    dispatch_semaphore_wait(s_inflight_semaphore, DISPATCH_TIME_FOREVER);
    s_frame_inflight_reserved = true;
    return true;
}

static void release_inflight_frame(void)
{
    if(!s_frame_inflight_reserved || !s_inflight_semaphore)
        return;
    dispatch_semaphore_signal(s_inflight_semaphore);
    s_frame_inflight_reserved = false;
}

static matrix_float4x4 matrix_from_pf_mat4(const mat4x4_t *in)
{
    return (matrix_float4x4){
        .columns[0] = {in->cols[0][0], in->cols[0][1], in->cols[0][2], in->cols[0][3]},
        .columns[1] = {in->cols[1][0], in->cols[1][1], in->cols[1][2], in->cols[1][3]},
        .columns[2] = {in->cols[2][0], in->cols[2][1], in->cols[2][2], in->cols[2][3]},
        .columns[3] = {in->cols[3][0], in->cols[3][1], in->cols[3][2], in->cols[3][3]},
    };
}

static void make_shadow_light_space(vec3_t light_pos, vec3_t cam_pos, vec3_t cam_dir,
                                    matrix_float4x4 *out_view, matrix_float4x4 *out_proj,
                                    matrix_float4x4 *out_light_space)
{
    float t = cam_pos.y / cam_dir.y;
    vec3_t cam_ray_ground_isec = {
        cam_pos.x - t * cam_dir.x,
        0.0f,
        cam_pos.z - t * cam_dir.z
    };

    vec3_t light_dir = light_pos;
    PFM_Vec3_Normal(&light_dir, &light_dir);
    PFM_Vec3_Scale(&light_dir, -1.0f, &light_dir);

    vec3_t right = {-1.0f, 0.0f, 0.0f};
    vec3_t up;
    PFM_Vec3_Cross(&light_dir, &right, &up);

    t = fabsf((cam_pos.y + METAL_LIGHT_EXTRA_HEIGHT) / light_dir.y);
    vec3_t light_origin, delta;
    PFM_Vec3_Scale(&light_dir, -t, &delta);
    PFM_Vec3_Add(&cam_ray_ground_isec, &delta, &light_origin);

    vec3_t target;
    PFM_Vec3_Add(&light_origin, &light_dir, &target);

    mat4x4_t light_view;
    mat4x4_t light_proj;
    PFM_Mat4x4_MakeLookAt(&light_origin, &target, &up, &light_view);
    PFM_Mat4x4_MakeOrthographic(-CONFIG_SHADOW_FOV, CONFIG_SHADOW_FOV,
        CONFIG_SHADOW_FOV, -CONFIG_SHADOW_FOV, 0.1f, CONFIG_SHADOW_DRAWDIST, &light_proj);

    mat4x4_t light_space;
    PFM_Mat4x4_Mult4x4(&light_proj, &light_view, &light_space);
    *out_view = matrix_from_pf_mat4(&light_view);
    *out_proj = matrix_from_pf_mat4(&light_proj);
    *out_light_space = matrix_from_pf_mat4(&light_space);
}

static void present_clear(void)
{
    update_drawable_size();
    if(!reserve_inflight_frame())
        return;

    id<CAMetalDrawable> drawable = [s_layer nextDrawable];
    if(!drawable) {
        release_inflight_frame();
        return;
    }

    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    pass.colorAttachments[0].texture = drawable.texture;
    pass.colorAttachments[0].loadAction = MTLLoadActionClear;
    pass.colorAttachments[0].storeAction = MTLStoreActionStore;
    pass.colorAttachments[0].clearColor = MTLClearColorMake(0.0, 0.0, 0.0, 1.0);

    id<MTLCommandBuffer> command_buffer = [s_queue commandBuffer];
    if(!command_buffer) {
        release_inflight_frame();
        return;
    }
    if(s_frame_inflight_reserved && s_inflight_semaphore) {
        dispatch_semaphore_t inflight = s_inflight_semaphore;
        [command_buffer addCompletedHandler:^(id<MTLCommandBuffer> buffer){
            (void)buffer;
            dispatch_semaphore_signal(inflight);
        }];
        s_frame_inflight_reserved = false;
    }
    id<MTLRenderCommandEncoder> encoder = [command_buffer renderCommandEncoderWithDescriptor:pass];
    if(encoder)
        [encoder endEncoding];
    [command_buffer presentDrawable:drawable];
    [command_buffer commit];
}

static NSUInteger desired_frame_sample_count(void)
{
    if(!s_device)
        return 1;
    return [s_device supportsTextureSampleCount:METAL_MSAA_SAMPLES] ? METAL_MSAA_SAMPLES : 1;
}

static bool frame_uses_msaa(void)
{
    return s_frame_sample_count > 1;
}

static bool ensure_frame_msaa_texture(NSUInteger sample_count)
{
    if(sample_count <= 1)
        return false;

    NSUInteger width = (NSUInteger)s_layer.drawableSize.width;
    NSUInteger height = (NSUInteger)s_layer.drawableSize.height;
    if(!width || !height)
        return false;

    if(s_frame_msaa_texture
    && s_frame_msaa_texture.width == width
    && s_frame_msaa_texture.height == height
    && s_frame_msaa_texture.sampleCount == sample_count
    && s_frame_msaa_texture.pixelFormat == s_layer.pixelFormat) {
        return true;
    }

    s_frame_msaa_texture = nil;

    MTLTextureDescriptor *desc = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:s_layer.pixelFormat
                                                                                     width:width
                                                                                    height:height
                                                                                 mipmapped:NO];
    desc.textureType = MTLTextureType2DMultisample;
    desc.sampleCount = sample_count;
    desc.storageMode = MTLStorageModePrivate;
    desc.usage = MTLTextureUsageRenderTarget;
    s_frame_msaa_texture = [s_device newTextureWithDescriptor:desc];
    return s_frame_msaa_texture != nil;
}

static bool ensure_frame_depth_texture(NSUInteger sample_count)
{
    NSUInteger width = (NSUInteger)s_layer.drawableSize.width;
    NSUInteger height = (NSUInteger)s_layer.drawableSize.height;
    if(!width || !height)
        return false;

    if(s_frame_depth_texture
    && s_frame_depth_texture.width == width
    && s_frame_depth_texture.height == height
    && s_frame_depth_texture.sampleCount == sample_count
    && s_frame_depth_texture.pixelFormat == MTLPixelFormatDepth32Float) {
        return true;
    }

    s_frame_depth_texture = nil;

    MTLTextureDescriptor *desc = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatDepth32Float
                                                                                     width:width
                                                                                    height:height
                                                                                 mipmapped:NO];
    desc.textureType = sample_count > 1 ? MTLTextureType2DMultisample : MTLTextureType2D;
    desc.sampleCount = sample_count;
    desc.storageMode = MTLStorageModePrivate;
    desc.usage = MTLTextureUsageRenderTarget;
    s_frame_depth_texture = [s_device newTextureWithDescriptor:desc];
    return s_frame_depth_texture != nil;
}

static bool frame_has_depth(void)
{
    return s_frame_encoder && s_frame_depth_texture;
}

static id<MTLDepthStencilState> ensure_depth_state(bool write)
{
    id<MTLDepthStencilState> __strong *slot = write ? &s_depth_write_state : &s_depth_read_state;
    if(*slot)
        return *slot;

    MTLDepthStencilDescriptor *desc = [[MTLDepthStencilDescriptor alloc] init];
    desc.depthCompareFunction = MTLCompareFunctionLessEqual;
    desc.depthWriteEnabled = write ? YES : NO;
    *slot = [s_device newDepthStencilStateWithDescriptor:desc];
    return *slot;
}

static bool ensure_shadow_sampler(void)
{
    if(s_shadow_sampler)
        return true;

    MTLSamplerDescriptor *desc = [[MTLSamplerDescriptor alloc] init];
    desc.minFilter = MTLSamplerMinMagFilterNearest;
    desc.magFilter = MTLSamplerMinMagFilterNearest;
    desc.sAddressMode = MTLSamplerAddressModeClampToEdge;
    desc.tAddressMode = MTLSamplerAddressModeClampToEdge;
    s_shadow_sampler = [s_device newSamplerStateWithDescriptor:desc];
    return s_shadow_sampler != nil;
}

static bool ensure_shadow_depth_texture(void)
{
    if(s_shadow_depth_texture
    && s_shadow_depth_texture.width == CONFIG_SHADOW_MAP_RES
    && s_shadow_depth_texture.height == CONFIG_SHADOW_MAP_RES
    && s_shadow_depth_texture.pixelFormat == MTLPixelFormatDepth32Float) {
        return true;
    }

    s_shadow_depth_texture = nil;

    MTLTextureDescriptor *desc = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatDepth32Float
                                                                                     width:CONFIG_SHADOW_MAP_RES
                                                                                    height:CONFIG_SHADOW_MAP_RES
                                                                                 mipmapped:NO];
    desc.storageMode = MTLStorageModePrivate;
    desc.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
    s_shadow_depth_texture = [s_device newTextureWithDescriptor:desc];
    return s_shadow_depth_texture != nil;
}

static id<MTLRenderPipelineState> build_ui_pipeline(NSUInteger sample_count)
{
    NSError *error = nil;
    NSString *source = [NSString stringWithUTF8String:s_ui_shader_source];
    id<MTLLibrary> library = [s_device newLibraryWithSource:source options:nil error:&error];
    if(!library) {
        fprintf(stderr, "Metal UI shader compile failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    id<MTLFunction> vertex = [library newFunctionWithName:@"ui_vertex"];
    id<MTLFunction> fragment = [library newFunctionWithName:@"ui_fragment"];
    if(!vertex || !fragment) {
        fprintf(stderr, "Metal UI shader entrypoint lookup failed.\n");
        return nil;
    }

    MTLVertexDescriptor *vertex_desc = [MTLVertexDescriptor vertexDescriptor];
    vertex_desc.attributes[0].format = MTLVertexFormatFloat2;
    vertex_desc.attributes[0].offset = offsetof(struct ui_vert, screen_pos);
    vertex_desc.attributes[0].bufferIndex = 0;
    vertex_desc.attributes[1].format = MTLVertexFormatFloat2;
    vertex_desc.attributes[1].offset = offsetof(struct ui_vert, uv);
    vertex_desc.attributes[1].bufferIndex = 0;
    vertex_desc.attributes[2].format = MTLVertexFormatUChar4Normalized;
    vertex_desc.attributes[2].offset = offsetof(struct ui_vert, color);
    vertex_desc.attributes[2].bufferIndex = 0;
    vertex_desc.layouts[0].stride = sizeof(struct ui_vert);
    vertex_desc.layouts[0].stepFunction = MTLVertexStepFunctionPerVertex;

    MTLRenderPipelineDescriptor *pipeline_desc = [[MTLRenderPipelineDescriptor alloc] init];
    pipeline_desc.vertexFunction = vertex;
    pipeline_desc.fragmentFunction = fragment;
    pipeline_desc.vertexDescriptor = vertex_desc;
    pipeline_desc.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
    pipeline_desc.rasterSampleCount = sample_count;
    pipeline_desc.colorAttachments[0].blendingEnabled = YES;
    pipeline_desc.colorAttachments[0].rgbBlendOperation = MTLBlendOperationAdd;
    pipeline_desc.colorAttachments[0].alphaBlendOperation = MTLBlendOperationAdd;
    pipeline_desc.colorAttachments[0].sourceRGBBlendFactor = MTLBlendFactorSourceAlpha;
    pipeline_desc.colorAttachments[0].sourceAlphaBlendFactor = MTLBlendFactorSourceAlpha;
    pipeline_desc.colorAttachments[0].destinationRGBBlendFactor = MTLBlendFactorOneMinusSourceAlpha;
    pipeline_desc.colorAttachments[0].destinationAlphaBlendFactor = MTLBlendFactorOneMinusSourceAlpha;

    id<MTLRenderPipelineState> pipeline = [s_device newRenderPipelineStateWithDescriptor:pipeline_desc error:&error];
    if(!pipeline) {
        fprintf(stderr, "Metal UI pipeline creation failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    MTLSamplerDescriptor *sampler_desc = [[MTLSamplerDescriptor alloc] init];
    sampler_desc.minFilter = MTLSamplerMinMagFilterLinear;
    sampler_desc.magFilter = MTLSamplerMinMagFilterLinear;
    sampler_desc.sAddressMode = MTLSamplerAddressModeClampToEdge;
    sampler_desc.tAddressMode = MTLSamplerAddressModeClampToEdge;
    s_ui_sampler = [s_device newSamplerStateWithDescriptor:sampler_desc];
    if(!s_ui_sampler) {
        fprintf(stderr, "Metal UI sampler creation failed.\n");
        release_ui_resources();
        return nil;
    }

    return pipeline;
}

static id<MTLRenderPipelineState> ensure_ui_pipeline(bool multisampled)
{
    id<MTLRenderPipelineState> __strong *slot = multisampled ? &s_ui_msaa_pipeline : &s_ui_pipeline;
    if(*slot && s_ui_sampler)
        return *slot;
    *slot = build_ui_pipeline(multisampled ? METAL_MSAA_SAMPLES : 1);
    return *slot;
}

static id<MTLRenderPipelineState> build_terrain_pipeline(NSUInteger sample_count, bool depth_enabled)
{
    NSError *error = nil;
    NSString *source = [NSString stringWithUTF8String:s_terrain_shader_source];
    id<MTLLibrary> library = [s_device newLibraryWithSource:source options:nil error:&error];
    if(!library) {
        fprintf(stderr, "Metal terrain shader compile failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    id<MTLFunction> vertex = [library newFunctionWithName:@"terrain_vertex"];
    id<MTLFunction> fragment = [library newFunctionWithName:@"terrain_fragment"];
    if(!vertex || !fragment) {
        fprintf(stderr, "Metal terrain shader entrypoint lookup failed.\n");
        return nil;
    }

    MTLVertexDescriptor *vertex_desc = [MTLVertexDescriptor vertexDescriptor];
    vertex_desc.attributes[0].format = MTLVertexFormatFloat3;
    vertex_desc.attributes[0].offset = offsetof(struct terrain_vert, pos);
    vertex_desc.attributes[0].bufferIndex = 0;
    vertex_desc.attributes[1].format = MTLVertexFormatFloat2;
    vertex_desc.attributes[1].offset = offsetof(struct terrain_vert, uv);
    vertex_desc.attributes[1].bufferIndex = 0;
    vertex_desc.attributes[2].format = MTLVertexFormatFloat3;
    vertex_desc.attributes[2].offset = offsetof(struct terrain_vert, normal);
    vertex_desc.attributes[2].bufferIndex = 0;
    vertex_desc.attributes[3].format = MTLVertexFormatInt;
    vertex_desc.attributes[3].offset = offsetof(struct terrain_vert, material_idx);
    vertex_desc.attributes[3].bufferIndex = 0;
    vertex_desc.layouts[0].stride = sizeof(struct terrain_vert);
    vertex_desc.layouts[0].stepFunction = MTLVertexStepFunctionPerVertex;

    MTLRenderPipelineDescriptor *pipeline_desc = [[MTLRenderPipelineDescriptor alloc] init];
    pipeline_desc.vertexFunction = vertex;
    pipeline_desc.fragmentFunction = fragment;
    pipeline_desc.vertexDescriptor = vertex_desc;
    pipeline_desc.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
    pipeline_desc.rasterSampleCount = sample_count;
    if(depth_enabled)
        pipeline_desc.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float;

    id<MTLRenderPipelineState> pipeline = [s_device newRenderPipelineStateWithDescriptor:pipeline_desc error:&error];
    if(!pipeline) {
        fprintf(stderr, "Metal terrain pipeline creation failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    return pipeline;
}

static id<MTLRenderPipelineState> ensure_terrain_pipeline(bool multisampled, bool depth_enabled)
{
    id<MTLRenderPipelineState> __strong *slot = NULL;
    if(depth_enabled) {
        slot = multisampled ? &s_terrain_depth_msaa_pipeline : &s_terrain_depth_pipeline;
    } else {
        slot = multisampled ? &s_terrain_msaa_pipeline : &s_terrain_pipeline;
    }
    if(*slot)
        return *slot;
    *slot = build_terrain_pipeline(multisampled ? METAL_MSAA_SAMPLES : 1, depth_enabled);
    return *slot;
}

static bool ensure_scene_sampler(void)
{
    if(s_scene_sampler)
        return true;

    MTLSamplerDescriptor *sampler_desc = [[MTLSamplerDescriptor alloc] init];
    sampler_desc.minFilter = MTLSamplerMinMagFilterLinear;
    sampler_desc.magFilter = MTLSamplerMinMagFilterLinear;
    sampler_desc.mipFilter = MTLSamplerMipFilterNotMipmapped;
    sampler_desc.sAddressMode = MTLSamplerAddressModeRepeat;
    sampler_desc.tAddressMode = MTLSamplerAddressModeRepeat;
    s_scene_sampler = [s_device newSamplerStateWithDescriptor:sampler_desc];
    return s_scene_sampler != nil;
}

static id<MTLRenderPipelineState> build_static_mesh_pipeline(bool translucent, NSUInteger sample_count,
                                                             bool depth_enabled)
{
    NSError *error = nil;
    NSString *source = [NSString stringWithUTF8String:s_static_mesh_shader_source];
    id<MTLLibrary> library = [s_device newLibraryWithSource:source options:nil error:&error];
    if(!library) {
        fprintf(stderr, "Metal static mesh shader compile failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    id<MTLFunction> vertex = [library newFunctionWithName:@"static_mesh_vertex"];
    id<MTLFunction> fragment = [library newFunctionWithName:@"static_mesh_fragment"];
    if(!vertex || !fragment) {
        fprintf(stderr, "Metal static mesh shader entrypoint lookup failed.\n");
        return nil;
    }

    MTLVertexDescriptor *vertex_desc = [MTLVertexDescriptor vertexDescriptor];
    vertex_desc.attributes[0].format = MTLVertexFormatFloat3;
    vertex_desc.attributes[0].offset = offsetof(struct vertex, pos);
    vertex_desc.attributes[0].bufferIndex = 0;
    vertex_desc.attributes[1].format = MTLVertexFormatFloat2;
    vertex_desc.attributes[1].offset = offsetof(struct vertex, uv);
    vertex_desc.attributes[1].bufferIndex = 0;
    vertex_desc.attributes[2].format = MTLVertexFormatFloat3;
    vertex_desc.attributes[2].offset = offsetof(struct vertex, normal);
    vertex_desc.attributes[2].bufferIndex = 0;
    vertex_desc.attributes[3].format = MTLVertexFormatInt;
    vertex_desc.attributes[3].offset = offsetof(struct vertex, material_idx);
    vertex_desc.attributes[3].bufferIndex = 0;
    vertex_desc.layouts[0].stride = sizeof(struct vertex);
    vertex_desc.layouts[0].stepFunction = MTLVertexStepFunctionPerVertex;

    MTLRenderPipelineDescriptor *pipeline_desc = [[MTLRenderPipelineDescriptor alloc] init];
    pipeline_desc.vertexFunction = vertex;
    pipeline_desc.fragmentFunction = fragment;
    pipeline_desc.vertexDescriptor = vertex_desc;
    pipeline_desc.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
    pipeline_desc.rasterSampleCount = sample_count;
    if(depth_enabled)
        pipeline_desc.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float;
    if(translucent) {
        pipeline_desc.colorAttachments[0].blendingEnabled = YES;
        pipeline_desc.colorAttachments[0].rgbBlendOperation = MTLBlendOperationAdd;
        pipeline_desc.colorAttachments[0].alphaBlendOperation = MTLBlendOperationAdd;
        pipeline_desc.colorAttachments[0].sourceRGBBlendFactor = MTLBlendFactorSourceColor;
        pipeline_desc.colorAttachments[0].destinationRGBBlendFactor = MTLBlendFactorOneMinusSourceColor;
        pipeline_desc.colorAttachments[0].sourceAlphaBlendFactor = MTLBlendFactorSourceAlpha;
        pipeline_desc.colorAttachments[0].destinationAlphaBlendFactor = MTLBlendFactorOneMinusSourceAlpha;
    }

    id<MTLRenderPipelineState> pipeline = [s_device newRenderPipelineStateWithDescriptor:pipeline_desc error:&error];
    if(!pipeline) {
        fprintf(stderr, "Metal static mesh pipeline creation failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    return pipeline;
}

static id<MTLRenderPipelineState> ensure_static_mesh_pipeline(bool translucent, bool multisampled,
                                                              bool depth_enabled)
{
    id<MTLRenderPipelineState> __strong *slot = NULL;
    if(depth_enabled && translucent) {
        slot = multisampled ? &s_static_mesh_blend_depth_msaa_pipeline : &s_static_mesh_blend_depth_pipeline;
    } else if(depth_enabled) {
        slot = multisampled ? &s_static_mesh_depth_msaa_pipeline : &s_static_mesh_depth_pipeline;
    } else if(translucent) {
        slot = multisampled ? &s_static_mesh_blend_msaa_pipeline : &s_static_mesh_blend_pipeline;
    } else {
        slot = multisampled ? &s_static_mesh_msaa_pipeline : &s_static_mesh_pipeline;
    }
    if(*slot)
        return *slot;
    *slot = build_static_mesh_pipeline(translucent, multisampled ? METAL_MSAA_SAMPLES : 1, depth_enabled);
    return *slot;
}

static id<MTLRenderPipelineState> build_world_color_pipeline(NSUInteger sample_count)
{
    NSError *error = nil;
    NSString *source = [NSString stringWithUTF8String:s_world_color_shader_source];
    id<MTLLibrary> library = [s_device newLibraryWithSource:source options:nil error:&error];
    if(!library) {
        fprintf(stderr, "Metal world-color shader compile failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    id<MTLFunction> vertex = [library newFunctionWithName:@"world_color_vertex"];
    id<MTLFunction> fragment = [library newFunctionWithName:@"world_color_fragment"];
    if(!vertex || !fragment) {
        fprintf(stderr, "Metal world-color shader entrypoint lookup failed.\n");
        return nil;
    }

    MTLVertexDescriptor *vertex_desc = [MTLVertexDescriptor vertexDescriptor];
    vertex_desc.attributes[0].format = MTLVertexFormatFloat3;
    vertex_desc.attributes[0].offset = offsetof(struct colored_vert, pos);
    vertex_desc.attributes[0].bufferIndex = 0;
    vertex_desc.attributes[1].format = MTLVertexFormatFloat4;
    vertex_desc.attributes[1].offset = offsetof(struct colored_vert, color);
    vertex_desc.attributes[1].bufferIndex = 0;
    vertex_desc.layouts[0].stride = sizeof(struct colored_vert);
    vertex_desc.layouts[0].stepFunction = MTLVertexStepFunctionPerVertex;

    MTLRenderPipelineDescriptor *pipeline_desc = [[MTLRenderPipelineDescriptor alloc] init];
    pipeline_desc.vertexFunction = vertex;
    pipeline_desc.fragmentFunction = fragment;
    pipeline_desc.vertexDescriptor = vertex_desc;
    pipeline_desc.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
    pipeline_desc.rasterSampleCount = sample_count;
    pipeline_desc.colorAttachments[0].blendingEnabled = YES;
    pipeline_desc.colorAttachments[0].rgbBlendOperation = MTLBlendOperationAdd;
    pipeline_desc.colorAttachments[0].alphaBlendOperation = MTLBlendOperationAdd;
    pipeline_desc.colorAttachments[0].sourceRGBBlendFactor = MTLBlendFactorSourceAlpha;
    pipeline_desc.colorAttachments[0].sourceAlphaBlendFactor = MTLBlendFactorSourceAlpha;
    pipeline_desc.colorAttachments[0].destinationRGBBlendFactor = MTLBlendFactorOneMinusSourceAlpha;
    pipeline_desc.colorAttachments[0].destinationAlphaBlendFactor = MTLBlendFactorOneMinusSourceAlpha;

    id<MTLRenderPipelineState> pipeline = [s_device newRenderPipelineStateWithDescriptor:pipeline_desc error:&error];
    if(!pipeline) {
        fprintf(stderr, "Metal world-color pipeline creation failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    return pipeline;
}

static id<MTLRenderPipelineState> ensure_world_color_pipeline(bool multisampled)
{
    id<MTLRenderPipelineState> __strong *slot = multisampled ? &s_world_color_msaa_pipeline : &s_world_color_pipeline;
    if(*slot)
        return *slot;
    *slot = build_world_color_pipeline(multisampled ? METAL_MSAA_SAMPLES : 1);
    return *slot;
}

static id<MTLRenderPipelineState> build_water_surface_pipeline(NSUInteger sample_count)
{
    NSError *error = nil;
    NSString *source = [NSString stringWithUTF8String:s_water_surface_shader_source];
    id<MTLLibrary> library = [s_device newLibraryWithSource:source options:nil error:&error];
    if(!library) {
        fprintf(stderr, "Metal water-surface shader compile failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    id<MTLFunction> vertex = [library newFunctionWithName:@"water_surface_vertex"];
    id<MTLFunction> fragment = [library newFunctionWithName:@"water_surface_fragment"];
    if(!vertex || !fragment) {
        fprintf(stderr, "Metal water-surface shader entrypoint lookup failed.\n");
        return nil;
    }

    MTLVertexDescriptor *vertex_desc = [MTLVertexDescriptor vertexDescriptor];
    vertex_desc.attributes[0].format = MTLVertexFormatFloat3;
    vertex_desc.attributes[0].offset = 0;
    vertex_desc.attributes[0].bufferIndex = 0;
    vertex_desc.layouts[0].stride = sizeof(vec3_t);
    vertex_desc.layouts[0].stepFunction = MTLVertexStepFunctionPerVertex;

    MTLRenderPipelineDescriptor *pipeline_desc = [[MTLRenderPipelineDescriptor alloc] init];
    pipeline_desc.vertexFunction = vertex;
    pipeline_desc.fragmentFunction = fragment;
    pipeline_desc.vertexDescriptor = vertex_desc;
    pipeline_desc.colorAttachments[0].pixelFormat = MTLPixelFormatBGRA8Unorm;
    pipeline_desc.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float;
    pipeline_desc.rasterSampleCount = sample_count;
    pipeline_desc.colorAttachments[0].blendingEnabled = YES;
    pipeline_desc.colorAttachments[0].rgbBlendOperation = MTLBlendOperationAdd;
    pipeline_desc.colorAttachments[0].alphaBlendOperation = MTLBlendOperationAdd;
    pipeline_desc.colorAttachments[0].sourceRGBBlendFactor = MTLBlendFactorSourceAlpha;
    pipeline_desc.colorAttachments[0].sourceAlphaBlendFactor = MTLBlendFactorOne;
    pipeline_desc.colorAttachments[0].destinationRGBBlendFactor = MTLBlendFactorOneMinusSourceAlpha;
    pipeline_desc.colorAttachments[0].destinationAlphaBlendFactor = MTLBlendFactorOneMinusSourceAlpha;

    id<MTLRenderPipelineState> pipeline = [s_device newRenderPipelineStateWithDescriptor:pipeline_desc error:&error];
    if(!pipeline) {
        fprintf(stderr, "Metal water-surface pipeline creation failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    return pipeline;
}

static id<MTLRenderPipelineState> ensure_water_surface_pipeline(bool multisampled)
{
    id<MTLRenderPipelineState> __strong *slot = multisampled ? &s_water_surface_msaa_pipeline : &s_water_surface_pipeline;
    if(*slot)
        return *slot;
    *slot = build_water_surface_pipeline(multisampled ? METAL_MSAA_SAMPLES : 1);
    return *slot;
}

static id<MTLRenderPipelineState> build_shadow_depth_pipeline(size_t vertex_stride)
{
    NSError *error = nil;
    NSString *source = [NSString stringWithUTF8String:s_shadow_depth_shader_source];
    id<MTLLibrary> library = [s_device newLibraryWithSource:source options:nil error:&error];
    if(!library) {
        fprintf(stderr, "Metal shadow-depth shader compile failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    id<MTLFunction> vertex = [library newFunctionWithName:@"shadow_depth_vertex"];
    if(!vertex) {
        fprintf(stderr, "Metal shadow-depth shader entrypoint lookup failed.\n");
        return nil;
    }

    MTLVertexDescriptor *vertex_desc = [MTLVertexDescriptor vertexDescriptor];
    vertex_desc.attributes[0].format = MTLVertexFormatFloat3;
    vertex_desc.attributes[0].offset = 0;
    vertex_desc.attributes[0].bufferIndex = 0;
    vertex_desc.layouts[0].stride = vertex_stride;
    vertex_desc.layouts[0].stepFunction = MTLVertexStepFunctionPerVertex;

    MTLRenderPipelineDescriptor *pipeline_desc = [[MTLRenderPipelineDescriptor alloc] init];
    pipeline_desc.vertexFunction = vertex;
    pipeline_desc.vertexDescriptor = vertex_desc;
    pipeline_desc.depthAttachmentPixelFormat = MTLPixelFormatDepth32Float;

    id<MTLRenderPipelineState> pipeline = [s_device newRenderPipelineStateWithDescriptor:pipeline_desc error:&error];
    if(!pipeline) {
        fprintf(stderr, "Metal shadow-depth pipeline creation failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return nil;
    }

    return pipeline;
}

static id<MTLRenderPipelineState> ensure_shadow_depth_pipeline(bool terrain)
{
    id<MTLRenderPipelineState> __strong *slot = terrain ? &s_shadow_terrain_pipeline : &s_shadow_mesh_pipeline;
    if(*slot)
        return *slot;
    *slot = build_shadow_depth_pipeline(terrain ? sizeof(struct terrain_vert) : sizeof(struct vertex));
    return *slot;
}

static void frame_begin(void)
{
    if(s_frame_command_buffer)
        return;

    update_drawable_size();
    if(!reserve_inflight_frame())
        return;

    s_frame_drawable = [s_layer nextDrawable];
    if(!s_frame_drawable) {
        release_inflight_frame();
        return;
    }

    NSUInteger sample_count = desired_frame_sample_count();
    if(sample_count > 1 && !ensure_frame_msaa_texture(sample_count)) {
        sample_count = 1;
    }
    s_frame_sample_count = sample_count;
    (void)ensure_frame_depth_texture(sample_count);

    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    if(sample_count > 1) {
        pass.colorAttachments[0].texture = s_frame_msaa_texture;
        pass.colorAttachments[0].resolveTexture = s_frame_drawable.texture;
        pass.colorAttachments[0].storeAction = MTLStoreActionMultisampleResolve;
    } else {
        pass.colorAttachments[0].texture = s_frame_drawable.texture;
        pass.colorAttachments[0].storeAction = MTLStoreActionStore;
    }
    pass.colorAttachments[0].loadAction = MTLLoadActionClear;
    pass.colorAttachments[0].clearColor = MTLClearColorMake(0.0, 0.0, 0.0, 1.0);
    if(s_frame_depth_texture) {
        pass.depthAttachment.texture = s_frame_depth_texture;
        pass.depthAttachment.loadAction = MTLLoadActionClear;
        pass.depthAttachment.storeAction = MTLStoreActionStore;
        pass.depthAttachment.clearDepth = 1.0;
    }

    s_frame_command_buffer = [s_queue commandBuffer];
    if(!s_frame_command_buffer) {
        reset_frame_state();
        release_inflight_frame();
        return;
    }
    s_frame_encoder = [s_frame_command_buffer renderCommandEncoderWithDescriptor:pass];
    if(!s_frame_encoder) {
        reset_frame_state();
        release_inflight_frame();
        return;
    }

    MTLViewport viewport = {
        .originX = 0.0,
        .originY = 0.0,
        .width = s_layer.drawableSize.width,
        .height = s_layer.drawableSize.height,
        .znear = 0.0,
        .zfar = 1.0
    };
    [s_frame_encoder setViewport:viewport];
}

static bool frame_resume(void)
{
    if(s_frame_encoder)
        return true;
    if(!s_frame_command_buffer || !s_frame_drawable)
        return false;

    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    if(s_frame_sample_count > 1 && s_frame_msaa_texture) {
        pass.colorAttachments[0].texture = s_frame_msaa_texture;
        pass.colorAttachments[0].resolveTexture = s_frame_drawable.texture;
        pass.colorAttachments[0].loadAction = MTLLoadActionLoad;
        pass.colorAttachments[0].storeAction = MTLStoreActionMultisampleResolve;
    } else {
        pass.colorAttachments[0].texture = s_frame_drawable.texture;
        pass.colorAttachments[0].loadAction = MTLLoadActionLoad;
        pass.colorAttachments[0].storeAction = MTLStoreActionStore;
    }
    if(s_frame_depth_texture) {
        pass.depthAttachment.texture = s_frame_depth_texture;
        pass.depthAttachment.loadAction = MTLLoadActionLoad;
        pass.depthAttachment.storeAction = MTLStoreActionStore;
    }

    s_frame_encoder = [s_frame_command_buffer renderCommandEncoderWithDescriptor:pass];
    if(!s_frame_encoder)
        return false;

    MTLViewport viewport = {
        .originX = 0.0,
        .originY = 0.0,
        .width = s_layer.drawableSize.width,
        .height = s_layer.drawableSize.height,
        .znear = 0.0,
        .zfar = 1.0
    };
    [s_frame_encoder setViewport:viewport];
    return true;
}

static void frame_end(void)
{
    if(!s_frame_encoder)
        return;
    [s_frame_encoder endEncoding];
    s_frame_encoder = nil;
}

static void frame_present(void)
{
    if(!s_frame_command_buffer) {
        present_clear();
        return;
    }

    frame_end();
    if(s_frame_inflight_reserved && s_inflight_semaphore) {
        dispatch_semaphore_t inflight = s_inflight_semaphore;
        [s_frame_command_buffer addCompletedHandler:^(id<MTLCommandBuffer> buffer){
            (void)buffer;
            dispatch_semaphore_signal(inflight);
        }];
        s_frame_inflight_reserved = false;
    }
    [s_frame_command_buffer presentDrawable:s_frame_drawable];
    [s_frame_command_buffer commit];
    reset_frame_state();
}

static void frame_abort(void)
{
    if(s_frame_encoder) {
        [s_frame_encoder endEncoding];
    }
    reset_frame_state();
    release_inflight_frame();
}

static bool shadow_enabled_for_draw(void)
{
    return s_shadows_enabled && s_shadow_map_valid && s_shadow_depth_texture && s_shadow_sampler;
}

static void shadow_pass_begin(const vec3_t *light_pos, const vec3_t *cam_pos, const vec3_t *cam_dir)
{
    if(!light_pos || !cam_pos || !cam_dir)
        return;
    if(!ensure_shadow_depth_texture() || !ensure_shadow_sampler())
        return;

    make_shadow_light_space(*light_pos, *cam_pos, *cam_dir,
        &s_shadow_view, &s_shadow_proj, &s_shadow_light_space);

    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    pass.depthAttachment.texture = s_shadow_depth_texture;
    pass.depthAttachment.loadAction = MTLLoadActionClear;
    pass.depthAttachment.storeAction = MTLStoreActionStore;
    pass.depthAttachment.clearDepth = 1.0;

    s_shadow_command_buffer = [s_queue commandBuffer];
    if(!s_shadow_command_buffer)
        return;

    s_shadow_encoder = [s_shadow_command_buffer renderCommandEncoderWithDescriptor:pass];
    if(!s_shadow_encoder) {
        s_shadow_command_buffer = nil;
        return;
    }

    MTLViewport viewport = {
        .originX = 0.0,
        .originY = 0.0,
        .width = CONFIG_SHADOW_MAP_RES,
        .height = CONFIG_SHADOW_MAP_RES,
        .znear = 0.0,
        .zfar = 1.0
    };
    [s_shadow_encoder setViewport:viewport];

    id<MTLDepthStencilState> depth_state = ensure_depth_state(true);
    if(depth_state)
        [s_shadow_encoder setDepthStencilState:depth_state];
    [s_shadow_encoder setCullMode:MTLCullModeFront];
    [s_shadow_encoder setFrontFacingWinding:MTLWindingCounterClockwise];

    s_shadow_pass_active = true;
    s_shadow_map_valid = false;
}

static void shadow_pass_end(void)
{
    if(!s_shadow_pass_active)
        return;

    if(s_shadow_encoder) {
        [s_shadow_encoder endEncoding];
        s_shadow_encoder = nil;
    }
    if(s_shadow_command_buffer) {
        [s_shadow_command_buffer commit];
        [s_shadow_command_buffer waitUntilCompleted];
        s_shadow_command_buffer = nil;
        s_shadow_map_valid = true;
    }
    s_shadow_pass_active = false;
}

static void render_shadow_vertex_stream(const void *verts, size_t verts_size, size_t vertex_count,
                                        const mat4x4_t *model, bool terrain)
{
    if(!s_shadow_pass_active || !s_shadow_encoder || !verts || !verts_size || !vertex_count || !model)
        return;

    id<MTLRenderPipelineState> pipeline = ensure_shadow_depth_pipeline(terrain);
    if(!pipeline)
        return;

    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:verts
        length:verts_size options:MTLResourceStorageModeShared];
    if(!vertex_buffer)
        return;

    struct metal_shadow_uniforms uniforms = {
        .model = matrix_from_pf_mat4(model),
        .view = s_shadow_view,
        .proj = s_shadow_proj,
    };
    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [s_shadow_encoder setRenderPipelineState:pipeline];
    [s_shadow_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_shadow_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [s_shadow_encoder drawPrimitives:MTLPrimitiveTypeTriangle
                         vertexStart:0
                         vertexCount:vertex_count];
}

static void render_shadow_depth_draw(const struct render_private *priv, const mat4x4_t *model)
{
    if(!priv || !model)
        return;

    if(priv->metal_is_terrain) {
        if(!priv->metal_terrain_verts || !priv->metal_terrain_verts_size || !priv->mesh.num_verts)
            return;
        render_shadow_vertex_stream(priv->metal_terrain_verts, priv->metal_terrain_verts_size,
            priv->mesh.num_verts, model, true);
        return;
    }

    if(priv->metal_is_static_mesh && !priv->uses_pose_buffer) {
        if(!priv->metal_static_verts || !priv->metal_static_verts_size || !priv->mesh.num_verts)
            return;
        render_shadow_vertex_stream(priv->metal_static_verts, priv->metal_static_verts_size,
            priv->mesh.num_verts, model, false);
        return;
    }

    if(priv->metal_is_anim_mesh && priv->uses_pose_buffer && s_have_anim_uid) {
        struct vertex *skinned = malloc(priv->mesh.num_verts * sizeof(*skinned));
        if(!skinned)
            return;

        size_t dst_idx = 0;
        bool ok = append_skinned_anim_mesh(priv, s_curr_anim_uid, model, skinned, &dst_idx);
        if(ok) {
            mat4x4_t identity;
            PFM_Mat4x4_Identity(&identity);
            render_shadow_vertex_stream(skinned, dst_idx * sizeof(*skinned), dst_idx, &identity, false);
        }
        free(skinned);
    }
}

static void render_shadow_batched_stat_entities(const vec_rstat_t *ents)
{
    vec_rstat_t *mutable_ents = (vec_rstat_t *)ents;
    if(!mutable_ents)
        return;

    for(int i = 0; i < vec_size(mutable_ents); i++) {
        const struct ent_stat_rstate *curr = &vec_AT(mutable_ents, i);
        render_shadow_depth_draw(curr->render_private, &curr->model);
    }
}

static void render_shadow_batched_anim_entities(const vec_ranim_t *ents)
{
    vec_ranim_t *mutable_ents = (vec_ranim_t *)ents;
    if(!mutable_ents)
        return;

    for(int i = 0; i < vec_size(mutable_ents); i++) {
        const struct ent_anim_rstate *curr = &vec_AT(mutable_ents, i);
        s_curr_anim_uid = curr->uid;
        s_have_anim_uid = true;
        render_shadow_depth_draw(curr->render_private, &curr->model);
    }
}

static MTLScissorRect scissor_rect_for_cmd(const struct nk_draw_command *cmd,
                                           struct nk_vec2i curr_vres,
                                           int drawable_w, int drawable_h)
{
    const float sx = (float)drawable_w / curr_vres.x;
    const float sy = (float)drawable_h / curr_vres.y;

    NSInteger x = (NSInteger)floorf(cmd->clip_rect.x * sx);
    NSInteger y = (NSInteger)floorf(cmd->clip_rect.y * sy);
    NSInteger w = (NSInteger)ceilf(cmd->clip_rect.w * sx);
    NSInteger h = (NSInteger)ceilf(cmd->clip_rect.h * sy);

    if(x < 0) {
        w += x;
        x = 0;
    }
    if(y < 0) {
        h += y;
        y = 0;
    }
    if(x > drawable_w)
        x = drawable_w;
    if(y > drawable_h)
        y = drawable_h;
    if(x + w > drawable_w)
        w = drawable_w - x;
    if(y + h > drawable_h)
        h = drawable_h - y;
    if(w < 0)
        w = 0;
    if(h < 0)
        h = 0;

    return (MTLScissorRect){
        .x = (NSUInteger)x,
        .y = (NSUInteger)y,
        .width = (NSUInteger)w,
        .height = (NSUInteger)h
    };
}

static void render_ui_draw_list(const struct nk_draw_list *dl)
{
    id<MTLRenderPipelineState> pipeline = nil;
    if(!s_ui_font_texture)
        return;

    frame_begin();
    if(!s_frame_encoder)
        return;
    pipeline = ensure_ui_pipeline(frame_uses_msaa());
    if(!pipeline)
        return;

    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:dl->vertices->memory.ptr
        length:dl->vertices->memory.size options:MTLResourceStorageModeShared];
    id<MTLBuffer> index_buffer = [s_device newBufferWithBytes:dl->elements->memory.ptr
        length:dl->elements->memory.size options:MTLResourceStorageModeShared];
    if(!vertex_buffer || !index_buffer)
        return;

    [s_frame_encoder setRenderPipelineState:pipeline];
    [s_frame_encoder setDepthStencilState:nil];
    [s_frame_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_frame_encoder setFragmentTexture:s_ui_font_texture atIndex:0];
    [s_frame_encoder setFragmentSamplerState:s_ui_sampler atIndex:0];

    int drawable_w = (int)s_layer.drawableSize.width;
    int drawable_h = (int)s_layer.drawableSize.height;
    struct nk_vec2i curr_vres = {drawable_w, drawable_h};
    NSUInteger index_offset = 0;

    const struct nk_draw_command *cmd;
    for(cmd = nk__draw_list_begin(dl, dl->buffer); cmd;
        cmd = nk__draw_list_next(cmd, dl->buffer, dl)) {

        if(cmd->userdata.ptr) {
            struct nk_command_userdata *ud = cmd->userdata.ptr;
            switch(ud->type) {
            case NK_COMMAND_SET_VRES:
                curr_vres = ud->vec2i;
                PF_FREE(ud);
                continue;
            case NK_COMMAND_IMAGE_TEXPATH:
            case NK_COMMAND_IMAGE_TEXPATH_REGION:
                PF_FREE(ud);
                index_offset += cmd->elem_count * sizeof(nk_draw_index);
                continue;
            default:
                PF_FREE(ud);
                continue;
            }
        }

        if(!cmd->elem_count) {
            continue;
        }

        if((uintptr_t)cmd->texture.id != 1) {
            index_offset += cmd->elem_count * sizeof(nk_draw_index);
            continue;
        }

        MTLScissorRect scissor = scissor_rect_for_cmd(cmd, curr_vres, drawable_w, drawable_h);
        if(scissor.width == 0 || scissor.height == 0) {
            index_offset += cmd->elem_count * sizeof(nk_draw_index);
            continue;
        }

        struct metal_ui_uniforms uniforms = {
            .view_size = {curr_vres.x, curr_vres.y},
            ._padding = {0.0f, 0.0f}
        };
        id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
            length:sizeof(uniforms) options:MTLResourceStorageModeShared];
        if(!uniform_buffer) {
            index_offset += cmd->elem_count * sizeof(nk_draw_index);
            continue;
        }

        [s_frame_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
        [s_frame_encoder setScissorRect:scissor];
        [s_frame_encoder drawIndexedPrimitives:MTLPrimitiveTypeTriangle
                                    indexCount:cmd->elem_count
                                     indexType:MTLIndexTypeUInt32
                                   indexBuffer:index_buffer
                             indexBufferOffset:index_offset];

        index_offset += cmd->elem_count * sizeof(nk_draw_index);
    }
}

static void render_ui_triangles(const struct ui_vert *verts, size_t nverts, id<MTLTexture> texture)
{
    id<MTLRenderPipelineState> pipeline = nil;
    if(!verts || !nverts || !texture)
        return;

    frame_begin();
    if(!s_frame_encoder)
        return;
    pipeline = ensure_ui_pipeline(frame_uses_msaa());
    if(!pipeline)
        return;

    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:verts
        length:nverts * sizeof(*verts) options:MTLResourceStorageModeShared];
    if(!vertex_buffer)
        return;

    int drawable_w = (int)s_layer.drawableSize.width;
    int drawable_h = (int)s_layer.drawableSize.height;
    struct metal_ui_uniforms uniforms = {
        .view_size = {drawable_w, drawable_h},
        ._padding = {0.0f, 0.0f}
    };
    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [s_frame_encoder setRenderPipelineState:pipeline];
    [s_frame_encoder setDepthStencilState:nil];
    [s_frame_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_frame_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder setFragmentTexture:texture atIndex:0];
    [s_frame_encoder setFragmentSamplerState:s_ui_sampler atIndex:0];
    [s_frame_encoder drawPrimitives:MTLPrimitiveTypeTriangle
                        vertexStart:0
                        vertexCount:nverts];
}

static vec2_t transform_model_point(const mat4x4_t *model, vec2_t point)
{
    mat4x4_t copy = *model;
    vec4_t in = {point.x, point.y, 0.0f, 1.0f};
    vec4_t out;
    PFM_Mat4x4_Mult4x1(&copy, &in, &out);
    return (vec2_t){out.x, out.y};
}

static void make_minimap_models(const vec2_t *center_pos, const int *side_len_px,
                                mat4x4_t *out_model, mat4x4_t *out_border_model)
{
    mat4x4_t tmp;
    mat4x4_t tilt, trans, scale;
    PFM_Mat4x4_MakeRotZ(DEG_TO_RAD(-45.0f), &tilt);
    PFM_Mat4x4_MakeScale((*side_len_px) / 2.0f, (*side_len_px) / 2.0f, 1.0f, &scale);
    PFM_Mat4x4_MakeTrans(center_pos->x, center_pos->y, 0.0f, &trans);
    PFM_Mat4x4_Mult4x4(&scale, &tilt, &tmp);
    PFM_Mat4x4_Mult4x4(&trans, &tmp, out_model);

    float scale_fac = ((*side_len_px) + 2 * MINIMAP_BORDER_WIDTH) / 2.0f;
    mat4x4_t border_scale;
    PFM_Mat4x4_MakeScale(scale_fac, scale_fac, scale_fac, &border_scale);
    PFM_Mat4x4_Mult4x4(&border_scale, &tilt, &tmp);
    PFM_Mat4x4_Mult4x4(&trans, &tmp, out_border_model);
}

static void build_minimap_quad(const mat4x4_t *model, struct ui_vert out[6])
{
    const vec2_t local[4] = {
        {-1.0f, -1.0f},
        {-1.0f,  1.0f},
        { 1.0f,  1.0f},
        { 1.0f, -1.0f},
    };
    const vec2_t uv[4] = {
        {0.0f, 0.0f},
        {0.0f, 1.0f},
        {1.0f, 1.0f},
        {1.0f, 0.0f},
    };
    const int idx[6] = {0, 1, 2, 0, 2, 3};

    for(int i = 0; i < 6; i++) {
        int src = idx[i];
        vec2_t screen = transform_model_point(model, local[src]);
        out[i] = (struct ui_vert){
            .screen_pos = screen,
            .uv = uv[src],
            .color = {255, 255, 255, 255},
        };
    }
}

static bool build_minimap_view_proj(const struct map *map,
                                    matrix_float4x4 *out_view,
                                    matrix_float4x4 *out_proj)
{
    struct map_resolution res;
    M_GetResolution(map, &res);

    vec3_t map_center = M_GetCenterPos(map);
    vec2_t map_size = {
        res.chunk_w * res.tile_w * X_COORDS_PER_TILE,
        res.chunk_h * res.tile_h * Z_COORDS_PER_TILE
    };

    struct camera *map_cam = Camera_New();
    if(!map_cam)
        return false;

    vec3_t offset = {0.0f, 200.0f, 0.0f};
    PFM_Vec3_Add(&map_center, &offset, &map_center);
    Camera_SetPos(map_cam, map_center);
    Camera_SetPitchAndYaw(map_cam, -90.0f, 90.0f);

    float map_dim = fmaxf(map_size.x, map_size.y);
    vec2_t bot_left = {-(map_dim / 2.0f), (map_dim / 2.0f)};
    vec2_t top_right = {(map_dim / 2.0f), -(map_dim / 2.0f)};
    Camera_TickFinishOrthographic(map_cam, bot_left, top_right);

    mat4x4_t view, proj;
    Camera_MakeViewMat(map_cam, &view);
    Camera_MakeProjMat(map_cam, &proj);
    Camera_Free(map_cam);

    *out_view = matrix_from_pf_mat4(&view);
    *out_proj = matrix_from_pf_mat4(&proj);
    return true;
}

static id<MTLBuffer> ensure_persistent_vertex_buffer(void **slot,
                                                     const void *bytes,
                                                     size_t length)
{
    if(!slot || !bytes || !length || !s_device)
        return nil;
    if(*slot)
        return (__bridge id<MTLBuffer>)*slot;

    id<MTLBuffer> buffer = [s_device newBufferWithBytes:bytes
        length:length options:MTLResourceStorageModeShared];
    if(!buffer)
        return nil;

    *slot = (__bridge_retained void *)buffer;
    return buffer;
}

static id<MTLRenderCommandEncoder> active_scene_encoder(void)
{
    if(s_water_scene_pass_active && s_water_scene_encoder)
        return s_water_scene_encoder;
    return s_frame_encoder;
}

static bool active_scene_depth_enabled(void)
{
    if(s_water_scene_pass_active && s_water_scene_encoder)
        return true;
    return frame_has_depth();
}

static vector_float4 current_water_clip_params(void)
{
    return (vector_float4){
        (float)s_water_scene_clip_mode,
        0.0f,
        METAL_WATER_LEVEL,
        0.0f
    };
}

static void draw_terrain_to_encoder(id<MTLRenderCommandEncoder> encoder,
                                    const struct render_private *priv,
                                    const mat4x4_t *model,
                                    matrix_float4x4 view,
                                    matrix_float4x4 proj)
{
    struct render_private *mutable_priv = (struct render_private *)priv;
    id<MTLRenderPipelineState> pipeline = nil;
    bool multisampled = (encoder == s_frame_encoder) && frame_uses_msaa();
    bool depth_enabled = ((encoder == s_frame_encoder) && frame_has_depth())
                      || ((encoder == s_water_scene_encoder) && s_water_scene_pass_active);
    if(!encoder || !priv || !priv->metal_is_terrain)
        return;
    if(!priv->metal_terrain_verts || !priv->metal_terrain_verts_size || !priv->mesh.num_verts)
        return;
    pipeline = ensure_terrain_pipeline(multisampled, depth_enabled);
    if(!pipeline)
        return;

    id<MTLBuffer> vertex_buffer = ensure_persistent_vertex_buffer(
        &mutable_priv->metal_terrain_vertex_buffer,
        priv->metal_terrain_verts,
        priv->metal_terrain_verts_size);
    if(!vertex_buffer)
        return;

    struct metal_terrain_uniforms uniforms = {
        .model = matrix_from_pf_mat4(model),
        .view = view,
        .proj = proj,
        .view_pos = {s_scene_view_pos.x, s_scene_view_pos.y, s_scene_view_pos.z, 1.0f},
        .map_pos = s_map_pos,
        .tile_world_size = s_map_tile_world_size,
        .chunk_size = s_map_chunk_size,
        .tiles_per_chunk = s_map_tiles_per_chunk,
        .terrain_params = {
            (float)s_terrain_texture_count,
            0.0f,
            0.0f,
            0.0f,
        },
        .water_params = {
            SDL_GetTicks() / 1000.0f,
            s_water_buffer ? 1.0f : 0.0f,
            s_fog_buffer ? 1.0f : 0.0f,
            (s_water_dudv_texture && s_water_normal_texture) ? 1.0f : 0.0f,
        },
        .light_space_transform = s_shadow_light_space,
        .shadow_params = {
            shadow_enabled_for_draw() ? 1.0f : 0.0f,
            0.0015f,
            0.58f,
            1.25f,
        },
        .clip_params = current_water_clip_params(),
    };
    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [encoder setRenderPipelineState:pipeline];
    if(depth_enabled) {
        id<MTLDepthStencilState> depth_state = ensure_depth_state(true);
        if(depth_state)
            [encoder setDepthStencilState:depth_state];
    } else {
        [encoder setDepthStencilState:nil];
    }
    [encoder setCullMode:MTLCullModeNone];
    [encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [encoder setFragmentBuffer:uniform_buffer offset:0 atIndex:1];
    if(s_fog_buffer) {
        [encoder setFragmentBuffer:s_fog_buffer offset:0 atIndex:2];
    }
    if(s_water_buffer) {
        [encoder setFragmentBuffer:s_water_buffer offset:0 atIndex:3];
    }
    if(s_terrain_texture_array && ensure_scene_sampler()) {
        [encoder setFragmentTexture:s_terrain_texture_array atIndex:0];
        [encoder setFragmentSamplerState:s_scene_sampler atIndex:0];
    }
    if(s_water_dudv_texture && ensure_scene_sampler()) {
        [encoder setFragmentTexture:s_water_dudv_texture atIndex:1];
        [encoder setFragmentSamplerState:s_scene_sampler atIndex:0];
    }
    if(s_water_normal_texture && ensure_scene_sampler()) {
        [encoder setFragmentTexture:s_water_normal_texture atIndex:2];
        [encoder setFragmentSamplerState:s_scene_sampler atIndex:0];
    }
    if(shadow_enabled_for_draw()) {
        [encoder setFragmentTexture:s_shadow_depth_texture atIndex:3];
        [encoder setFragmentSamplerState:s_shadow_sampler atIndex:1];
    }
    [encoder drawPrimitives:MTLPrimitiveTypeTriangle
                vertexStart:0
                vertexCount:priv->mesh.num_verts];
}

static void update_fog_texture(void *buff, const size_t *size)
{
    if(!buff || !size)
        return;
    if(*size == 0)
        return;

    if(s_map_chunk_size.x > 0u && s_map_chunk_size.y > 0u) {
        size_t expected = (size_t)s_map_chunk_size.x * (size_t)s_map_chunk_size.y
                        * (size_t)s_map_tiles_per_chunk.x * (size_t)s_map_tiles_per_chunk.y;
        if(*size != expected)
            return;
    }

    s_fog_buffer = [s_device newBufferWithBytes:buff
        length:*size options:MTLResourceStorageModeShared];
}

static id<MTLTexture> load_rgba_texture_2d(const char *path)
{
    if(!path || !s_device)
        return nil;

    int width = 0, height = 0, nr_channels = 0;
    unsigned char *data = stbi_load(path, &width, &height, &nr_channels, 4);
    if(!data)
        return nil;

    MTLTextureDescriptor *desc = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                                                                     width:width
                                                                                    height:height
                                                                                 mipmapped:NO];
    desc.usage = MTLTextureUsageShaderRead;
    id<MTLTexture> texture = [s_device newTextureWithDescriptor:desc];
    if(texture) {
        MTLRegion region = MTLRegionMake2D(0, 0, width, height);
        [texture replaceRegion:region
                   mipmapLevel:0
                     withBytes:data
                   bytesPerRow:width * 4];
    }

    stbi_image_free(data);
    return texture;
}

static void init_water_resources(void)
{
    char path[1024];

    s_water_dudv_texture = nil;
    s_water_normal_texture = nil;

    snprintf(path, sizeof(path), "%s/%s", g_basepath, METAL_WATER_DUDV_PATH);
    s_water_dudv_texture = load_rgba_texture_2d(path);

    snprintf(path, sizeof(path), "%s/%s", g_basepath, METAL_WATER_NORMAL_PATH);
    s_water_normal_texture = load_rgba_texture_2d(path);
}

static void fill_fallback_terrain_rgba(unsigned char *dst, size_t npixels, uint32_t idx)
{
    const unsigned char palette[][4] = {
        { 92, 140,  66, 255 },
        {112, 158,  77, 255 },
        {148, 138,  82, 255 },
        {105, 115,  69, 255 },
        {163, 153,  94, 255 },
        { 74, 110,  61, 255 },
        {128, 125,  79, 255 },
        {122, 145,  87, 255 },
    };
    const unsigned char *rgba = palette[idx % (sizeof(palette) / sizeof(palette[0]))];
    for(size_t i = 0; i < npixels; i++) {
        memcpy(dst + i * 4, rgba, 4);
    }
}

static void update_terrain_textures(const char map_texfiles[][256], const size_t *num_textures)
{
    s_terrain_texture_array = nil;
    s_terrain_texture_count = 0;

    if(!map_texfiles || !num_textures || !*num_textures || !s_device)
        return;

    MTLTextureDescriptor *desc = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                                                                     width:CONFIG_TILE_TEX_RES
                                                                                    height:CONFIG_TILE_TEX_RES
                                                                                 mipmapped:NO];
    desc.textureType = MTLTextureType2DArray;
    desc.arrayLength = *num_textures;
    desc.usage = MTLTextureUsageShaderRead;

    id<MTLTexture> texture = [s_device newTextureWithDescriptor:desc];
    if(!texture)
        return;

    const size_t bytes_per_row = CONFIG_TILE_TEX_RES * 4;
    const size_t bytes_per_image = bytes_per_row * CONFIG_TILE_TEX_RES;
    const size_t npixels = CONFIG_TILE_TEX_RES * CONFIG_TILE_TEX_RES;
    unsigned char *fallback = malloc(bytes_per_image);
    unsigned char *resized = malloc(bytes_per_image);
    if(!fallback || !resized) {
        free(fallback);
        free(resized);
        return;
    }

    MTLRegion region = MTLRegionMake2D(0, 0, CONFIG_TILE_TEX_RES, CONFIG_TILE_TEX_RES);
    for(size_t i = 0; i < *num_textures; i++) {
        char path[512];
        snprintf(path, sizeof(path), "%s/assets/map_textures/%s", g_basepath, map_texfiles[i]);

        int width = 0, height = 0, nr_channels = 0;
        unsigned char *data = stbi_load(path, &width, &height, &nr_channels, 4);
        const unsigned char *upload = fallback;

        if(data) {
            if(width == CONFIG_TILE_TEX_RES && height == CONFIG_TILE_TEX_RES) {
                upload = data;
            } else if(stbir_resize_uint8(data, width, height, 0,
                                         resized, CONFIG_TILE_TEX_RES, CONFIG_TILE_TEX_RES, 0, 4)) {
                upload = resized;
            } else {
                fill_fallback_terrain_rgba(fallback, npixels, (uint32_t)i);
            }
        } else {
            fill_fallback_terrain_rgba(fallback, npixels, (uint32_t)i);
        }

        [texture replaceRegion:region
                   mipmapLevel:0
                         slice:i
                     withBytes:upload
                   bytesPerRow:bytes_per_row
                 bytesPerImage:bytes_per_image];
        stbi_image_free(data);
    }

    free(fallback);
    free(resized);
    s_terrain_texture_array = texture;
    s_terrain_texture_count = (uint32_t)*num_textures;
}

static void update_water_mask(const struct map *map, const struct map_resolution *res)
{
    if(!map || !res || !s_device)
        return;

    const size_t total = (size_t)res->chunk_w * (size_t)res->chunk_h
                       * (size_t)res->tile_w * (size_t)res->tile_h;
    unsigned char *mask = malloc(total);
    if(!mask)
        return;

    size_t idx = 0;
    for(int chunk_r = 0; chunk_r < res->chunk_h; chunk_r++) {
    for(int chunk_c = 0; chunk_c < res->chunk_w; chunk_c++) {
    for(int tile_r = 0; tile_r < res->tile_h; tile_r++) {
    for(int tile_c = 0; tile_c < res->tile_w; tile_c++, idx++) {
        struct tile *tile = NULL;
        struct tile_desc td = {chunk_r, chunk_c, tile_r, tile_c};
        bool exists = M_TileForDesc(map, td, &tile);
        mask[idx] = (exists && tile && M_Tile_BaseHeight(tile) < 0) ? 1u : 0u;
    }}}}

    s_water_buffer = [s_device newBufferWithBytes:mask
        length:total options:MTLResourceStorageModeShared];
    free(mask);
}

static void render_terrain_draw(const struct render_private *priv, const mat4x4_t *model)
{
    if(!priv || !priv->metal_is_terrain)
        return;
    if(!priv->metal_terrain_verts || !priv->metal_terrain_verts_size || !priv->mesh.num_verts)
        return;
    if(!s_have_scene_view || !s_have_scene_proj)
        return;
    if(s_water_scene_pass_active && s_water_scene_encoder) {
        draw_terrain_to_encoder(s_water_scene_encoder, priv, model, s_scene_view, s_scene_proj);
        return;
    }
    frame_begin();
    if(!s_frame_encoder)
        return;

    draw_terrain_to_encoder(s_frame_encoder, priv, model, s_scene_view, s_scene_proj);
}

static void water_target_size(NSUInteger *out_w, NSUInteger *out_h)
{
    const CGFloat drawable_w = s_layer.drawableSize.width;
    const CGFloat drawable_h = s_layer.drawableSize.height;
    NSUInteger width = drawable_w > 0.0 ? (NSUInteger)floor(drawable_w / 2.5) : 1;
    width = width > 0 ? width : 1;

    CGFloat aspect = (drawable_h > 0.0) ? (drawable_w / drawable_h) : 1.0;
    if(aspect <= 0.0)
        aspect = 1.0;

    NSUInteger height = (NSUInteger)floor(width / aspect);
    height = height > 0 ? height : 1;
    *out_w = width;
    *out_h = height;
}

static bool ensure_water_target_texture(id<MTLTexture> __strong *slot,
                                        MTLPixelFormat pixel_format,
                                        NSUInteger width,
                                        NSUInteger height,
                                        MTLTextureUsage usage)
{
    if(*slot
    && (*slot).width == width
    && (*slot).height == height
    && (*slot).pixelFormat == pixel_format) {
        return true;
    }

    *slot = nil;
    MTLTextureDescriptor *desc = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:pixel_format
                                                                                     width:width
                                                                                    height:height
                                                                                 mipmapped:NO];
    desc.storageMode = MTLStorageModePrivate;
    desc.usage = usage;
    *slot = [s_device newTextureWithDescriptor:desc];
    return *slot != nil;
}

static bool ensure_water_scene_textures(void)
{
    NSUInteger width = 0, height = 0;
    water_target_size(&width, &height);

    const MTLTextureUsage color_usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
    const MTLTextureUsage depth_usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
    return ensure_water_target_texture(&s_water_reflection_texture, MTLPixelFormatBGRA8Unorm, width, height, color_usage)
        && ensure_water_target_texture(&s_water_reflection_depth_texture, MTLPixelFormatDepth32Float, width, height, depth_usage)
        && ensure_water_target_texture(&s_water_refraction_texture, MTLPixelFormatBGRA8Unorm, width, height, color_usage)
        && ensure_water_target_texture(&s_water_refraction_depth_texture, MTLPixelFormatDepth32Float, width, height, depth_usage);
}

static void render_water_scene_terrain(const struct render_input *in,
                                       const struct camera *cam,
                                       id<MTLTexture> color,
                                       id<MTLTexture> depth,
                                       MTLClearColor clear_color,
                                       bool enabled,
                                       int clip_mode)
{
    if(!in || !in->map || !cam || !color || !depth || !s_frame_command_buffer)
        return;

    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    pass.colorAttachments[0].texture = color;
    pass.colorAttachments[0].loadAction = MTLLoadActionClear;
    pass.colorAttachments[0].storeAction = MTLStoreActionStore;
    pass.colorAttachments[0].clearColor = clear_color;
    pass.depthAttachment.texture = depth;
    pass.depthAttachment.loadAction = MTLLoadActionClear;
    pass.depthAttachment.storeAction = MTLStoreActionStore;
    pass.depthAttachment.clearDepth = 1.0;

    s_water_scene_encoder = [s_frame_command_buffer renderCommandEncoderWithDescriptor:pass];
    if(!s_water_scene_encoder)
        return;

    MTLViewport viewport = {
        .originX = 0.0,
        .originY = 0.0,
        .width = color.width,
        .height = color.height,
        .znear = 0.0,
        .zfar = 1.0
    };
    [s_water_scene_encoder setViewport:viewport];

    s_water_scene_pass_active = true;
    s_water_scene_clip_mode = clip_mode;
    if(enabled) {
        M_RenderVisibleMap(in->map, cam, false, RENDER_PASS_REGULAR);
        render_batched_anim_entities(&in->cam_vis_anim);
        render_batched_stat_entities(&in->cam_vis_stat);
    }
    s_water_scene_clip_mode = METAL_WATER_CLIP_NONE;
    s_water_scene_pass_active = false;

    [s_water_scene_encoder endEncoding];
    s_water_scene_encoder = nil;
}

static void render_water_scene_textures(const struct render_input *in,
                                        const bool *refraction,
                                        const bool *reflection)
{
    if(!in || !in->map || !s_frame_command_buffer)
        return;
    if(!ensure_water_scene_textures())
        return;

    frame_end();

    matrix_float4x4 saved_view = s_scene_view;
    matrix_float4x4 saved_proj = s_scene_proj;
    vector_float3 saved_view_pos = s_scene_view_pos;
    bool saved_have_view = s_have_scene_view;
    bool saved_have_proj = s_have_scene_proj;
    bool saved_shadows = s_shadows_enabled;
    bool saved_have_anim_uid = s_have_anim_uid;
    uint32_t saved_anim_uid = s_curr_anim_uid;

    const bool refract_on = refraction ? *refraction : true;
    const bool reflect_on = reflection ? *reflection : true;
    s_shadows_enabled = false;

    render_water_scene_terrain(in, in->cam, s_water_refraction_texture, s_water_refraction_depth_texture,
        MTLClearColorMake(0.0, 0.0, 0.0, 1.0), refract_on, METAL_WATER_CLIP_KEEP_BELOW);

    struct camera *reflect_cam = Camera_New();
    if(reflect_cam) {
        vec3_t cam_pos = Camera_GetPos(in->cam);
        vec3_t cam_dir = Camera_GetDir(in->cam);
        cam_pos.y -= (cam_pos.y - METAL_WATER_LEVEL) * 2.0f;
        cam_dir.y *= -1.0f;
        Camera_SetPos(reflect_cam, cam_pos);
        Camera_SetDir(reflect_cam, cam_dir);
        Camera_TickFinishPerspective(reflect_cam);

        render_water_scene_terrain(in, reflect_cam, s_water_reflection_texture, s_water_reflection_depth_texture,
            MTLClearColorMake(0.2, 0.3, 0.3, 1.0), reflect_on, METAL_WATER_CLIP_KEEP_ABOVE);
        Camera_Free(reflect_cam);
    }

    s_scene_view = saved_view;
    s_scene_proj = saved_proj;
    s_scene_view_pos = saved_view_pos;
    s_have_scene_view = saved_have_view;
    s_have_scene_proj = saved_have_proj;
    s_shadows_enabled = saved_shadows;
    s_have_anim_uid = saved_have_anim_uid;
    s_curr_anim_uid = saved_anim_uid;
}

static void render_water_surface(const struct render_input *in, const bool *refraction, const bool *reflection)
{
    if(!in || !in->map || !s_water_buffer)
        return;
    if(!s_have_scene_view || !s_have_scene_proj)
        return;
    if(s_map_chunk_size.x == 0u || s_map_chunk_size.y == 0u
    || s_map_tiles_per_chunk.x == 0u || s_map_tiles_per_chunk.y == 0u) {
        return;
    }

    frame_begin();
    if(!s_frame_encoder || !frame_has_depth())
        return;

    render_water_scene_textures(in, refraction, reflection);
    if(!frame_resume() || !frame_has_depth())
        return;

    id<MTLRenderPipelineState> pipeline = ensure_water_surface_pipeline(frame_uses_msaa());
    if(!pipeline)
        return;

    const vec3_t tl = (vec3_t){+1.0f, METAL_WATER_LEVEL, +1.0f};
    const vec3_t tr = (vec3_t){-1.0f, METAL_WATER_LEVEL, +1.0f};
    const vec3_t bl = (vec3_t){+1.0f, METAL_WATER_LEVEL, -1.0f};
    const vec3_t br = (vec3_t){-1.0f, METAL_WATER_LEVEL, -1.0f};
    const vec3_t verts[] = {
        tl, bl, tr,
        bl, br, tr
    };

    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:verts
        length:sizeof(verts) options:MTLResourceStorageModeShared];
    if(!vertex_buffer)
        return;

    vec3_t pos = M_GetCenterPos(in->map);
    mat4x4_t trans;
    PFM_Mat4x4_MakeTrans(pos.x, pos.y, pos.z, &trans);

    struct map_resolution res;
    M_GetResolution(in->map, &res);
    const float half_x = (res.chunk_w * res.tile_w * X_COORDS_PER_TILE) / 2.0f;
    const float half_z = (res.chunk_h * res.tile_h * Z_COORDS_PER_TILE) / 2.0f;

    mat4x4_t scale;
    PFM_Mat4x4_MakeScale(half_x, 1.0f, half_z, &scale);

    mat4x4_t model;
    PFM_Mat4x4_Mult4x4(&trans, &scale, &model);

    vec3_t map_pos = M_GetPos(in->map);
    struct metal_water_surface_uniforms uniforms = {
        .model = matrix_from_pf_mat4(&model),
        .view = s_scene_view,
        .proj = s_scene_proj,
        .view_pos = {s_scene_view_pos.x, s_scene_view_pos.y, s_scene_view_pos.z, 1.0f},
        .map_pos = {map_pos.x, map_pos.z},
        .tile_world_size = {
            res.field_w / res.tile_w,
            res.field_h / res.tile_h,
        },
        .chunk_size = {
            (uint32_t)res.chunk_w,
            (uint32_t)res.chunk_h,
        },
        .tiles_per_chunk = {
            (uint32_t)res.tile_w,
            (uint32_t)res.tile_h,
        },
        .water_params = {
            SDL_GetTicks() / 1000.0f,
            s_water_buffer ? 1.0f : 0.0f,
            s_fog_buffer ? 1.0f : 0.0f,
            (s_water_dudv_texture && s_water_normal_texture) ? 1.0f : 0.0f,
        },
        .water_texture_params = {
            s_layer.drawableSize.width,
            s_layer.drawableSize.height,
            (reflection && *reflection && s_water_reflection_texture) ? 1.0f : 0.0f,
            (refraction && *refraction && s_water_refraction_texture) ? 1.0f : 0.0f,
        },
    };

    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [s_frame_encoder setRenderPipelineState:pipeline];
    id<MTLDepthStencilState> depth_state = ensure_depth_state(false);
    if(depth_state)
        [s_frame_encoder setDepthStencilState:depth_state];
    [s_frame_encoder setCullMode:MTLCullModeNone];
    [s_frame_encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [s_frame_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_frame_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder setFragmentBuffer:uniform_buffer offset:0 atIndex:1];
    if(s_fog_buffer)
        [s_frame_encoder setFragmentBuffer:s_fog_buffer offset:0 atIndex:2];
    [s_frame_encoder setFragmentBuffer:s_water_buffer offset:0 atIndex:3];
    if(ensure_scene_sampler()) {
        [s_frame_encoder setFragmentSamplerState:s_scene_sampler atIndex:0];
        if(s_water_dudv_texture)
            [s_frame_encoder setFragmentTexture:s_water_dudv_texture atIndex:0];
        if(s_water_normal_texture)
            [s_frame_encoder setFragmentTexture:s_water_normal_texture atIndex:1];
    }
    if(s_water_reflection_texture)
        [s_frame_encoder setFragmentTexture:s_water_reflection_texture atIndex:2];
    if(s_water_refraction_texture)
        [s_frame_encoder setFragmentTexture:s_water_refraction_texture atIndex:3];
    [s_frame_encoder drawPrimitives:MTLPrimitiveTypeTriangle
                        vertexStart:0
                        vertexCount:sizeof(verts) / sizeof(verts[0])];
}

static void fill_material_uniforms(const struct render_private *priv,
                                   vector_float4 out[MAX_MATERIALS])
{
    for(size_t i = 0; i < MAX_MATERIALS; i++) {
        out[i] = (vector_float4){0.65f, 0.65f, 0.65f, 1.0f};
    }
    for(size_t i = 0; i < priv->num_materials && i < MAX_MATERIALS; i++) {
        out[i] = (vector_float4){
            priv->materials[i].diffuse_clr.x,
            priv->materials[i].diffuse_clr.y,
            priv->materials[i].diffuse_clr.z,
            1.0f
        };
    }
}

static void fill_fallback_material_rgba(unsigned char *dst, size_t npixels, const struct material *mat)
{
    unsigned char rgba[4] = {
        (unsigned char)SDL_clamp((int)lrintf(mat->diffuse_clr.x * 255.0f), 0, 255),
        (unsigned char)SDL_clamp((int)lrintf(mat->diffuse_clr.y * 255.0f), 0, 255),
        (unsigned char)SDL_clamp((int)lrintf(mat->diffuse_clr.z * 255.0f), 0, 255),
        255,
    };
    for(size_t i = 0; i < npixels; i++) {
        memcpy(dst + i * 4, rgba, 4);
    }
}

static bool texture_has_cutout_alpha(const unsigned char *rgba, size_t npixels)
{
    if(!rgba)
        return false;

    for(size_t i = 0; i < npixels; i++) {
        unsigned char alpha = rgba[i * 4 + 3];
        if(alpha < 250) {
            return true;
        }
    }
    return false;
}

static id<MTLTexture> ensure_material_texture_array(struct render_private *priv)
{
    if(!priv || !priv->num_materials || !s_device)
        return nil;
    if(priv->metal_material_texture_array)
        return (__bridge id<MTLTexture>)priv->metal_material_texture_array;

    MTLTextureDescriptor *desc = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                                                                     width:CONFIG_ARR_TEX_RES
                                                                                    height:CONFIG_ARR_TEX_RES
                                                                                 mipmapped:NO];
    desc.textureType = MTLTextureType2DArray;
    desc.arrayLength = priv->num_materials;
    desc.usage = MTLTextureUsageShaderRead;

    id<MTLTexture> texture = [s_device newTextureWithDescriptor:desc];
    if(!texture)
        return nil;

    const size_t bytes_per_row = CONFIG_ARR_TEX_RES * 4;
    const size_t bytes_per_image = bytes_per_row * CONFIG_ARR_TEX_RES;
    const size_t npixels = CONFIG_ARR_TEX_RES * CONFIG_ARR_TEX_RES;
    unsigned char *fallback = malloc(bytes_per_image);
    unsigned char *resized = malloc(bytes_per_image);
    if(!fallback || !resized) {
        free(fallback);
        free(resized);
        return nil;
    }

    bool has_cutout_alpha = false;
    MTLRegion region = MTLRegionMake2D(0, 0, CONFIG_ARR_TEX_RES, CONFIG_ARR_TEX_RES);
    for(size_t i = 0; i < priv->num_materials; i++) {
        const struct material *mat = &priv->materials[i];
        unsigned char *data = NULL;
        int width = 0, height = 0, nr_channels = 0;

        if(mat->texname[0]) {
            char primary_path[1024];
            char secondary_path[1024];
            if(priv->metal_asset_basedir[0]) {
                snprintf(primary_path, sizeof(primary_path), "%s/%s", priv->metal_asset_basedir, mat->texname);
            } else {
                snprintf(primary_path, sizeof(primary_path), "%s", mat->texname);
            }
            snprintf(secondary_path, sizeof(secondary_path), "%s/%s", g_basepath, mat->texname);
            data = stbi_load(primary_path, &width, &height, &nr_channels, 4);
            if(!data) {
                data = stbi_load(secondary_path, &width, &height, &nr_channels, 4);
            }
        }

        const unsigned char *upload = fallback;
        if(data) {
            if(width == CONFIG_ARR_TEX_RES && height == CONFIG_ARR_TEX_RES) {
                upload = data;
            } else if(stbir_resize_uint8(data, width, height, 0,
                                         resized, CONFIG_ARR_TEX_RES, CONFIG_ARR_TEX_RES, 0, 4)) {
                upload = resized;
            } else {
                fill_fallback_material_rgba(fallback, npixels, mat);
            }
        } else {
            fill_fallback_material_rgba(fallback, npixels, mat);
        }

        if(upload != fallback && texture_has_cutout_alpha(upload, npixels)) {
            has_cutout_alpha = true;
        }

        [texture replaceRegion:region
                   mipmapLevel:0
                         slice:i
                     withBytes:upload
                   bytesPerRow:bytes_per_row
                 bytesPerImage:bytes_per_image];
        stbi_image_free(data);
    }

    free(fallback);
    free(resized);
    priv->metal_material_texture_array = (__bridge_retained void *)texture;
    priv->metal_material_texture_count = priv->num_materials;
    priv->metal_materials_have_cutout_alpha = has_cutout_alpha;
    return texture;
}

static void render_static_vertex_stream(const struct render_private *priv,
                                        const mat4x4_t *model,
                                        const struct vertex *verts,
                                        size_t verts_size,
                                        bool translucent)
{
    struct render_private *mutable_priv = (struct render_private *)priv;
    id<MTLRenderPipelineState> pipeline = nil;
    id<MTLRenderCommandEncoder> encoder = nil;
    size_t vertex_count = verts_size / sizeof(*verts);
    bool depth_enabled = active_scene_depth_enabled();
    if(!priv || !verts || !verts_size || !priv->mesh.num_verts)
        return;
    if(!vertex_count)
        return;
    if(!s_have_scene_view || !s_have_scene_proj)
        return;
    if(!(s_water_scene_pass_active && s_water_scene_encoder))
        frame_begin();
    encoder = active_scene_encoder();
    if(!encoder)
        return;
    depth_enabled = active_scene_depth_enabled();
    pipeline = ensure_static_mesh_pipeline(translucent, encoder == s_frame_encoder && frame_uses_msaa(), depth_enabled);
    if(!pipeline)
        return;

    id<MTLTexture> texture_array = ensure_material_texture_array(mutable_priv);
    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:verts
        length:verts_size options:MTLResourceStorageModeShared];
    if(!vertex_buffer)
        return;

    struct metal_static_mesh_uniforms uniforms = {
        .model = matrix_from_pf_mat4(model),
        .view = s_scene_view,
        .proj = s_scene_proj,
        .light_space_transform = s_shadow_light_space,
        .effect_params = {(float)mutable_priv->metal_material_texture_count, 0.0f, 0.0f, 0.0f},
        .shadow_params = {
            shadow_enabled_for_draw() ? 1.0f : 0.0f,
            0.0015f,
            0.58f,
            1.25f,
        },
        .clip_params = current_water_clip_params(),
    };
    fill_material_uniforms(priv, uniforms.material_diffuse);

    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [encoder setRenderPipelineState:pipeline];
    if(depth_enabled) {
        id<MTLDepthStencilState> depth_state = ensure_depth_state(!translucent);
        if(depth_state)
            [encoder setDepthStencilState:depth_state];
    } else {
        [encoder setDepthStencilState:nil];
    }
    [encoder setCullMode:mutable_priv->metal_materials_have_cutout_alpha ? MTLCullModeNone : MTLCullModeBack];
    [encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [encoder setFragmentBuffer:uniform_buffer offset:0 atIndex:1];
    if(texture_array && ensure_scene_sampler()) {
        [encoder setFragmentTexture:texture_array atIndex:0];
        [encoder setFragmentSamplerState:s_scene_sampler atIndex:0];
    }
    if(shadow_enabled_for_draw()) {
        [encoder setFragmentTexture:s_shadow_depth_texture atIndex:1];
        [encoder setFragmentSamplerState:s_shadow_sampler atIndex:1];
    }
    [encoder drawPrimitives:MTLPrimitiveTypeTriangle
                vertexStart:0
                vertexCount:vertex_count];
}

static void render_static_mesh_draw(const struct render_private *priv, const mat4x4_t *model, bool translucent)
{
    struct render_private *mutable_priv = (struct render_private *)priv;
    id<MTLRenderPipelineState> pipeline = nil;
    id<MTLRenderCommandEncoder> encoder = nil;
    bool depth_enabled = false;
    if(!priv || !priv->metal_is_static_mesh)
        return;
    if(!priv->metal_static_verts || !priv->metal_static_verts_size)
        return;
    if(!s_have_scene_view || !s_have_scene_proj)
        return;
    if(!(s_water_scene_pass_active && s_water_scene_encoder))
        frame_begin();
    encoder = active_scene_encoder();
    if(!encoder)
        return;
    depth_enabled = active_scene_depth_enabled();
    pipeline = ensure_static_mesh_pipeline(translucent, encoder == s_frame_encoder && frame_uses_msaa(), depth_enabled);
    if(!pipeline)
        return;

    id<MTLTexture> texture_array = ensure_material_texture_array(mutable_priv);
    id<MTLBuffer> vertex_buffer = ensure_persistent_vertex_buffer(
        &mutable_priv->metal_static_vertex_buffer,
        priv->metal_static_verts,
        priv->metal_static_verts_size);
    if(!vertex_buffer)
        return;

    struct metal_static_mesh_uniforms uniforms = {
        .model = matrix_from_pf_mat4(model),
        .view = s_scene_view,
        .proj = s_scene_proj,
        .light_space_transform = s_shadow_light_space,
        .effect_params = {(float)mutable_priv->metal_material_texture_count, 0.0f, 0.0f, 0.0f},
        .shadow_params = {
            shadow_enabled_for_draw() ? 1.0f : 0.0f,
            0.0015f,
            0.58f,
            1.25f,
        },
        .clip_params = current_water_clip_params(),
    };
    fill_material_uniforms(priv, uniforms.material_diffuse);

    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [encoder setRenderPipelineState:pipeline];
    if(depth_enabled) {
        id<MTLDepthStencilState> depth_state = ensure_depth_state(!translucent);
        if(depth_state)
            [encoder setDepthStencilState:depth_state];
    } else {
        [encoder setDepthStencilState:nil];
    }
    [encoder setCullMode:mutable_priv->metal_materials_have_cutout_alpha ? MTLCullModeNone : MTLCullModeBack];
    [encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [encoder setFragmentBuffer:uniform_buffer offset:0 atIndex:1];
    if(texture_array && ensure_scene_sampler()) {
        [encoder setFragmentTexture:texture_array atIndex:0];
        [encoder setFragmentSamplerState:s_scene_sampler atIndex:0];
    }
    if(shadow_enabled_for_draw()) {
        [encoder setFragmentTexture:s_shadow_depth_texture atIndex:1];
        [encoder setFragmentSamplerState:s_shadow_sampler atIndex:1];
    }
    [encoder drawPrimitives:MTLPrimitiveTypeTriangle
                vertexStart:0
                vertexCount:priv->mesh.num_verts];
}

static void render_world_colored_strip(const vec3_t *positions, size_t nverts, const vec3_t *color)
{
    id<MTLRenderPipelineState> pipeline = nil;
    if(!positions || !nverts || !color)
        return;
    if(!s_have_scene_view || !s_have_scene_proj)
        return;

    struct vertex *verts = malloc(nverts * sizeof(*verts));
    if(!verts)
        return;

    for(size_t i = 0; i < nverts; i++) {
        verts[i].pos = positions[i];
        verts[i].uv = (vec2_t){0.0f, 0.0f};
        verts[i].normal = (vec3_t){0.0f, 1.0f, 0.0f};
        verts[i].material_idx = 0;
    }

    frame_begin();
    if(!s_frame_encoder) {
        free(verts);
        return;
    }
    pipeline = ensure_static_mesh_pipeline(false, frame_uses_msaa(), false);
    if(!pipeline) {
        free(verts);
        return;
    }

    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:verts
        length:nverts * sizeof(*verts) options:MTLResourceStorageModeShared];
    free(verts);
    if(!vertex_buffer)
        return;

    mat4x4_t identity;
    PFM_Mat4x4_Identity(&identity);

    struct metal_static_mesh_uniforms uniforms = {
        .model = matrix_from_pf_mat4(&identity),
        .view = s_scene_view,
        .proj = s_scene_proj,
    };
    for(size_t i = 0; i < MAX_MATERIALS; i++) {
        uniforms.material_diffuse[i] = (vector_float4){color->x, color->y, color->z, 1.0f};
    }

    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [s_frame_encoder setRenderPipelineState:pipeline];
    [s_frame_encoder setDepthStencilState:nil];
    [s_frame_encoder setCullMode:MTLCullModeNone];
    [s_frame_encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [s_frame_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_frame_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder setFragmentBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder drawPrimitives:MTLPrimitiveTypeTriangleStrip
                        vertexStart:0
                        vertexCount:nverts];
}

static void render_world_colored_verts(const struct colored_vert *verts, size_t nverts,
                                       MTLPrimitiveType primitive)
{
    id<MTLRenderPipelineState> pipeline = nil;
    if(!verts || !nverts)
        return;
    if(!s_have_scene_view || !s_have_scene_proj)
        return;

    frame_begin();
    if(!s_frame_encoder)
        return;
    pipeline = ensure_world_color_pipeline(frame_uses_msaa());
    if(!pipeline)
        return;

    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:verts
        length:nverts * sizeof(*verts) options:MTLResourceStorageModeShared];
    if(!vertex_buffer)
        return;

    struct metal_world_color_uniforms uniforms = {
        .view = s_scene_view,
        .proj = s_scene_proj,
    };
    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [s_frame_encoder setRenderPipelineState:pipeline];
    [s_frame_encoder setDepthStencilState:nil];
    [s_frame_encoder setCullMode:MTLCullModeNone];
    [s_frame_encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [s_frame_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_frame_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder drawPrimitives:primitive
                        vertexStart:0
                        vertexCount:nverts];
}

static void render_screenspace_colored_triangles(const vec3_t *positions, size_t nverts, const vec3_t *color)
{
    id<MTLRenderPipelineState> pipeline = nil;
    if(!positions || !nverts || !color)
        return;

    struct vertex *verts = malloc(nverts * sizeof(*verts));
    if(!verts)
        return;

    for(size_t i = 0; i < nverts; i++) {
        verts[i].pos = positions[i];
        verts[i].uv = (vec2_t){0.0f, 0.0f};
        verts[i].normal = (vec3_t){0.0f, 1.0f, 0.0f};
        verts[i].material_idx = 0;
    }

    frame_begin();
    if(!s_frame_encoder) {
        free(verts);
        return;
    }
    pipeline = ensure_static_mesh_pipeline(false, frame_uses_msaa(), false);
    if(!pipeline) {
        free(verts);
        return;
    }

    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:verts
        length:nverts * sizeof(*verts) options:MTLResourceStorageModeShared];
    free(verts);
    if(!vertex_buffer)
        return;

    int win_width = 0, win_height = 0;
    Engine_WinDrawableSize(&win_width, &win_height);

    mat4x4_t model, view, proj;
    PFM_Mat4x4_Identity(&model);
    PFM_Mat4x4_Identity(&view);
    PFM_Mat4x4_MakeOrthographic(0.0f, win_width, win_height, 0.0f, -1.0f, 1.0f, &proj);

    struct metal_static_mesh_uniforms uniforms = {
        .model = matrix_from_pf_mat4(&model),
        .view = matrix_from_pf_mat4(&view),
        .proj = matrix_from_pf_mat4(&proj),
    };
    for(size_t i = 0; i < MAX_MATERIALS; i++) {
        uniforms.material_diffuse[i] = (vector_float4){color->x, color->y, color->z, 1.0f};
    }

    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [s_frame_encoder setRenderPipelineState:pipeline];
    [s_frame_encoder setDepthStencilState:nil];
    [s_frame_encoder setCullMode:MTLCullModeNone];
    [s_frame_encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [s_frame_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_frame_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder setFragmentBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder drawPrimitives:MTLPrimitiveTypeTriangle
                        vertexStart:0
                        vertexCount:nverts];
}

static void render_screenspace_line_segment(vec2_t a, vec2_t b, float width, const vec3_t *color)
{
    vec2_t ab;
    PFM_Vec2_Sub(&b, &a, &ab);
    float len = PFM_Vec2_Len(&ab);
    if(len <= 0.0f)
        return;

    vec2_t dir;
    PFM_Vec2_Scale(&ab, 1.0f / len, &dir);
    vec2_t perp = {-dir.y, dir.x};
    float half = fmaxf(width, 1.0f) * 0.5f;
    PFM_Vec2_Scale(&perp, half, &perp);

    vec2_t a0, a1, b0, b1;
    PFM_Vec2_Sub(&a, &perp, &a0);
    PFM_Vec2_Add(&a, &perp, &a1);
    PFM_Vec2_Sub(&b, &perp, &b0);
    PFM_Vec2_Add(&b, &perp, &b1);

    const vec3_t verts[6] = {
        {a0.x, a0.y, 0.0f},
        {a1.x, a1.y, 0.0f},
        {b1.x, b1.y, 0.0f},
        {a0.x, a0.y, 0.0f},
        {b1.x, b1.y, 0.0f},
        {b0.x, b0.y, 0.0f},
    };
    render_screenspace_colored_triangles(verts, 6, color);
}

static void render_screenspace_line_loop(const vec2_t *points, size_t npoints,
                                         float width, const vec3_t *color)
{
    if(!points || npoints < 2 || !color)
        return;

    for(size_t i = 0; i < npoints; i++) {
        render_screenspace_line_segment(points[i], points[(i + 1) % npoints], width, color);
    }
}

static bool clip_axis(float p, float q, float *t0, float *t1)
{
    if(p == 0.0f)
        return q >= 0.0f;

    float r = q / p;
    if(p < 0.0f) {
        if(r > *t1)
            return false;
        if(r > *t0)
            *t0 = r;
    } else {
        if(r < *t0)
            return false;
        if(r < *t1)
            *t1 = r;
    }
    return true;
}

static bool clip_segment_to_unit_square(vec2_t a, vec2_t b, vec2_t *out_a, vec2_t *out_b)
{
    float t0 = 0.0f;
    float t1 = 1.0f;
    vec2_t d;
    PFM_Vec2_Sub(&b, &a, &d);

    if(!clip_axis(-d.x, a.x + 1.0f, &t0, &t1))
        return false;
    if(!clip_axis( d.x, 1.0f - a.x, &t0, &t1))
        return false;
    if(!clip_axis(-d.y, a.y + 1.0f, &t0, &t1))
        return false;
    if(!clip_axis( d.y, 1.0f - a.y, &t0, &t1))
        return false;

    *out_a = (vec2_t){a.x + d.x * t0, a.y + d.y * t0};
    *out_b = (vec2_t){a.x + d.x * t1, a.y + d.y * t1};
    return true;
}

static void render_box2d(const vec2_t *screen_pos, const vec2_t *signed_size,
                         const vec3_t *color, const float *width)
{
    if(!screen_pos || !signed_size || !color || !width)
        return;

    float x0 = screen_pos->x;
    float y0 = screen_pos->y;
    float x1 = screen_pos->x + signed_size->x;
    float y1 = screen_pos->y + signed_size->y;

    float left = fminf(x0, x1);
    float right = fmaxf(x0, x1);
    float top = fminf(y0, y1);
    float bottom = fmaxf(y0, y1);

    float w = right - left;
    float h = bottom - top;
    if(w <= 0.0f || h <= 0.0f)
        return;

    float t = fmaxf(*width, 1.0f);
    t = fminf(t, w * 0.5f);
    t = fminf(t, h * 0.5f);
    if(t <= 0.0f)
        return;

    const vec3_t verts[] = {
        {left, top, 0.0f}, {right, top, 0.0f}, {right, top + t, 0.0f},
        {left, top, 0.0f}, {right, top + t, 0.0f}, {left, top + t, 0.0f},

        {left, bottom - t, 0.0f}, {right, bottom - t, 0.0f}, {right, bottom, 0.0f},
        {left, bottom - t, 0.0f}, {right, bottom, 0.0f}, {left, bottom, 0.0f},

        {left, top + t, 0.0f}, {left + t, top + t, 0.0f}, {left + t, bottom - t, 0.0f},
        {left, top + t, 0.0f}, {left + t, bottom - t, 0.0f}, {left, bottom - t, 0.0f},

        {right - t, top + t, 0.0f}, {right, top + t, 0.0f}, {right, bottom - t, 0.0f},
        {right - t, top + t, 0.0f}, {right, bottom - t, 0.0f}, {right - t, bottom - t, 0.0f},
    };

    render_screenspace_colored_triangles(verts, sizeof(verts) / sizeof(verts[0]), color);
}

static void render_screenspace_rect(float left, float top, float right, float bottom,
                                    const vec3_t *color)
{
    if(!color)
        return;
    if(right <= left || bottom <= top)
        return;

    const vec3_t verts[] = {
        {left,  top,    0.0f},
        {right, top,    0.0f},
        {right, bottom, 0.0f},
        {left,  top,    0.0f},
        {right, bottom, 0.0f},
        {left,  bottom, 0.0f},
    };
    render_screenspace_colored_triangles(verts, sizeof(verts) / sizeof(verts[0]), color);
}

static void render_healthbars(const size_t *num_ents, GLfloat *ent_health_pc,
                              vec3_t *ent_top_pos_ws, int *yoffsets,
                              const struct camera *cam)
{
    if(!num_ents || !ent_health_pc || !ent_top_pos_ws || !yoffsets || !cam)
        return;
    if(*num_ents == 0)
        return;

    int width, height;
    Engine_WinDrawableSize(&width, &height);

    mat4x4_t view, proj;
    Camera_MakeViewMat(cam, &view);
    Camera_MakeProjMat(cam, &proj);

    const float half_h = fmaxf(4.0f / 1080.0f * height, 4.0f);
    const float half_w = 40.0f / 1080.0f * height;
    const float border = 1.0f;
    const vec3_t bg = {0.0f, 0.0f, 0.0f};

    for(size_t i = 0; i < *num_ents; i++) {
        vec4_t ent_top_homo = {
            ent_top_pos_ws[i].x,
            ent_top_pos_ws[i].y,
            ent_top_pos_ws[i].z,
            1.0f
        };

        vec4_t tmp = {0};
        vec4_t clip = {0};
        PFM_Mat4x4_Mult4x1(&view, &ent_top_homo, &tmp);
        PFM_Mat4x4_Mult4x1(&proj, &tmp, &clip);
        if(fabsf(clip.w) < 0.0001f)
            continue;

        vec3_t ndc = {clip.x / clip.w, clip.y / clip.w, clip.z / clip.w};
        if(ndc.z < -1.0f || ndc.z > 1.0f)
            continue;

        float screen_x = (ndc.x + 1.0f) * width * 0.5f;
        float screen_y = height - ((ndc.y + 1.0f) * height * 0.5f);
        screen_y += yoffsets[i];

        float left = screen_x - half_w;
        float right = screen_x + half_w;
        float top = screen_y - half_h;
        float bottom = screen_y + half_h;

        render_screenspace_rect(left, top, right, bottom, &bg);

        float inner_left = left + border;
        float inner_right = right - border;
        float inner_top = top + border;
        float inner_bottom = bottom - border;
        float fill_right = inner_left + (inner_right - inner_left) * SDL_clamp(ent_health_pc[i], 0.0f, 1.0f);

        vec3_t fill = {
            1.0f - SDL_clamp(ent_health_pc[i], 0.0f, 1.0f),
            SDL_clamp(ent_health_pc[i], 0.0f, 1.0f),
            0.0f
        };
        render_screenspace_rect(inner_left, inner_top, fill_right, inner_bottom, &fill);
    }
}

static void render_map_overlay_quads(vec2_t *xz_corners, vec3_t *colors, const size_t *count,
                                     mat4x4_t *model, bool *on_water_surface,
                                     const struct map *map)
{
    if(!xz_corners || !colors || !count || !model || !on_water_surface || !map || !*count)
        return;

    const size_t surf_verts = *count * 4 * 3;
    const size_t line_verts = *count * 4 * 2;
    struct colored_vert *surf_vbuff = malloc(surf_verts * sizeof(*surf_vbuff));
    struct colored_vert *line_vbuff = malloc(line_verts * sizeof(*line_vbuff));
    if(!surf_vbuff || !line_vbuff) {
        free(surf_vbuff);
        free(line_vbuff);
        return;
    }

    struct colored_vert *surf_base = surf_vbuff;
    struct colored_vert *line_base = line_vbuff;

    for(size_t i = 0; i < *count; i++, xz_corners += 4, colors++) {
        vec2_t center = (vec2_t){
            (xz_corners[0].x + xz_corners[1].x + xz_corners[2].x + xz_corners[3].x) / 4.0f,
            (xz_corners[0].y + xz_corners[1].y + xz_corners[2].y + xz_corners[3].y) / 4.0f,
        };
        vec2_t verts[5] = {
            center,
            xz_corners[0], xz_corners[1],
            xz_corners[2], xz_corners[3],
        };
        vec3_t verts_3d[5];

        for(int j = 0; j < (int)(sizeof(verts) / sizeof(verts[0])); j++) {
            vec4_t xz_homo = {verts[j].x, 0.0f, verts[j].y, 1.0f};
            vec4_t ws_homo;
            PFM_Mat4x4_Mult4x1(model, &xz_homo, &ws_homo);
            ws_homo.x /= ws_homo.w;
            ws_homo.z /= ws_homo.w;

            float height = M_HeightAtPoint(map, (vec2_t){ws_homo.x, ws_homo.z}) + 0.1f;
            if(*on_water_surface)
                height = MAX(height, 0.1f);

            verts_3d[j] = (vec3_t){ws_homo.x, height, ws_homo.z};
        }

        vec4_t surf_color = {colors->x, colors->y, colors->z, 0.25f};
        vec4_t line_color = {colors->x, colors->y, colors->z, 0.75f};

        *surf_base++ = (struct colored_vert){verts_3d[0], surf_color};
        *surf_base++ = (struct colored_vert){verts_3d[1], surf_color};
        *surf_base++ = (struct colored_vert){verts_3d[2], surf_color};

        *surf_base++ = (struct colored_vert){verts_3d[0], surf_color};
        *surf_base++ = (struct colored_vert){verts_3d[2], surf_color};
        *surf_base++ = (struct colored_vert){verts_3d[3], surf_color};

        *surf_base++ = (struct colored_vert){verts_3d[0], surf_color};
        *surf_base++ = (struct colored_vert){verts_3d[3], surf_color};
        *surf_base++ = (struct colored_vert){verts_3d[4], surf_color};

        *surf_base++ = (struct colored_vert){verts_3d[0], surf_color};
        *surf_base++ = (struct colored_vert){verts_3d[4], surf_color};
        *surf_base++ = (struct colored_vert){verts_3d[1], surf_color};

        *line_base++ = (struct colored_vert){verts_3d[1], line_color};
        *line_base++ = (struct colored_vert){verts_3d[2], line_color};

        *line_base++ = (struct colored_vert){verts_3d[2], line_color};
        *line_base++ = (struct colored_vert){verts_3d[3], line_color};

        *line_base++ = (struct colored_vert){verts_3d[3], line_color};
        *line_base++ = (struct colored_vert){verts_3d[4], line_color};

        *line_base++ = (struct colored_vert){verts_3d[4], line_color};
        *line_base++ = (struct colored_vert){verts_3d[1], line_color};
    }

    render_world_colored_verts(surf_vbuff, surf_verts, MTLPrimitiveTypeTriangle);
    render_world_colored_verts(line_vbuff, line_verts, MTLPrimitiveTypeLine);

    free(surf_vbuff);
    free(line_vbuff);
}

static void render_minimap_bake(const struct map *map, void **chunk_rprivates, mat4x4_t *chunk_model_mats)
{
    if(!map || !chunk_rprivates || !chunk_model_mats)
        return;
    if(!ensure_terrain_pipeline(false, false))
        return;

    matrix_float4x4 view, proj;
    if(!build_minimap_view_proj(map, &view, &proj))
        return;

    MTLTextureDescriptor *desc = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatBGRA8Unorm
                                                                                     width:METAL_MINIMAP_RES
                                                                                    height:METAL_MINIMAP_RES
                                                                                 mipmapped:NO];
    desc.usage = MTLTextureUsageRenderTarget | MTLTextureUsageShaderRead;
    s_minimap_texture = [s_device newTextureWithDescriptor:desc];
    if(!s_minimap_texture)
        return;

    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    pass.colorAttachments[0].texture = s_minimap_texture;
    pass.colorAttachments[0].loadAction = MTLLoadActionClear;
    pass.colorAttachments[0].storeAction = MTLStoreActionStore;
    pass.colorAttachments[0].clearColor = MTLClearColorMake(0.0, 0.0, 0.0, 1.0);

    id<MTLCommandBuffer> command_buffer = [s_queue commandBuffer];
    id<MTLRenderCommandEncoder> encoder = [command_buffer renderCommandEncoderWithDescriptor:pass];
    if(!encoder)
        return;

    MTLViewport viewport = {
        .originX = 0.0,
        .originY = 0.0,
        .width = METAL_MINIMAP_RES,
        .height = METAL_MINIMAP_RES,
        .znear = 0.0,
        .zfar = 1.0
    };
    [encoder setViewport:viewport];

    struct map_resolution res;
    M_GetResolution(map, &res);
    for(int r = 0; r < res.chunk_h; r++) {
    for(int c = 0; c < res.chunk_w; c++) {
        size_t idx = r * res.chunk_w + c;
        draw_terrain_to_encoder(encoder, chunk_rprivates[idx], &chunk_model_mats[idx], view, proj);
    }}

    [encoder endEncoding];
    [command_buffer commit];
    [command_buffer waitUntilCompleted];
}

static void render_minimap_update_chunk(const struct map *map, void *chunk_rprivate,
                                        mat4x4_t *chunk_model)
{
    if(!map || !chunk_rprivate || !chunk_model || !s_minimap_texture)
        return;
    if(!ensure_terrain_pipeline(false, false))
        return;

    matrix_float4x4 view, proj;
    if(!build_minimap_view_proj(map, &view, &proj))
        return;

    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    pass.colorAttachments[0].texture = s_minimap_texture;
    pass.colorAttachments[0].loadAction = MTLLoadActionLoad;
    pass.colorAttachments[0].storeAction = MTLStoreActionStore;

    id<MTLCommandBuffer> command_buffer = [s_queue commandBuffer];
    id<MTLRenderCommandEncoder> encoder = [command_buffer renderCommandEncoderWithDescriptor:pass];
    if(!encoder)
        return;

    MTLViewport viewport = {
        .originX = 0.0,
        .originY = 0.0,
        .width = METAL_MINIMAP_RES,
        .height = METAL_MINIMAP_RES,
        .znear = 0.0,
        .zfar = 1.0
    };
    [encoder setViewport:viewport];
    draw_terrain_to_encoder(encoder, chunk_rprivate, chunk_model, view, proj);
    [encoder endEncoding];
    [command_buffer commit];
    [command_buffer waitUntilCompleted];
}

static void render_minimap_frustum(const struct map *map, const struct camera *cam,
                                   const mat4x4_t *model)
{
    if(!map || !cam || !model)
        return;

    vec3_t tr, tl, br, bl;
    struct frustum cam_frust;
    Camera_MakeFrustum(cam, &cam_frust);
    vec3_t cam_pos = Camera_GetPos(cam);

    struct plane ground_plane = {
        .point = {0.0f, 0.0f, 0.0f},
        .normal = {0.0f, 1.0f, 0.0f},
    };

    vec3_t tr_dir, tl_dir, br_dir, bl_dir;
    PFM_Vec3_Sub(&cam_frust.ftr, &cam_frust.ntr, &tr_dir);
    PFM_Vec3_Sub(&cam_frust.ftl, &cam_frust.ntl, &tl_dir);
    PFM_Vec3_Sub(&cam_frust.fbr, &cam_frust.nbr, &br_dir);
    PFM_Vec3_Sub(&cam_frust.fbl, &cam_frust.nbl, &bl_dir);
    PFM_Vec3_Normal(&tr_dir, &tr_dir);
    PFM_Vec3_Normal(&tl_dir, &tl_dir);
    PFM_Vec3_Normal(&br_dir, &br_dir);
    PFM_Vec3_Normal(&bl_dir, &bl_dir);

    float t;
    if(!C_RayIntersectsPlane(cam_pos, tr_dir, ground_plane, &t))
        t = 1e10f;
    PFM_Vec3_Scale(&tr_dir, t, &tr_dir);
    PFM_Vec3_Add(&cam_pos, &tr_dir, &tr);

    if(!C_RayIntersectsPlane(cam_pos, tl_dir, ground_plane, &t))
        t = 1e10f;
    PFM_Vec3_Scale(&tl_dir, t, &tl_dir);
    PFM_Vec3_Add(&cam_pos, &tl_dir, &tl);

    if(!C_RayIntersectsPlane(cam_pos, br_dir, ground_plane, &t))
        return;
    PFM_Vec3_Scale(&br_dir, t, &br_dir);
    PFM_Vec3_Add(&cam_pos, &br_dir, &br);

    if(!C_RayIntersectsPlane(cam_pos, bl_dir, ground_plane, &t))
        return;
    PFM_Vec3_Scale(&bl_dir, t, &bl_dir);
    PFM_Vec3_Add(&cam_pos, &bl_dir, &bl);

    vec2_t norm[4] = {
        M_WorldCoordsToNormMapCoords(map, (vec2_t){tr.x, tr.z}),
        M_WorldCoordsToNormMapCoords(map, (vec2_t){tl.x, tl.z}),
        M_WorldCoordsToNormMapCoords(map, (vec2_t){bl.x, bl.z}),
        M_WorldCoordsToNormMapCoords(map, (vec2_t){br.x, br.z}),
    };

    vec3_t black = {0.0f, 0.0f, 0.0f};
    vec3_t white = {1.0f, 1.0f, 1.0f};
    for(int i = 0; i < 4; i++) {
        vec2_t clipped_a, clipped_b;
        if(!clip_segment_to_unit_square(norm[i], norm[(i + 1) % 4], &clipped_a, &clipped_b))
            continue;

        vec2_t black_a = transform_model_point(model, clipped_a);
        vec2_t black_b = transform_model_point(model, clipped_b);
        vec2_t white_a = {black_a.x - 1.0f, black_a.y - 1.0f};
        vec2_t white_b = {black_b.x - 1.0f, black_b.y - 1.0f};

        render_screenspace_line_segment(black_a, black_b, 1.0f, &black);
        render_screenspace_line_segment(white_a, white_b, 1.0f, &white);
    }
}

static void render_minimap(const struct map *map, const struct camera *cam,
                           vec2_t *center_pos, const int *side_len_px, vec4_t *border_clr)
{
    if(!center_pos || !side_len_px || !border_clr || !s_minimap_texture)
        return;

    mat4x4_t model, border_model;
    make_minimap_models(center_pos, side_len_px, &model, &border_model);

    const vec2_t border_local[4] = {
        {-1.0f, -1.0f},
        {-1.0f,  1.0f},
        { 1.0f,  1.0f},
        { 1.0f, -1.0f},
    };
    const vec3_t border_verts[6] = {
        {transform_model_point(&border_model, border_local[0]).x, transform_model_point(&border_model, border_local[0]).y, 0.0f},
        {transform_model_point(&border_model, border_local[1]).x, transform_model_point(&border_model, border_local[1]).y, 0.0f},
        {transform_model_point(&border_model, border_local[2]).x, transform_model_point(&border_model, border_local[2]).y, 0.0f},
        {transform_model_point(&border_model, border_local[0]).x, transform_model_point(&border_model, border_local[0]).y, 0.0f},
        {transform_model_point(&border_model, border_local[2]).x, transform_model_point(&border_model, border_local[2]).y, 0.0f},
        {transform_model_point(&border_model, border_local[3]).x, transform_model_point(&border_model, border_local[3]).y, 0.0f},
    };
    vec3_t border_color = {border_clr->x, border_clr->y, border_clr->z};
    render_screenspace_colored_triangles(border_verts, 6, &border_color);

    struct ui_vert quad[6];
    build_minimap_quad(&model, quad);
    render_ui_triangles(quad, 6, s_minimap_texture);

    if(cam)
        render_minimap_frustum(map, cam, &model);
}

static void render_minimap_units(const struct map *map, vec2_t *center_pos,
                                 const int *side_len_px, size_t *nunits,
                                 vec2_t *posbuff, vec3_t *colorbuff)
{
    (void)map;
    if(!center_pos || !side_len_px || !nunits || !posbuff || !colorbuff)
        return;
    if(*nunits == 0)
        return;

    mat4x4_t model, border_model;
    make_minimap_models(center_pos, side_len_px, &model, &border_model);

    float half_extent = 4.0f / (*side_len_px);
    for(size_t i = 0; i < *nunits; i++) {
        vec2_t offset = posbuff[i];
        const vec2_t local[4] = {
            {offset.x - half_extent, offset.y - half_extent},
            {offset.x - half_extent, offset.y + half_extent},
            {offset.x + half_extent, offset.y + half_extent},
            {offset.x + half_extent, offset.y - half_extent},
        };

        const vec3_t verts[6] = {
            {transform_model_point(&model, local[0]).x, transform_model_point(&model, local[0]).y, 0.0f},
            {transform_model_point(&model, local[1]).x, transform_model_point(&model, local[1]).y, 0.0f},
            {transform_model_point(&model, local[2]).x, transform_model_point(&model, local[2]).y, 0.0f},
            {transform_model_point(&model, local[0]).x, transform_model_point(&model, local[0]).y, 0.0f},
            {transform_model_point(&model, local[2]).x, transform_model_point(&model, local[2]).y, 0.0f},
            {transform_model_point(&model, local[3]).x, transform_model_point(&model, local[3]).y, 0.0f},
        };
        render_screenspace_colored_triangles(verts, 6, &colorbuff[i]);
    }
}

static void render_minimap_free(void)
{
    s_minimap_texture = nil;
}

static void render_selection_circle(const vec2_t *xz, const float *radius, const float *width,
                                    const vec3_t *color, const struct map *map)
{
    if(!xz || !radius || !width || !color || !map)
        return;

    enum { NUM_SAMPLES = 48, NUM_VERTS = NUM_SAMPLES * 2 + 2 };
    vec3_t vbuff[NUM_VERTS];

    for(int i = 0; i < NUM_SAMPLES * 2; i += 2) {
        float theta = (2.0f * (float)M_PI) * ((float)i / NUM_SAMPLES);

        float x_near = xz->x + (*radius) * cosf(theta);
        float z_near = xz->z - (*radius) * sinf(theta);

        float x_far = xz->x + (*radius + *width) * cosf(theta);
        float z_far = xz->z - (*radius + *width) * sinf(theta);

        float height_near = M_HeightAtPoint(map, M_ClampedMapCoordinate(map, (vec2_t){x_near, z_near}));
        float height_far = M_HeightAtPoint(map, M_ClampedMapCoordinate(map, (vec2_t){x_far, z_far}));

        vbuff[i] = (vec3_t){x_near, height_near + 0.1f, z_near};
        vbuff[i + 1] = (vec3_t){x_far, height_far + 0.1f, z_far};
    }
    vbuff[NUM_SAMPLES * 2] = vbuff[0];
    vbuff[NUM_SAMPLES * 2 + 1] = vbuff[1];

    render_world_colored_strip(vbuff, NUM_VERTS, color);
}

static void render_selection_rectangle(const struct obb *box, const float *width,
                                       const vec3_t *color, const struct map *map)
{
    if(!box || !width || !color || !map)
        return;

    const float pad = 1.0f;
    vec2_t corners[4] = {
        {box->corners[0].x, box->corners[0].z},
        {box->corners[1].x, box->corners[1].z},
        {box->corners[5].x, box->corners[5].z},
        {box->corners[4].x, box->corners[4].z},
    };

    float lens[4];
    vec2_t deltas[4];
    PFM_Vec2_Sub(&corners[1], &corners[0], &deltas[0]);
    PFM_Vec2_Sub(&corners[2], &corners[1], &deltas[1]);
    PFM_Vec2_Sub(&corners[3], &corners[2], &deltas[2]);
    PFM_Vec2_Sub(&corners[0], &corners[3], &deltas[3]);

    for(int i = 0; i < 4; i++) {
        lens[i] = PFM_Vec2_Len(&deltas[i]);
        PFM_Vec2_Normal(&deltas[i], &deltas[i]);
    }

    float sample_dist = fminf(X_COORDS_PER_TILE, Z_COORDS_PER_TILE);
    size_t nsamples = 0;
    for(int i = 0; i < 4; i++) {
        nsamples += (size_t)ceilf(lens[i] / sample_dist) + 1;
    }

    const int nverts = (int)(nsamples * 2 + 2);
    vec3_t *vbuff = malloc(nverts * sizeof(*vbuff));
    if(!vbuff)
        return;

    int vbuff_idx = 0;
    for(int i = 0; i < 4; i++) {
        vec3_t pdir = (vec3_t){-deltas[i].z, 0.0f, deltas[i].x};
        PFM_Vec3_Scale(&pdir, *width / 2.0f, &pdir);

        int side_samples = (int)ceilf(lens[i] / sample_dist) + 1;
        for(int j = 0; j < side_samples; j++) {
            vec2_t dir = deltas[i];
            PFM_Vec2_Scale(&dir, fminf(j * sample_dist, lens[i]), &dir);

            vec2_t xz;
            PFM_Vec2_Add(&corners[i], &dir, &xz);

            vec3_t point = (vec3_t){
                xz.x,
                M_HeightAtPoint(map, M_ClampedMapCoordinate(map, xz)) + 0.1f,
                xz.z
            };

            vec3_t nudge = (vec3_t){-deltas[i].z, 0.0f, deltas[i].x};
            vec3_t nudged;
            PFM_Vec3_Scale(&nudge, pad, &nudge);
            PFM_Vec3_Add(&point, &nudge, &nudged);

            PFM_Vec3_Sub(&nudged, &pdir, &vbuff[vbuff_idx++]);
            PFM_Vec3_Add(&nudged, &pdir, &vbuff[vbuff_idx++]);
        }
    }

    vbuff[nsamples * 2 + 0] = vbuff[0];
    vbuff[nsamples * 2 + 1] = vbuff[1];
    render_world_colored_strip(vbuff, nverts, color);
    free(vbuff);
}

static void render_skinned_mesh_draw(const struct render_private *priv, const mat4x4_t *model, bool translucent)
{
    if(!priv || !priv->metal_is_anim_mesh || !priv->uses_pose_buffer)
        return;
    if(!priv->metal_anim_verts || !priv->metal_anim_verts_size || !priv->mesh.num_verts)
        return;
    if(!s_have_anim_uid)
        return;

    const struct skeleton *skel = A_GetBindSkeleton(s_curr_anim_uid);
    if(!skel || !skel->inv_bind_poses)
        return;

    size_t njoints = 0;
    mat4x4_t curr_pose[METAL_MAX_JOINTS];
    A_GetCurrPoseMats(s_curr_anim_uid, &njoints, curr_pose);
    if(!njoints)
        return;
    if(njoints > METAL_MAX_JOINTS)
        njoints = METAL_MAX_JOINTS;

    mat4x4_t skin_mats[METAL_MAX_JOINTS];
    for(size_t i = 0; i < njoints; i++) {
        PFM_Mat4x4_Mult4x4(&curr_pose[i], &skel->inv_bind_poses[i], &skin_mats[i]);
    }

    struct anim_vert *src = priv->metal_anim_verts;
    struct vertex *skinned = malloc(priv->mesh.num_verts * sizeof(*skinned));
    if(!skinned)
        return;

    for(int i = 0; i < priv->mesh.num_verts; i++) {
        struct anim_vert *curr = &src[i];
        vec4_t blended_pos = {0};
        vec4_t blended_normal = {0};
        bool weighted = false;

        for(int j = 0; j < 6; j++) {
            float weight = curr->weights[j];
            uint32_t joint_idx = curr->joint_indices[j];
            if(weight <= 0.0f || joint_idx >= njoints)
                continue;

            vec4_t in_pos = {curr->pos.x, curr->pos.y, curr->pos.z, 1.0f};
            vec4_t out_pos = {0};
            PFM_Mat4x4_Mult4x1(&skin_mats[joint_idx], &in_pos, &out_pos);
            blended_pos.x += out_pos.x * weight;
            blended_pos.y += out_pos.y * weight;
            blended_pos.z += out_pos.z * weight;
            blended_pos.w += out_pos.w * weight;

            vec4_t in_normal = {curr->normal.x, curr->normal.y, curr->normal.z, 0.0f};
            vec4_t out_normal = {0};
            PFM_Mat4x4_Mult4x1(&skin_mats[joint_idx], &in_normal, &out_normal);
            blended_normal.x += out_normal.x * weight;
            blended_normal.y += out_normal.y * weight;
            blended_normal.z += out_normal.z * weight;
            weighted = true;
        }

        skinned[i].uv = curr->uv;
        skinned[i].material_idx = curr->material_idx;

        if(weighted) {
            skinned[i].pos = (vec3_t){blended_pos.x, blended_pos.y, blended_pos.z};
            vec3_t normal = (vec3_t){blended_normal.x, blended_normal.y, blended_normal.z};
            if(PFM_Vec3_Len(&normal) > 0.0001f) {
                PFM_Vec3_Normal(&normal, &skinned[i].normal);
            }else{
                skinned[i].normal = curr->normal;
            }
        }else{
            skinned[i].pos = curr->pos;
            skinned[i].normal = curr->normal;
        }
    }

    render_static_vertex_stream(priv, model, skinned, priv->mesh.num_verts * sizeof(*skinned), translucent);
    free(skinned);
}

static void append_transformed_static_mesh(const struct render_private *priv,
                                           const mat4x4_t *model,
                                           struct vertex *dst,
                                           size_t *dst_idx)
{
    if(!priv || !priv->metal_static_verts || !dst || !dst_idx)
        return;

    const struct vertex *src = priv->metal_static_verts;
    mat4x4_t model_copy = *model;
    mat4x4_t inv_model, normal_model;
    PFM_Mat4x4_Inverse(&model_copy, &inv_model);
    PFM_Mat4x4_Transpose(&inv_model, &normal_model);

    for(int i = 0; i < priv->mesh.num_verts; i++) {
        vec4_t in_pos = {src[i].pos.x, src[i].pos.y, src[i].pos.z, 1.0f};
        vec4_t out_pos = {0};
        PFM_Mat4x4_Mult4x1(&model_copy, &in_pos, &out_pos);

        vec4_t in_normal = {src[i].normal.x, src[i].normal.y, src[i].normal.z, 0.0f};
        vec4_t out_normal = {0};
        PFM_Mat4x4_Mult4x1(&normal_model, &in_normal, &out_normal);

        struct vertex *curr = &dst[(*dst_idx)++];
        curr->pos = (vec3_t){out_pos.x, out_pos.y, out_pos.z};
        curr->uv = src[i].uv;
        curr->material_idx = src[i].material_idx;

        vec3_t normal = (vec3_t){out_normal.x, out_normal.y, out_normal.z};
        if(PFM_Vec3_Len(&normal) > 0.0001f) {
            PFM_Vec3_Normal(&normal, &curr->normal);
        }else{
            curr->normal = src[i].normal;
        }
    }
}

static bool append_skinned_anim_mesh(const struct render_private *priv,
                                     uint32_t uid,
                                     const mat4x4_t *model,
                                     struct vertex *dst,
                                     size_t *dst_idx)
{
    if(!priv || !priv->metal_is_anim_mesh || !priv->uses_pose_buffer)
        return false;
    if(!priv->metal_anim_verts || !priv->mesh.num_verts || !dst || !dst_idx)
        return false;

    const struct skeleton *skel = A_GetBindSkeleton(uid);
    if(!skel || !skel->inv_bind_poses)
        return false;

    size_t njoints = 0;
    mat4x4_t curr_pose[METAL_MAX_JOINTS];
    A_GetCurrPoseMats(uid, &njoints, curr_pose);
    if(!njoints)
        return false;
    if(njoints > METAL_MAX_JOINTS)
        njoints = METAL_MAX_JOINTS;

    mat4x4_t skin_mats[METAL_MAX_JOINTS];
    for(size_t i = 0; i < njoints; i++) {
        PFM_Mat4x4_Mult4x4(&curr_pose[i], &skel->inv_bind_poses[i], &skin_mats[i]);
    }

    mat4x4_t model_copy = *model;
    mat4x4_t inv_model, normal_model;
    PFM_Mat4x4_Inverse(&model_copy, &inv_model);
    PFM_Mat4x4_Transpose(&inv_model, &normal_model);

    struct anim_vert *src = priv->metal_anim_verts;
    for(int i = 0; i < priv->mesh.num_verts; i++) {
        struct anim_vert *curr = &src[i];
        vec4_t blended_pos = {0};
        vec4_t blended_normal = {0};
        bool weighted = false;

        for(int j = 0; j < 6; j++) {
            float weight = curr->weights[j];
            uint32_t joint_idx = curr->joint_indices[j];
            if(weight <= 0.0f || joint_idx >= njoints)
                continue;

            vec4_t in_pos = {curr->pos.x, curr->pos.y, curr->pos.z, 1.0f};
            vec4_t out_pos = {0};
            PFM_Mat4x4_Mult4x1(&skin_mats[joint_idx], &in_pos, &out_pos);
            blended_pos.x += out_pos.x * weight;
            blended_pos.y += out_pos.y * weight;
            blended_pos.z += out_pos.z * weight;
            blended_pos.w += out_pos.w * weight;

            vec4_t in_normal = {curr->normal.x, curr->normal.y, curr->normal.z, 0.0f};
            vec4_t out_normal = {0};
            PFM_Mat4x4_Mult4x1(&skin_mats[joint_idx], &in_normal, &out_normal);
            blended_normal.x += out_normal.x * weight;
            blended_normal.y += out_normal.y * weight;
            blended_normal.z += out_normal.z * weight;
            weighted = true;
        }

        vec3_t local_pos;
        vec3_t local_normal;
        if(weighted) {
            local_pos = (vec3_t){blended_pos.x, blended_pos.y, blended_pos.z};
            local_normal = (vec3_t){blended_normal.x, blended_normal.y, blended_normal.z};
            if(PFM_Vec3_Len(&local_normal) > 0.0001f) {
                PFM_Vec3_Normal(&local_normal, &local_normal);
            }else{
                local_normal = curr->normal;
            }
        }else{
            local_pos = curr->pos;
            local_normal = curr->normal;
        }

        vec4_t in_pos = {local_pos.x, local_pos.y, local_pos.z, 1.0f};
        vec4_t out_pos = {0};
        PFM_Mat4x4_Mult4x1(&model_copy, &in_pos, &out_pos);

        vec4_t in_normal = {local_normal.x, local_normal.y, local_normal.z, 0.0f};
        vec4_t out_normal = {0};
        PFM_Mat4x4_Mult4x1(&normal_model, &in_normal, &out_normal);

        struct vertex *out = &dst[(*dst_idx)++];
        out->pos = (vec3_t){out_pos.x, out_pos.y, out_pos.z};
        out->uv = curr->uv;
        out->material_idx = curr->material_idx;

        vec3_t normal = (vec3_t){out_normal.x, out_normal.y, out_normal.z};
        if(PFM_Vec3_Len(&normal) > 0.0001f) {
            PFM_Vec3_Normal(&normal, &out->normal);
        }else{
            out->normal = local_normal;
        }
    }

    return true;
}

static void render_batched_stat_entities(const vec_rstat_t *ents)
{
    vec_rstat_t *mutable_ents = (vec_rstat_t *)ents;
    if(!mutable_ents)
        return;

    size_t nents = vec_size(mutable_ents);
    bool *consumed = calloc(nents, sizeof(*consumed));
    if(!consumed) {
        for(int i = 0; i < nents; i++) {
            const struct ent_stat_rstate *curr = &vec_AT(mutable_ents, i);
            const struct render_private *priv = curr->render_private;
            if(!priv || !priv->metal_is_static_mesh || priv->uses_pose_buffer)
                continue;
            render_static_mesh_draw(priv, &curr->model, curr->translucent);
        }
        return;
    }

    for(int i = 0; i < nents; i++) {
        if(consumed[i])
            continue;

        const struct ent_stat_rstate *curr = &vec_AT(mutable_ents, i);
        const struct render_private *priv = curr->render_private;
        if(!priv || !priv->metal_is_static_mesh || priv->uses_pose_buffer)
            continue;

        if(curr->translucent && !priv->metal_static_verts) {
            consumed[i] = true;
            render_static_mesh_draw(priv, &curr->model, true);
            continue;
        }

        if(curr->translucent) {
            size_t total_verts = priv->mesh.num_verts;
            int j = i + 1;
            while(j < nents) {
                const struct ent_stat_rstate *other = &vec_AT(mutable_ents, j);
                if(!other->translucent || other->render_private != priv)
                    break;
                total_verts += priv->mesh.num_verts;
                j++;
            }

            if(j == i + 1) {
                consumed[i] = true;
                render_static_mesh_draw(priv, &curr->model, true);
                continue;
            }

            struct vertex *combined = malloc(total_verts * sizeof(*combined));
            if(!combined) {
                consumed[i] = true;
                render_static_mesh_draw(priv, &curr->model, true);
                continue;
            }

            size_t dst_idx = 0;
            for(int k = i; k < j; k++) {
                const struct ent_stat_rstate *other = &vec_AT(mutable_ents, k);
                consumed[k] = true;
                append_transformed_static_mesh(priv, &other->model, combined, &dst_idx);
            }

            mat4x4_t identity;
            PFM_Mat4x4_Identity(&identity);
            render_static_vertex_stream(priv, &identity, combined, dst_idx * sizeof(*combined), true);
            free(combined);
            continue;
        }

        if(!priv->metal_static_verts || !priv->mesh.num_verts) {
            consumed[i] = true;
            render_static_mesh_draw(priv, &curr->model, false);
            continue;
        }

        size_t group_count = 1;
        size_t total_verts = priv->mesh.num_verts;
        consumed[i] = true;

        for(int j = i + 1; j < nents; j++) {
            if(consumed[j])
                continue;

            const struct ent_stat_rstate *other = &vec_AT(mutable_ents, j);
            if(other->translucent || other->render_private != priv)
                continue;

            consumed[j] = true;
            group_count++;
            total_verts += priv->mesh.num_verts;
        }

        if(group_count == 1) {
            render_static_mesh_draw(priv, &curr->model, false);
            continue;
        }

        struct vertex *combined = malloc(total_verts * sizeof(*combined));
        if(!combined) {
            render_static_mesh_draw(priv, &curr->model, false);
            for(int j = i + 1; j < nents; j++) {
                const struct ent_stat_rstate *other = &vec_AT(mutable_ents, j);
                if(other->translucent || other->render_private != priv)
                    continue;
                render_static_mesh_draw(priv, &other->model, false);
            }
            continue;
        }

        size_t dst_idx = 0;
        append_transformed_static_mesh(priv, &curr->model, combined, &dst_idx);
        for(int j = i + 1; j < nents; j++) {
            const struct ent_stat_rstate *other = &vec_AT(mutable_ents, j);
            if(other->translucent || other->render_private != priv)
                continue;
            append_transformed_static_mesh(priv, &other->model, combined, &dst_idx);
        }

        mat4x4_t identity;
        PFM_Mat4x4_Identity(&identity);
        render_static_vertex_stream(priv, &identity, combined, dst_idx * sizeof(*combined), false);
        free(combined);
    }

    free(consumed);
}

static void render_batched_anim_entities(const vec_ranim_t *ents)
{
    vec_ranim_t *mutable_ents = (vec_ranim_t *)ents;
    if(!mutable_ents)
        return;

    size_t nents = vec_size(mutable_ents);
    bool *consumed = calloc(nents, sizeof(*consumed));
    if(!consumed) {
        for(int i = 0; i < nents; i++) {
            const struct ent_anim_rstate *curr = &vec_AT(mutable_ents, i);
            const struct render_private *priv = curr->render_private;
            if(!priv || !priv->metal_is_anim_mesh || !priv->uses_pose_buffer)
                continue;
            s_curr_anim_uid = curr->uid;
            s_have_anim_uid = true;
            render_skinned_mesh_draw(priv, &curr->model, curr->translucent);
        }
        return;
    }

    for(int i = 0; i < nents; i++) {
        if(consumed[i])
            continue;

        const struct ent_anim_rstate *curr = &vec_AT(mutable_ents, i);
        const struct render_private *priv = curr->render_private;
        if(!priv || !priv->metal_is_anim_mesh || !priv->uses_pose_buffer)
            continue;

        if(curr->translucent && !priv->metal_anim_verts) {
            consumed[i] = true;
            s_curr_anim_uid = curr->uid;
            s_have_anim_uid = true;
            render_skinned_mesh_draw(priv, &curr->model, true);
            continue;
        }

        if(curr->translucent) {
            size_t total_verts = priv->mesh.num_verts;
            int j = i + 1;
            while(j < nents) {
                const struct ent_anim_rstate *other = &vec_AT(mutable_ents, j);
                if(!other->translucent || other->render_private != priv)
                    break;
                total_verts += priv->mesh.num_verts;
                j++;
            }

            if(j == i + 1) {
                consumed[i] = true;
                s_curr_anim_uid = curr->uid;
                s_have_anim_uid = true;
                render_skinned_mesh_draw(priv, &curr->model, true);
                continue;
            }

            struct vertex *combined = malloc(total_verts * sizeof(*combined));
            if(!combined) {
                consumed[i] = true;
                s_curr_anim_uid = curr->uid;
                s_have_anim_uid = true;
                render_skinned_mesh_draw(priv, &curr->model, true);
                continue;
            }

            bool ok = true;
            size_t dst_idx = 0;
            for(int k = i; ok && k < j; k++) {
                const struct ent_anim_rstate *other = &vec_AT(mutable_ents, k);
                consumed[k] = true;
                ok = append_skinned_anim_mesh(priv, other->uid, &other->model, combined, &dst_idx);
            }

            if(!ok) {
                free(combined);
                for(int k = i; k < j; k++) {
                    const struct ent_anim_rstate *other = &vec_AT(mutable_ents, k);
                    s_curr_anim_uid = other->uid;
                    s_have_anim_uid = true;
                    render_skinned_mesh_draw(priv, &other->model, true);
                }
                continue;
            }

            mat4x4_t identity;
            PFM_Mat4x4_Identity(&identity);
            render_static_vertex_stream(priv, &identity, combined, dst_idx * sizeof(*combined), true);
            free(combined);
            continue;
        }

        if(!priv->metal_anim_verts || !priv->mesh.num_verts) {
            consumed[i] = true;
            s_curr_anim_uid = curr->uid;
            s_have_anim_uid = true;
            render_skinned_mesh_draw(priv, &curr->model, false);
            continue;
        }

        size_t group_count = 1;
        size_t total_verts = priv->mesh.num_verts;
        consumed[i] = true;

        for(int j = i + 1; j < nents; j++) {
            if(consumed[j])
                continue;

            const struct ent_anim_rstate *other = &vec_AT(mutable_ents, j);
            if(other->translucent || other->render_private != priv)
                continue;

            consumed[j] = true;
            group_count++;
            total_verts += priv->mesh.num_verts;
        }

        if(group_count == 1) {
            s_curr_anim_uid = curr->uid;
            s_have_anim_uid = true;
            render_skinned_mesh_draw(priv, &curr->model, false);
            continue;
        }

        struct vertex *combined = malloc(total_verts * sizeof(*combined));
        if(!combined) {
            s_curr_anim_uid = curr->uid;
            s_have_anim_uid = true;
            render_skinned_mesh_draw(priv, &curr->model, false);
            for(int j = i + 1; j < nents; j++) {
                const struct ent_anim_rstate *other = &vec_AT(mutable_ents, j);
                if(other->translucent || other->render_private != priv)
                    continue;
                s_curr_anim_uid = other->uid;
                s_have_anim_uid = true;
                render_skinned_mesh_draw(priv, &other->model, false);
            }
            continue;
        }

        bool ok = true;
        size_t dst_idx = 0;
        ok = append_skinned_anim_mesh(priv, curr->uid, &curr->model, combined, &dst_idx);
        for(int j = i + 1; ok && j < nents; j++) {
            const struct ent_anim_rstate *other = &vec_AT(mutable_ents, j);
            if(other->translucent || other->render_private != priv)
                continue;
            ok = append_skinned_anim_mesh(priv, other->uid, &other->model, combined, &dst_idx);
        }

        if(!ok) {
            free(combined);
            s_curr_anim_uid = curr->uid;
            s_have_anim_uid = true;
            render_skinned_mesh_draw(priv, &curr->model, false);
            for(int j = i + 1; j < nents; j++) {
                const struct ent_anim_rstate *other = &vec_AT(mutable_ents, j);
                if(other->translucent || other->render_private != priv)
                    continue;
                s_curr_anim_uid = other->uid;
                s_have_anim_uid = true;
                render_skinned_mesh_draw(priv, &other->model, false);
            }
            continue;
        }

        mat4x4_t identity;
        PFM_Mat4x4_Identity(&identity);
        render_static_vertex_stream(priv, &identity, combined, dst_idx * sizeof(*combined), false);
        free(combined);
    }

    free(consumed);
}

static void dispatch_or_drop_cmd(struct rcmd cmd)
{
    if(cmd.func == R_GL_BeginFrame) {
        R_Metal_FrameBegin();
        return;
    }
    if(cmd.func == R_GL_EndFrame) {
        R_Metal_FrameEnd();
        return;
    }
    if(cmd.func == R_GL_SetScreenspaceDrawMode
    || cmd.func == R_GL_SwapchainPresentLast
    || cmd.func == R_GL_DrawLoadingScreen) {
        return;
    }
    if(cmd.func == R_GL_SetViewMatAndPos) {
        s_scene_view = matrix_from_pf_mat4(cmd.args[0]);
        if(cmd.args[1]) {
            const vec3_t *pos = cmd.args[1];
            s_scene_view_pos = (vector_float3){pos->x, pos->y, pos->z};
        }
        s_have_scene_view = true;
        return;
    }
    if(cmd.func == R_GL_SetProj) {
        s_scene_proj = matrix_from_pf_mat4(cmd.args[0]);
        s_have_scene_proj = true;
        return;
    }
    if(cmd.func == R_GL_AnimSetUniforms) {
        s_curr_anim_uid = *(const uint32_t *)cmd.args[2];
        s_have_anim_uid = true;
        return;
    }
    if(cmd.func == R_GL_MapInit) {
        update_terrain_textures(cmd.args[0], cmd.args[1]);
        return;
    }
    if(cmd.func == R_GL_WaterInit) {
        init_water_resources();
        return;
    }
    if(cmd.func == R_GL_WaterShutdown) {
        s_water_dudv_texture = nil;
        s_water_normal_texture = nil;
        return;
    }
    if(cmd.func == R_GL_DrawWater) {
        render_water_surface(cmd.args[0], cmd.args[1], cmd.args[2]);
        return;
    }
    if(cmd.func == R_GL_MapBegin) {
        const bool *shadows = cmd.args[0];
        const vec2_t *pos = cmd.args[1];
        const struct map_resolution *res = cmd.args[4];
        const struct map *map = cmd.args[5];
        s_shadows_enabled = shadows ? *shadows : false;
        s_map_pos = (vector_float2){pos->x, pos->y};
        s_map_tile_world_size = (vector_float2){
            res->field_w / res->tile_w,
            res->field_h / res->tile_h,
        };
        s_map_chunk_size = (vector_uint2){
            (uint32_t)res->chunk_w,
            (uint32_t)res->chunk_h,
        };
        s_map_tiles_per_chunk = (vector_uint2){
            (uint32_t)res->tile_w,
            (uint32_t)res->tile_h,
        };
        update_water_mask(map, res);
        return;
    }
    if(cmd.func == R_GL_MapEnd) {
        return;
    }
    if(cmd.func == R_GL_MapShutdown) {
        s_terrain_texture_array = nil;
        s_terrain_texture_count = 0;
        s_water_buffer = nil;
        s_fog_buffer = nil;
        return;
    }
    if(cmd.func == R_GL_MapUpdateFog) {
        update_fog_texture(cmd.args[0], cmd.args[1]);
        return;
    }
    if(cmd.func == R_GL_SetShadowsEnabled) {
        s_shadows_enabled = cmd.args[0] ? *(const bool *)cmd.args[0] : false;
        return;
    }
    if(cmd.func == R_GL_DepthPassBegin) {
        shadow_pass_begin(cmd.args[0], cmd.args[1], cmd.args[2]);
        return;
    }
    if(cmd.func == R_GL_DepthPassEnd) {
        shadow_pass_end();
        return;
    }
    if(cmd.func == R_GL_RenderDepthMap) {
        render_shadow_depth_draw(cmd.args[0], cmd.args[1]);
        return;
    }
    if(cmd.func == R_GL_Batch_AllocChunks
    || cmd.func == R_GL_Batch_Reset) {
        return;
    }
    if(cmd.func == R_GL_Batch_RenderDepthMap) {
        const struct render_input *in = cmd.args[0];
        render_shadow_batched_anim_entities(&in->light_vis_anim);
        render_shadow_batched_stat_entities(&in->light_vis_stat);
        return;
    }
    if(cmd.func == R_GL_Batch_Draw) {
        const struct render_input *in = cmd.args[0];
        render_batched_anim_entities(&in->cam_vis_anim);
        render_batched_stat_entities(&in->cam_vis_stat);
        return;
    }
    if(cmd.func == R_GL_Batch_DrawWithID) {
        const struct render_input *in = cmd.args[0];
        render_batched_anim_entities(&in->cam_vis_anim);
        render_batched_stat_entities(&in->cam_vis_stat);
        return;
    }
    if(cmd.func == R_GL_Draw) {
        const struct render_private *priv = cmd.args[0];
        bool translucent = cmd.args[2] ? *(const bool *)cmd.args[2] : false;
        if(priv && priv->metal_is_terrain) {
            render_terrain_draw(priv, cmd.args[1]);
            return;
        }
        if(priv && priv->metal_is_static_mesh && !priv->uses_pose_buffer) {
            render_static_mesh_draw(priv, cmd.args[1], translucent);
            return;
        }
        if(priv && priv->metal_is_anim_mesh && priv->uses_pose_buffer) {
            render_skinned_mesh_draw(priv, cmd.args[1], translucent);
        }
        return;
    }
    if(cmd.func == R_GL_DrawSelectionCircle) {
        render_selection_circle(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4]);
        return;
    }
    if(cmd.func == R_GL_DrawSelectionRectangle) {
        render_selection_rectangle(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3]);
        return;
    }
    if(cmd.func == R_GL_DrawBox2D) {
        render_box2d(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3]);
        return;
    }
    if(cmd.func == R_GL_DrawHealthbars) {
        render_healthbars(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4]);
        return;
    }
    if(cmd.func == R_GL_DrawMapOverlayQuads) {
        render_map_overlay_quads(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4], cmd.args[5]);
        return;
    }
    if(cmd.func == R_GL_MinimapBake) {
        render_minimap_bake(cmd.args[0], cmd.args[1], cmd.args[2]);
        return;
    }
    if(cmd.func == R_GL_MinimapUpdateChunk) {
        render_minimap_update_chunk(cmd.args[0], cmd.args[1], cmd.args[2]);
        return;
    }
    if(cmd.func == R_GL_MinimapRender) {
        render_minimap(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4]);
        return;
    }
    if(cmd.func == R_GL_MinimapRenderUnits) {
        render_minimap_units(cmd.args[0], cmd.args[1], cmd.args[2], cmd.args[3], cmd.args[4], cmd.args[5]);
        return;
    }
    if(cmd.func == R_GL_MinimapFree) {
        render_minimap_free();
        return;
    }

    if(cmd.func == R_GL_UI_Init
    || cmd.func == R_GL_UI_Shutdown
    || cmd.func == R_GL_UI_Render
    || cmd.func == R_GL_UI_UploadFontAtlas
    || cmd.func == R_Metal_Backend_CommandSetSwapInterval
    || cmd.func == R_Metal_Backend_CommandSetDebugLogMask
    || cmd.func == R_Metal_Backend_CommandSetTraceGPU) {
        render_dispatch_cmd(cmd);
        return;
    }
}

static void process_cmds(queue_rcmd_t *cmds)
{
    while(queue_size(*cmds) > 0) {
        struct rcmd curr;
        queue_rcmd_pop(cmds, &curr);
        dispatch_or_drop_cmd(curr);
    }
}

static bool render_init_ctx(struct render_init_arg *arg)
{
    (void)arg;

    s_device = MTLCreateSystemDefaultDevice();
    if(!s_device) {
        fprintf(stderr, "Failed to create Metal device.\n");
        return false;
    }

    s_queue = [s_device newCommandQueue];
    if(!s_queue) {
        fprintf(stderr, "Failed to create Metal command queue.\n");
        return false;
    }

    s_layer = (__bridge CAMetalLayer *)SDL_Metal_GetLayer(s_metal_view);
    if(!s_layer) {
        fprintf(stderr, "Failed to acquire CAMetalLayer.\n");
        return false;
    }

    s_layer.device = s_device;
    s_layer.pixelFormat = MTLPixelFormatBGRA8Unorm;
    s_layer.framebufferOnly = NO;
    s_layer.displaySyncEnabled = YES;
    s_layer.allowsNextDrawableTimeout = NO;
    if([s_layer respondsToSelector:@selector(setMaximumDrawableCount:)]) {
        s_layer.maximumDrawableCount = 3;
    }
    update_drawable_size();

    strncpy(s_info_vendor, "Apple", sizeof(s_info_vendor) - 1);
    const char *name = [[s_device name] UTF8String];
    strncpy(s_info_renderer, name ? name : "Metal Device", sizeof(s_info_renderer) - 1);
    strncpy(s_info_version, "Metal", sizeof(s_info_version) - 1);
    strncpy(s_info_sl_version, "MSL", sizeof(s_info_sl_version) - 1);
    s_have_scene_view = false;
    s_have_scene_proj = false;
    s_scene_view_pos = (vector_float3){0.0f, 0.0f, 0.0f};
    s_have_anim_uid = false;
    s_shadow_pass_active = false;
    s_shadow_map_valid = false;
    s_shadows_enabled = false;
    s_frame_inflight_reserved = false;
    return true;
}

static void render_destroy_ctx(void)
{
    frame_abort();
    shadow_pass_end();
    release_scene_resources();
    release_ui_resources();
#if !OS_OBJECT_USE_OBJC
    if(s_inflight_semaphore)
        dispatch_release(s_inflight_semaphore);
#endif
    s_inflight_semaphore = NULL;
    s_layer = nil;
    s_queue = nil;
    s_device = nil;
    if(s_metal_view) {
        SDL_Metal_DestroyView(s_metal_view);
        s_metal_view = NULL;
    }
}

static int render(void *data)
{
    @autoreleasepool {
        s_rstate = (struct render_sync_state *)data;
        s_window = s_rstate->arg->in_window;

        Engine_SetRenderThreadID(SDL_ThreadID());

        bool quit = render_wait_cmd(s_rstate);
        assert(!quit);
        bool initialized = render_init_ctx(s_rstate->arg);
        s_rstate->arg->out_success = initialized;
        s_rstate->arg = NULL;
        render_signal_done(s_rstate, RSTAT_DONE);

        while(initialized) {
            @autoreleasepool {
                quit = render_wait_cmd(s_rstate);
                if(quit)
                    break;

                process_cmds(&G_GetRenderWS()->commands);
                if(s_rstate->swap_buffers || s_frame_command_buffer) {
                    frame_present();
                }

                render_signal_done(s_rstate, RSTAT_DONE);
            }
        }

        if(initialized)
            render_destroy_ctx();
    }
    return 0;
}

SDL_Thread *R_Metal_Backend_Run(struct render_sync_state *rstate)
{
    ASSERT_IN_MAIN_THREAD();

    s_metal_view = SDL_Metal_CreateView(rstate->arg->in_window);
    if(!s_metal_view) {
        fprintf(stderr, "SDL_Metal_CreateView failed: %s\n", SDL_GetError());
        return NULL;
    }

    return SDL_CreateThread(render, "render", rstate);
}

void R_Metal_Backend_InitAttributes(void)
{
}

bool R_Metal_Backend_ComputeShaderSupported(void)
{
    return false;
}

const char *R_Metal_Backend_GetInfo(enum render_info attr)
{
    switch(attr) {
    case RENDER_INFO_VENDOR:     return s_info_vendor;
    case RENDER_INFO_RENDERER:   return s_info_renderer;
    case RENDER_INFO_VERSION:    return s_info_version;
    case RENDER_INFO_SL_VERSION: return s_info_sl_version;
    case RENDER_INFO_BACKEND:    return "METAL";
    default: assert(0); return NULL;
    }
}

Uint32 R_Metal_Backend_WindowFlags(void)
{
    return SDL_WINDOW_METAL | SDL_WINDOW_SHOWN;
}

void R_Metal_Backend_WindowDrawableSize(SDL_Window *window, int *out_w, int *out_h)
{
    SDL_Metal_GetDrawableSize(window, out_w, out_h);
}

void R_Metal_Backend_PresentWindow(SDL_Window *window)
{
    (void)window;
    frame_present();
}

void R_Metal_Backend_Yield(void)
{
    ASSERT_IN_RENDER_THREAD();
    frame_present();
}

void R_Metal_Backend_CommandSetSwapInterval(const bool *on)
{
    (void)on;
}

void R_Metal_Backend_CommandSetDebugLogMask(const int *mask)
{
    (void)mask;
}

void R_Metal_Backend_CommandSetTraceGPU(const bool *on)
{
    g_trace_gpu = *on;
}

void R_Metal_Backend_DispatchCmd(struct rcmd cmd)
{
    dispatch_or_drop_cmd(cmd);
}

void R_Metal_FrameBegin(void)
{
    frame_begin();
}

void R_Metal_FrameEnd(void)
{
    frame_end();
}

void R_Metal_UI_Init(void)
{
    (void)ensure_ui_pipeline(false);
}

void R_Metal_UI_Shutdown(void)
{
    release_ui_resources();
}

void R_Metal_UI_UploadFontAtlas(void *image, const int *w, const int *h)
{
    if(!s_device)
        return;

    s_ui_font_texture = nil;

    MTLTextureDescriptor *desc = [MTLTextureDescriptor texture2DDescriptorWithPixelFormat:MTLPixelFormatRGBA8Unorm
                                                                                     width:*w
                                                                                    height:*h
                                                                                 mipmapped:NO];
    desc.usage = MTLTextureUsageShaderRead;
    s_ui_font_texture = [s_device newTextureWithDescriptor:desc];
    if(!s_ui_font_texture)
        return;

    MTLRegion region = {
        {0, 0, 0},
        {(NSUInteger)*w, (NSUInteger)*h, 1}
    };
    [s_ui_font_texture replaceRegion:region mipmapLevel:0 withBytes:image bytesPerRow:(NSUInteger)(*w * 4)];
}

void R_Metal_UI_Render(const struct nk_draw_list *dl)
{
    render_ui_draw_list(dl);
}
