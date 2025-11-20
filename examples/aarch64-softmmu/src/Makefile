BINARY = minimal

PREFIX 		?=aarch64-non-elf-

CC 		:=$(PREFIX)gcc

LDSCRIPT = ./aarch64-virt.ld

make:
	$(CC) -g -mcpu=cortex-a53 -ffreestanding -Wl,--gc-sections -nostartfiles -nostdlib -nodefaultlibs -Wl,-T,$(LDSCRIPT) crt0.s minimal.c -o $(BINARY).elf

clean:
	rm $(BINARY).elf -f
