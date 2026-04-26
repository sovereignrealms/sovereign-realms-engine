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
#include "../lib/public/mem.h"

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
static id<MTLRenderPipelineState> s_terrain_pipeline;
static id<MTLRenderPipelineState> s_static_mesh_pipeline;
static id<MTLSamplerState>       s_ui_sampler;
static id<MTLTexture>            s_ui_font_texture;
static id<MTLTexture>            s_minimap_texture;

static id<CAMetalDrawable>       s_frame_drawable;
static id<MTLCommandBuffer>      s_frame_command_buffer;
static id<MTLRenderCommandEncoder> s_frame_encoder;

static char s_info_vendor[128];
static char s_info_renderer[128];
static char s_info_version[128];
static char s_info_sl_version[128];
static matrix_float4x4 s_scene_view;
static matrix_float4x4 s_scene_proj;
static bool            s_have_scene_view;
static bool            s_have_scene_proj;
static uint32_t        s_curr_anim_uid;
static bool            s_have_anim_uid;

#define METAL_MAX_JOINTS 256
#define METAL_MINIMAP_RES 1024

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
"    float3 normal [[attribute(2)]];\n"
"    int material_idx [[attribute(3)]];\n"
"};\n"
"struct TerrainUniforms {\n"
"    float4x4 model;\n"
"    float4x4 view;\n"
"    float4x4 proj;\n"
"};\n"
"struct TerrainVertexOut {\n"
"    float4 position [[position]];\n"
"    float3 normal;\n"
"    uint material_idx;\n"
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
"    return out;\n"
"}\n"
"fragment float4 terrain_fragment(TerrainVertexOut in [[stage_in]]) {\n"
"    float3 light_dir = normalize(float3(0.35, 0.85, 0.20));\n"
"    float diffuse = max(dot(normalize(in.normal), light_dir), 0.18);\n"
"    float3 ambient = float3(0.18, 0.20, 0.16);\n"
"    float3 color = terrain_material_color(in.material_idx);\n"
"    return float4(color * diffuse + ambient * color, 1.0);\n"
"}\n";

static const char *s_static_mesh_shader_source =
"#include <metal_stdlib>\n"
"using namespace metal;\n"
"#define METAL_MAX_MATERIALS 16\n"
"struct StaticMeshVertexIn {\n"
"    float3 position [[attribute(0)]];\n"
"    float3 normal [[attribute(2)]];\n"
"    int material_idx [[attribute(3)]];\n"
"};\n"
"struct StaticMeshUniforms {\n"
"    float4x4 model;\n"
"    float4x4 view;\n"
"    float4x4 proj;\n"
"    float4 material_diffuse[METAL_MAX_MATERIALS];\n"
"};\n"
"struct StaticMeshVertexOut {\n"
"    float4 position [[position]];\n"
"    float3 normal;\n"
"    uint material_idx;\n"
"};\n"
"vertex StaticMeshVertexOut static_mesh_vertex(StaticMeshVertexIn in [[stage_in]], constant StaticMeshUniforms &uniforms [[buffer(1)]]) {\n"
"    StaticMeshVertexOut out;\n"
"    float4 world_pos = uniforms.model * float4(in.position, 1.0);\n"
"    out.position = uniforms.proj * uniforms.view * world_pos;\n"
"    out.normal = normalize((uniforms.model * float4(in.normal, 0.0)).xyz);\n"
"    out.material_idx = (uint)clamp(in.material_idx, 0, METAL_MAX_MATERIALS - 1);\n"
"    return out;\n"
"}\n"
"fragment float4 static_mesh_fragment(StaticMeshVertexOut in [[stage_in]], constant StaticMeshUniforms &uniforms [[buffer(1)]]) {\n"
"    float3 light_dir = normalize(float3(0.35, 0.85, 0.20));\n"
"    float diffuse = max(dot(normalize(in.normal), light_dir), 0.18);\n"
"    float3 base = uniforms.material_diffuse[in.material_idx].xyz;\n"
"    float3 ambient = base * 0.18;\n"
"    return float4(base * diffuse + ambient, 1.0);\n"
"}\n";

struct metal_ui_uniforms{
    float view_size[2];
    float _padding[2];
};

struct metal_terrain_uniforms{
    matrix_float4x4 model;
    matrix_float4x4 view;
    matrix_float4x4 proj;
};

struct metal_static_mesh_uniforms{
    matrix_float4x4 model;
    matrix_float4x4 view;
    matrix_float4x4 proj;
    vector_float4 material_diffuse[MAX_MATERIALS];
};

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
}

static void release_scene_resources(void)
{
    s_minimap_texture = nil;
    s_terrain_pipeline = nil;
    s_static_mesh_pipeline = nil;
}

