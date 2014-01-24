#!/bin/bash

# 
# quick test to run the 2013 federal election WA senate count and check totals against verified logs
#

rm -rf log; mkdir -p log

base="aec_fed2013_wa/count1"

time ./senatecount.py aec_fed2013_wa/aec_fed2013_wa.json ./angular/data/
