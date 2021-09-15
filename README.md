# ARCHIE

ARCHIE is a QEMU-based framework for ARCHitecture-Independent Evaluation of faults.
It allows the user to define fault campaigns using a JSON configuration file and automatically run the whole campaign without user input.
ARCHIE is capable of simulating permanent and transient faults into instructions, memory, and registers.
Behavioural data of the target is collected and stored inside an HDF5 log file for later analysis.

To use this python program, Qemu with the faultplugin is needed (qemu can be found in [qemu](https://github.com/tibersam/archie-qemu), the faultplugin in the faultplugin folder).
An exemplary analysis script for an AES round skip can be found in the folder "analysis".

[[_TOC_]]

## Build

For the toolchain qemu and the faultplugin needs to be compiled. This can be done by running the build.sh script.
Please make sure the required libraries for [qemu](https://wiki.qemu.org/Hosts/Linux) and the for ARCHIE the [python libraries](#installation) are installed.
For Ubuntu the build script can install the missing dependencies for qemu and python. It will ask you if it should install the dependencies.
```
./build.sh
```
Alternatively the build instructions are provided in the following sections.

## In qemu

First make sure the basic requirements for qemu are installed. See wiki for needed libraries (https://wiki.qemu.org/Hosts/Linux).
On Ubuntu systems you can install the minimum required packages with:
```
sudo apt install git build-essential ninja-build libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev
```

Checkout git submodule qemu, which should checkout tcg_plugin_dev of the git. see code segment below.

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

With this, qemu is build in qemu/build/debug/ and the plugin is build in faultplugin/
If you change the build directory for qemu, please change the path in the [Makefile](faultplugin/Makefile) in the faultplugin/ folder for building the plugin.

## In ARCHIE

### Installation

For the python3 program, the following libraries are needed
```
pandas (tested 0.25.3)
tables (tested 3.6.1)
python-prctl (tested 1.6.1)
numpy (tested 1.17.4)
json (tested 2.0.9), or json5 (tested 0.9.6)
```
These python3 libraries can either be installed using your linux-distribution's installation method or using pip3 
json5 is strongly recommended as it allows integers to be represented as hexadecimal numbers.

For pip3 the [requirements.txt](requirements.txt) can be used.
If you are using pip3, please make sure to install **libcap-dev**. It is required for python-prctl. see also [https://pythonhosted.org/python-prctl/#downloading-and-installing](https://pythonhosted.org/python-prctl/#downloading-and-installing)

### Config files

To use the python3 program (controller.py), two configuration files are needed. These files are json format. See https://www.json.org/json-en.html for details.

**qemuconf.json** contains an object containing the path to the qemu executable, the plugin library and the kernel, that should be run by qemu. See "qemuconf.json" for a valid json file with paths. Please change the paths to your respective system. The folder **miniblink** contains a demo binary for initial experimentation. To test it, modify the kernel path to ``"kernel" : "miniblink/miniblink.bin``. If another architecture should be used, change the line ``"machine" : "stm32f0discovery"`` by replacing stm32f0discovery with the associated name in qemu. To find the name, execute qemu binary with option ``-M ?``.

**fault.json** contains the description of faults. It contains an object that entails the start point object, endpoint object, memdump object and an array of faults. 
Please see the descriptions in [**fault-readme.md**](fault-readme.md) to see how to build this json object. An example setup for several experiments can be found in fault.json

The program output will be stored in an hdf5 file. For a description of how to interpret the file content see [**hdf5-readme.md**](hdf5-readme.md).

### Running the program

To run the python3 program, type:
```
python3 controller.py --debug --fault fault.json --qemu qemuconf.json output.hdf5
```
replace fault.json and qemuconf.json with the respective files

The --debug flag creates a log file for each experiment. The name of the log file has the following format: ``log_experiment-id.txt``, e.g., ``log_4.txt`` for the experiment with ID 4

To obtain further information on the input parameters, type:
```
python3 controller.py --help
```

#### GNU Debugger

It is possible to connect to a running qemu instance with gdb. To use this feature in the framework and observe introduced faults the --gdb flag can be used.
It will start the internal qemu process with gdb enabled and stops at startup of the simulated system. To connect to qemu from gdb use port 1234.
It also will force the framework to only spawn one worker and it will step through all faults configured in fault.json. If one specific fault is required, the json file needs to be edited to only contain this specific fault.
```
python3 controller.py --gdb --fault fault.json --qemu qemuconf.json output.hdf5
```
To connect from gdb to the qemu session use
```
targ rem:localhost:1234
```
QEMU will wait unil the GDB session is attached. The debugging mode is only suitable for the analysis of a low number of faults. Stepping through a large amount of faults is cumbersome. This should be considered when adjusting the json files.

