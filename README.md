# ARCHIE

[ARCHIE] (https://fdtc.deib.polimi.it/FDTC21/slides/session%201%20-%20paper%203.pdf) is a QEMU-based framework for ARCHitecture-Independent Evaluation of faults.
It allows the user to define fault campaigns using a JSON configuration file and automatically run the whole campaign without additional user input.
ARCHIE is capable of simulating permanent and transient faults in instructions, memory, and registers.
Behavioral data of the target is collected and stored inside an HDF5 log file for later analysis.

To use this Python program, QEMU with the fault plugin is needed (QEMU can be found in [qemu](https://github.com/Fraunhofer-AISEC/archie-qemu), the fault plugin can be found in the [faultplugin](faultplugin) folder).

An exemplary analysis script for an Advanced Encryption Standard (AES) round skip can be found in the folder "analysis".

[[_TOC_]]

## Build

For the toolchain QEMU and the fault plugin need to be compiled. This can be done automatically by running the *build.sh* script.
Please make sure the required libraries for [qemu](https://wiki.qemu.org/Hosts/Linux) and the [python libraries](#installation) for ARCHIE are installed.
For Ubuntu, the build script can install the missing dependencies for QEMU and Python. It will ask you if it should install the dependencies.
```
./build.sh
```
Alternatively, the build instructions are provided in the following sections.

## In [archie-qemu](https://github.com/Fraunhofer-AISEC/archie-qemu)

ARCHIE was tested with QEMU 6.0, which is available in [archie-qemu](https://github.com/Fraunhofer-AISEC/archie-qemu).
First make sure the basic requirements for QEMU are installed. See the wiki for required libraries (https://wiki.qemu.org/Hosts/Linux).
On Ubuntu systems, you can install the minimum required packages with:
```
sudo apt install git build-essential ninja-build libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev
```

Checkout git submodule qemu, which should checkout tcg_plugin_dev of the git. See code segment below.

```
git submodule update --init
cd qemu
mkdir build
cd build
mkdir debug
cd debug
./../../configure --target-list=arm-softmmu --enable-debug --enable-plugins --disable-sdl --disable-gtk --disable-curses --disable-vnc
make -j {CPUCORENUMBER}
cd ../../../faultplugin/
make
```

With this, *archie-qemu* is build in qemu/build/debug/ and the plugin is build in *faultplugin/*
If you change the build directory for *archie-qemu*, please change the path in the [Makefile](faultplugin/Makefile) in the *faultplugin/* folder for building the plugin.

## In [archie](https://github.com/Fraunhofer-AISEC/archie)

### Installation

For the Python3 program, the following libraries are needed
```
pandas (tested 0.25.3)
tables (tested 3.6.1)
python-prctl (tested 1.6.1)
numpy (tested 1.17.4)
json (tested 2.0.9), or json5 (tested 0.9.6)
```
These python3 libraries can either be installed using your linux-distribution's installation method or by using pip3.
JSON5 is strongly recommended as it allows integers to be represented as hexadecimal numbers.

For pip3 the [requirements.txt](requirements.txt) can be used.
If you are using pip3, please make sure to install **libcap-dev**. It is required for python-prctl. See also [https://pythonhosted.org/python-prctl/#downloading-and-installing](https://pythonhosted.org/python-prctl/#downloading-and-installing)

### Config files

To use the python3 program (controller.py), two configuration files are needed. These files are in JSON format. See https://www.json.org/json-en.html for details.

**qemuconf.json** contains an object with the path to the QEMU executable, the plugin library and the kernel, that should be run by QEMU. See "qemuconf.json" for a valid json file with paths. Please adjust the paths to your respective system. The folder **miniblink** contains a demo binary for initial experimentation. To test it, modify the kernel path to ``"kernel" : "miniblink/miniblink.bin``. If another architecture should be used, change the line ``"machine" : "stm32f0discovery"`` by replacing stm32f0discovery with the associated name in QEMU. To find the name, execute the QEMU binary with option ``-M ?``.

**fault.json** contains the description of faults. It contains an object that entails the start point object, endpoint object, memdump object and an array of faults. 
Please see the descriptions in [**fault-readme.md**](fault-readme.md) to see how to build this JSON object. An example setup for several experiments can be found in fault.json

The program output will be stored in an HDF5 file. For a description of how to interpret the file content see [**hdf5-readme.md**](hdf5-readme.md).

### Running the program

To run the python3 program, type:
```
python3 controller.py --debug --fault fault.json --qemu qemuconf.json output.hdf5
```
Replace *fault.json* and *qemuconf.json* with the corresponding files.

The *--debug flag* creates a log file for each experiment. The name of the log file has the following format: ``log_experiment-id.txt``, e.g., ``log_4.txt`` for the experiment with ID 4.

To obtain further information on the input parameters, type:
```
python3 controller.py --help
```

#### GNU Debugger

It is possible to connect to a running QEMU instance with GDB. To use this feature in the framework and observe introduced faults the *--gdb* flag can be set.
ARCHIE will start the internal QEMU process with GDB enabled and halts at the startup of the simulated system. To connect to QEMU from GDB use port 1234.
It also will force the framework to only spawn one worker and it will step through all faults configured in *fault.json*. If one specific fault is required, the JSON file needs to be edited to only contain this specific fault.
```
python3 controller.py --gdb --fault fault.json --qemu qemuconf.json output.hdf5
```
To connect from GDB to the QEMU session use
```
targ rem:localhost:1234
```
QEMU will wait unil the GDB session is attached. The debugging mode is only suitable for the analysis of a low number of faults. Stepping through a large amount of faults is cumbersome. This should be considered when adjusting the JSON files.

