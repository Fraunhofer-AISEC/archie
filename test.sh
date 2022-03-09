#!/bin/bash

echo "Make faultplugin"
cd faultplugin
make
cd ..

echo "Test Archie"
pytest 
