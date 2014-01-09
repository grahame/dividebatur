#!/bin/bash

# 
# quick test to run the 2013 federal election WA senate count and check totals against verified logs
#

rm -rf log; mkdir -p log

base="aec_fed2013_wa/count1"

time ./senatecount.py "$base"/data 1 1

echo
echo "** cross checking logs; any diffs are problems"
echo

for i in "$base"/verified/*.json; do
    echo "checking log: $i"
    diff -u $i log/
    echo
done

