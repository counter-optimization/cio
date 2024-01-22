#!/bin/bash

# set -x
set -o pipefail
set -o nounset

function usage
{
    echo "Usage: ./get_bap_numbers.sh </path/to/cio/run/dir>"
    exit 2
}

if [[ $# -ne 1 ]];
then
    usage
fi

CIO_DIR=$1
RUN_TIMES="$CIO_DIR/cio-run-times.csv"
CHECKING_LOG="$CIO_DIR/bap.log"

if [[ ! -r "$RUN_TIMES" ]];
then
    echo "Couldn't read file cio-run-times.csv in $CIO_DIR"
    exit 1
fi

if [[ ! -r "$CHECKING_LOG" ]];
then
    echo "Couldn't read file bap.log in $CIO_DIR"
    exit 1
fi
readarray <<<$(cut -f 2 -d',' "$RUN_TIMES" | tail -n 5)
START_TIMES=(${MAPFILE[@]})
readarray <<<$(cut -f 3 -d',' "$RUN_TIMES" | tail -n 5)
END_TIMES=(${MAPFILE[@]})

if [[ "${#START_TIMES[@]}" -ne "${#END_TIMES[@]}" || ${#START_TIMES[@]} -ne 5 ]];
then
    echo "Malformed file $RUN_TIMES, did everything run?"
    exit 1
fi

COMPILATION_TIME=$(("${END_TIMES[0]}" - "${START_TIMES[0]}"))
CHECKING_TIME=$(("${END_TIMES[1]}" - "${START_TIMES[1]}"))
MITIGATION_TIME=$(("${END_TIMES[2]}" - "${START_TIMES[2]}"))
DOUBLECHECKING_TIME=$(("${END_TIMES[3]}" - "${START_TIMES[3]}"))
TOTAL_TIME=$(("${END_TIMES[4]}" - "${START_TIMES[4]}"))

echo "------------------------------------------"
echo -e "Total cio runtime: $TOTAL_TIME"
echo -e "\tCompilation: $COMPILATION_TIME"
echo -e "\tChecking: $CHECKING_TIME"
echo -e "\tMitigation: $MITIGATION_TIME"
echo -e "\tDouble checking: $DOUBLECHECKING_TIME"
echo "------------------------------------------"
grep -A 9 -E 'cs stats:' latest-cio-build/bap.log
echo "------------------------------------------"
grep -A 9 -E 'ss stats:' latest-cio-build/bap.log
echo "------------------------------------------"


