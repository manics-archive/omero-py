#!/bin/sh
set -eux

if [ "${PLATFORM}" == "miniconda" ]; then
    # Override the version string for dev builds
    if [ -z "${TRAVIS_TAG}" ]; then
      export VERSION_SUFFIX=".${TRAVIS_BRANCH}";
    else
      export VERSION_SUFFIX="";
    fi
    conda build -c ${REQUIREMENTS_CHANNEL} ./recipe
else
    docker build -t omero-py .
fi
