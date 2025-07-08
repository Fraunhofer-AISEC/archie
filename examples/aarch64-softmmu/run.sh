#!/bin/sh
python3 ../../controller.py --debug --fault fault.json  --qemu qemuconf.json output.hdf5
