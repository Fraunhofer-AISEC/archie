int main(void) {
    volatile int i = 1;
    volatile int x = 0;

    while (i) {
	__asm__("nop");
    }

    x = 0x10;

    // Another loop to ensure that the program does not lock up after finishing execution.
    // Otherwise archie will wait infinitely
    while (x) {
	__asm__("nop");
    }

    return x;
}
