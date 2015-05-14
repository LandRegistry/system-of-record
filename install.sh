#!/bin/bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir

virtualenv -p python3 ~/venvs/system-of-record
source ~/venvs/system-of-record/bin/activate
if [ -d /usr/pgsql-9.3/bin ]; then
  export PATH=$PATH:/usr/pgsql-9.3/bin
fi
pip install -r requirements.txt
