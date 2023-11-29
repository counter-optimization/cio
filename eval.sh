#!/bin/bash

set -u
set -x

EVAL_START_TIME=$(TZ='America/Los_Angeles' date +%F-%H:%M:%S-%Z)
TOP_EVAL_DIR=$EVAL_START_TIME-eval
LATEST_EVAL_DIR="latest-eval-dir"

# defaults, set by user
BASELINE_CC=`realpath /usr/bin/clang`
CC=`realpath ~/llvm-project/build/bin/clang`
CHECKER_DIR=`realpath ./checker`
LIBSODIUM_DIR=`realpath ./libsodium`
LIBSODIUM_AR=$LIBSODIUM_DIR/src/libsodium/.libs/libsodium.a
LIBSODIUM_BASELINE_DIR="libsodium.built."
LIBSODIUM_ASM_DIR="libsodium.built.asm"
LIBSODIUM_REG_RES_DIR="libsodium.built.rr"
NUM_MAKE_JOB_SLOTS=8

EXTRA_MAKEFILE_FLAGS=""

BASELINE_DIR="baseline"
ASM_DIR="asm"
REG_RES_DIR="rr" # register reservation only, no mitigations
CS_DIR="cs"
SS_DIR="ss"
SS_CS_DIR="ss+cs"

CS_DIR_VADD="cs-vadd"
CS_DIR_MUL64="cs-mul64"
CS_DIR_SHIFT="cs-shift"
CS_DIR_LEA="cs-lea"
CS_DIR_64="cs-64"
CS_DIR_32="cs-32"

VALIDATE=0
VALIDATION_DIR=""

EVAL_MSG_LEN=100
EVAL_MSG=$(timeout 0.01s cat /dev/urandom | tr -dc '[:alnum:]' | fold -w $EVAL_MSG_LEN | head -n 1)

DYNAMIC_HIT_COUNTS=0

function usage
{
    echo "Usage: ./eval.sh [ -h | --help (displays this message) ]
			   [ -b | --baseline-cc <path to baseline c compiler> ]
			   [ -c | --cc <path to c compiler> ]
			   [ -p | --checker-dir <path to root checker dir> ]
			   [ -t | --crypto-dir <path to the crypto lib project that has the root makefile> ]
			   [ -v | --validate <path to a prior eval directory against which to validate results> ]
			   [ -m | --makefile-flags \"<~double quoted string~ of extra flags for the Makefile>\" ]
			   [ -d | --dynamic-hit-counts (record dynamic hit counts) ]
			   [ -j <num make job slots> ]"
    exit 2
}

PARSED_ARGS=$(getopt -o "dhb:c:p:t:v:m:j:" -l "help,baseline-cc:,cc:,checker-dir:,dynamic-hit-counts,crypto-dir:,validate:,makefile-flags:" -n eval.sh -- "$@")

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
	'-b' | '--baseline-cc')
	    echo BASELINE_CC opt
	    BASELINE_CC=$2
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
	'-v' | '--validate')
		VALIDATE=1
	    VALIDATION_DIR=$2
	    shift 2
	    continue
	    ;;
	'-d' | '--dynamic-hit-counts')
	    DYNAMIC_HIT_COUNTS=1
	    shift
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
test -L "$LATEST_EVAL_DIR" && rm "$LATEST_EVAL_DIR"
ln -s "$TOP_EVAL_DIR" "$LATEST_EVAL_DIR"

make libsodium_init
make checker_init

# baseline
echo "Running baseline microbenchmarks..."
make clean

if [[ $DYNAMIC_HIT_COUNTS -eq 1 ]]; then
    EXTRA_CIO_FLAGS="--dynamic-hit-counts"
else
    EXTRA_CIO_FLAGS=""
fi

if [ ! -d "$LIBSODIUM_BASELINE_DIR" ]; then
	cd $LIBSODIUM_DIR
	./configure --disable-asm CC=$BASELINE_CC
	make -j "$NUM_MAKE_JOB_SLOTS" CC=$BASELINE_CC

	if [[ $? -ne 0 ]]; then
		echo "Error building baseline libsodium. Exiting"
		exit -1
	fi
	
	make check CC=$BASELINE_CC -j "$NUM_MAKE_JOB_SLOTS"
	cd ..
	mkdir $LIBSODIUM_BASELINE_DIR
	cp $LIBSODIUM_AR $LIBSODIUM_BASELINE_DIR/libsodium.a
fi

taskset -c 0 make MITIGATIONS="" EVAL_DIR="$TOP_EVAL_DIR/$BASELINE_DIR" \
    CC=$BASELINE_CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    EVAL_MSG=$EVAL_MSG EXTRA_EVAL_CFLAGS="-DBASELINE_COMPILE" EXTRA_CIO_FLAGS="$EXTRA_CIO_FLAGS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running baseline"
       exit -1
