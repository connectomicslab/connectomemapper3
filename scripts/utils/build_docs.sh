#!/bin/sh
# Copyright (C) 2009-2022, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

# Build the documentation using BASH shell interpreter and Sphinx doc generator.
#
# All python packages related to Sphinx necessary to build the docs
# are provided in the `py39cmp-gui` conda environment described by
# `environment.yml` / `environment_macosx.yml` files.
#
# Usage conda activate py39cmp-gui
#       /bin/bash build_docs.sh
#
# Created by Sebastien Tourbier
# Source: https://github.com/connectomicslab/connectomemapper3/blob/master/build_docs.sh

# Get the directory where this script is located
# to derive the path to the project and docs root
# directories
UTILSDIR=$(cd "$(dirname "$0")"; pwd)
SCRIPTSDIR="$(dirname "$UTILSDIR")"
BASEDIR="$(dirname "$SCRIPTSDIR")"

# Install the latest version of the code
cd "$BASEDIR"
# pip install .

# Indicate we are building the docs when reading cmp source code
export READTHEDOCS="True"

# Clean a potential existing build and build the HTML documentation
cd "$BASEDIR/docs"
echo "INFO: Building documentation in $(pwd)/_build/html"
make clean
make html

# Remove $READTHEDOCS
unset READTHEDOCS
