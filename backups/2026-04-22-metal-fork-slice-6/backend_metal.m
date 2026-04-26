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

    id<MTLBuffer> vertex_buffer = [s_device newBufferWithBytes:priv->metal_terrain_verts
        length:priv->metal_terrain_verts_size options:MTLResourceStorageModeShared];
    if(!vertex_buffer)
        return;

    struct metal_terrain_uniforms uniforms = {
        .model = matrix_from_pf_mat4(model),
        .view = s_scene_view,
        .proj = s_scene_proj,
    };
    id<MTLBuffer> uniform_buffer = [s_device newBufferWithBytes:&uniforms
        length:sizeof(uniforms) options:MTLResourceStorageModeShared];
    if(!uniform_buffer)
        return;

    [s_frame_encoder setRenderPipelineState:s_terrain_pipeline];
    [s_frame_encoder setCullMode:MTLCullModeNone];
    [s_frame_encoder setFrontFacingWinding:MTLWindingCounterClockwise];
    [s_frame_encoder setVertexBuffer:vertex_buffer offset:0 atIndex:0];
    [s_frame_encoder setVertexBuffer:uniform_buffer offset:0 atIndex:1];
    [s_frame_encoder drawPrimitives:MTLPrimitiveTypeTriangle
                        vertexStart:0
                        vertexCount:priv->mesh.num_verts];
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
    if(!priv || !priv->metal_is_static_mesh)
        return;
    if(!priv->metal_static_verts || !priv->metal_static_verts_size)
        return;

    render_static_vertex_stream(priv, model, priv->metal_static_verts, priv->metal_static_verts_size);
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
