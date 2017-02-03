#!/bin/bash

rm $(dirname "$0")/GFEmail.txt
rm $(dirname "$0")/gf_images/*

python3 $(dirname "$0")/GoogleFinance.py > $(dirname "$0")/GFEmail.txt

if [ -n "$(cat GFEmail.txt | grep '\!\!\!')" ]
	then python3 $(dirname "$0")/GFEmail.py --signal
	else python3 $(dirname "$0")/GFEmail.py --all
fi
