if [[ ! -e log ]]; then
    mkdir log
elif [[ ! -d log ]]; then
    rm log
    mkdir log
fi

start=2
end=18

for insn_seq_len in `seq ${start} ${end}`; do
    echo Running insn_seq_len: $insn_seq_len

    # generate the hardcoded insn sequence file
    subbed_file_name=synth/synth-comp-simp-defenses-macrod.rkt
    # cat synth/synth-comp-simp-defenses-macrod.rkt \
    #     | sed "s/REPLACE_ME/${insn_seq_len}/" > ${subbed_file_name}

    log_file=./log/${insn_seq_len}-seq-len-synthesis-post-testing-`date "+%F-%T" | sed s/:/-/g`.log
    racket ${subbed_file_name} ${insn_seq_len} &> ${log_file} &
    pids[$i]=$!
    echo Done starting insn_seq_len: $insn_seq_len
done

for pid_no in ${pids[*]}; do
    echo Waiting on pid $pid_no
    wait $pid_no
done


# start_insn_seq_len=1
# end_insn_seq_len=20
# for len in `seq ${start_insn_seq_len} ${end_insn_seq_len}`; do
#     log_file=`date -u | tr ' ' '-'`-len-${len}.log
#     echo Running synth for insn seq len: $len
#     racket synth-comp-simp-defenses.rkt $len >> ${log_file} 2>&1
#     exit_code=$?
#     echo Synth for insn seq len had exit code: $exit_code
#     echo Synth for insn seq len had exit code: $exit_code >> ${log_file}
#     echo Done running synth for insn seq len: $len
# done
