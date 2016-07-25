#!/bin/bash

# 
# quick test to run the 2013 federal election WA senate count and check totals against verified logs
#

#!/bin/bash

cd ..

rm -rf log; mkdir -p log

base="aec_fed2013_wa/count1"

time python3 -m dividebatur.senatecount './dividebatur/aec_fed2013_wa/aec_fed2013_wa.json' './dividebatur/angular/data/'
