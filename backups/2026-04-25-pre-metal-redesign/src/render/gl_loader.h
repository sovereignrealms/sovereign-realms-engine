#ifndef GL_LOADER_H
#define GL_LOADER_H

#include <stdbool.h>

#if defined(__APPLE__)
#ifndef GL_GLEXT_PROTOTYPES
#define GL_GLEXT_PROTOTYPES 1
#endif
#include <SDL_opengl.h>
#include <SDL_opengl_glext.h>

#define PF_GL_FUNCTIONS(X) \
    X(PFNGLACTIVETEXTUREPROC, glActiveTexture) \
    X(PFNGLATTACHSHADERPROC, glAttachShader) \
    X(PFNGLBINDBUFFERPROC, glBindBuffer) \
    X(PFNGLBINDBUFFERBASEPROC, glBindBufferBase) \
    X(PFNGLBINDFRAMEBUFFERPROC, glBindFramebuffer) \
    X(PFNGLBINDIMAGETEXTUREPROC, glBindImageTexture) \
    X(PFNGLBINDRENDERBUFFERPROC, glBindRenderbuffer) \
    X(PFNGLBINDTEXTUREPROC, glBindTexture) \
    X(PFNGLBINDVERTEXARRAYPROC, glBindVertexArray) \
    X(PFNGLBLENDEQUATIONPROC, glBlendEquation) \
    X(PFNGLBLENDFUNCPROC, glBlendFunc) \
    X(PFNGLBLITFRAMEBUFFERPROC, glBlitFramebuffer) \
    X(PFNGLBUFFERDATAPROC, glBufferData) \
    X(PFNGLBUFFERSTORAGEPROC, glBufferStorage) \
    X(PFNGLBUFFERSUBDATAPROC, glBufferSubData) \
    X(PFNGLCHECKFRAMEBUFFERSTATUSPROC, glCheckFramebufferStatus) \
    X(PFNGLCLEARPROC, glClear) \
    X(PFNGLCLEARCOLORPROC, glClearColor) \
    X(PFNGLCLIENTWAITSYNCPROC, glClientWaitSync) \
    X(PFNGLCOMPILESHADERPROC, glCompileShader) \
    X(PFNGLCOPYBUFFERSUBDATAPROC, glCopyBufferSubData) \
    X(PFNGLCOPYIMAGESUBDATAPROC, glCopyImageSubData) \
    X(PFNGLCREATEPROGRAMPROC, glCreateProgram) \
    X(PFNGLCREATESHADERPROC, glCreateShader) \
    X(PFNGLCULLFACEPROC, glCullFace) \
    X(PFNGLDEBUGMESSAGECALLBACKPROC, glDebugMessageCallback) \
    X(PFNGLDEBUGMESSAGECONTROLPROC, glDebugMessageControl) \
    X(PFNGLDELETEBUFFERSPROC, glDeleteBuffers) \
    X(PFNGLDELETEFRAMEBUFFERSPROC, glDeleteFramebuffers) \
    X(PFNGLDELETEQUERIESPROC, glDeleteQueries) \
    X(PFNGLDELETERENDERBUFFERSPROC, glDeleteRenderbuffers) \
    X(PFNGLDELETESHADERPROC, glDeleteShader) \
    X(PFNGLDELETESYNCPROC, glDeleteSync) \
    X(PFNGLDELETETEXTURESPROC, glDeleteTextures) \
    X(PFNGLDELETEVERTEXARRAYSPROC, glDeleteVertexArrays) \
    X(PFNGLDEPTHFUNCPROC, glDepthFunc) \
    X(PFNGLDEPTHMASKPROC, glDepthMask) \
    X(PFNGLDISABLEPROC, glDisable) \
    X(PFNGLDISPATCHCOMPUTEPROC, glDispatchCompute) \
    X(PFNGLDRAWARRAYSPROC, glDrawArrays) \
    X(PFNGLDRAWARRAYSINSTANCEDPROC, glDrawArraysInstanced) \
    X(PFNGLDRAWBUFFERPROC, glDrawBuffer) \
    X(PFNGLDRAWBUFFERSPROC, glDrawBuffers) \
    X(PFNGLDRAWELEMENTSPROC, glDrawElements) \
    X(PFNGLENABLEPROC, glEnable) \
    X(PFNGLENABLEVERTEXATTRIBARRAYPROC, glEnableVertexAttribArray) \
    X(PFNGLFENCESYNCPROC, glFenceSync) \
    X(PFNGLFLUSHMAPPEDBUFFERRANGEPROC, glFlushMappedBufferRange) \
    X(PFNGLFRAMEBUFFERRENDERBUFFERPROC, glFramebufferRenderbuffer) \
    X(PFNGLFRAMEBUFFERTEXTUREPROC, glFramebufferTexture) \
    X(PFNGLFRAMEBUFFERTEXTURE2DPROC, glFramebufferTexture2D) \
    X(PFNGLFRAMEBUFFERTEXTURELAYERPROC, glFramebufferTextureLayer) \
    X(PFNGLFRONTFACEPROC, glFrontFace) \
    X(PFNGLGENBUFFERSPROC, glGenBuffers) \
    X(PFNGLGENFRAMEBUFFERSPROC, glGenFramebuffers) \
    X(PFNGLGENQUERIESPROC, glGenQueries) \
    X(PFNGLGENRENDERBUFFERSPROC, glGenRenderbuffers) \
    X(PFNGLGENTEXTURESPROC, glGenTextures) \
    X(PFNGLGENVERTEXARRAYSPROC, glGenVertexArrays) \
    X(PFNGLGENERATEMIPMAPPROC, glGenerateMipmap) \
    X(PFNGLGETBOOLEANVPROC, glGetBooleanv) \
    X(PFNGLGETBUFFERPARAMETERIVPROC, glGetBufferParameteriv) \
    X(PFNGLGETBUFFERSUBDATAPROC, glGetBufferSubData) \
    X(PFNGLGETERRORPROC, glGetError) \
    X(PFNGLGETFLOATVPROC, glGetFloatv) \
    X(PFNGLGETINTEGERI_VPROC, glGetIntegeri_v) \
    X(PFNGLGETINTEGERVPROC, glGetIntegerv) \
    X(PFNGLGETPROGRAMINFOLOGPROC, glGetProgramInfoLog) \
    X(PFNGLGETPROGRAMIVPROC, glGetProgramiv) \
    X(PFNGLGETQUERYOBJECTIVPROC, glGetQueryObjectiv) \
    X(PFNGLGETQUERYOBJECTUI64VPROC, glGetQueryObjectui64v) \
    X(PFNGLGETSHADERINFOLOGPROC, glGetShaderInfoLog) \
    X(PFNGLGETSHADERIVPROC, glGetShaderiv) \
    X(PFNGLGETSTRINGPROC, glGetString) \
    X(PFNGLGETTEXIMAGEPROC, glGetTexImage) \
    X(PFNGLGETTEXLEVELPARAMETERIVPROC, glGetTexLevelParameteriv) \
    X(PFNGLGETTEXPARAMETERIVPROC, glGetTexParameteriv) \
    X(PFNGLGETTEXTURESUBIMAGEPROC, glGetTextureSubImage) \
    X(PFNGLGETUNIFORMBLOCKINDEXPROC, glGetUniformBlockIndex) \
    X(PFNGLGETUNIFORMLOCATIONPROC, glGetUniformLocation) \
    X(PFNGLISTEXTUREPROC, glIsTexture) \
    X(PFNGLLINEWIDTHPROC, glLineWidth) \
    X(PFNGLLINKPROGRAMPROC, glLinkProgram) \
    X(PFNGLMAPBUFFERPROC, glMapBuffer) \
    X(PFNGLMAPBUFFERRANGEPROC, glMapBufferRange) \
    X(PFNGLMEMORYBARRIERPROC, glMemoryBarrier) \
    X(PFNGLMULTIDRAWARRAYSINDIRECTPROC, glMultiDrawArraysIndirect) \
    X(PFNGLPIXELSTOREIPROC, glPixelStorei) \
    X(PFNGLPOINTSIZEPROC, glPointSize) \
    X(PFNGLPOPDEBUGGROUPPROC, glPopDebugGroup) \
    X(PFNGLPROVOKINGVERTEXPROC, glProvokingVertex) \
    X(PFNGLPUSHDEBUGGROUPPROC, glPushDebugGroup) \
    X(PFNGLQUERYCOUNTERPROC, glQueryCounter) \
    X(PFNGLREADBUFFERPROC, glReadBuffer) \
    X(PFNGLREADPIXELSPROC, glReadPixels) \
    X(PFNGLRENDERBUFFERSTORAGEPROC, glRenderbufferStorage) \
    X(PFNGLSCISSORPROC, glScissor) \
    X(PFNGLSHADERSOURCEPROC, glShaderSource) \
    X(PFNGLSTENCILFUNCPROC, glStencilFunc) \
    X(PFNGLSTENCILOPPROC, glStencilOp) \
    X(PFNGLTEXBUFFERPROC, glTexBuffer) \
    X(PFNGLTEXIMAGE2DPROC, glTexImage2D) \
    X(PFNGLTEXIMAGE3DPROC, glTexImage3D) \
    X(PFNGLTEXPARAMETERFPROC, glTexParameterf) \
    X(PFNGLTEXPARAMETERIPROC, glTexParameteri) \
    X(PFNGLTEXSTORAGE2DPROC, glTexStorage2D) \
    X(PFNGLTEXSUBIMAGE3DPROC, glTexSubImage3D) \
    X(PFNGLUNIFORM1FVPROC, glUniform1fv) \
    X(PFNGLUNIFORM1IVPROC, glUniform1iv) \
    X(PFNGLUNIFORM2FVPROC, glUniform2fv) \
    X(PFNGLUNIFORM2IVPROC, glUniform2iv) \
    X(PFNGLUNIFORM3FVPROC, glUniform3fv) \
    X(PFNGLUNIFORM3IVPROC, glUniform3iv) \
    X(PFNGLUNIFORM4FVPROC, glUniform4fv) \
    X(PFNGLUNIFORM4IVPROC, glUniform4iv) \
    X(PFNGLUNIFORMBLOCKBINDINGPROC, glUniformBlockBinding) \
    X(PFNGLUNIFORMMATRIX3FVPROC, glUniformMatrix3fv) \
    X(PFNGLUNIFORMMATRIX4FVPROC, glUniformMatrix4fv) \
    X(PFNGLUNMAPBUFFERPROC, glUnmapBuffer) \
    X(PFNGLUSEPROGRAMPROC, glUseProgram) \
    X(PFNGLVERTEXATTRIBDIVISORPROC, glVertexAttribDivisor) \
    X(PFNGLVERTEXATTRIBIPOINTERPROC, glVertexAttribIPointer) \
    X(PFNGLVERTEXATTRIBPOINTERPROC, glVertexAttribPointer) \
    X(PFNGLVIEWPORTPROC, glViewport)