fi

# with inline asm
echo "Running microbenchmarks with inline asm enabled..."
make clean

if [ ! -d "$LIBSODIUM_ASM_DIR" ]; then
	cd $LIBSODIUM_DIR
	./configure CC=$BASELINE_CC
	make -j "$NUM_MAKE_JOB_SLOTS" CC=$BASELINE_CC
	make check CC=$BASELINE_CC -j "$NUM_MAKE_JOB_SLOTS"
	cd ..
	mkdir $LIBSODIUM_ASM_DIR
	cp $LIBSODIUM_AR $LIBSODIUM_ASM_DIR/libsodium.a
fi

taskset -c 0 make MITIGATIONS="$ASM_DIR" EVAL_DIR="$TOP_EVAL_DIR/$ASM_DIR" \
    CC=$BASELINE_CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=8 EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
	EVAL_MSG=$EVAL_MSG  \
    run_eval

# with register reservation only
echo "Running microbenchmarks with register reservation.."
make clean

if [ ! -d "$LIBSODIUM_REG_RES_DIR" ]; then
	cd $LIBSODIUM_DIR
	./configure --disable-asm CC=$CC
	make -j "$NUM_MAKE_JOB_SLOTS" CC=$CC
	
	if [[ $? -ne 0 ]]; then
		echo "Error building libsodium with register reservation. Exiting"
		exit -1
	fi

	make check CC=$CC -j "$NUM_MAKE_JOB_SLOTS"
	cd ..
	mkdir $LIBSODIUM_REG_RES_DIR
	cp $LIBSODIUM_AR $LIBSODIUM_REG_RES_DIR/libsodium.a
fi

taskset -c 0 make -j 32 MITIGATIONS="$REG_RES_DIR" EVAL_DIR="$TOP_EVAL_DIR/$REG_RES_DIR" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
	EVAL_MSG=$EVAL_MSG CFLAGS="-O0 -Werror -std=c18 -DNO_DYN_HIT_COUNTS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running with register reservation only"
       exit -1
fi

# ss only
echo "Running microbenchmarks with silent store mitigations.."
make clean
taskset -c 0 make -j 32 MITIGATIONS="--ss" EVAL_DIR="$TOP_EVAL_DIR/$SS_DIR" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
	EVAL_MSG=$EVAL_MSG EXTRA_CIO_FLAGS="$EXTRA_CIO_FLAGS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running ss mitigations"
       exit -1
fi

# cs only
echo "Running microbenchmarks with comp simp mitigations.."
make clean
taskset -c 0 make -j 32 MITIGATIONS="--cs" EVAL_DIR="$TOP_EVAL_DIR/$CS_DIR" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    EVAL_MSG=$EVAL_MSG EXTRA_CIO_FLAGS="$EXTRA_CIO_FLAGS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running cs mitigations"
       exit -1
fi

echo "Running microbenchmarks with limited comp simp mitigations: 64-bit multiply.."
make clean
taskset -c 0 make -j 32 MITIGATIONS="--cs" MITIGATIONS_STR="cs_mul64" \
    EVAL_DIR="$TOP_EVAL_DIR/$CS_DIR_MUL64" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    EVAL_MSG=$EVAL_MSG \
	EXTRA_CIO_FLAGS="--cflags \"-mllvm --x86-cs-enable-multiply-64\" $EXTRA_CIO_FLAGS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running cs 64-bit multiply mitigations"
       exit -1
fi

echo "Running microbenchmarks with limited comp simp mitigations: shift.."
make clean
taskset -c 0 make -j 32 MITIGATIONS="--cs" MITIGATIONS_STR="cs_shift" \
    EVAL_DIR="$TOP_EVAL_DIR/$CS_DIR_SHIFT" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    EVAL_MSG=$EVAL_MSG \
	EXTRA_CIO_FLAGS="--cflags \"-mllvm --x86-cs-enable-shift\" $EXTRA_CIO_FLAGS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running cs shift mitigations"
       exit -1
fi

echo "Running microbenchmarks with limited comp simp mitigations: vadd.."
make clean
taskset -c 0 make -j 32 MITIGATIONS="--cs" MITIGATIONS_STR="cs_vadd" \
    EVAL_DIR="$TOP_EVAL_DIR/$CS_DIR_VADD" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    EVAL_MSG=$EVAL_MSG \
	EXTRA_CIO_FLAGS="--cflags \"-mllvm --x86-cs-enable-vadd\" $EXTRA_CIO_FLAGS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running cs vadd mitigations"
       exit -1
