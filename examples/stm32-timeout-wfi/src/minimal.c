typedef void (*vector_table_entry_t)(void);

typedef struct {
	unsigned int *initial_sp_value; /**< Initial stack pointer value. */
	vector_table_entry_t reset;
	vector_table_entry_t nmi;
	vector_table_entry_t hard_fault;
	vector_table_entry_t memory_manage_fault; /* not in CM0 */
	vector_table_entry_t bus_fault;           /* not in CM0 */
	vector_table_entry_t usage_fault;         /* not in CM0 */
	vector_table_entry_t reserved_x001c[4];
	vector_table_entry_t sv_call;
	vector_table_entry_t debug_monitor;       /* not in CM0 */
	vector_table_entry_t reserved_x0034;
	vector_table_entry_t pend_sv;
	vector_table_entry_t systick;
	vector_table_entry_t irq[0];
} vector_table_t;

extern vector_table_t vector_table;

int main(void) {
    volatile int i = 1;
    volatile int x = 0;

    while (i) {
	__asm__("nop");
    }

    x = 0x10;

    return x;
}

void reset_handler(void) {
    main();

    while(1) {
	__asm__("wfi");
    }
}

__attribute__ ((section(".vectors")))
vector_table_t vector_table = {
	.initial_sp_value = (unsigned *)0x20002000,
	.reset = reset_handler
};
