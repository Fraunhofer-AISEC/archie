#!/bin/bash

set -Eeuo pipefail

build_dir="build/debug"

install_qemu_packages() {
	echo "Install QEMU dependencies"
	echo "Try to find out distro"
	echo "Running on ${PRETTY_NAME:-Linux}"
	if [ "${ID:-linux}" = "debian" ] || [ "${ID_LIKE#*debian*}" != "${ID_LIKE}" ]
	then
		echo "Looks like Debian!"
		sudo apt-get install git build-essential ninja-build libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev
	else
		echo "Distro Version not supported by script. Please install dependencies of QEMU by looking in the QEMU wiki"
	fi
}

install_python3_pip3() {
	echo "Running on ${PRETTY_NAME:-Linux}"
	if [ "${ID:-linux}" = "debian" ] || [ "${ID_LIKE#*debian*}" != "${ID_LIKE}" ]
	then
		echo "Looks like Debian!"
		echo "Need to install libcap-dev for python-prctl"
		sudo apt install libcap-dev
	else
		echo "You might need to install libcap-dev for python-prctl"
	fi

	echo "Install with pip3"
	pip3 install -r requirements.txt
}

install_python3_distro() {
	echo "Running on ${PRETTY_NAME:-Linux}"
	if [ "${ID:-linux}" = "debian" ] || [ "${ID_LIKE#*debian*}" != "${ID_LIKE}" ]
	then
		echo "Looks like Debian!"
		sudo apt-get install python3-tables python3-pandas python3-prctl
	else
		echo "Distro package manager not yet supported"
	fi
}

install_python3_packages() {
	echo "Install python3 packages"
	echo "Schould this script use pip3 or the distro package manager?"
	select answer in "pip3" "distro"; do
		case $answer in
			pip3 ) install_python3_pip3 ; break;;
			distro ) install_python3_distro ; break;;
		esac
	done
}

#Begin of installation script


test -e /etc/os-release && os_release='/etc/os-release'  ||  test -e /usr/lib/os-release && os_release='/usr/lib/os-release' 
. "${os_release}"

echo "Should this script try to install the required QEMU libraries and tools?"
select yn in "YES" "NO"; do
	case $yn in
		YES ) install_qemu_packages ; break;;
		NO ) echo "See Readme for required packages"; break;;
	esac
	echo "use 1 or 2 to answer yes or no"
done

echo Should this script try to install the required libraries for the Python3 part of ARCHIE?
select yn in "YES" "NO"; do
	case $yn in
		YES ) install_python3_packages ; break;;
		NO ) echo "See Readme for required packages"; break;;
	esac
	echo "use 1 or 2 to answer yes or no"
done

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

echo "Do you want to delete log files and HDF5 file?"
select yn in "YES" "NO"; do
	case $yn in
		YES ) rm log_* && rm test.hdf5 && echo "Deleted log and HDF5 files"; break;;
		NO ) echo "cmd to delete: rm log_* && rm test.hdf5"; break;;
	esac
	echo "Please type the number corresponding to Yes or No"
done
echo "Archie was build and tested successfully"
