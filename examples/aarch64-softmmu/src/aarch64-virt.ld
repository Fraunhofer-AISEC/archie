MEMORY
{
   RAM (rwx)  : ORIGIN = 0x40000000, LENGTH = 128M 
}
ENTRY(_start)

PROVIDE(__stack_top = ORIGIN(RAM) + LENGTH(RAM));
