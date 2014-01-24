dividebatur: process single-transferable-vote elections as used for the Australian Senate under the Commonwealth Electoral Act (1918)

## License

Copyright 2013 Grahame Bowland

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

The AEC provided data under aec\_fed2013\_wa/data is licensed under a 
Creative Commons Attribution 3.0 Australia Licence (CC BY 3.0), and is 
© Commonwealth of Australia. License terms:

    http://aec.gov.au/footer/Copyright.htm

## Usage
./run\_aec\_fed2013\_wa.sh will run a count of the Fed2013 WA Senate count 
using data from the first count of ballots.  The data for these tests is in 
the repository under fed2013\_wasenate1/data

./update.sh will pull down the data needed for a WA count from the AEC

## Structure
senatecount.py builds up the initial data needed to begin the count, and then hands it to counter.py

counter.py processes the vote. Note it may require user input to break ties which occur choosing a candidate 
to exclude, choosing the order of election, or choosing the final candidate elected.