#define PF_GL_DECLARE(type, name) extern __typeof__(name) *pf_##name;
PF_GL_FUNCTIONS(PF_GL_DECLARE)
#undef PF_GL_DECLARE

#ifndef PF_GL_NO_ALIASES
#define glActiveTexture pf_glActiveTexture
#define glAttachShader pf_glAttachShader
#define glBindBuffer pf_glBindBuffer
#define glBindBufferBase pf_glBindBufferBase
#define glBindFramebuffer pf_glBindFramebuffer
#define glBindImageTexture pf_glBindImageTexture
#define glBindRenderbuffer pf_glBindRenderbuffer
#define glBindTexture pf_glBindTexture
#define glBindVertexArray pf_glBindVertexArray
#define glBlendEquation pf_glBlendEquation
#define glBlendFunc pf_glBlendFunc
#define glBlitFramebuffer pf_glBlitFramebuffer
#define glBufferData pf_glBufferData
#define glBufferStorage pf_glBufferStorage
#define glBufferSubData pf_glBufferSubData
#define glCheckFramebufferStatus pf_glCheckFramebufferStatus
#define glClear pf_glClear
#define glClearColor pf_glClearColor
#define glClientWaitSync pf_glClientWaitSync
#define glCompileShader pf_glCompileShader
#define glCopyBufferSubData pf_glCopyBufferSubData
#define glCopyImageSubData pf_glCopyImageSubData
#define glCreateProgram pf_glCreateProgram
#define glCreateShader pf_glCreateShader
#define glCullFace pf_glCullFace
#define glDebugMessageCallback pf_glDebugMessageCallback
#define glDebugMessageControl pf_glDebugMessageControl
#define glDeleteBuffers pf_glDeleteBuffers
#define glDeleteFramebuffers pf_glDeleteFramebuffers
#define glDeleteQueries pf_glDeleteQueries
#define glDeleteRenderbuffers pf_glDeleteRenderbuffers
#define glDeleteShader pf_glDeleteShader
#define glDeleteSync pf_glDeleteSync
#define glDeleteTextures pf_glDeleteTextures
#define glDeleteVertexArrays pf_glDeleteVertexArrays
#define glDepthFunc pf_glDepthFunc
#define glDepthMask pf_glDepthMask
#define glDisable pf_glDisable
#define glDispatchCompute pf_glDispatchCompute
#define glDrawArrays pf_glDrawArrays
#define glDrawArraysInstanced pf_glDrawArraysInstanced
#define glDrawBuffer pf_glDrawBuffer
#define glDrawBuffers pf_glDrawBuffers
#define glDrawElements pf_glDrawElements
#define glEnable pf_glEnable
#define glEnableVertexAttribArray pf_glEnableVertexAttribArray
#define glFenceSync pf_glFenceSync
#define glFlushMappedBufferRange pf_glFlushMappedBufferRange
#define glFramebufferRenderbuffer pf_glFramebufferRenderbuffer
#define glFramebufferTexture pf_glFramebufferTexture
#define glFramebufferTexture2D pf_glFramebufferTexture2D
#define glFramebufferTextureLayer pf_glFramebufferTextureLayer
#define glFrontFace pf_glFrontFace
#define glGenBuffers pf_glGenBuffers
#define glGenFramebuffers pf_glGenFramebuffers
#define glGenQueries pf_glGenQueries
#define glGenRenderbuffers pf_glGenRenderbuffers
#define glGenTextures pf_glGenTextures
#define glGenVertexArrays pf_glGenVertexArrays
#define glGenerateMipmap pf_glGenerateMipmap
#define glGetBooleanv pf_glGetBooleanv
#define glGetBufferParameteriv pf_glGetBufferParameteriv
#define glGetBufferSubData pf_glGetBufferSubData
#define glGetError pf_glGetError
#define glGetFloatv pf_glGetFloatv
#define glGetIntegeri_v pf_glGetIntegeri_v
#define glGetIntegerv pf_glGetIntegerv
#define glGetProgramInfoLog pf_glGetProgramInfoLog
#define glGetProgramiv pf_glGetProgramiv
#define glGetQueryObjectiv pf_glGetQueryObjectiv
#define glGetQueryObjectui64v pf_glGetQueryObjectui64v
#define glGetShaderInfoLog pf_glGetShaderInfoLog
#define glGetShaderiv pf_glGetShaderiv
#define glGetString pf_glGetString
#define glGetTexImage pf_glGetTexImage
#define glGetTexLevelParameteriv pf_glGetTexLevelParameteriv
#define glGetTexParameteriv pf_glGetTexParameteriv
#define glGetTextureSubImage pf_glGetTextureSubImage
#define glGetUniformBlockIndex pf_glGetUniformBlockIndex
#define glGetUniformLocation pf_glGetUniformLocation
#define glIsTexture pf_glIsTexture
#define glLineWidth pf_glLineWidth
#define glLinkProgram pf_glLinkProgram
#define glMapBuffer pf_glMapBuffer
#define glMapBufferRange pf_glMapBufferRange
#define glMemoryBarrier pf_glMemoryBarrier
#define glMultiDrawArraysIndirect pf_glMultiDrawArraysIndirect
#define glPixelStorei pf_glPixelStorei
#define glPointSize pf_glPointSize
#define glPopDebugGroup pf_glPopDebugGroup
#define glProvokingVertex pf_glProvokingVertex
#define glPushDebugGroup pf_glPushDebugGroup
#define glQueryCounter pf_glQueryCounter
#define glReadBuffer pf_glReadBuffer
#define glReadPixels pf_glReadPixels
#define glRenderbufferStorage pf_glRenderbufferStorage
#define glScissor pf_glScissor
#define glShaderSource pf_glShaderSource
#define glStencilFunc pf_glStencilFunc
#define glStencilOp pf_glStencilOp
#define glTexBuffer pf_glTexBuffer
#define glTexImage2D pf_glTexImage2D
#define glTexImage3D pf_glTexImage3D
#define glTexParameterf pf_glTexParameterf
#define glTexParameteri pf_glTexParameteri
#define glTexStorage2D pf_glTexStorage2D
#define glTexSubImage3D pf_glTexSubImage3D
#define glUniform1fv pf_glUniform1fv
#define glUniform1iv pf_glUniform1iv
#define glUniform2fv pf_glUniform2fv
#define glUniform2iv pf_glUniform2iv
#define glUniform3fv pf_glUniform3fv
#define glUniform3iv pf_glUniform3iv
#define glUniform4fv pf_glUniform4fv
#define glUniform4iv pf_glUniform4iv
#define glUniformBlockBinding pf_glUniformBlockBinding
#define glUniformMatrix3fv pf_glUniformMatrix3fv
#define glUniformMatrix4fv pf_glUniformMatrix4fv
#define glUnmapBuffer pf_glUnmapBuffer
#define glUseProgram pf_glUseProgram
#define glVertexAttribDivisor pf_glVertexAttribDivisor
#define glVertexAttribIPointer pf_glVertexAttribIPointer
#define glVertexAttribPointer pf_glVertexAttribPointer
#define glViewport pf_glViewport
#endif

#else
#include <GL/glew.h>
#endif

bool PFGL_Load(void);
void PFGL_Reset(void);

bool PFGL_HasVersion33(void);
bool PFGL_KHRDebugSupported(void);
bool PFGL_CopyImageSupported(void);
bool PFGL_BufferStorageSupported(void);
bool PFGL_MultiDrawIndirectSupported(void);
bool PFGL_ComputeShaderSupported(void);
bool PFGL_TimerQuerySupported(void);
bool PFGL_TextureSubImageSupported(void);

#endif
