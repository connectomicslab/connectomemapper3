#!/bin/sh
# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

# Build the docker image of Connectome Mapper 3.
#
# Usage /bin/sh build_bidsapp.sh
#
# Created by Sebastien Tourbier
# Source: https://github.com/connectomicslab/connectomemapper3/blob/master/build_bidsapp.sh

# Get the current date and time
CMP_BUILD_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "$CMP_BUILD_DATE"

# Get Connectome Mapper 3 version
VERSION=$(python get_version.py)
echo "$VERSION"

# Get the version control commit hash
VCS_REF=$(git rev-parse --verify HEAD)
echo "$VCS_REF"

# Build the Docker image
docker build --rm --build-arg BUILD_DATE="$CMP_BUILD_DATE "\
				  --build-arg VCS_REF="$VCS_REF" \
				  --build-arg VERSION="$VERSION" \
				  -t sebastientourbier/connectomemapper-bidsapp:"${VERSION}" .
