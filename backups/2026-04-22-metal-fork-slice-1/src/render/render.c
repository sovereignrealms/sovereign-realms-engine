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

#include "public/render_ctrl.h"
#include "backend_local.h"
#include "../settings.h"
#include "../main.h"
#include "../game/public/game.h"

#include <assert.h>
#include <math.h>
#include <stdio.h>
#include <string.h>


#define EPSILON     (1.0f / 1024)

/*****************************************************************************/
/* GLOBAL VARIABLES                                                          */
/*****************************************************************************/

bool g_trace_gpu;

/*****************************************************************************/
/* STATIC FUNCTIONS                                                          */
/*****************************************************************************/

static bool ar_validate(const struct sval *new_val)
{
    if(new_val->type != ST_TYPE_VEC2)
        return false;

    float AR_MIN = 0.5f, AR_MAX = 2.5f;
    return (new_val->as_vec2.x / new_val->as_vec2.y >= AR_MIN)
        && (new_val->as_vec2.x / new_val->as_vec2.y <= AR_MAX);
}

static void ar_commit(const struct sval *new_val)
{
    struct sval res;
    ss_e status = Settings_Get("pf.video.resolution", &res);
    if(status == SS_NO_SETTING)
        return;

    assert(status == SS_OKAY);
    float curr_ratio = res.as_vec2.x / res.as_vec2.y;
    float new_ratio = new_val->as_vec2.x / new_val->as_vec2.y;
    if(fabs(new_ratio - curr_ratio) < EPSILON)
        return;

    struct sval new_res = {.type = ST_TYPE_VEC2};
    if(new_ratio > curr_ratio) {
        new_res.as_vec2 = (vec2_t){
            .x = res.as_vec2.x,
            .y = res.as_vec2.y / (new_ratio / curr_ratio)
        };
    }else{
        new_res.as_vec2 = (vec2_t){
            .x = res.as_vec2.x / (curr_ratio / new_ratio),
            .y = res.as_vec2.y
        };
    }

    status = Settings_SetNoValidate("pf.video.resolution", &new_res);
    assert(status == SS_OKAY);
}

static bool res_validate(const struct sval *new_val)
{
    if(new_val->type != ST_TYPE_VEC2)
        return false;

    struct sval ar;
    ss_e status = Settings_Get("pf.video.aspect_ratio", &ar);
    if(status != SS_NO_SETTING) {
        assert(status == SS_OKAY);
        float set_ar = ar.as_vec2.x / ar.as_vec2.y;
        if(fabs(new_val->as_vec2.x / new_val->as_vec2.y - set_ar) > EPSILON)
            return false;
    }

    const int DIM_MIN = 360, DIM_MAX = 5120;
    return (new_val->as_vec2.x >= DIM_MIN && new_val->as_vec2.x <= DIM_MAX)
        && (new_val->as_vec2.y >= DIM_MIN && new_val->as_vec2.y <= DIM_MAX);
}

static void res_commit(const struct sval *new_val)
{
    int rval = Engine_SetRes(new_val->as_vec2.x, new_val->as_vec2.y);
    assert(0 == rval || fprintf(stderr, "Failed to set window resolution:%s\n", SDL_GetError()));

    int width, height;
    Engine_WinDrawableSize(&width, &height);

    if(PF_RENDER_BACKEND_OPENGL) {
        extern void R_GL_SetViewport(int *x, int *y, int *w, int *h);
        extern void R_GL_SwapchainSetRes(int *x, int *y);

        int viewport[4] = {0, 0, width, height};
        R_PushCmd((struct rcmd){
            .func = R_GL_SetViewport,
            .nargs = 4,
            .args = {
                R_PushArg(&viewport[0], sizeof(viewport[0])),
                R_PushArg(&viewport[1], sizeof(viewport[1])),
                R_PushArg(&viewport[2], sizeof(viewport[2])),
                R_PushArg(&viewport[3], sizeof(viewport[3])),
            },
        });
        R_PushCmd((struct rcmd){
            .func = R_GL_SwapchainSetRes,
            .nargs = 2,
            .args = {
                R_PushArg(&viewport[2], sizeof(viewport[2])),
                R_PushArg(&viewport[3], sizeof(viewport[3]))
            }
        });
    }
}

