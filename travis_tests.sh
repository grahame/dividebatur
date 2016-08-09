#!/bin/bash

set -eux

NOSETESTS=$(which nosetests3 || which nosetests)

$NOSETESTS -v dividebatur

for i in aec_data/*/*.json; do
    time python3 -m dividebatur.senatecount -v --only-verified "$i" './angular/data/'
done

flake8 --ignore=E501,E731 dividebatur
