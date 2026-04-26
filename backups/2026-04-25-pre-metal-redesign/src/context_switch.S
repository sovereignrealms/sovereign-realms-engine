#
#  This file is part of Permafrost Engine.
#  Copyright (C) 2023 Eduard Permyakov
#
#  Permafrost Engine is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  Permafrost Engine is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
#  Linking this software statically or dynamically with other modules is making
#  a combined work based on this software. Thus, the terms and conditions of
#  the GNU General Public License cover the whole combination.
#
#  As a special exception, the copyright holders of Permafrost Engine give
#  you permission to link Permafrost Engine with independent modules to produce
#  an executable, regardless of the license terms of these independent
#  modules, and to copy and distribute the resulting executable under
#  terms of your choice, provided that you also meet, for each linked
#  independent module, the terms and conditions of the license of that
#  module. An independent module is a module which is not derived from
#  or based on Permafrost Engine. If you modify Permafrost Engine, you may
#  extend this exception to your version of Permafrost Engine, but you are not
#  obliged to do so. If you do not wish to do so, delete this exception
#  statement from your version.
#

#if defined(__APPLE__)
#define EXT(sym) _##sym
#else
#define EXT(sym) sym
#endif

#if defined(__x86_64__) || defined(_WIN64)

#if defined(_WIN32)

# parameter 0 (%rcx) - save ctx ptr
# parameter 1 (%rdx) - load ctx ptr
# parameter 2 (%r8)  - return value
# parameter 3 (%r9)  - arg passed to
#                      context code

.text
.global EXT(sched_switch_ctx)

EXT(sched_switch_ctx):
Lsave_ctx:
   lea Lback(%rip), %rax
   push %rax
   mov %rbx,  0x0(%rcx)
   mov %rsp,  0x8(%rcx)
   mov %rbp, 0x10(%rcx)
   mov %rdi, 0x18(%rcx)
   mov %rsi, 0x20(%rcx)
   mov %r12, 0x28(%rcx)
   mov %r13, 0x30(%rcx)
   mov %r14, 0x38(%rcx)
   mov %r15, 0x40(%rcx)
   stmxcsr 0x48(%rcx)
   fstcw   0x4c(%rcx)
   movdqa %xmm6, 0x50(%rcx)
   movdqa %xmm7, 0x60(%rcx)
   movdqa %xmm8, 0x70(%rcx)
   movdqa %xmm9, 0x80(%rcx)
   movdqa %xmm10, 0x90(%rcx)
   movdqa %xmm11, 0xa0(%rcx)
   movdqa %xmm12, 0xb0(%rcx)
   movdqa %xmm13, 0xc0(%rcx)
   movdqa %xmm14, 0xd0(%rcx)
   movdqa %xmm15, 0xe0(%rcx)
Lload_ctx:
   mov  0x0(%rdx), %rbx
   mov  0x8(%rdx), %rsp
   mov 0x10(%rdx), %rbp
   mov 0x18(%rdx), %rdi
   mov 0x20(%rdx), %rsi
   mov 0x28(%rdx), %r12
   mov 0x30(%rdx), %r13
   mov 0x38(%rdx), %r14
   mov 0x40(%rdx), %r15
   ldmxcsr 0x48(%rdx)
   fldcw   0x4c(%rdx)
   movdqa 0x50(%rdx), %xmm6
   movdqa 0x60(%rdx), %xmm7
   movdqa 0x70(%rdx), %xmm8
   movdqa 0x80(%rdx), %xmm9
   movdqa 0x90(%rdx), %xmm10
   movdqa 0xa0(%rdx), %xmm11
   movdqa 0xb0(%rdx), %xmm12
   movdqa 0xc0(%rdx), %xmm13
   movdqa 0xd0(%rdx), %xmm14
   movdqa 0xe0(%rdx), %xmm15
   mov %rdx, %rcx
   mov %r9, %rdx
   mov %r8, %rax
Lback:
   ret

.text
.global EXT(sched_task_exit_trampoline)

EXT(sched_task_exit_trampoline):
   mov %rax, %rcx
   jmp EXT(sched_task_exit)

