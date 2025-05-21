#!/bin/sh
if [ "$1" = "--unicorn" ]; then
    python3 ../../controller.py --debug --fault fault_unicorn.json --qemu qemuconf.json output.hdf5 --unicorn
else
    python3 ../../controller.py --debug --fault fault.json --qemu qemuconf.json output.hdf5
fi

