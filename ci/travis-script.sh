#!/bin/sh
set -eux

if [ "${PLATFORM}" == "miniconda" ]; then
    conda build -c ${REQUIREMENTS_CHANNEL} ./recipe
else
    docker build -t omero-py .
fi
