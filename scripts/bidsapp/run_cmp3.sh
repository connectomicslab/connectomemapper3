#!/bin/bash
echo User: $(id -un $USER) && echo Group: $(id -gn $USER) &&
. "$FSLDIR/etc/fslconf/fsl.sh" &&
export && \
echo "SHELL: $SHELL" && \
echo "PATH: $PATH" && \
. activate "${CONDA_ENV}" &&
xvfb-run -s "-screen 0 900x900x24 -ac +extension GLX -noreset" -a python /app/connectomemapper3/run.py "$@"
