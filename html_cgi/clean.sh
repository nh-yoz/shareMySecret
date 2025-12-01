#!/bin/bash
# Delete files where expires time (epoch) is less than now

FOLDER="$(dirname ${0})"
CONFIG_FILE="${FOLDER}/config.py"
[ ! -f "${CONFIG_FILE}" ] && echo "ERROR: File 'config.py' not found!" && exit 1

SECRET_PATH="$(grep 'secret_files_path' "${CONFIG_FILE}" | sed "s/^.*['\"]\(.*\)['\"].*\$/\1/")"
[ ! -d "${SECRET_PATH}" ] && echo "ERROR: Folder '${SECRET_PATH}' not found!" && exit 1

NOW=$(date +%s)
for f in ${SECRET_PATH}/*; do
   EXPIRES=$(head -3 "${f}" | grep -Eo 'expires: [0-9]+' | cut -d ' ' -f 2 | cut -d '.' -f 1)
   [ -z ${EXPIRES} ] && echo "No expiration time found for file '${f}'"
   [[ $EXPIRES =~ ^[0-9]+$ ]] && [ $EXPIRES -lt $NOW ] && rm -f "${f}" && echo "Deleted file '${f}'"
done
