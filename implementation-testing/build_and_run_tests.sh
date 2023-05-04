#!/bin/bash

# Check if important ENV variables are set or not

if [[ ! -d "$LLVM_HOME" ]]; then
    echo "set env var LLVM_HOME to clang/llvm-project build dir"
    exit 1
fi

if [[ ! -e "$CC" ]]; then
    echo "set env var CC to our clang or system clang"
    exit 
fi

# Generate the obj file containing all implementations (orig insns + transforms)
# and each fuzzer file

FUZZ_HARNESSES_DIR=./fuzz_harnesses
TEST_O=./test.o

test "-d $FUZZ_HARNESSES_DIR" && rm -r "$FUZZ_HARNESSES_DIR"
mkdir "$FUZZ_HARNESSES_DIR"

python3 llvm-test-compsimp-transforms.py "$FUZZ_HARNESSES_DIR"

GENERATION_RET_STATUS=$?

if [[ ! -e "$TEST_O" || "$GENERATION_RET_STATUS" -ne 0 ]]; then
    echo "error running llvm-test-compsimp-transforms.py exiting."
    exit 2
fi

HARNESS_C_FILES=$(ls $FUZZ_HARNESSES_DIR/*.c)
declare -a FUZZERS

for harness_file in $HARNESS_C_FILES; do
    obj_file=${harness_file/%.c/.o}
    final_file=${harness_file/%.c/}
    echo "Building $final_file..."
    
    clang -g -O0 -Wall -fsanitize=fuzzer-no-link -c $harness_file -o $obj_file

    COMPILE_STATUS=$?

    if [[ "$COMPILE_STATUS" -ne 0 ]]; then
	echo "error compiling harness file $harness_file with exit status: $COMPILE_STATUS"
	exit "$COMPILE_STATUS"
    fi
    
    clang -g -O0 -Wall -fsanitize=fuzzer $TEST_O $obj_file -o $final_file

    LINK_STATUS=$?

    if [[ "$LINK_STATUS" -ne 0 ]]; then
	echo "error linking harness file $obj_file with exit status: $LINK_STATUS"
	exit "$LINK_STATUS"
    fi

    FUZZERS=("${FUZZERS[@]}" "$final_file")
done

echo "fuzzers are: ${FUZZERS[@]}"

# Run all fuzzers in a thread (process) pool using xargs

# ALL_FUZZERS=$(find $FUZZ_HARNESSES_DIR \(-not -iname '*.c'\) \(-not -iname '*.o'\))

if [[ ! -v NUM_FUZZ_JOBS ]]; then
    NUM_FUZZ_JOBS=1
fi

if [[ ! -v NUM_FUZZ_RUNS ]]; then
    NUM_FUZZ_RUNS=100000 # 100,000
fi

if [[ ! -v MAX_SEED_LEN ]]; then
    MAX_SEED_LEN=650
fi

if [[ $NUM_FUZZ_JOBS -eq 1 ]]; then
    # do in serial
    for fuzzer in "${FUZZERS[@]}"; do
	echo "running fuzzer $fuzzer"
	$fuzzer -close_fd_mask=0 -runs=$NUM_FUZZ_RUNS -max_len=$MAX_SEED_LEN -len_control=0 -timeout=10 &> $fuzzer.log

	if [[ $? -ne 0 ]]; then
	    echo "fuzzer $fuzzer returned non-zero exit status, see $fuzzer.log"
	fi
    done
else
    # do in parallel
    echo "${FUZZERS[@]}" | xargs -I {} --max-procs=$NUM_FUZZ_JOBS bash -c "echo running fuzzer {} && ({} -close_fd_mask=0 -runs=$NUM_FUZZ_RUNS -max_len=$MAX_SEED_LEN -len_control=0 -timeout=10 &> {}.log || echo fuzzer {} returned non-zero exit status, see {}.log)"
fi

echo "Done running fuzzers"

# Did any errors happen?

MISMATCHES=$(find $FUZZ_HARNESSES_DIR -iname '*.log' -exec grep -Eil 'mismatch' {} \;)

for logfile in $MISMATCHES; do
    echo "Mismatch in original,transformed output states in logfile: $logfile"
done

echo "cleaning up ./crash-* files. check $FUZZ_HARNESSES_DIR/*.log files for more detailed info"
rm crash-*
