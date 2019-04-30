#!/usr/bin/sh

DIR="$(dirname $(readlink -f "$0"))"
echo "Building documentation in $DIR/docs/_build/html"

OLDPWD=$PWD

cd $DIR/docs
make clean
make html

cd $OLDPWD