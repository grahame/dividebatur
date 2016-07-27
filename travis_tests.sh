#!/bin/bash

set -e

echo "** Tests: Federal 2013 WA **"
./run_aec_fed2013_wa.sh

echo "** Tests: Federal 2016 **"
./run_aec_fed2016.sh

