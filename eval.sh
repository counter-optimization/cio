#!/bin/bash

EVAL_START_TIME=$(TZ='America/Los_Angeles' date +%F-%H:%M:%S-%Z)
TOP_EVAL_DIR=$EVAL_START_TIME-eval

# defaults, set by user
CC=`realpath ~/llvm-project/build/bin/clang`
CHECKER_DIR=`realpath ./checker`
LIBSODIUM_DIR=`realpath ./libsodium`
NUM_MAKE_JOB_SLOTS=8

EXTRA_MAKEFILE_FLAGS=""

BASELINE_DIR="baseline"
CS_DIR="cs"
SS_DIR="ss"
SS_CS_DIR="ss-cs"
CS_SS_DIR="cs-ss"

function usage
{
    echo "Usage: ./eval.sh [ -h | --help (displays this message) ]
			   [ -c | --cc <path to c compiler> ]
			   [ -p | --checker-dir <path to root checker dir> ]
			   [ -t | --crypto-dir <path to the crypto lib project that has the root makefile> ]
			   [ -m | --makefile-flags \"<~double quoted string~ of extra flags for the Makefile>\" ]
			   [ -j <num make job slots> ]"
    exit 2
}

PARSED_ARGS=$(getopt -o "hc:p:t:m:j:" -l "help,cc:,checker-dir:,crypto-dir:,makefile-flags:" -n eval.sh -- "$@")

if [[ $? -ne 0 ]]; then
       echo "Error parsing args"
       usage
fi

eval set -- "$PARSED_ARGS"
unset PARSED_ARGS

while true; do
    case "$1" in
	'-h' | '--help')
	    usage
	    ;;
	'-j')
	    NUM_MAKE_JOB_SLOTS=$2
	    shift 2
	    continue
	    ;;
	'-c' | '--cc')
	    echo CC opt
	    CC=$2
	    shift 2
	    continue
	    ;;
	'-p' | '--checker-dir')
	    CHECKER_DIR=$2
	    shift 2
	    continue
	    ;;
	'-m' | '--makefile-flags')
	    EXTRA_MAKEFILE_FLAGS=$2
	    shift 2
	    continue
	    ;;
	'-t' | '--crypto-dir')
	    TARGET_DIR=$2
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

mkdir $TOP_EVAL_DIR

# baseline
make MITIGATIONS="" EVAL_DIR="$TOP_EVAL_DIR/$BASELINE_DIR" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running baseline"
       exit -1
fi

# cs only
make MITIGATIONS="--cs" EVAL_DIR="$TOP_EVAL_DIR/$CS_DIR" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running cs mitigations"
       exit -1
fi

# ss only
make MITIGATIONS="--ss" EVAL_DIR="$TOP_EVAL_DIR/$SS_DIR" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running ss mitigations"
       exit -1
fi

# cs then ss
make MITIGATIONS="--cs --ss" EVAL_DIR="$TOP_EVAL_DIR/$CS_SS_DIR" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running cs-ss mitigations"
       exit -1
fi

# ss then cs
# make MITIGATIONS="--ss --cs" EVAL_DIR="$TOP_EVAL_DIR/$SS_CS_DIR" \
#     CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
#     NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
#     run_eval

# if [[ $? -ne 0 ]]; then
#        echo "Error running ss-cs mitigations"
#        exit -1
# fi

# generate plots
python3 process_eval_data.py $EVAL_DIR $BASELINE_DIR \
    $CS_DIR $SS_DIR $CS_SS_DIR
