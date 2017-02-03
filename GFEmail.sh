#!/bin/bash

rm /tmp/GFEmail.txt
rm $(dirname "$0")/images/gf/*

python3 $(dirname "$0")/GoogleFinance.py > /tmp/GFEmail.txt

if [ -n "$(cat /tmp/GFEmail.txt | grep '\!\!\!')" ]
	then python3 $(dirname "$0")/GFEmail.py --signal
	else python3 $(dirname "$0")/GFEmail.py --all
fi
