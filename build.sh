#!/bin/bash

set -Eeuo pipefail

build_dir="build/debug"

install_qemu_packages() {
	echo "Install QEMU dependencies"
	echo "Try to findout distro"
	if [ -f /etc/lsb-release ]; then
		if grep -Fxq "DISTRIB_ID=Ubuntu" /etc/lsb-release
		then
			echo "Found Ubuntu. Now run sudo apt install to install packages"
			sudo apt install git build-essential ninja-build libglib2.0-dev libfdt-dev libpixman-1-dev zlib1g-dev
		else
			echo "Distro Version not supported by script. Please install dependencies of QEMU by looking in the QEMU wiki"
		fi
	else 
		echo "Distro version not supported by script. Please install dependencies described in QEMU wiki"
	fi; 
}

install_python3_pip3() {
	if [ -f /etc/lsb-release ]; then
		if grep -Fxq "DISTRIB_ID=Ubuntu" /etc/lsb-release
		then
			echo "Need to install libcap-dev for python-prctl"
			sudo apt install libcap-dev
		else
			echo "You might need to install libcap-dev for python-prctl"
		fi
	else
		echo "You might need to install libcap-dev for python-prctl"
	fi

	echo "Use pip3"
	pip3 install -r requirements.txt
}

install_python3_packages() {
	echo "Install python3 packages"
	echo "Schould this script use pip3 or the distro package manager?"
	select answer in "pip3" "apt" "Not_listed"; do
		case $answer in
			pip3 ) install_python3_pip3 ; break;;
			apt ) sudo apt install python3-tables python3-pandas python3-prctl ; break;;
			Not_listed ) echo "see Readme for the required python3 libraries" ; break;;
		esac
	done
}

#Begin of installation scritp

echo "Should this script try to install the required QEMU libraries and tools?"
select yn in "YES" "NO"; do
	case $yn in
		YES ) install_qemu_packages ; break;;
		NO ) echo "See Readme for required packages"; break;;
	esac
	echo "use 1 or 2 to anser yes or no"
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

echo "Do you want to keep log files and HDF5 file?"
select yn in "Yes" "No"; do
	case $yn in
		Yes ) rm log_* && rm test.hdf5 && echo "Deleted log and HDF5 files"; break;;
		No ) echo "cmd to delete: rm log_* && rm test.hdf5"; break;;
	esac
	echo "Please type the number corresponding to Yes or No"
done
echo "Archie was build and tested successfully"
