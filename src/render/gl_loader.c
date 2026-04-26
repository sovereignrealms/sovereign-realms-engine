#define PF_GL_NO_ALIASES
#include "gl_loader.h"

#if defined(__APPLE__)

#include <SDL.h>

#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

struct pf_gl_caps {
    bool version_3_3;
    bool version_4_3;
    bool khr_debug;
    bool arb_copy_image;
    bool arb_buffer_storage;
    bool arb_multi_draw_indirect;
    bool arb_compute_shader;
    bool arb_shader_storage_buffer_object;
    bool timer_query;
    bool texture_sub_image;
};

static struct pf_gl_caps s_caps;

#define PF_GL_DEFINE(type, name) __typeof__(name) *pf_##name = NULL;
PF_GL_FUNCTIONS(PF_GL_DEFINE)
#undef PF_GL_DEFINE

static bool pfgl_is_optional(const char *name)
{
    return 0 == strcmp(name, "glDebugMessageCallback")
        || 0 == strcmp(name, "glDebugMessageControl")
        || 0 == strcmp(name, "glPushDebugGroup")
        || 0 == strcmp(name, "glPopDebugGroup")
        || 0 == strcmp(name, "glCopyImageSubData")
        || 0 == strcmp(name, "glGetTextureSubImage")
        || 0 == strcmp(name, "glBufferStorage")
        || 0 == strcmp(name, "glMultiDrawArraysIndirect")
        || 0 == strcmp(name, "glBindImageTexture")
        || 0 == strcmp(name, "glDispatchCompute")
        || 0 == strcmp(name, "glMemoryBarrier")
        || 0 == strcmp(name, "glGetIntegeri_v")
        || 0 == strcmp(name, "glBindBufferBase")
        || 0 == strcmp(name, "glGetBufferSubData")
        || 0 == strcmp(name, "glGenQueries")
        || 0 == strcmp(name, "glDeleteQueries")
        || 0 == strcmp(name, "glQueryCounter")
        || 0 == strcmp(name, "glGetQueryObjectiv")
        || 0 == strcmp(name, "glGetQueryObjectui64v");
}

static bool pfgl_load_proc(const char *name, void **out)
{
    *out = SDL_GL_GetProcAddress(name);
    if(!*out)
        *out = dlsym(RTLD_DEFAULT, name);
    if(*out || pfgl_is_optional(name))
        return true;

    fprintf(stderr, "Failed to load required OpenGL function: %s\n", name);
    return false;
}

static bool pfgl_parse_version(const char *version, int *major, int *minor)
{
    return version && (2 == sscanf(version, "%d.%d", major, minor));
}

static bool pfgl_version_at_least(int major, int minor, int req_major, int req_minor)
{
    return (major > req_major) || (major == req_major && minor >= req_minor);
}

