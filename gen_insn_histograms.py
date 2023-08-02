import os
import csv
import argparse

def get_binary_contents(binary_filepath : str):
    if not os.path.exists(binary_filepath):
        print(f"Couldn't find binary file {binary_filepath}")
        return

    # dump disassembled binary into a temp file
    dump_filepath = '__gen_insn_histograms_temp'
    os.system(f'objdump -d --no-addresses --no-show-raw-insn -M suffix {binary_filepath} > {dump_filepath}')
        
    file = open(dump_filepath)
    contents = file.read()
    file.close()

    os.system(f'rm {dump_filepath}')
    return contents


def get_histogram_for_function(file_contents : str, func_name : str):
    ''' Get instruction histogram for a function. The resulting histogram
        is a dict with instruction names as keys and counts of the
        corresponding instructions as values. This function makes certain
        assumptions about the format of the provided file contents, consistent
        with disassembled binaries produced by `objdump` with the flags
        `-d --no-addresses --no-show-raw-insn`. The flag `-M suffix` is also
        recommended, to disambiguate between instructions that perform the
        same operation at different bitwidths.
        '''
    print(f"Calculating instruction histogram for function {func_name}...")

    start = file_contents.find(f'{func_name}>:\n')
    if start < 0:
        print(f"ERROR: Could not find function {func_name} in file")
        return
    
    end = file_contents.find('\n\n', start)
    lines = file_contents[start : end].split('\n\t')[1:]
    histo = dict[str,int]()

    for line in lines:
        insn = line.split()[0]
        if insn in histo.keys():
            histo[insn] += 1
        else:
            histo[insn] = 1

    return histo


def diff_histograms(original : dict[str,int], transformed : dict[str,int]):
    ''' Calculate the difference histogram between an original and transformed function.
        The difference histogram represents the modifications to instruction counts present
        in the transformed function versus the original, i.e.,
        transformed histogram - original histogram. Instructions whose counts are the same
        in both (i.e., a diff of 0) are omitted.
        
        In general, we expect to see a higher count of any given instruction in the
        transformed function. Negative diffs, indicating that an instruction was removed
        from the transformed function compared to the original, should only be present
        inasmuch as those instructions were replaced by equivalent sequences. In other
        words, the number of instructions removed from the transformed function should
        be no greater than the number of instructions in the original function to which
        some transformation was applied.
    '''
    diff = dict[str,int]()
    for insn in transformed.keys():
        if insn not in original.keys():
            diff[insn] = transformed[insn]
        elif transformed[insn] - original[insn] != 0:
            diff[insn] = transformed[insn] - original[insn]

    for insn in original.keys():
        if insn not in diff.keys():
            diff[insn] = -1 * original[insn]

    return diff


def gen_reference_histograms():
    print('Generating reference histograms...')
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
    
    ref_binary = get_binary_contents(ref_binary_filepath)

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
        
        # count instructions in original and transformed functions
        orig_histo = dict()
        orig_lines = ref_binary[orig_start : ref_binary.find(func_end_key, orig_start)].split('\n\t')[1:]
        for line in orig_lines:
            insn = line.split()[0]
            if insn in orig_histo.keys():
                orig_histo[insn] += 1
            else:
                orig_histo[insn] = 1
        
        # print(f"Original histogram: {orig_histo}")
        
        trns_histo = dict()
        trns_lines = ref_binary[trns_start : ref_binary.find(func_end_key, trns_start)].split('\n\t')[1:]
        for line in trns_lines:
            insn = line.split()[0]
            if insn in trns_histo.keys():
                trns_histo[insn] += 1
            else:
                trns_histo[insn] = 1
        
        # print(f"Transformed histogram: {trns_histo}")
        
        # save difference between transformed and original instruction counts
        histograms[name] = diff_histograms(orig_histo, trns_histo)
        
        # print(f"Generated histogram for {name}:")
        # print(histograms[name])
        # print()
        
        # update search index
        search_idx = ref_binary.find(func_start_key, trns_start)
    # end while search_idx != -1

    return histograms
# gen_reference_histograms()


def gen_expected_histograms(alerts_csv_filepath : str, ref_histograms : dict[str,dict[str,int]]):
    print('Generating expected difference histograms...')

    if not os.path.exists(alerts_csv_filepath):
        print(f"Couldn't find alerts CSV {alerts_csv_filepath}")
        return
    
    histograms = dict()
    alerts_csv = open(alerts_csv_filepath, newline='')
    reader = csv.DictReader(alerts_csv)

    for row in reader:
        func = row['subroutine_name']
        insn = row['mir_opcode']

        if insn not in ref_histograms.keys():
            print(f"Could not find reference data for instruction {insn}. Skipping")
            continue

        if func not in histograms.keys():
            histograms[func] = ref_histograms[insn]
        else:
            for i in ref_histograms[insn].keys():
                if i in histograms[func].keys():
                    histograms[func][i] += ref_histograms[insn][i]
                else:
                    histograms[func][i] = ref_histograms[insn][i]
    
    return histograms


def check_histograms(
        original_filepath : str, 
        transformed_filepath : str,
        alerts_csv_filepath : str, 
        ref_histograms : dict[str,dict[str,int]]
):
    ''' Compare actual and expected histograms differences between original and
        transformed binary files, using an alerts CSV and set of reference 
        histograms to calculate the expected histogram.
    '''
    expected = gen_expected_histograms(alerts_csv_filepath, ref_histograms)
    assert expected is not None, f"Couldn't generate expected histograms with alerts CSV {alerts_csv_filepath}"
    
    original_contents = get_binary_contents(original_filepath)
    assert original_contents is not None, f"Couldn't retrieve contents from binary {original_filepath}"
    
    transformed_contents = get_binary_contents(transformed_filepath)
    assert transformed_contents is not None, f"Couldn't retrieve contents from binary {transformed_filepath}"
    
    actual = dict()
    for func in expected.keys():
        original_histo = get_histogram_for_function(original_contents, func)
        assert original_histo is not None, f"Couldn't generate histogram for {func} in {original_filepath}"
        
        transformed_histo = get_histogram_for_function(transformed_contents, func)
        assert transformed_histo is not None, f"Couldn't generate histogram for {func} in {transformed_filepath}"
        
        actual[func] = diff_histograms(original_histo, transformed_histo)

        print(f"Expected histogram difference for function {func}:\n{expected[func]}")
        print(f"Actual histogram difference:\n{actual[func]}")

        diff = diff_histograms(expected[func], actual[func])
        if len(diff.keys()) == 0:
            print("Actual matches expected\n")
        else:
            print(f"WARNING: Actual differs from expected. Diff (actual - expected):\n{diff}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('alerts_csv',
                        help='CSV file containing data on which instructions received alerts '
                             'in each function. Emitted by checker.')
    parser.add_argument('original_binary',
                        help='Path to the original or baseline binary file, without transformations.')
    parser.add_argument('transformed_binary', help='Path to the transformed binary file.')

    args = parser.parse_args()

    ref_histograms = gen_reference_histograms()
    check_histograms(args.original_binary, args.transformed_binary, args.alerts_csv, ref_histograms)


if __name__ == "__main__":
    main()


