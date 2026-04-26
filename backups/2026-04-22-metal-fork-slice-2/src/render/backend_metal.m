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

#include "backend_local.h"
#include "../main.h"
#include "../game/public/game.h"

#include <assert.h>
#include <stdio.h>
#include <string.h>


extern bool g_trace_gpu;

static SDL_Window               *s_window;
static struct render_sync_state *s_rstate;
static SDL_MetalView             s_metal_view;
static id<MTLDevice>             s_device;
static id<MTLCommandQueue>       s_queue;
static CAMetalLayer             *s_layer;

static char s_info_vendor[128];
static char s_info_renderer[128];
static char s_info_version[128];
static char s_info_sl_version[128];

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

static void render_drop_cmds(queue_rcmd_t *cmds)
{
    while(queue_size(*cmds) > 0) {
        struct rcmd curr;
        queue_rcmd_pop(cmds, &curr);
    }
}

static void update_drawable_size(void)
{
    int width = 0, height = 0;
    SDL_Metal_GetDrawableSize(s_window, &width, &height);
    s_layer.drawableSize = CGSizeMake(width, height);
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
    return true;
}

static void render_present_clear(void)
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

static void render_destroy_ctx(void)
{
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
        quit = render_wait_cmd(s_rstate);
        if(quit)
            break;

        render_drop_cmds(&G_GetRenderWS()->commands);
        if(s_rstate->swap_buffers)
            render_present_clear();

        render_signal_done(s_rstate, RSTAT_DONE);
    }

    render_destroy_ctx();
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
    render_present_clear();
}

void R_Metal_Backend_Yield(void)
{
    ASSERT_IN_RENDER_THREAD();
    render_present_clear();
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
    (void)cmd;
}
