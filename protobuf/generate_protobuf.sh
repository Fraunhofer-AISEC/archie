#!/bin/bash

echo "Generating protobuf files for faultplugin"

protoc -I=./ --c_out=../faultplugin/ ./control.proto
protoc -I=./ --c_out=../faultplugin/ ./fault.proto
protoc -I=./ --c_out=../faultplugin/ ./data.proto

echo "Generating protobuf files for python controller"

# If installed protobuf compiler supports it
# create pyi files
if protoc -I=./ --python_out=../ --pyi_out=../ ./fault.proto; then
  protoc -I=./ --python_out=../ --pyi_out=../ ./control.proto
  protoc -I=./ --python_out=../ --pyi_out=../ ./data.proto
else
  echo "Protobuf compiler does not support pyi files"
  echo "Generating protobuf files without pyi files"
  protoc -I=./ --python_out=../ ./fault.proto
  protoc -I=./ --python_out=../ ./control.proto
  protoc -I=./ --python_out=../ ./data.proto
fi