bool PFGL_Load(void)
{
    PFGL_Reset();

    if(!SDL_GL_GetCurrentContext()) {
        fprintf(stderr, "PFGL_Load called without a current OpenGL context\n");
        return false;
    }

#define PF_GL_LOAD(type, name)                                                  \
    do {                                                                        \
        if(!pfgl_load_proc(#name, (void**)&pf_##name))                          \
            return false;                                                       \
    }while(0);
    PF_GL_FUNCTIONS(PF_GL_LOAD)
#undef PF_GL_LOAD

    const char *version = (const char*)pf_glGetString(GL_VERSION);
    int major = 0, minor = 0;
    if(!pfgl_parse_version(version, &major, &minor)) {
        fprintf(stderr, "Failed to parse OpenGL version string\n");
        return false;
    }

    s_caps.version_3_3 = pfgl_version_at_least(major, minor, 3, 3);
    s_caps.version_4_3 = pfgl_version_at_least(major, minor, 4, 3);
    s_caps.khr_debug =
        SDL_GL_ExtensionSupported("GL_KHR_debug")
        && pf_glDebugMessageCallback
        && pf_glDebugMessageControl
        && pf_glPushDebugGroup
        && pf_glPopDebugGroup;
    s_caps.arb_copy_image =
        SDL_GL_ExtensionSupported("GL_ARB_copy_image")
        && pf_glCopyImageSubData;
    s_caps.arb_buffer_storage =
        SDL_GL_ExtensionSupported("GL_ARB_buffer_storage")
        && pf_glBufferStorage;
    s_caps.arb_multi_draw_indirect =
        SDL_GL_ExtensionSupported("GL_ARB_multi_draw_indirect")
        && pf_glMultiDrawArraysIndirect;
    s_caps.arb_compute_shader =
        SDL_GL_ExtensionSupported("GL_ARB_compute_shader")
        && pf_glDispatchCompute
        && pf_glBindImageTexture
        && pf_glGetIntegeri_v;
    s_caps.arb_shader_storage_buffer_object =
        SDL_GL_ExtensionSupported("GL_ARB_shader_storage_buffer_object")
        && pf_glBindBufferBase
        && pf_glMemoryBarrier
        && pf_glGetBufferSubData;
    s_caps.timer_query =
        SDL_GL_ExtensionSupported("GL_ARB_timer_query")
        && pf_glGenQueries
        && pf_glDeleteQueries
        && pf_glQueryCounter
        && pf_glGetQueryObjectiv
        && pf_glGetQueryObjectui64v;
    s_caps.texture_sub_image = (NULL != pf_glGetTextureSubImage);
    return true;
}

void PFGL_Reset(void)
{
    memset(&s_caps, 0, sizeof(s_caps));

#define PF_GL_CLEAR(type, name) pf_##name = NULL;
    PF_GL_FUNCTIONS(PF_GL_CLEAR);
#undef PF_GL_CLEAR
}

bool PFGL_HasVersion33(void)
{
    return s_caps.version_3_3;
}

bool PFGL_KHRDebugSupported(void)
{
    return s_caps.khr_debug;
}

bool PFGL_CopyImageSupported(void)
{
    return s_caps.arb_copy_image;
}

bool PFGL_BufferStorageSupported(void)
{
    return s_caps.arb_buffer_storage;
}

bool PFGL_MultiDrawIndirectSupported(void)
{
    return s_caps.arb_multi_draw_indirect;
}

bool PFGL_ComputeShaderSupported(void)
{
    return s_caps.version_4_3
        || (s_caps.arb_compute_shader && s_caps.arb_shader_storage_buffer_object);
}

bool PFGL_TimerQuerySupported(void)
{
    return s_caps.timer_query;
}

bool PFGL_TextureSubImageSupported(void)
{
    return s_caps.texture_sub_image;
}

#else

bool PFGL_Load(void)
{
    glewExperimental = GL_TRUE;
    return (glewInit() == GLEW_OK);
}

void PFGL_Reset(void)
{
}

bool PFGL_HasVersion33(void)
{
    return GLEW_VERSION_3_3;
}

bool PFGL_KHRDebugSupported(void)
{
    return GLEW_KHR_debug;
}

bool PFGL_CopyImageSupported(void)
{
    return GLEW_ARB_copy_image;
}

bool PFGL_BufferStorageSupported(void)
{
    return GLEW_ARB_buffer_storage;
}

bool PFGL_MultiDrawIndirectSupported(void)
{
    return GL_ARB_multi_draw_indirect;
}

bool PFGL_ComputeShaderSupported(void)
{
    return (GLEW_VERSION_4_3
        || (GLEW_ARB_compute_shader && GLEW_ARB_shader_storage_buffer_object));
}

bool PFGL_TimerQuerySupported(void)
{
    return (GLEW_VERSION_3_3 || GLEW_ARB_timer_query);
}

bool PFGL_TextureSubImageSupported(void)
{
    return (GLEW_VERSION_4_5 || GLEW_ARB_get_texture_sub_image);
}

#endif
