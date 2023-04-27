# This Readme documents the structure for fault.json files.

The order of the blocks in the json file can be switched.

[[_TOC_]]

## JSON vs JSON5

For ARCHIE the JSON5 python3 library is strongly recommended. The main advantage above the standard JSON library is the support for Hex integers.
Furthermore JSON5 allows to add comments to the configuration file, while JSON does not.
For a general overview over JSON, read [here](https://www.json.org/json-en.html).
For a general overview what JSON5 has to offer over JSON, read [here](https://json5.org/)

When using JSON5, all integers, e.g addresses, can be provided as Hex numbers or normal integers. When using JSON only normal integers are allowed.
Configuration files for JSON will work with the JSON5 library but not the other way around.

If JSON5  and JSON libraries are installed, ARCHIE will use the JSON5 library.

## General structure
The top structure is a Dictionary (in python concepts speaking).
Here we can define general parameters.

### max_instruction_count
max_instruction_count is used by the plugin to set the maximum of executed instructions. The start and end of these instructions is determined by start and end. In total, there are three possible configurations:
* "start" and "end" points are defined: The instruction count begins at the end of the Translation Block (TB) that contains the start address, and either ends after the last TB associated with "end" (when single-stepping is disabled) or when the instruction corresponding to the end address was reached (when single-stepping is not enabled) 
* only "start" is defined: The instructions count begins at the end of the Translation Block (TB) that contains the start address. It ends when max_instruction_count instructions (not TB!) have been executed.
* only "end" is defined: The instruction count starts at the first instruction of the program / startup code (for a microcontroller: boot loader level) and ends either when the specified end address (or after the last TB block, if single-stepping is disabled) is reached or when *end - start + max_instruction_count* instructions have been reached. 
* neither "start" or "end" are defined: The counting of instructions begins at the first instruction of the specified binary and ends after max_instruction_count instructions have been reached.
The purpose of setting a start and end point for the analysis is to reduce the number of callbacks to the Qemu plugin and thus reduce the amount of time needed. 

max_instruction_count has two contexts. The first one is if no end point is defined, the counting of max_instruction_count begins at the start point / start of execution of guest kernel (i.e. the first instruction of the program, in case of a microcontroller this would be the bootloader).
The second scenario is if an end point is defined. The framework will calculate the number of instruction executed between start point / start of execution until end point. Afterwards it adds max_instruction_count as a delta for potential faults. So max_instruction_count in this context is a delta of instructions executed until Qemu terminates.

Criteria for ending the instruction count (if "end" block exists in fault.json):
* end address is reached (or last TB finished) 
* a limit of *end - start + max_instruction_count* instructions is reached (relative limit) 

Criteria for ending the instruction count (if "end" block does not exists in fault.json):
* max_instruction_count (limit) instructions have been executed (absolute limit)

The limit is necessary, since the program could be caught up in an infinite loop caused by the "injected" faults. To determine which of these terminating conditions applied, the output file (in HDF5 format) can be consulted. In table "faults" (under "experiments"), the attribute "endpoint" reveals whether the first end point (value: 1) or whether the absolute or relative limit (value: 0) was reached. In addition, the termination reason ("max tb" or "endpoint {address}/{counter}") is included in the attribute "end_reason" of table "faults". The number of instructions specified in max_instruction_count is only treated as an absolute value when "end" is not defined, otherwise max_instruction_count only goes into the calculation of the limit (*end - start + max_instruction_count*) for the termination of the plugin.

Currently, when the start point is set, the respective translation block that contains "start" is skipped. The counting of instructions is begun after this TB. A translation block is begun (and ended) after (at) any kind of branch operation. In single-stepping mode, one instruction corresponds to one TB. Single-stepping is enabled automatically after the trigger counter incrementation terminates and the fault is "injected". Hence, a more detailed analysis of the fault propagation is provided. Single-stepping can also be enabled via the command line (within QEMU) or by setting fault_lifespan to a value that differs from 0. In certain cases, single-stepping can be activated unintentionally: Just before the trigger counter has performed its last incrementation (i.e., the last trigger count was not yet reached), single-stepping is enabled. If however, the trigger address is not passed again within the program flow, single-stepping still remains enabled.

To remove the start or end point, delete the respective block in fault.json (e.g., delete ``"start": { ...}`` to remove the start point).

### start
The start point is also a dictionary containing two variables. Its address and counter.
Address defines an instruction in the kernel whose execution determines when the tracking of the plugin should start. The counter is the amount of executions of the start instruction until the plugin tracking is enabled. So if it is set to 1 it will start the execution of the plugin when the instruction is first reached. If it is set to 2 it will start the plugin at the second execution of start. Keep in mind that the start point is inside a translation block and is only accurate to the translation block level. Only after the translation block that contains the start address is finished, an analysis of faults is possible. Hence, it has to be taken care of that the faults are defined in subsequent translation blocks.

### end
End is similar to start. It defines the end point of execution. It has two variables.
Address is the address of the end instruction. It needs to be a valid instruction address!
Counter is the amount of executions of the end point. 1 means at the first encounter of the "end" instruction, the program is terminated. If it is 2 it is terminated at the second execution etc.

Multiple end points can be specified by defining "end" as an array.

**Attention!**
The end point counter is not an absolute value, but relative to the specified "start".
The start of counting depends on if "start" is set or not. If it is set, the end point counter is enabled as soon as the start point is reached. If it is not set, the end point is enabled from the start of the execution of the kernel. This means that as soon as the "start" address in the respective TB has been found, the counter for the end point begins to run. In case of an AES algorithm, where the start was set to round 4, and the end point was set to round 9, the end point counter will start at round 4, thus terminating the plugin tracking at 4+9 rounds. Keep that in mind!


### memorydump
Memory dump is a list of dictionaries. Each dictionary defines a memory region that should be dumped at the end of execution.
Each dictionary contains to members: Address defines the start address of the memory dump. Length defines the amount of bytes, that should be dumped. Several memory dumps are possible by inserting several dictionaries, i.e., ``{ "address" : ..., "length" : .... }``

Currently, register dumps are not possible.

### faults
"faults" is the most complex structure that can be defined in fault.json.
It is a list of lists of dictionaries.
The inner list allows to define multiple faults that should be performed together.
The outer list allows to define faults that should be performed and are independent of each other. 

Faulting registers differs from the configuration of faulting data or instructions. The fault address in this case is not set to an instruction, but to a register, e.g. r3.
In terms of register faults, the trigger can not be set automatically, i.e. trigger values with negative values are not defined in this case. The trigger has to be set to a valid instruction (or instruction range). Register faults were tested for ARM and RISC-V

#### faults dictionary
The faults dictionary contains the following members
* fault_address
* fault_address_exclude
* fault_type
* fault_model
* fault_lifespan
* fault_mask
* trigger_address
* trigger_counter
* num_bytes (optional)

Except for fault_type and fault_model, it is possible to define a range of values for the parameters.
That is why each element is placed inside a list. Each list has either one or three members. Three members are decoded as python3 ranged parameters. One member is processed as single value.
Furthermore if the list is replaced with a dictionary, it is possible to define special range options.

Each dictionary has two entries called type and range.
Type is a string, that specifies the desired operation. Range contains the needed numerical values depending on type.
Shift implements a left shift. The first number is the value to be shifted, the second number is the lowest shift number and the third the highest shift number.
For example if the configuration is ``{"type" : "shift", "range" : [1, 0, 5]}``, the 1 is shifted 0 to 4 positions to the left, i.e., (1 << 0 to 1 << 4). The step size is 1.

##### fault_address
Fault address defines the fault location. It needs to be a valid system address. It is not checked by the framework. If fault_address is [-1] it is replaced by the unrolled trigger address, i.e., the entire trigger range is inserted (if specified), otherwise only the trigger address is copied. 

Currently, by setting [-1], the trigger and fault address are equal and, hence, fault injection is not possible.

Wildcard faults can be used to fault all instructions recorded during the golden run. They are specified using an asterisk (*). An optional start and end point can be specified. Each endpoint is in the format `address/hitcounter`. The hitcounter is optional, just the address can be specified to use the default of 1. A complete example of a wildcard fault is the following.

``"fault_address" : ["start/2", "*", "end/2"]``

In the local wildcard mode, all occurrences of a wildcard range will be selected. It is specified by setting the hitcounter of both the wildcard start and end points to zero. The following is an example of a wildcard fault type in the local mode.

``"fault_address" : ["start/0", "*", "end/0"]``

Example 1:
``"fault_address" : [address1]``

A fault is inserted at the respective address. This setting results in one experiment, i.e., one experiment is associated with one fault.

Example 2:
``"fault_address" : [address1, address2, step]``

In this case, the first fault is inserted into "address1", and successively, the next fault will be inserted into *address1 + step*, and so forth. The last fault is inserted at *address2 - step*, i.e., *address2* is exclusive. For each fault, a separate experiment is started. The experiments are conducted consecutively.
 

**Attention!**
"-1" for the fault_address and for the trigger_address have different meanings. If the fault_address is set to "-1", the trigger address is copied. Parameters like "-2", "-3", ... are not defined for the fault_address. 
If the trigger_address is defined as "-1", the trigger address is set to one instruction ahead of the fault address. In this case, "-2", "-3" and so forth, lead to the trigger address being to set to two or three instructions ahead of the fault address.

Currently, only addresses in decimal representation are accepted. 

###### fault_exclude

For the wildcard mode there is the possibility to exclude certain instructions.
The fault_exclude address ranges are specified by start and end.
No faults are generated for addresses within this range.
It is evaluated similar to a pythonic range.
Hence, a fault address equal to the end value is not excluded.
The ranges are collected within a list in the fault config to allow for multiple exclude ranges.

Example:
``"fault_address_exclude" : [ ["start", "end"] ]``

###### fault_type
Valid fault types are "instruction", "data" and "reg".
This defines the location and type of fault.
"instruction" assumes that the fault address is an instruction to fault.
"data" assumes that the faulted address is not an instruction to fault.
In both cases fault_address must be a valid system memory address on the target.
"reg" changes the meaning of fault_address. In this case, it then stands for the gdb register number to place the fault. On ARM, R0 is 0, PC is 15. Please see TODO for more information. 

Example for "reg": Fault in R5 :
```
  "fault_address" : [5],
  "fault_type" : "reg",
  ...
```

For all fault types a register dump is generated at the point of injection and, if non permanent, also after lifespan expired.
For "data" and "instruction" a memory dump of a fault_address is generated. It contains the condition Pre-fault, After fault and after lifespan.
Furthermore for "instruction" a disassembly of the faulted assembly instruction is generated.

###### fault_model
Currently, four fault models are implemented: "set1", "set0", "toggle", and "overwrite".
"set1" replaces all bits that are defined by fault_mask with 1 (OR), "set0" with 0 (NAND) and "toggle" toggles these bits (XOR).

Overwrite allows to set a location ( instruction, memory or register) to a specific value. With it an instruction could be rewritten to a nop instruction on the fly. This is done with the overwrite example in fault.json file. The value to be written is defined by "fault_mask" parameter. It is written to "fault_address", beginning with the lowest byte and incrementing. It therefore is little-endian.
num_bytes is used to determen how many bytes should be overwritten. Up to a maximum of 16 bytes can currently be overwritten with the help of this model.

##### fault_lifespan
Defines the number of instructions a fault is valid. If fault_lifespan is [0] it means the fault is permanent. If it is a positive number, fault_lifespan defines how many instructions the fault remains in the system. After this number of instructions, the fault is reverted. This has the potential to behave in a strange way, if the system changed the content at the respective address while the temporary fault was still active. It will only revert flipped bits back to the original state. Temporary faults are, thus, only recommended for flash memory, since usually in case of flash, less write accesses are occurring.

If the trigger_address is set to a negative number, trigger_address + fault_lifespan must be larger or equal to 0. Otherwise ARCHIE will remove the fault configuration with a warning. In addition, the fault_lifespan is automatically reduced if the trigger address is calculated to be before the start point.

##### fault_mask
Defines which bits to flip. It can be any number, however what matters is the bit representation. Each bit set will result in a fault in this location. The fault mask can also be defined as a range, e.g.
```
   "fault_masks" : [1, 20, 1]
```
The framework internally uses a bit mask of 128 bits, so any positive number from 0 to 2^128 is valid.

Alternatively it is possible to use a dictionary instead of a range.
In this case there exists at least the entry type. Other entries depend on the type.
For example when you want to shift a bit mask, you can use the type "shift" as follows
```
{"type" : "shift", "range" : [3, 7, 10]}
```
The shift corresponds to a left shift. In the above case, the number 3 is subsequently shifted by 7, 8, 9 to the left (binary representation).


##### trigger_address
Defines the trigger instruction, i.e., when this instruction has been executed, the faults (defined in fault mask) are inserted into the respective fault address. The trigger_address must be an executed instruction! For every fault address, there is a separate test, i.e., experiment. 
If trigger_address is a negative value, i.e., [-x], the framework assumes that the fault_address is a valid instruction. It will then search the trigger address x instructions before this fault_location. This means, it is possible to directly inject the fault into the instruction before the faulted instruction should be executed.
If the trigger_address is defined as "-1", the trigger address is set to one instruction ahead of the fault address. In this case, "-2", "-3" and so forth, lead to the trigger address being to set to two or three instructions ahead of the fault address.

The trigger has to be at least one instruction ahead of the fault address. If the trigger and fault address are equal, no faults will be injected!

##### trigger_counter
In case of a positive trigger_counter, this defines at which execution of the trigger instruction a fault is "injected".
In case it is set to zero, the fault is typically ignored, except if the fault is of type instruction. Then it is injected as soon as the start criteria is met.
In case of a negative trigger_address, trigger_counter represents which execution of the fault instruction should be faulted.
In the experiments, not all TBs are seen, but only the ones where a difference compared to the golden run can be observed.
The trigger counter can also be defined as a range, e.g. [128, 160, 1]. In this example, after 128, 129, 130, ... until 160 instruction executions, a fault is injected.

##### num_bytes
Num bytes is currently only used by the "overwrite" fault model. See section [fault_model](#fault_model). For all other fault models this parameter is not used and ignored. If it is not proved within a fault dictionary it is added. It therefore can be left out if a fault model does not use "num_bytes".

**Attention!** If a range is specified despite it being not used it is stille unrolled. This leads to multiple faults with the same configuration!

### ring_buffer
Use of the ring buffer implementation to store the list of executed translation blocks can be controlled with the `ring_buffer` configuration property. It expects to be passed a boolean value. If unspecified, it will default to `true`.

### mem_info
Enable collection of data on all memory accesses. The configuration property expects to be passed a boolean value. If unspecified, it will default to `false`.
