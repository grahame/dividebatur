#!/bin/bash

rm -rf venv
virtualenv -p /usr/local/bin/python3.3 ./venv
. ./venv/bin/activate
pip install Jinja2
