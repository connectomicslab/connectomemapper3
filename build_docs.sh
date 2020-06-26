#!/usr/bin/bash

if [[ "$OSTYPE" == "linux-gnu" ]]; then
        # Linux
        DIR="$(dirname $(readlink -f "$0"))"
elif [[ "$OSTYPE" == "darwin"* ]]; then
        # Mac OSX
        DIR="$(dirname "$0")"
fi

echo "Building documentation in $DIR/docs/_build/html"

OLDPWD="$PWD"

cd "$DIR/docs"
make clean
make html

cd "$OLDPWD"