static bool dm_validate(const struct sval *new_val)
{
    assert(new_val->type == ST_TYPE_INT);
    if(new_val->type != ST_TYPE_INT)
        return false;

    return new_val->as_int == PF_WF_FULLSCREEN
        || new_val->as_int == PF_WF_BORDERLESS_WIN
        || new_val->as_int == PF_WF_WINDOW;
}

static void dm_commit(const struct sval *new_val)
{
    Engine_SetDispMode(new_val->as_int);
}

static bool bool_val_validate(const struct sval *new_val)
{
    return new_val->type == ST_TYPE_BOOL;
}

static void vsync_commit(const struct sval *new_val)
{
    R_PushCmd((struct rcmd){
        .func = R_Backend_CommandSetSwapInterval,
        .nargs = 1,
        .args = {R_PushArg(&new_val->as_bool, sizeof(bool))},
    });
}

static bool int_val_validate(const struct sval *new_val)
{
    return new_val->type == ST_TYPE_INT;
}

static void debug_logmask_commit(const struct sval *new_val)
{
    R_PushCmd((struct rcmd){
        .func = R_Backend_CommandSetDebugLogMask,
        .nargs = 1,
        .args = {R_PushArg(&new_val->as_int, sizeof(int))},
    });
}

static void trace_gpu_commit(const struct sval *new_val)
{
    R_PushCmd((struct rcmd){
        .func = R_Backend_CommandSetTraceGPU,
        .nargs = 1,
        .args = {R_PushArg(&new_val->as_bool, sizeof(bool))},
    });
}

/*****************************************************************************/
/* EXTERN FUNCTIONS                                                          */
/*****************************************************************************/

bool R_Init(const char *base_path)
{
    (void)base_path;

    ss_e status;
    SDL_DisplayMode dm;
    SDL_GetDesktopDisplayMode(0, &dm);

    status = Settings_Create((struct setting){
        .name = "pf.video.aspect_ratio",
        .val = (struct sval){
            .type = ST_TYPE_VEC2,
            .as_vec2 = (vec2_t){dm.w, dm.h}
        },
        .prio = 0,
        .validate = ar_validate,
        .commit = ar_commit,
    });
    assert(status == SS_OKAY);

    struct sval ar_pair;
    Settings_Get("pf.video.aspect_ratio", &ar_pair);
    float ar = ar_pair.as_vec2.x / ar_pair.as_vec2.y;
    float native_ar = (float)dm.w / dm.h;

    vec2_t res_default;
    if(ar < native_ar) {
        res_default = (vec2_t){dm.h * ar, dm.h};
    }else{
        res_default = (vec2_t){dm.w, dm.w / ar};
    }

    status = Settings_Create((struct setting){
        .name = "pf.video.resolution",
        .val = (struct sval){
            .type = ST_TYPE_VEC2,
            .as_vec2 = res_default
        },
        .prio = 1,
        .validate = res_validate,
        .commit = res_commit,
    });
    assert(status == SS_OKAY);

    status = Settings_Create((struct setting){
        .name = "pf.video.display_mode",
        .val = (struct sval){
            .type = ST_TYPE_INT,
            .as_int = PF_WF_BORDERLESS_WIN
        },
        .prio = 0,
        .validate = dm_validate,
        .commit = dm_commit,
    });
    assert(status == SS_OKAY);

    status = Settings_Create((struct setting){
        .name = "pf.video.window_always_on_top",
        .val = (struct sval){
            .type = ST_TYPE_BOOL,
            .as_bool = false
        },
        .prio = 0,
        .validate = bool_val_validate,
        .commit = NULL,
    });
    assert(status == SS_OKAY);

    status = Settings_Create((struct setting){
        .name = "pf.video.vsync",
        .val = (struct sval){
            .type = ST_TYPE_BOOL,
            .as_bool = true
        },
        .prio = 0,
        .validate = bool_val_validate,
        .commit = vsync_commit,
    });
    assert(status == SS_OKAY);

    status = Settings_Create((struct setting){
        .name = "pf.video.water_reflection",
        .val = (struct sval){
            .type = ST_TYPE_BOOL,
            .as_bool = true
        },
        .prio = 0,
        .validate = bool_val_validate,
        .commit = NULL,
    });
    assert(status == SS_OKAY);

    status = Settings_Create((struct setting){
        .name = "pf.video.water_refraction",
        .val = (struct sval){
            .type = ST_TYPE_BOOL,
            .as_bool = true
        },
        .prio = 0,
        .validate = bool_val_validate,
        .commit = NULL,
    });
    assert(status == SS_OKAY);

    status = Settings_Create((struct setting){
        .name = "pf.debug.render_log_mask",
        .val = (struct sval){
            .type = ST_TYPE_INT,
            .as_int = 0x1,
        },
        .prio = 0,
        .validate = int_val_validate,
        .commit = debug_logmask_commit,
    });
    assert(status == SS_OKAY);

    status = Settings_Create((struct setting){
        .name = "pf.debug.trace_gpu",
        .val = (struct sval){
            .type = ST_TYPE_BOOL,
            .as_bool = false,
        },
        .prio = 0,
        .validate = bool_val_validate,
        .commit = trace_gpu_commit,
    });
    assert(status == SS_OKAY);

    return true;
}

