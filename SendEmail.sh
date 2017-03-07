#!/bin/bash

case "$1" in
	tsp)
		script="ThriftSavingsPlan.py"
		;;
	gf)
		script="GoogleFinance.py"
		;;
	*)
		echo $"Usage: $0 {tsp|gf}"
		exit 1
esac

name=$(echo $1 | awk '{print toupper($0)}')
email="/tmp/${name}Email.txt"

rm $email
rm $(dirname "$0")/images/$1/*

python3 $(dirname "$0")/$script > $email

if [ -n "$(cat $email | grep '\!\!\!')" ]
	then python3 $(dirname "$0")/SendEmail.py $1 --signal
	else python3 $(dirname "$0")/SendEmail.py $1
fi
