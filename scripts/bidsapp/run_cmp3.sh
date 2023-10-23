#!/bin/bash
. "$FSLDIR/etc/fslconf/fsl.sh" &&
. activate "${CONDA_ENV}" &&
xvfb-run -s "-screen 0 900x900x24 -ac +extension GLX -noreset" -a python /app/run.py "$@"
