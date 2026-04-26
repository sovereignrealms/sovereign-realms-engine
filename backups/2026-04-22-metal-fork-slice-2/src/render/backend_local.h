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

#ifndef BACKEND_LOCAL_H
#define BACKEND_LOCAL_H

#include "public/render_ctrl.h"

#include <stdbool.h>

#if !defined(PF_RENDER_BACKEND_OPENGL)
#define PF_RENDER_BACKEND_OPENGL 0
#endif

#if !defined(PF_RENDER_BACKEND_METAL)
#define PF_RENDER_BACKEND_METAL 0
#endif

#if (PF_RENDER_BACKEND_OPENGL + PF_RENDER_BACKEND_METAL) != 1
#error "Select exactly one render backend."
#endif

SDL_Thread *R_GL_Backend_Run(struct render_sync_state *rstate);
void        R_GL_Backend_InitAttributes(void);
bool        R_GL_Backend_ComputeShaderSupported(void);
const char *R_GL_Backend_GetInfo(enum render_info attr);
Uint32      R_GL_Backend_WindowFlags(void);
void        R_GL_Backend_WindowDrawableSize(SDL_Window *window, int *out_w, int *out_h);
void        R_GL_Backend_PresentWindow(SDL_Window *window);
void        R_GL_Backend_Yield(void);
void        R_GL_Backend_CommandSetSwapInterval(const bool *on);
void        R_GL_Backend_CommandSetDebugLogMask(const int *mask);
void        R_GL_Backend_CommandSetTraceGPU(const bool *on);
void        R_GL_Backend_DispatchCmd(struct rcmd cmd);

SDL_Thread *R_Metal_Backend_Run(struct render_sync_state *rstate);
void        R_Metal_Backend_InitAttributes(void);
bool        R_Metal_Backend_ComputeShaderSupported(void);
const char *R_Metal_Backend_GetInfo(enum render_info attr);
Uint32      R_Metal_Backend_WindowFlags(void);
void        R_Metal_Backend_WindowDrawableSize(SDL_Window *window, int *out_w, int *out_h);
void        R_Metal_Backend_PresentWindow(SDL_Window *window);
void        R_Metal_Backend_Yield(void);
void        R_Metal_Backend_CommandSetSwapInterval(const bool *on);
void        R_Metal_Backend_CommandSetDebugLogMask(const int *mask);
void        R_Metal_Backend_CommandSetTraceGPU(const bool *on);
void        R_Metal_Backend_DispatchCmd(struct rcmd cmd);

#if PF_RENDER_BACKEND_METAL
#define R_Backend_Run R_Metal_Backend_Run
#define R_Backend_InitAttributes R_Metal_Backend_InitAttributes
#define R_Backend_ComputeShaderSupported R_Metal_Backend_ComputeShaderSupported
#define R_Backend_GetInfo R_Metal_Backend_GetInfo
#define R_Backend_WindowFlags R_Metal_Backend_WindowFlags
#define R_Backend_WindowDrawableSize R_Metal_Backend_WindowDrawableSize
#define R_Backend_PresentWindow R_Metal_Backend_PresentWindow
#define R_Backend_Yield R_Metal_Backend_Yield
#define R_Backend_CommandSetSwapInterval R_Metal_Backend_CommandSetSwapInterval
#define R_Backend_CommandSetDebugLogMask R_Metal_Backend_CommandSetDebugLogMask
#define R_Backend_CommandSetTraceGPU R_Metal_Backend_CommandSetTraceGPU
#define R_Backend_DispatchCmd R_Metal_Backend_DispatchCmd
#else
#define R_Backend_Run R_GL_Backend_Run
#define R_Backend_InitAttributes R_GL_Backend_InitAttributes
#define R_Backend_ComputeShaderSupported R_GL_Backend_ComputeShaderSupported
#define R_Backend_GetInfo R_GL_Backend_GetInfo
#define R_Backend_WindowFlags R_GL_Backend_WindowFlags
#define R_Backend_WindowDrawableSize R_GL_Backend_WindowDrawableSize
#define R_Backend_PresentWindow R_GL_Backend_PresentWindow
#define R_Backend_Yield R_GL_Backend_Yield
#define R_Backend_CommandSetSwapInterval R_GL_Backend_CommandSetSwapInterval
#define R_Backend_CommandSetDebugLogMask R_GL_Backend_CommandSetDebugLogMask
#define R_Backend_CommandSetTraceGPU R_GL_Backend_CommandSetTraceGPU
#define R_Backend_DispatchCmd R_GL_Backend_DispatchCmd
#endif

#endif
