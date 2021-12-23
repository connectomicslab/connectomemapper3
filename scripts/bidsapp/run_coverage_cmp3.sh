#!/bin/bash
echo User: $(id -un $USER) && echo Group: $(id -gn $USER) &&
. "$FSLDIR/etc/fslconf/fsl.sh" &&
export && \
echo "SHELL: $SHELL" && \
echo "PATH: $PATH" && \
. activate "${CONDA_ENV}" &&
xvfb-run -s "-screen 0 900x900x24 -ac +extension GLX -noreset" \
-a coverage run --source=cmp,cmtklib --omit=*/bidsappmanager/*,*/cli/*,*/viz/*,*/process* \
/app/connectomemapper3/run.py "$@" \
|& tee /bids_dir/code/log.txt &&
coverage html -d /bids_dir/code/coverage_html &&
coverage xml -o /bids_dir/code/coverage.xml &&
coverage json -o /bids_dir/code/coverage.json
