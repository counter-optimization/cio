#!/bin/bash

set -u
set -e

OUT_CSV=./transformed.checker.output.csv

LLVM_HOME=~/llvm-project/build/ python3 ./llvm-test-compsimp-transforms.py ./fuzz_harnesses --verifiable-tests

bash ./write_transformed_config_file.sh ./test.o ./transformed.uarch_checker.config

bap --plugin-path=../checker/bap/interval/ --pass=uarch-checker --uarch-checker-double-check --uarch-checker-output-csv-file="$OUT_CSV" --uarch-checker-config-file=./transformed.uarch_checker.config --uarch-checker-ss --uarch-checker-cs --uarch-checker-symex-profiling-output-file=./symex-profiling-data.csv --no-optimization --bil-optimization=0 ./test.o 

echo "done. results in $OUT_CSV. transformed sequences can be objdumped from ./test.o by subname"
