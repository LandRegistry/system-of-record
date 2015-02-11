#!/usr/bin/env bash

if [ "$1" = "-d" ]
then
  source ./environment.sh
  python3 run.py
else
  foremon start
fi
