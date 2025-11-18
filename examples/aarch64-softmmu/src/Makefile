BINARY = minimal

PREFIX 		:=arm-none-eabi-

CC 		:=$(PREFIX)gcc

LDSCRIPT = ./aarch64-virt.ld

make:
	$(CC) -g -mcpu=cortex-a53 -mthumb -ffreestanding -Wl,--gc-sections -nostartfiles -nostdlib -nodefaultlibs -Wl,-T,$(LDSCRIPT) crt0.s minimal.c -o $(BINARY).elf

clean:
	rm $(BINARY).elf -f
