#!/bin/bash

rm $(dirname "$0")/images/*
python3 $(dirname "$0")/ThriftSavingsPlan.py > $(dirname "$0")/TSPEmail.txt
python3 $(dirname "$0")/TSPEmail.py
