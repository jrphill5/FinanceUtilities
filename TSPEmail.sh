#!/bin/bash

rm /tmp/TSPEmail.txt
rm $(dirname "$0")/images/tsp/*

python3 $(dirname "$0")/ThriftSavingsPlan.py > /tmp/TSPEmail.txt

if [ -n "$(cat /tmp/TSPEmail.txt | grep '\!\!\!')" ]
	then python3 $(dirname "$0")/TSPEmail.py --signal
	else python3 $(dirname "$0")/TSPEmail.py --all
fi
