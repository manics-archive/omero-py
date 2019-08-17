#!/bin/sh
set -eux

if [ "${PLATFORM}" = "miniconda" ]; then
    export PATH="$HOME/miniconda/bin:$PATH"
    anaconda -t $CONDA_UPLOAD_TOKEN upload $HOME/miniconda/conda-bld/noarch/$PACKAGE_NAME-*.tar.bz2 "$@"
fi
