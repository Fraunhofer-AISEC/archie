#!/bin/bash

echo "Make faultplugin"
cd faultplugin
make
cd ..

echo "Check if formating is correct"
black --check --diff *.py analysis/*.py

echo "Test Archie"
pytest 
