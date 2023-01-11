# -*- Mode: makefile -*-
#
# This Makefile example is fairly independent from the main makefile
# so users can take and adapt it for their build. We only really
# include config-host.mak so we don't have to repeat probing for
# cflags that the main configure has already done for us.
#

#BUILD_DIR := $(CURDIR)/../../../build/release
BUILD_DIR := $(CURDIR)/../qemu/build/debug

include $(BUILD_DIR)/config-host.mak

VPATH += $(SRC_PATH)/tests/plugin/develop

NAMES :=
#NAMES += bb
#NAMES += empty
NAMES += faultplugin
#NAMES += mem
#NAMES += hotblocks
#NAMES += howvec
#NAMES += hotpages
#NAMES += lockstep

SONAMES := $(addsuffix .so,$(addprefix lib,$(NAMES)))

# The main QEMU uses Glib extensively so it's perfectly fine to use it
# in plugins (which many example do).
CFLAGS = $(GLIB_CFLAGS)
CFLAGS += -fPIC
CFLAGS += $(if $(findstring no-psabi,$(QEMU_CFLAGS)),-Wpsabi)
CFLAGS += -I$(SRC_PATH)/include
#CFLAGS += -I$(SRC_PATH)/include/hw/core
CFLAGS += -I$(BUILD_DIR)
# Used for protobuf
LDLIBS = -lprotobuf-c
all: $(SONAMES)

lib/avl.o: lib/avl.c
	$(CC) $(CFLAGS) -c -o $@ $<

faultdata.o: faultdata.c
	$(CC) $(CFLAGS) -c -o $@ $<

registerdump.o: registerdump.c
	$(CC) $(CFLAGS) -c -o $@ $<

singlestep.o: singlestep.c
	$(CC) $(CFLAGS) -c -o $@ $<

fault_list.o: fault_list.c
	$(CC) $(CFLAGS) -c -o $@ $<

fault_injection.o: fault_injection.c
	$(CC) $(CFLAGS) -c -o $@ $<

tb_info_data_collection.o: tb_info_data_collection.c
	$(CC) $(CFLAGS) -c -o $@ $<

tb_exec_data_collection.o: tb_exec_data_collection.c
	$(CC) $(CFLAGS) -c -o $@ $<

tb_faulted_collection.o : tb_faulted_collection.c
	$(CC) $(CFLAGS) -c -o $@ $<

fault.pb-c.o: fault.pb-c.c
	$(CC) $(CFLAGS) -c -o $@ $<

control.pb-c.o: control.pb-c.c
	$(CC) $(CFLAGS) -c -o $@ $<

data.pb-c.o: data.pb-c.c
	$(CC) $(CFLAGS) -c -o $@ $<

%.o: %.c
	$(CC) $(CFLAGS) -c -o $@ $<

lib%.so: %.o lib/avl.o faultdata.o registerdump.o singlestep.o fault_list.o fault_injection.o tb_info_data_collection.o tb_exec_data_collection.o tb_faulted_collection.o fault.pb-c.o control.pb-c.o data.pb-c.o
	$(CC) -shared -Wl,-soname,$@ -o $@ $^ $(LDLIBS)

clean:
	rm -f *.o *.so *.d
	rm -f lib/*.o
	rm -Rf .libs

.PHONY: all clean
