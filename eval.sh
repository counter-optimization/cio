#!/bin/bash

EVAL_START_TIME=$(TZ='America/Los_Angeles' date +%F-%H:%M:%S-%Z)
TOP_EVAL_DIR=$EVAL_START_TIME-eval

CS_DIR="cs"
SS_DIR="ss"
SS_CS_DIR="ss-cs"
CS_SS_DIR="cs-ss"

mkdir $TOP_EVAL_DIR

# cs only
make MITIGATIONS="--cs" EVAL_DIR="$TOP_EVAL_DIR/$CS_DIR" run_eval

# ss only
make MITIGATIONS="--ss" EVAL_DIR="$TOP_EVAL_DIR/$SS_DIR" run_eval

# cs then ss
make MITIGATIONS="--cs --ss" EVAL_DIR="$TOP_EVAL_DIR/$CS_SS_DIR" run_eval

# ss then cs
make MITIGATIONS="--ss --cs" EVAL_DIR="$TOP_EVAL_DIR/$SS_CS_DIR" run_eval
