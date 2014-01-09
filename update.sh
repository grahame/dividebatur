#!/bin/bash

dir=incoming/data-`date +%Y%m%d.%H%M`

mkdir "$dir" && (cd $dir;
    wget http://www.aec.gov.au/Elections/federal_elections/2013/files/wa-gvt.csv
    wget http://www.aec.gov.au/election/files/2013federalelection-all-candidates-nat-22-08.csv
    wget http://vtr.aec.gov.au/External/SenateStateBtlDownload-17496-WA.zip && unzip SenateStateBtlDownload-17496-WA.zip
    wget http://vtr.aec.gov.au/Downloads/SenateFirstPrefsByStateByVoteTypeDownload-17496.csv
    wget http://vtr.aec.gov.au/Downloads/SenateCandidatesDownload-17496.csv
)