static void reset_frame_state(void)
{
    s_frame_encoder = nil;
    s_frame_command_buffer = nil;
    s_frame_drawable = nil;
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

static void present_clear(void)
{
    update_drawable_size();

    id<CAMetalDrawable> drawable = [s_layer nextDrawable];
    if(!drawable)
        return;

    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    pass.colorAttachments[0].texture = drawable.texture;
    pass.colorAttachments[0].loadAction = MTLLoadActionClear;
    pass.colorAttachments[0].storeAction = MTLStoreActionStore;
    pass.colorAttachments[0].clearColor = MTLClearColorMake(0.0, 0.0, 0.0, 1.0);

    id<MTLCommandBuffer> command_buffer = [s_queue commandBuffer];
    id<MTLRenderCommandEncoder> encoder = [command_buffer renderCommandEncoderWithDescriptor:pass];
    [encoder endEncoding];
    [command_buffer presentDrawable:drawable];
    [command_buffer commit];
    [command_buffer waitUntilCompleted];
}

static bool ensure_ui_pipeline(void)
{
    if(s_ui_pipeline && s_ui_sampler)
        return true;

    NSError *error = nil;
    NSString *source = [NSString stringWithUTF8String:s_ui_shader_source];
    id<MTLLibrary> library = [s_device newLibraryWithSource:source options:nil error:&error];
    if(!library) {
        fprintf(stderr, "Metal UI shader compile failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return false;
    }

    id<MTLFunction> vertex = [library newFunctionWithName:@"ui_vertex"];
    id<MTLFunction> fragment = [library newFunctionWithName:@"ui_fragment"];
    if(!vertex || !fragment) {
        fprintf(stderr, "Metal UI shader entrypoint lookup failed.\n");
        return false;
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
    pipeline_desc.colorAttachments[0].blendingEnabled = YES;
    pipeline_desc.colorAttachments[0].rgbBlendOperation = MTLBlendOperationAdd;
    pipeline_desc.colorAttachments[0].alphaBlendOperation = MTLBlendOperationAdd;
    pipeline_desc.colorAttachments[0].sourceRGBBlendFactor = MTLBlendFactorSourceAlpha;
    pipeline_desc.colorAttachments[0].sourceAlphaBlendFactor = MTLBlendFactorSourceAlpha;
    pipeline_desc.colorAttachments[0].destinationRGBBlendFactor = MTLBlendFactorOneMinusSourceAlpha;
    pipeline_desc.colorAttachments[0].destinationAlphaBlendFactor = MTLBlendFactorOneMinusSourceAlpha;

    s_ui_pipeline = [s_device newRenderPipelineStateWithDescriptor:pipeline_desc error:&error];
    if(!s_ui_pipeline) {
        fprintf(stderr, "Metal UI pipeline creation failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return false;
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
        return false;
    }

    return true;
}

static bool ensure_terrain_pipeline(void)
{
    if(s_terrain_pipeline)
        return true;

    NSError *error = nil;
    NSString *source = [NSString stringWithUTF8String:s_terrain_shader_source];
    id<MTLLibrary> library = [s_device newLibraryWithSource:source options:nil error:&error];
    if(!library) {
        fprintf(stderr, "Metal terrain shader compile failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return false;
    }

    id<MTLFunction> vertex = [library newFunctionWithName:@"terrain_vertex"];
    id<MTLFunction> fragment = [library newFunctionWithName:@"terrain_fragment"];
    if(!vertex || !fragment) {
        fprintf(stderr, "Metal terrain shader entrypoint lookup failed.\n");
        return false;
    }

    MTLVertexDescriptor *vertex_desc = [MTLVertexDescriptor vertexDescriptor];
    vertex_desc.attributes[0].format = MTLVertexFormatFloat3;
    vertex_desc.attributes[0].offset = offsetof(struct terrain_vert, pos);
    vertex_desc.attributes[0].bufferIndex = 0;
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

    s_terrain_pipeline = [s_device newRenderPipelineStateWithDescriptor:pipeline_desc error:&error];
    if(!s_terrain_pipeline) {
        fprintf(stderr, "Metal terrain pipeline creation failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return false;
    }

    return true;
}

static bool ensure_static_mesh_pipeline(void)
{
    if(s_static_mesh_pipeline)
        return true;

    NSError *error = nil;
    NSString *source = [NSString stringWithUTF8String:s_static_mesh_shader_source];
    id<MTLLibrary> library = [s_device newLibraryWithSource:source options:nil error:&error];
    if(!library) {
        fprintf(stderr, "Metal static mesh shader compile failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return false;
    }

    id<MTLFunction> vertex = [library newFunctionWithName:@"static_mesh_vertex"];
    id<MTLFunction> fragment = [library newFunctionWithName:@"static_mesh_fragment"];
    if(!vertex || !fragment) {
        fprintf(stderr, "Metal static mesh shader entrypoint lookup failed.\n");
        return false;
    }

    MTLVertexDescriptor *vertex_desc = [MTLVertexDescriptor vertexDescriptor];
    vertex_desc.attributes[0].format = MTLVertexFormatFloat3;
    vertex_desc.attributes[0].offset = offsetof(struct vertex, pos);
    vertex_desc.attributes[0].bufferIndex = 0;
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

    s_static_mesh_pipeline = [s_device newRenderPipelineStateWithDescriptor:pipeline_desc error:&error];
    if(!s_static_mesh_pipeline) {
        fprintf(stderr, "Metal static mesh pipeline creation failed: %s\n",
            error ? [[error localizedDescription] UTF8String] : "unknown error");
        return false;
    }

    return true;
}

static void frame_begin(void)
{
    if(s_frame_command_buffer)
        return;

    update_drawable_size();

    s_frame_drawable = [s_layer nextDrawable];
    if(!s_frame_drawable)
        return;

    MTLRenderPassDescriptor *pass = [MTLRenderPassDescriptor renderPassDescriptor];
    pass.colorAttachments[0].texture = s_frame_drawable.texture;
    pass.colorAttachments[0].loadAction = MTLLoadActionClear;
    pass.colorAttachments[0].storeAction = MTLStoreActionStore;
    pass.colorAttachments[0].clearColor = MTLClearColorMake(0.0, 0.0, 0.0, 1.0);

    s_frame_command_buffer = [s_queue commandBuffer];
    s_frame_encoder = [s_frame_command_buffer renderCommandEncoderWithDescriptor:pass];
    if(!s_frame_encoder) {
        reset_frame_state();
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
    [s_frame_command_buffer presentDrawable:s_frame_drawable];
    [s_frame_command_buffer commit];
    [s_frame_command_buffer waitUntilCompleted];
    reset_frame_state();
}

static void frame_abort(void)
{
    if(s_frame_encoder) {
        [s_frame_encoder endEncoding];
    }
    reset_frame_state();
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
    if(!s_ui_font_texture)
        return;
    if(!ensure_ui_pipeline())
        return;

    frame_begin();
    if(!s_frame_encoder)
        return;

    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:dl->vertices->memory.ptr
        length:dl->vertices->memory.size options:MTLResourceStorageModeShared];
    id<MTLBuffer> index_buffer = [s_device newBufferWithBytes:dl->elements->memory.ptr
        length:dl->elements->memory.size options:MTLResourceStorageModeShared];
    if(!vertex_buffer || !index_buffer)
        return;

    [s_frame_encoder setRenderPipelineState:s_ui_pipeline];
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
    if(!verts || !nverts || !texture)
        return;
    if(!ensure_ui_pipeline())
        return;

    frame_begin();
    if(!s_frame_encoder)
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

    [s_frame_encoder setRenderPipelineState:s_ui_pipeline];
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

static void draw_terrain_to_encoder(id<MTLRenderCommandEncoder> encoder,
                                    const struct render_private *priv,
                                    const mat4x4_t *model,
                                    matrix_float4x4 view,
                                    matrix_float4x4 proj)
{
    struct render_private *mutable_priv = (struct render_private *)priv;
    if(!encoder || !priv || !priv->metal_is_terrain)
        return;
    if(!priv->metal_terrain_verts || !priv->metal_terrain_verts_size || !priv->mesh.num_verts)
        return;
    if(!ensure_terrain_pipeline())
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
    };
    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [encoder setRenderPipelineState:s_terrain_pipeline];
    [encoder setCullMode:MTLCullModeNone];
    [encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [encoder drawPrimitives:MTLPrimitiveTypeTriangle
                vertexStart:0
                vertexCount:priv->mesh.num_verts];
}

static void render_terrain_draw(const struct render_private *priv, const mat4x4_t *model)
{
    if(!priv || !priv->metal_is_terrain)
        return;
    if(!priv->metal_terrain_verts || !priv->metal_terrain_verts_size || !priv->mesh.num_verts)
        return;
    if(!s_have_scene_view || !s_have_scene_proj)
        return;
    if(!ensure_terrain_pipeline())
        return;

    frame_begin();
    if(!s_frame_encoder)
        return;

    draw_terrain_to_encoder(s_frame_encoder, priv, model, s_scene_view, s_scene_proj);
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

static void render_static_vertex_stream(const struct render_private *priv,
                                        const mat4x4_t *model,
                                        const struct vertex *verts,
                                        size_t verts_size)
{
    if(!priv || !verts || !verts_size || !priv->mesh.num_verts)
        return;
    if(!s_have_scene_view || !s_have_scene_proj)
        return;
    if(!ensure_static_mesh_pipeline())
        return;

    frame_begin();
    if(!s_frame_encoder)
        return;

    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:verts
        length:verts_size options:MTLResourceStorageModeShared];
    if(!vertex_buffer)
        return;

    struct metal_static_mesh_uniforms uniforms = {
        .model = matrix_from_pf_mat4(model),
        .view = s_scene_view,
        .proj = s_scene_proj,
    };
    fill_material_uniforms(priv, uniforms.material_diffuse);

    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [s_frame_encoder setRenderPipelineState:s_static_mesh_pipeline];
    [s_frame_encoder setCullMode:MTLCullModeBack];
    [s_frame_encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [s_frame_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_frame_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder setFragmentBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder drawPrimitives:MTLPrimitiveTypeTriangle
                        vertexStart:0
                        vertexCount:priv->mesh.num_verts];
}

static void render_static_mesh_draw(const struct render_private *priv, const mat4x4_t *model)
{
    struct render_private *mutable_priv = (struct render_private *)priv;
    if(!priv || !priv->metal_is_static_mesh)
        return;
    if(!priv->metal_static_verts || !priv->metal_static_verts_size)
        return;
    if(!s_have_scene_view || !s_have_scene_proj)
        return;
    if(!ensure_static_mesh_pipeline())
        return;

    frame_begin();
    if(!s_frame_encoder)
        return;

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
    };
    fill_material_uniforms(priv, uniforms.material_diffuse);

    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [s_frame_encoder setRenderPipelineState:s_static_mesh_pipeline];
    [s_frame_encoder setCullMode:MTLCullModeBack];
    [s_frame_encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [s_frame_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_frame_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder setFragmentBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder drawPrimitives:MTLPrimitiveTypeTriangle
                        vertexStart:0
                        vertexCount:priv->mesh.num_verts];
}

static void render_world_colored_strip(const vec3_t *positions, size_t nverts, const vec3_t *color)
{
    if(!positions || !nverts || !color)
        return;
    if(!s_have_scene_view || !s_have_scene_proj)
        return;
    if(!ensure_static_mesh_pipeline())
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

    [s_frame_encoder setRenderPipelineState:s_static_mesh_pipeline];
    [s_frame_encoder setCullMode:MTLCullModeNone];
    [s_frame_encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [s_frame_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_frame_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder setFragmentBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder drawPrimitives:MTLPrimitiveTypeTriangleStrip
                        vertexStart:0
                        vertexCount:nverts];
}

static void render_screenspace_colored_triangles(const vec3_t *positions, size_t nverts, const vec3_t *color)
{
    if(!positions || !nverts || !color)
        return;
    if(!ensure_static_mesh_pipeline())
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

    [s_frame_encoder setRenderPipelineState:s_static_mesh_pipeline];
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

static void render_minimap_bake(const struct map *map, void **chunk_rprivates, mat4x4_t *chunk_model_mats)
{
    if(!map || !chunk_rprivates || !chunk_model_mats)
        return;
    if(!ensure_terrain_pipeline())
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
    if(!ensure_terrain_pipeline())
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

static void render_skinned_mesh_draw(const struct render_private *priv, const mat4x4_t *model)
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

    render_static_vertex_stream(priv, model, skinned, priv->mesh.num_verts * sizeof(*skinned));
    free(skinned);
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
    if(cmd.func == R_GL_MapBegin || cmd.func == R_GL_MapEnd) {
        return;
    }
    if(cmd.func == R_GL_Draw) {
        const struct render_private *priv = cmd.args[0];
        if(priv && priv->metal_is_terrain) {
            render_terrain_draw(priv, cmd.args[1]);
            return;
        }
        if(priv && priv->metal_is_static_mesh && !priv->uses_pose_buffer) {
            render_static_mesh_draw(priv, cmd.args[1]);
            return;
        }
        if(priv && priv->metal_is_anim_mesh && priv->uses_pose_buffer) {
            render_skinned_mesh_draw(priv, cmd.args[1]);
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
    update_drawable_size();

    strncpy(s_info_vendor, "Apple", sizeof(s_info_vendor) - 1);
    const char *name = [[s_device name] UTF8String];
    strncpy(s_info_renderer, name ? name : "Metal Device", sizeof(s_info_renderer) - 1);
    strncpy(s_info_version, "Metal", sizeof(s_info_version) - 1);
    strncpy(s_info_sl_version, "MSL", sizeof(s_info_sl_version) - 1);
    s_have_scene_view = false;
    s_have_scene_proj = false;
    s_have_anim_uid = false;
    return true;
}

static void render_destroy_ctx(void)
{
    frame_abort();
    release_scene_resources();
    release_ui_resources();
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
    (void)ensure_ui_pipeline();
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
