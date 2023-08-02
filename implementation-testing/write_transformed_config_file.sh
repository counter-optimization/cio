#!/bin/bash

# This script takes the fuzz test harness binary:
# ./pandora-eval/implementation-testing/test.o
# and generates a checker config file to verify
# the safety of the transformed functions.

set -e # exit if total command fails
set -u # no use of unset/uninit vars
set -f # no globbing
set -o pipefail # if pieces of a pipeline fail

TEST_OBJ_FILE=$1
OUTPUT_CONFIG_FILE=$2

if [[ ! -e "$TEST_OBJ_FILE" ]]; then
    echo "test obj file doesn't exist"
    exit 1
fi

if [[ -e "$OUTPUT_CONFIG_FILE" ]]; then
    truncate --size=0 "$OUTPUT_CONFIG_FILE"
fi

# each line of 'objdump --syms', when split on newline, has the 6th (1-indexed not 0-indexed)
# field as the symbol name.
SYM_NAMES=$(objdump --syms "$TEST_OBJ_FILE" | awk '{print $6}' | grep -E '^x86.*?transformed$')

for sym in $SYM_NAMES; do
    # just set all 6 GPR arguments to taint
    for i in {0..5}; do
	echo "$sym,$i" >> "$OUTPUT_CONFIG_FILE"
    done    
done
