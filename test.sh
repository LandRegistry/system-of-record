#!/usr/bin/env bash

dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $dir

source ~/venvs/system-of-record/bin/activate
source ./environment-test.sh

py.test --junitxml=TEST-systemofrecord.xml --cov application tests
