#!/bin/bash

python3 $(dirname "$0")/ThriftSavingsPlan.py > $(dirname "$0")/TSPEmail.txt
python3 $(dirname "$0")/TSPEmail.py
