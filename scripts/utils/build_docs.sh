#!/usr/bin/bash
# Copyright (C) 2009-2021, Ecole Polytechnique Federale de Lausanne (EPFL) and
# Hospital Center and University of Lausanne (UNIL-CHUV), Switzerland, and CMP3 contributors
# All rights reserved.
#
#  This software is distributed under the open-source license Modified BSD.

# Build the documentation using BASH shell interpreter and Sphinx doc generator.
#
# All python packages related to Sphinx necessary to build the docs
# are provided in the `py37cmp-gui` conda environment described by
# `environment.yml` / `environment_macosx.yml` files.
#
# Usage conda activate py37cmp-gui
#       /bin/bash build_docs.sh
#
# Created by Sebastien Tourbier
# Source: https://github.com/connectomicslab/connectomemapper3/blob/master/build_docs.sh

# Get the directory where this script is located
if [[ "$OSTYPE" == "linux-gnu" ]]; then
        # Linux
        DIR="$(dirname $(readlink -f "$0"))"
elif [[ "$OSTYPE" == "darwin"* ]]; then
        # Mac OSX
        DIR="$(dirname "$0")"
fi

echo "Building documentation in $DIR/docs/_build/html"

# Store current working directory
OLDPWD="$PWD"

# Go to the documentation root directory
cd "$DIR/docs"

# Clean an existing build
make clean

# Build the HTML documentation
make html

# Get back to current working directory
cd "$OLDPWD"