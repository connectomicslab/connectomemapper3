#!/bin/sh
PAPERDIR=$(cd "$(dirname "$0")"; pwd)

docker run --rm \
    --volume "${PAPERDIR}":/data \
    --user $(id -u):$(id -g) \
    --env JOURNAL=joss \
    openjournals/paperdraft
