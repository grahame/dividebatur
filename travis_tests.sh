#!/bin/bash

set -e

pip3 install flake8
pip3 install nose

nosetests -v dividebatur

for i in aec_data/*/verified.json; do
    time python3 -m dividebatur.senatecount "$i" './angular/data/'
done

flake8 --ignore=E501 dividebatur