#else

# parameter 0 (%rdi) - save ctx ptr
# parameter 1 (%rsi) - load ctx ptr
# parameter 2 (%rdx) - return value
# parameter 3 (%rcx) - arg passed to
#                      context code

.text
.global EXT(sched_switch_ctx)

EXT(sched_switch_ctx):
Lsave_ctx:
   lea Lback(%rip), %r8
   push %r8
   mov %rbx,  0x0(%rdi)
   mov %rsp,  0x8(%rdi)
   mov %rbp, 0x10(%rdi)
   mov %r12, 0x18(%rdi)
   mov %r13, 0x20(%rdi)
   mov %r14, 0x28(%rdi)
   mov %r15, 0x30(%rdi)
   stmxcsr 0x38(%rdi)
   fstcw   0x3c(%rdi)
Lload_ctx:
   mov  0x0(%rsi), %rbx
   mov  0x8(%rsi), %rsp
   mov 0x10(%rsi), %rbp
   mov 0x18(%rsi), %r12
   mov 0x20(%rsi), %r13
   mov 0x28(%rsi), %r14
   mov 0x30(%rsi), %r15
   ldmxcsr 0x38(%rsi)
   fldcw   0x3c(%rsi)
   mov %rcx, %rdi
   mov %rdx, %rax
Lback:
   ret

.text
.global EXT(sched_task_exit_trampoline)

EXT(sched_task_exit_trampoline):
   movq %rax, %rdi
   movq %rdx, %rsi
   jmp EXT(sched_task_exit)

#endif

#elif defined(__aarch64__) && defined(__APPLE__)

# parameter 0 (x0) - save ctx ptr
# parameter 1 (x1) - load ctx ptr
# parameter 2 (x2) - return value for resumed sched_switch_ctx
# parameter 3 (x3) - arg passed to task entry trampoline

.text
.align 2
.global EXT(sched_switch_ctx)

EXT(sched_switch_ctx):
Lsave_ctx:
    adr x9, Lback
    stp x19, x20, [x0, #0]
    stp x21, x22, [x0, #16]
    stp x23, x24, [x0, #32]
    stp x25, x26, [x0, #48]
    stp x27, x28, [x0, #64]
    str x29, [x0, #80]
    str x30, [x0, #88]
    mov x10, sp
    str x10, [x0, #96]
    str x9, [x0, #104]
    str d8,  [x0, #112]
    str d9,  [x0, #120]
    str d10, [x0, #128]
    str d11, [x0, #136]
    str d12, [x0, #144]
    str d13, [x0, #152]
    str d14, [x0, #160]
    str d15, [x0, #168]
    mrs x9, fpcr
    str x9, [x0, #176]
    mrs x9, fpsr
    str x9, [x0, #184]
Lload_ctx:
    ldp x19, x20, [x1, #0]
    ldp x21, x22, [x1, #16]
    ldp x23, x24, [x1, #32]
    ldp x25, x26, [x1, #48]
    ldp x27, x28, [x1, #64]
    ldr x29, [x1, #80]
    ldr x30, [x1, #88]
    ldr x10, [x1, #96]
    mov sp, x10
    ldr x9, [x1, #104]
    ldr d8,  [x1, #112]
    ldr d9,  [x1, #120]
    ldr d10, [x1, #128]
    ldr d11, [x1, #136]
    ldr d12, [x1, #144]
    ldr d13, [x1, #152]
    ldr d14, [x1, #160]
    ldr d15, [x1, #168]
    ldr x10, [x1, #176]
    msr fpcr, x10
    ldr x10, [x1, #184]
    msr fpsr, x10
    mov x0, x2
    mov x1, x3
    br x9
Lback:
    ret

.text
.align 2
.global EXT(sched_task_entry_trampoline)

EXT(sched_task_entry_trampoline):
    mov x0, x1
    br x19

.text
.align 2
.global EXT(sched_task_exit_trampoline)

EXT(sched_task_exit_trampoline):
    b EXT(sched_task_exit)

#else
#error "Unsupported platform"
#endif
