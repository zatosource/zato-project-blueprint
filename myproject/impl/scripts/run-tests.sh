#!/bin/bash

set -e
set -o pipefail

CURDIR="${BASH_SOURCE[0]}";RL="readlink";([[ `uname -s`=='Darwin' ]] || RL="$RL -f")
while([ -h "${CURDIR}" ]) do CURDIR=`$RL "${CURDIR}"`; done
N="/dev/null";pushd .>$N;cd `dirname ${CURDIR}`>$N;CURDIR=`pwd`;popd>$N

project_root=$(readlink -f $CURDIR/../../..)

PYTHONPATH=$project_root/myproject/impl/src:$project_root/myproject/testing/ext python -m unittest discover -s $project_root/myproject/testing/tests/ -v
