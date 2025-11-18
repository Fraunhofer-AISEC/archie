BINARY = minimal

PREFIX 		:=arm-none-eabi-

CC 		:=$(PREFIX)gcc

LDSCRIPT = ./aarch64-virt.ld

make:
	$(CC) -g -mcpu=cortex-a53 -mthumb -Wl,-static -nostartfiles -Wl,--start-group -lc -lgcc -lnosys -Wl,--end-group -Wl,-T,$(LDSCRIPT) minimal.c -o $(BINARY).elf

clean:
	rm $(BINARY).elf -f
