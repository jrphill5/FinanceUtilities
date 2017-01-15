#!/bin/bash

rm $(dirname "$0")/TSPEmail.txt
rm $(dirname "$0")/images/*

python3 $(dirname "$0")/ThriftSavingsPlan.py > $(dirname "$0")/TSPEmail.txt

if [ -n "$(cat TSPEmail.txt | grep '\!\!\!')" ]
	then python3 $(dirname "$0")/TSPEmail.py --signal
fi

python3 $(dirname "$0")/TSPEmail.py --all
