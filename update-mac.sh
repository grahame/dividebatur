#!/bin/bash

dir=incoming/data-`date +%Y%m%d.%H%M`

mkdir "$dir" && (cd $dir;
    curl -O http://www.aec.gov.au/Elections/federal_elections/2013/files/wa-gvt.csv
    curl -O http://www.aec.gov.au/election/files/2013federalelection-all-candidates-nat-22-08.csv
    curl -O http://vtr.aec.gov.au/External/SenateStateBtlDownload-17496-WA.zip && open SenateStateBtlDownload-17496-WA.zip
    curl -O http://vtr.aec.gov.au/Downloads/SenateFirstPrefsByStateByVoteTypeDownload-17496.csv
    curl -O http://vtr.aec.gov.au/Downloads/SenateCandidatesDownload-17496.csv
)

