BINARY = minimal

PREFIX 		:=riscv64-unknown-elf-

CC 		:=$(PREFIX)gcc

make:
	$(CC) -g -ffreestanding -Wl,--gc-sections -nostartfiles -nostdlib -nodefaultlibs -Wl,-T,riscv64-virt.ld crt0.s minimal.c -o $(BINARY).elf

clean:
	rm $(BINARY).elf
