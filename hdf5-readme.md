# This Readme documents the structure of the HDF5 output files

## Overall structure

### Goldenrun

The Goldenrun represents the program run (defined by "start" and "end", see fault-readme.md) without any injected faults. It therefore serves as a reference to compare the faulted program to. It consists of the  following tables:

* **armregisters:** register content after execution, currently only for ARM registers (future feature: multiple register dumps at multiple points in time)
* **faults:** fault specification according to fault.json file (in this case, no faults)

	* **endpoint:** is 1 if endpoint was reached, 0 if not. Is an attribute of the fault table. Can be used to determine if the guest exited through endpoint or max instruction limit. (accessed through fault.attrs.endpoint)

* a list of **memdumps**: containing the memory dumps starting at a certain location and of a certain length as defined in fault.json (future feature: multiple memdumps)
* **meminfo**: contains information on the memory accesses  

	* **address:** address of the memory access (store or load)
	* **counter:** number of times the memory access occurred 
	* **direction:** type of access, i.e., read (0) or write (1) 
	* **insaddr:** address of the instruction that triggered the memory access
	* **size:** number of bytes of the memory access
	* **tbid:** identity of translations block, i.e., start address of the respective TB

* **tbexeclist**: the list of translation blocks in between "start" and "end" (see fault-readme.md). The table contains the position of the translation block in the order of execution and the start address of the translation block. The same TB can be executed multiple times.
* **tbinfo**: content of the translation blocks listed in *tbexeclist*

	* **assembler:** contains the assembler instructions contained in one TB
	* **identity:** start address of TB
	* **ins_count:** number of instructions in the respective TB
	* **num_exec:** number of executions of the respective TB
	* **size:** size of TB in bytes

### Pregoldenrun

The Pregoldenrun includes everything before the translations block defined by "start". If "start" is not defined, the Pregoldenrun is empty.
In the Pregoldenrun no faults are injected. For an explanation of the tables in the hdf5 output file see previous section on Goldenrun.

### fault

For each "injected" fault an experiment is created that contains the data associated with the fault and the difference in translation blocks compared with the Goldenrun.
The order of experiments in the json config file is reversed in the hdf5 output file.
Each experiment has the same table structure as the Goldenrun. However, the table tbinfo contains only the differences compared to the Goldenrun. All identical executions are not listed.

By default, the list of executed translation blocks (`tbexeclist`) is stored in a ring buffer able to store the last 100 entries. This behavior is controlled with the fault configuration property `ring_buffer` and the `--disable-ring-buffer` command line argument, which takes precedence. For the goldenrun, the ring buffer is always disabled.

## Analysis

An exemplary analysis script of the hdf5 output for an AES round skip and differential fault analysis can be found in the folder *analysis*. 


