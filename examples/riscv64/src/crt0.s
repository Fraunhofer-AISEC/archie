.section .init, "ax"
.global _start
_start:
    .option norelax
    la sp, __stack_top
    add s0, sp, zero
    jal zero, main
    .end
