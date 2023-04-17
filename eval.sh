#!/bin/bash

EVAL_START_TIME=$(TZ='America/Los_Angeles' date +%F-%H:%M:%S-%Z)
TOP_EVAL_DIR=$EVAL_START_TIME-eval

# defaults, set by user
CC=`realpath ~/llvm-project/build/bin/clang`
CHECKER_DIR=`realpath ./checker`
LIBSODIUM_DIR=`realpath ./libsodium`
LIBSODIUM_AR=$LIBSODIUM_DIR/src/libsodium/.libs/libsodium.a
LIBSODIUM_BASELINE_DIR="libsodium.built."
NUM_MAKE_JOB_SLOTS=8

EXTRA_MAKEFILE_FLAGS=""

BASELINE_DIR="baseline"
CS_DIR="cs"
SS_DIR="ss"
SS_CS_DIR="ss-cs"
CS_SS_DIR="cs-ss"

EVAL_MSG_LEN=100
EVAL_MSG=$(timeout 0.01s cat /dev/urandom | tr -dc '[:alnum:]' | fold -w $EVAL_MSG_LEN | head -n 1)

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
echo "$EVAL_MSG" > $TOP_EVAL_DIR/msg.txt

# baseline
make clean
if [ ! -d "$LIBSODIUM_BASELINE_DIR" ]; then
	mkdir $LIBSODIUM_BASELINE_DIR
	make --directory=$LIBSODIUM_DIR
	cp $LIBSODIUM_AR libsodium.built./libsodium.a
fi
taskset -c 0 make MITIGATIONS="" EVAL_DIR="$TOP_EVAL_DIR/$BASELINE_DIR" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
	EVAL_MSG=$EVAL_MSG \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running baseline"
       exit -1
fi

# cs only
# make clean
# make MITIGATIONS="--cs" EVAL_DIR="$TOP_EVAL_DIR/$CS_DIR" \
#     CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
#     NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
#     EVAL_MSG=$EVAL_MSG \
#     run_eval

# if [[ $? -ne 0 ]]; then
#        echo "Error running cs mitigations"
#        exit -1
# fi

# ss only
make clean
taskset -c 0 make MITIGATIONS="--ss" EVAL_DIR="$TOP_EVAL_DIR/$SS_DIR" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
	EVAL_MSG=$EVAL_MSG \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running ss mitigations"
       exit -1
fi

# cs then ss
# make clean
# make MITIGATIONS="--cs --ss" EVAL_DIR="$TOP_EVAL_DIR/$CS_SS_DIR" \
#     CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
#     NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
#     EVAL_MSG=$EVAL_MSG \
#     run_eval

# if [[ $? -ne 0 ]]; then
#        echo "Error running cs-ss mitigations"
#        exit -1
# fi

# ss then cs
# make clean
# make MITIGATIONS="--ss --cs" EVAL_DIR="$TOP_EVAL_DIR/$SS_CS_DIR" \
#     CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
#     NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
#     EVAL_MSG=$EVAL_MSG \
#     run_eval

# if [[ $? -ne 0 ]]; then
#        echo "Error running ss-cs mitigations"
#        exit -1
# fi

# generate plots
python3 process_eval_data.py $TOP_EVAL_DIR $BASELINE_DIR \
    $SS_DIR # $CS_DIR $CS_SS_DIR
