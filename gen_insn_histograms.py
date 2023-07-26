import os

def gen_reference_histograms():
    ref_binary_filepath = os.path.join(
        '.',
        'implementation-testing',
        'fuzz_harnesses',
        'cs-ADD32rr-implementation-tester'
    )

    if not os.path.exists(ref_binary_filepath):
        print("Couldn't find reference binary file. Attempting to generate...")
        os.system('cd implementation-testing && ./build_and_run_tests')
        if not os.path.exists(ref_binary_filepath):
            print(f"Attempt to generate reference binary file failed. "
                   "Please run ./build_and_run_tests from the implementation-testing directory.")
            exit(-1)
    
    # dump disassembled binary into a temp file
    ref_dump_filepath = '__gen_insn_histograms_temp'
    os.system(f'objdump -d --no-addresses --no-show-raw-insn -M suffix {ref_binary_filepath} > {ref_dump_filepath}')
        
    file = open(ref_dump_filepath)
    ref_binary = file.read()
    file.close()

    os.system(f'rm {ref_dump_filepath}')

    # extract instruction histograms from disassembled binary
    histograms = dict()
    func_start_key = '\n<x86'
    func_end_key = '\n\tretq'
    orig_start_key = '_original>:'
    trns_start_key = '_transformed>:'

    search_idx = ref_binary.find(func_start_key)
    while search_idx != -1:
        orig_start = ref_binary.find(orig_start_key, search_idx)
        trns_start = ref_binary.find(trns_start_key, search_idx)

        name = ref_binary[ref_binary.find('_', search_idx) + 1 : orig_start]
        print(f"Reading reference histograms for {name}")
        
        # count instructions in original and transformed functions
        orig_histo = dict()
        orig_lines = ref_binary[orig_start : ref_binary.find(func_end_key, orig_start)].split('\n\t')[1:]
        for line in orig_lines:
            insn = line.split()[0]
            if insn in orig_histo.keys():
                orig_histo[insn] += 1
            else:
                orig_histo[insn] = 1
        
        print(f"Original histogram: {orig_histo}")
        
        trns_histo = dict()
        trns_lines = ref_binary[trns_start : ref_binary.find(func_end_key, trns_start)].split('\n\t')[1:]
        for line in trns_lines:
            insn = line.split()[0]
            if insn in trns_histo.keys():
                trns_histo[insn] += 1
            else:
                trns_histo[insn] = 1
        
        print(f"Transformed histogram: {trns_histo}")
        
        # save difference between transformed and original instruction counts
        histograms[name] = dict()
        for insn in trns_histo.keys():
            if insn not in orig_histo.keys():
                histograms[name][insn] = trns_histo[insn]
            elif trns_histo[insn] - orig_histo[insn] != 0:
                histograms[name][insn] = trns_histo[insn] - orig_histo[insn]
        
        # check for instructions that appear in original but not transformed function
        # (should be at most one)
        for insn in orig_histo.keys():
            if insn not in trns_histo.keys():
                histograms[name][insn] = -1 * orig_histo[insn]
        
        print(f"Generated histogram for {name}:")
        print(histograms[name])
        print()
        
        # update search index
        search_idx = ref_binary.find(func_start_key, trns_start)
    # end while search_idx != -1
# gen_reference_histograms()

def main():
    gen_reference_histograms()


if __name__ == "__main__":
    main()


