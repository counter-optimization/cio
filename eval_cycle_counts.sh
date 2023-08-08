#!/bin/bash

IMPL_TESTING_DIR=./implementation-testing
NUM_MEASUREMENTS=500000
LLVM_HOME=~/llvm-project/build
CLANG="$LLVM_HOME/bin/clang"

if [[ ! -d "$IMPL_TESTING_DIR" ]]; then
    echo "Can't find ./implementation-testing normally in pandora-eval dir"
    exit 1
fi

if [[ ! -d "$LLVM_HOME" ]]; then
    echo "Can't find LLVM_HOME (at LLVM_HOME=$LLVM_HOME)"
    exit 1
fi

if [[ ! -x "$CLANG" ]]; then
    echo "Can't find clang (at CLANG=$CLANG)"
    exit 1
fi

cd "$IMPL_TESTING_DIR"

MEASURE_CYCLE_ARG=1 NUM_FUZZ_RUNS=500000 NUM_FUZZ_JOBS=1 LLVM_HOME=$LLVM_HOME CC=$CLANG ./build_and_run_tests.sh --record-cycle-counts

# amortization-count set in setupTest function in CS,SS transform files in LLVM
python3 get_cycle_count_data.py --overhead-out-csv-file=transform-cycle-counts-overhead.csv --use-n-measurements=100000 --amortization-count=2000 fuzz_harnesses > cycle_counts.txt 

cp ./cycle_counts.txt ../
cp transform-cycle-counts-overhead.csv ../
cd ../

echo "Cycle count results are in: cycle_counts.txt"

