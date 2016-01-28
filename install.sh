#!/bin/bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir

virtualenv -p python3 ~/venvs/system-of-record
source ~/venvs/system-of-record/bin/activate
pip install -r requirements.txt

#Create the logging directory as it is required by default
if [ ! -d $dir/logs ]; then
	mkdir $dir/logs
fi
