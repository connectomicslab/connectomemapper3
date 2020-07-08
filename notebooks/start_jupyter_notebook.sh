#!/usr/bin/sh
DIR="$( dirname "${0}" )" # Get the directory where this script is stored
jupyter-notebook --no-browser --ip=0.0.0.0 --port=8889 --NotebookApp.token='cmp' --notebook-dir="$DIR"