SDL_Thread *R_Run(struct render_sync_state *rstate)
{
    return R_Backend_Run(rstate);
}

void *R_PushArg(const void *src, size_t size)
{
    struct render_workspace *ws = (SDL_ThreadID() == g_render_thread_id) ? G_GetRenderWS()
                                                                         : G_GetSimWS();
    void *ret = stalloc(&ws->args, size);
    if(!ret)
        return ret;

    memcpy(ret, src, size);
    return ret;
}

void *R_AllocArg(size_t size)
{
    struct render_workspace *ws = (SDL_ThreadID() == g_render_thread_id) ? G_GetRenderWS()
                                                                         : G_GetSimWS();
    return stalloc(&ws->args, size);
}

void R_PushCmd(struct rcmd cmd)
{
    if(SDL_ThreadID() == g_render_thread_id) {
        R_Backend_DispatchCmd(cmd);
        return;
    }

    queue_rcmd_push(&G_GetSimWS()->commands, &cmd);
}

void R_PushCmdImmediate(struct rcmd cmd)
{
    if(SDL_ThreadID() == g_render_thread_id) {
        R_Backend_DispatchCmd(cmd);
        return;
    }

    queue_rcmd_push(&G_GetRenderWS()->commands, &cmd);
}

void R_PushCmdImmediateFront(struct rcmd cmd)
{
    if(SDL_ThreadID() == g_render_thread_id) {
        R_Backend_DispatchCmd(cmd);
        return;
    }

    queue_rcmd_push_front(&G_GetRenderWS()->commands, &cmd);
}

bool R_InitWS(struct render_workspace *ws)
{
    if(!stalloc_init(&ws->args))
        goto fail_args;

    if(!queue_rcmd_init(&ws->commands, 2048))
        goto fail_queue;

    return true;

fail_queue:
    stalloc_destroy(&ws->args);
fail_args:
    return false;
}

void R_DestroyWS(struct render_workspace *ws)
{
    queue_rcmd_destroy(&ws->commands);
    stalloc_destroy(&ws->args);
}

void R_ClearWS(struct render_workspace *ws)
{
    queue_rcmd_clear(&ws->commands);
    stalloc_clear(&ws->args);
}

const char *R_GetInfo(enum render_info attr)
{
    return R_Backend_GetInfo(attr);
}

void R_InitAttributes(void)
{
    R_Backend_InitAttributes();
}

bool R_ComputeShaderSupported(void)
{
    return R_Backend_ComputeShaderSupported();
}

Uint32 R_WindowFlags(void)
{
    return R_Backend_WindowFlags();
}

void R_WindowDrawableSize(SDL_Window *window, int *out_w, int *out_h)
{
    R_Backend_WindowDrawableSize(window, out_w, out_h);
}

void R_PresentWindow(SDL_Window *window)
{
    R_Backend_PresentWindow(window);
}

void R_Yield(void)
{
    R_Backend_Yield();
}
