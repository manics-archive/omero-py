#!/bin/sh
set -eu

if [ "${PLATFORM}" == "miniconda" ]; then
    wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh;
    sh miniconda.sh -b -p $HOME/miniconda
    conda install -y conda-build anaconda-client
    conda info -a
else
    docker info
fi
