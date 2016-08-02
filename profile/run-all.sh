#!/bin/bash

rm *.prof
rm *.dot
for json in ../aec_data/*/profile.json; do
    rm -rf data
    mkdir data
    outprof=$(basename $(dirname $json)).prof
    outdot=$(basename $(dirname $json)).dot
    time python3 prof.py "$outprof" "$json" ./data/
    gprof2dot -f pstats "$outprof" -o "$outdot"
done
