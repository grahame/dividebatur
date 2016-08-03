#!/bin/bash

set -eux

# Install git-lfs
mkdir -p $HOME/bin
wget https://github.com/github/git-lfs/releases/download/v1.3.0/git-lfs-linux-amd64-1.3.0.tar.gz
tar xvfz git-lfs-linux-amd64-1.3.0.tar.gz
mv git-lfs-1.3.0/git-lfs $HOME/bin/git-lfs

# Install test dependencies
pip3 install flake8
pip3 install nose
