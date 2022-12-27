#!/bin/bash

echo "Generating protobuf files for faultplugin"

protoc -I=./ --c_out=../faultplugin/ ./fault.proto

echo "Generating protobuf files for python controller"

# If installed protobuf compiler supports it
# create pyi files
protoc -I=./ --python_out=../ --pyi_out=../ ./fault.proto
if [ $? -ne 0 ]
then
  echo "Protobuf compiler does not support pyi files"
  echo "Generating protobuf files without pyi files"
  protoc -I=./ --python_out=../ ./fault.proto
fi
