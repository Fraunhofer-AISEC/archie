#!/bin/sh
python ../../controller.py --debug --fault fault.json  --qemu qemuconf.json output.hdf5
