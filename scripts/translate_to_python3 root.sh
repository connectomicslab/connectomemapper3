#!/bin/sh

# Get the directory where the script is stored,
# which is supposed to be in the code folder of the dataset root directory)
# and get absolute path
SCRIPT_DIR="$(dirname "$0")"
SCRIPT_DIR="$(readlink -f "${SCRIPT_DIR}")"

MAIN_DIR="$(dirname "${SCRIPT_DIR}")"

echo "Main dir: ${MAIN_DIR}

PY3_DIR="${MAIN_DIR}/python3"

mkdir -p "${PY3_DIR}"

LOG_FILE="${PY3_DIR}/translation-log-root.txt"

echo "Log file: ${LOG_FILE}"


NAME="setup.py"
IN_DIR="${MAIN_DIR}/${NAME}"
OUT_DIR="${PY3_DIR}"
echo "Process folder $NAME (in: ${IN_DIR} / out: ${OUT_DIR})"
2to3 -f all  -p -W --output-dir="${OUT_DIR}" -W -n "${IN_DIR}" >> "${LOG_FILE}"

autopep8 -v --in-place "${PY3_DIR}/${NAME}"

NAME="setup_gui.py"
IN_DIR="${MAIN_DIR}/${NAME}"
OUT_DIR="${PY3_DIR}"
echo "Process folder $NAME (in: ${IN_DIR} / out: ${OUT_DIR})"
2to3 -f all  -p -W --output-dir="${OUT_DIR}" -W -n "${IN_DIR}" >> "${LOG_FILE}"

autopep8 -v --in-place "${PY3_DIR}/${NAME}"


NAME="run.py"
IN_DIR="${MAIN_DIR}/${NAME}"
OUT_DIR="${PY3_DIR}"
echo "Process folder $NAME (in: ${IN_DIR} / out: ${OUT_DIR})"
2to3 -f all  -p -W --output-dir="${OUT_DIR}" -W -n "${IN_DIR}" >> "${LOG_FILE}"

autopep8 -v --in-place "${PY3_DIR}/${NAME}"
