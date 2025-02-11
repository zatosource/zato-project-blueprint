#!/bin/bash

# Common options
set -e
set -x
set -o pipefail
shopt -s compat31

# Find our current directory
CURDIR="${BASH_SOURCE[0]}";RL="readlink";([[ `uname -s`=='Darwin' ]] || RL="$RL -f")
while([ -h "${CURDIR}" ]) do CURDIR=`$RL "${CURDIR}"`; done
N="/dev/null";pushd .>$N;cd `dirname ${CURDIR}`>$N;CURDIR=`pwd`;popd>$N

# What environment this is
export env_name=myproject

# What password to use when logging in to the dashboard
export dashboard_password=${My_Password:-$(uuidgen)}

# What Zato version to use
export zato_version=3.3

# Name the container
export container_name=zato-$env_name

# Absolute path to where to install code in the container
export target=/opt/hot-deploy

# Full address of the remote Docker package
export package_address=ghcr.io/zatosource/zato-$zato_version-quickstart:latest

# Absolute path to our source code on host
export host_root_dir=`readlink -f $CURDIR/../../`

# Directory on host pointing to the git clone with our project
export zato_project_root=$host_root_dir

# Our enmasse file to use
export enmasse_file=enmasse.yaml
export enmasse_file_full_path=$host_root_dir/config/enmasse/$enmasse_file

# Directory for auto-generated environment variables
mkdir -p $host_root_dir/config/auto-generated

# Populate environment variables for the server
echo '[env]'                               > $host_root_dir/config/auto-generated/env.ini
echo My_API_Password_1=$My_API_Password_1 >> $host_root_dir/config/auto-generated/env.ini
echo My_API_Password_2=$My_API_Password_2 >> $host_root_dir/config/auto-generated/env.ini
echo Zato_Project_Root=$target/$env_name  >> $host_root_dir/config/auto-generated/env.ini

# Log what we're about to do
echo Starting container $container_name

docker rm --force $container_name &&
docker run                                                \
                                                          \
    --name $container_name                                \
    --restart unless-stopped                              \
                                                          \
    -p 22022:22                                           \
    -p 8183:8183                                          \
    -p 17010:17010                                        \
                                                          \
    -e Zato_Dashboard_Password=$dashboard_password        \
    -e Zato_Log_Env_Details=true                          \
                                                          \
    --mount type=bind,source=$zato_project_root,target=$target/$env_name,readonly \
    --mount type=bind,source=$enmasse_file_full_path,target=$target/enmasse/enmasse.yaml,readonly \
    --mount type=bind,source=$host_root_dir/config/auto-generated/env.ini,target=$target/enmasse/env.ini,readonly \
    --mount type=bind,source=$host_root_dir/config/python-reqs/requirements.txt,target=$target/python-reqs/requirements.txt,readonly \
    $package_address
