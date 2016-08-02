dividebatur: process single-transferable-vote elections as used for the Australian Senate under the Commonwealth Electoral Act (1918)

For a high level overview of what this does, check this 
blog post:

http://blog.angrygoats.net/2014/01/25/counting-the-west-australian-senate-election/

## Build status
[![Build Status](https://travis-ci.org/grahame/dividebatur.svg?branch=master)](https://travis-ci.org/grahame/dividebatur)

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

The data located under `aec_data/` is licensed under a 
Creative Commons Attribution 3.0 Australia Licence (CC BY 3.0), and is 
© Commonwealth of Australia. Full License terms are on the
[AEC website](http://aec.gov.au/footer/Copyright.htm)

## Dependencies

For Ubuntu:

Git Large File Support:

```bash
$ mkdir -p $HOME/bin
$ wget https://github.com/github/git-lfs/releases/download/v1.3.0/git-lfs-linux-amd64-1.3.0.tar.gz
$ tar xvfz git-lfs-linux-amd64-1.3.0.tar.gz
$ mv git-lfs-1.3.0/git-lfs $HOME/bin/git-lfs
$ export PATH=$PATH:$HOME/bin/
```

# Optional to run tests
```bash
$ sudo apt-get install python3-pip
$ pip3 install flake8
$ pip3 install nose
```

## Usage

`git lfs pull` will download the large data files.

`./run_aec_fed2013_wa.sh` will run a count of the 2013/14 WA Senate count .
The data is in the repository under `aec_data/fed2013_wa`.

`./run_aec_fed2016.sh` will run a count for all states with data available,
for the 2016 federal election. The data is in the repository under `aec_data/fed2016`.

## Structure
senatecount.py builds up the initial data needed to begin the count, and then hands it to counter.py

counter.py processes the vote. Note it may require user input to break ties which occur choosing a candidate 
to exclude, choosing the order of election, or choosing the final candidate elected.


