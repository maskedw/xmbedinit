#!/bin/bash -e
##################################################
# {% include 'generated_by.txt' %}
##################################################
thisdir="$(dirname "${BASH_SOURCE:-$0}")"
cd "$thisdir"
BUILD_TYPE=Debug ./build.sh "$@"
