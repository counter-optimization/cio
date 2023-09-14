#!/bin/bash

VERIFICATION_RESULTS_DIR="verification-results"
CHECKER_DIR="../checker"
MISSING_TRANSFORMS_FILE="missing_tranforms.txt"
FAILED_TRANSFORMS_FILE="failed_tranforms.txt"
TRANSFORMS_FILE="all_insns.txt"
VERBOSE="-v"

function usage
{
    echo "Usage: ./verify_transforms.sh [ -h | --help (displays this message) ]
			   [ -f | --file <path to file with list of transforms to verify> ]
			   [ -p | --checker-dir <path to root checker dir> ]
			   [ -n | --not-verbose ]"
    exit 2
}

PARSED_ARGS=$(getopt -o "nhf:p:" -l "help,file:,checker-dir:,not-verbose" -n verify_transforms.sh -- "$@")

if [[ $? -ne 0 ]]; then
       echo "Error parsing args"
       usage
fi

eval set -- "$PARSED_ARGS"
unset PARSED_ARGS

echo $TRANSFORMS_FILE

while true; do
    echo "Hi"
    echo "$1"
    case "$1" in
	'-h' | '--help')
	    usage
	    ;;
	'-f' | '--file')
	    TRANSFORMS_FILE=$2
        echo "-f"
        echo $TRANSFORMS_FILE
	    shift 2
	    continue
	    ;;
	'-p' | '--checker-dir')
	    CHECKER_DIR=$2
	    shift 2
	    continue
	    ;;
	'-n' | '--not-verbose')
	    VERBOSE=""
	    shift 2
	    continue
	    ;;
	'--')
	    shift
	    break
	    ;;
	*)
	    echo "Unknown option $1"
	    usage
	    ;;
    esac
    shift
done

if [ ! -d "$VERIFICATION_RESULTS_DIR" ]; then
    mkdir $VERIFICATION_RESULTS_DIR
fi

for insn in $(cat $TRANSFORMS_FILE); do
    echo "Running verifier on $insn"
    racket $CHECKER_DIR/synth/verify.rkt -v $insn &> $VERIFICATION_RESULTS_DIR/$insn.txt
done

grep -r -l "N/A" verification-results | awk -F '[/.]' '{print$2}' > $MISSING_TRANSFORMS_FILE
grep -r -l "\"sat\"" verification-results | awk -F '[/.]' '{print$2}' > $FAILED_TRANSFORMS_FILE

echo ""
echo "Finished verification"
echo "See $MISSING_TRANSFORMS_FILE for list of instructions with no transforms found"
echo "See $FAILED_TRANSFORMS_FILE for list of instructions with at least one transform that failed verification"