fi

echo "Running microbenchmarks with limited comp simp mitigations: lea.."
make clean
taskset -c 0 make -j 32 MITIGATIONS="--cs" MITIGATIONS_STR="cs_lea" \
    EVAL_DIR="$TOP_EVAL_DIR/$CS_DIR_LEA" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    EVAL_MSG=$EVAL_MSG \
	EXTRA_CIO_FLAGS="--cflags \"-mllvm --x86-cs-enable-lea\" $EXTRA_CIO_FLAGS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running cs lea mitigations"
       exit -1
fi

echo "Running microbenchmarks with limited comp simp mitigations: misc 64-bit.."
make clean
taskset -c 0 make -j 32 MITIGATIONS="--cs" MITIGATIONS_STR="cs_64" \
    EVAL_DIR="$TOP_EVAL_DIR/$CS_DIR_64" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    EVAL_MSG=$EVAL_MSG \
	EXTRA_CIO_FLAGS="--cflags \"-mllvm --x86-cs-enable-64\" $EXTRA_CIO_FLAGS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running cs 64-bit mitigations"
       exit -1
fi

echo "Running microbenchmarks with limited comp simp mitigations: misc <=32-bit.."
make clean
taskset -c 0 make -j 32 MITIGATIONS="--cs" MITIGATIONS_STR="cs_32" \
    EVAL_DIR="$TOP_EVAL_DIR/$CS_DIR_32" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    EVAL_MSG=$EVAL_MSG \
	EXTRA_CIO_FLAGS="--cflags \"-mllvm --x86-cs-enable-32\" $EXTRA_CIO_FLAGS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running cs <=32-bit mitigations"
       exit -1
fi

# ss and cs
echo "Running microbenchmarks with silent store and comp simp mitigations.."
make clean
taskset -c 0 make -j 32 MITIGATIONS="--ss --cs" EVAL_DIR="$TOP_EVAL_DIR/$SS_CS_DIR" \
    CC=$CC CHECKER_DIR=$CHECKER_DIR LIBSODIUM_DIR=$LIBSODIUM_DIR \
    NUM_MAKE_JOB_SLOTS=$NUM_MAKE_JOB_SLOTS EXTRA_MAKEFILE_FLAGS=$EXTRA_MAKEFILE_FLAGS \
    EVAL_MSG=$EVAL_MSG EXTRA_CIO_FLAGS="$EXTRA_CIO_FLAGS" \
    run_eval

if [[ $? -ne 0 ]]; then
       echo "Error running ss+cs mitigations"
       exit -1
fi

# generate plots
if [[ "$VALIDATE" -eq 1 ]]; then
	echo ""
	echo "Validating baseline..."
	python3 process_eval_data.py $TOP_EVAL_DIR $BASELINE_DIR "../$VALIDATION_DIR/$BASELINE_DIR"
	mv $TOP_EVAL_DIR/calculated_data.txt $TOP_EVAL_DIR/baseline_validation_data.txt

	echo ""
	echo "Validating register reservation only..."
	python3 process_eval_data.py $TOP_EVAL_DIR $REG_RES_DIR "../$VALIDATION_DIR/$REG_RES_DIR"
	mv $TOP_EVAL_DIR/calculated_data.txt $TOP_EVAL_DIR/rr_validation_data.txt

	echo ""
	echo "Validating SS..."
	python3 process_eval_data.py $TOP_EVAL_DIR $SS_DIR "../$VALIDATION_DIR/ss"
	mv $TOP_EVAL_DIR/calculated_data.txt $TOP_EVAL_DIR/ss_validation_data.txt

	echo ""
	echo "Validating CS..."
	python3 process_eval_data.py $TOP_EVAL_DIR $CS_DIR "../$VALIDATION_DIR/cs"
	mv $TOP_EVAL_DIR/calculated_data.txt $TOP_EVAL_DIR/cs_validation_data.txt

	echo ""
	echo "Validating SS+CS..."
	python3 process_eval_data.py $TOP_EVAL_DIR $SS_CS_DIR "../$VALIDATION_DIR/ss+cs"
	mv $TOP_EVAL_DIR/calculated_data.txt $TOP_EVAL_DIR/ss+cs_validation_data.txt
fi

echo ""
echo "Overheads vs baseline:"
python3 process_eval_data.py $TOP_EVAL_DIR $BASELINE_DIR \
    $SS_DIR $CS_DIR \
	$CS_DIR_MUL64 $CS_DIR_SHIFT $CS_DIR_VADD $CS_DIR_LEA $CS_DIR_64 $CS_DIR_32 \
    $SS_CS_DIR $REG_RES_DIR
