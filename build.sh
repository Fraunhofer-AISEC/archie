#!/bin/bash

set -Eeuo pipefail

build_dir="build/debug"

if [[ ! -f "qemu/README.rst" ]]; then
	echo "Checkout submodules"
	git submodule update --init
fi

echo "Building QEMU for archie"
cd qemu
if [[ ! -e $build_dir ]]; then
	mkdir -p $build_dir
fi
cd $build_dir
./../../configure --target-list=arm-softmmu --enable-debug --enable-plugins --disable-sdl --disable-gtk --disable-curses --disable-vnc
make -j $(nproc --all)

echo "Building faultplugin"
cd ../../../faultplugin/
make clean && make
cd ..

echo "Test ARCHIE"
python3 controller.py --debug --qemu qemuconf.json --fault fault.json test.hdf5

echo "Do you want to keep log files and HDF5 file?"
select yn in "Yes" "No"; do
	case $yn in
		Yes ) rm log_* && rm test.hdf5 && echo "Deleted log and HDF5 files"; break;;
		No ) echo "cmd to delete: rm log_* && rm test.hdf5"; break;;
	esac
	echo "Please type the number corresponding to Yes or No"
done
echo "Archie was build and tested successfully"
