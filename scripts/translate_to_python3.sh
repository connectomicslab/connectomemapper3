#!/bin/sh

# Get the directory where the script is stored,
# which is supposed to be in the code folder of the dataset root directory)
# and get absolute path
SCRIPT_DIR="$(dirname "$0")"
SCRIPT_DIR="$(readlink -f ${SCRIPT_DIR})"

MAIN_DIR="$(dirname "${SCRIPT_DIR}")"

echo "Main dir: ${MAIN_DIR}"

PY3_DIR="${MAIN_DIR}/python3"

mkdir -p ${PY3_DIR}

LOG_FILE="${PY3_DIR}/translation-log.txt"

echo "Log file: ${LOG_FILE}"


NAME=cmp
IN_DIR="${MAIN_DIR}/${NAME}"
OUT_DIR="${PY3_DIR}/${NAME}"
echo "Process folder $NAME (in: ${IN_DIR} / out: ${OUT_DIR})"
2to3 -f all  -p -W --output-dir=${OUT_DIR} -W -n ${IN_DIR} > ${LOG_FILE}
2to3 -f all  -p -W --output-dir=${OUT_DIR} -W -n ${IN_DIR} > ${LOG_FILE}

NAME=cmtklib
IN_DIR="${MAIN_DIR}/${NAME}"
OUT_DIR="${PY3_DIR}/${NAME}"
echo "Process folder $NAME (in: ${IN_DIR} / out: ${OUT_DIR})"
2to3 -f all  -p -W --output-dir=${OUT_DIR} -W -n ${IN_DIR} >> ${LOG_FILE}


NAME=tests
IN_DIR="${MAIN_DIR}/${NAME}"
OUT_DIR="${PY3_DIR}/${NAME}"
echo "Process folder $NAME (in: ${IN_DIR} / out: ${OUT_DIR})"
2to3 -f all  -p -W --output-dir=${OUT_DIR} -W -n ${IN_DIR} >> ${LOG_FILE}

NAME=scripts
IN_DIR="${MAIN_DIR}/${NAME}"
OUT_DIR="${PY3_DIR}/${NAME}"
echo "Process folder $NAME (in: ${IN_DIR} / out: ${OUT_DIR})"
2to3 -f all  -p -W --output-dir=${OUT_DIR} -W -n ${IN_DIR} >> ${LOG_FILE}