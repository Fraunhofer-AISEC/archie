    .section .text.startup
    .global _start
    .align  4

_start:
    // Set up stack pointer
    ldr     x9, =__stack_top
    mov     sp, x9
    mov     fp, sp      // x29 = frame pointer (fp)

    bl      main

1:  b 1b
