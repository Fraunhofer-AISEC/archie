#!/bin/bash

echo "Generating protobuf files for faultplugin"

protoc --c_out=../faultplugin/protobuf ./control.proto
protoc --c_out=../faultplugin/protobuf ./fault.proto
protoc --c_out=../faultplugin/protobuf ./data.proto

echo "Generating protobuf files for python controller"

# If installed protobuf compiler supports it
# create pyi files
if protoc --python_out=./ --pyi_out=./ ./fault.proto; then
  protoc --python_out=./ --pyi_out=./ ./control.proto
  protoc --python_out=./ --pyi_out=./ ./data.proto
else
  echo "Protobuf compiler does not support pyi files"
  echo "Generating protobuf files without pyi files"
  protoc --python_out=./ ./fault.proto
  protoc --python_out=./ ./control.proto
  protoc --python_out=./ ./data.proto
fi
