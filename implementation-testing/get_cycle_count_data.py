import argparse
import sys
from pathlib import Path
import re
import statistics

LOG_FILE_EXTENSION = "*.log"

"""
csv header is defined in ./implementation-tester.c in function
static void print_cycle_counts()
"""
CSV_HEADER = "orig,transformed"

# following regexes used to validate preconditions about
# syntax of the eval data so processing goes smoothly
CSV_ROW_RE = re.compile(r"^\d+,\d+$") # per line
FILE_NAME_RE = re.compile(r".+?-.+?-.+?-.+?\.log")

usage_msg = """
get cycle counts after running ./build_and_run_tests.sh --record-cycle-counts
"""

EMPTY_TEST_OPCODE_NAME = "cs-VPCOMPRESSBZ256rrkz"

argparser = argparse.ArgumentParser(usage_msg)
argparser.add_argument('test_dir')
argparser.add_argument('--amortization-count',
                       action='store',
                       default=1,
                       type=int)
argparser.add_argument('--use-n-measurements',
                       action='store',
                       default=-1,
                       type=int)
argparser.add_argument('--overhead-out-csv-file',
                       action='store',
                       default=None,
                       type=str)
argparser.add_argument('--avg-cycles-csv-file',
                       action='store',
                       default=None,
                       type=str)

def get_opcode_name(logfilename):
    if re.fullmatch(FILE_NAME_RE, logfilename) is None:
        print(f"Log file name is badly formed: {logfilename}")
        sys.exit(1)
    else:
        cs_or_ss, mir_opcode, _, _ = logfilename.split("-")
        return f"{cs_or_ss}-{mir_opcode}"

def get_measurement_overhead(cycle_counts):
    origvtran = cycle_counts[EMPTY_TEST_OPCODE_NAME]
    all_counts = origvtran['original'] + origvtran['transformed']
    avg = statistics.fmean(all_counts)
    pstdev = statistics.pstdev(all_counts)
    print(f"measurement overhead is: {avg} ± {pstdev}")
    del cycle_counts[EMPTY_TEST_OPCODE_NAME] # so it's not used later
    return avg

def remove_measurement_overhead(nums, overhead, amortization_count):
    for num in nums:
        yield (num / amortization_count)
    # for num in nums:
    #     removed = num - overhead
    #     if removed < 0.0:
    #         yield 0.0
    #     else:
    #         yield removed / amortization_count

def ratio(numerators, denomenators):
    for n, d in zip(numerators, denomenators):
        yield (n / d if d != 0 else 1)

if __name__ == '__main__':
    args = argparser.parse_args()
    
    test_dir = Path(args.test_dir)
    amortization_count = args.amortization_count
    use_n_measurements = args.use_n_measurements

    if not test_dir.exists() or not test_dir.is_dir():
        print(f"error: test dir {test_dir} doesn't exist or isn't dir")
        sys.exit(1)

    # cycle counts
    # this is a dict from: miropcode -> {"original", "transformed"} -> list of cycle counts
    cycle_counts = dict()

    # since libfuzzer randomly generates input data,
    # there is no guarantee the num of csv lines in each log
    # file is the same. to avoid wrongly varying variation
    # between opcode measurements, take the min of the
    # num_csv_lines_int
    #
    # giant number init value to just use:
    #    least_csv_lines = min(least_csv_lines, curnum_csv_lines)
    least_csv_lines = 9999999999999999999999999999999999999999999
    who_has_least = None

    for log in test_dir.glob(LOG_FILE_EXTENSION):
        txt = log.read_text()
        lines = txt.splitlines()
        
        origvtrans_store = dict()

        try:
            header_line_idx = lines.index(CSV_HEADER)
        except ValueError: # if CSV_HEADER not found
            print(f"File {log} does not have cycle count data (no csv header line found). "
                  "Fuzzer num_runs parameter probably too low to hit counts")
            sys.exit(1)

        line_num = header_line_idx + 1
        cycle_count_lines = lines[line_num:]

        # discard the first 100 since the first 3 or so can have
        # ramp up times (50,000 cycles which is unrealistic)
        default_discard_amount = 100 # from the start
        if use_n_measurements == -1:
            cycle_count_lines = cycle_count_lines[default_discard_amount:]
        else:
            if use_n_measurements < len(cycle_count_lines):
                # otherwise, take the last `use_n_measurements` measurements
                cycle_count_lines = cycle_count_lines[-use_n_measurements:]
            else:
                print(f"{log.name} only has {len(cycle_count_lines)} measurements, so cannot use --use-n-measurements={use_n_measurements}")
                sys.exit(2)

        # compute least_csv_lines
        cur_num_csv_lines = len(cycle_count_lines)
        if cur_num_csv_lines < least_csv_lines:
            least_csv_lines = cur_num_csv_lines
            who_has_least = log.name
        
        for line in cycle_count_lines:
            if re.fullmatch(CSV_ROW_RE, line) is None:
                print(f"line num {line_num} in file {log} is badly formed.")
                print(f"the line is: {line}")
                sys.exit(1)
                    
            orig_cycles, _, transformed_cycles = line.partition(",")
            orig_cycles = int(orig_cycles)
            transformed_cycles = int(transformed_cycles)

            if 'original' not in origvtrans_store:
                origvtrans_store['original'] = []
            if 'transformed' not in origvtrans_store:
                origvtrans_store['transformed'] = []
                
            origvtrans_store['original'].append(orig_cycles)
            origvtrans_store['transformed'].append(transformed_cycles)

            line_num += 1

        opcode_name = get_opcode_name(log.name)
        cycle_counts[opcode_name] = origvtrans_store

    # end of main loop over all log files. now compute stats/visualizations

    print(f"Least number of opcodes ({least_csv_lines}) in {who_has_least}")

    # truncate the number of counts on all measurements to
    # least_csv_lines
    for opcode in cycle_counts:
        origvtransformed = cycle_counts[opcode]
        origvtransformed['original'] = origvtransformed['original'][:least_csv_lines]
        origvtransformed['transformed'] = origvtransformed['transformed'][:least_csv_lines]
        cycle_counts[opcode] = origvtransformed

    measurement_overhead = get_measurement_overhead(cycle_counts)
    
    print(f"N = {least_csv_lines}")
    orig_avg_cycles = []
    trans_avg_cycles = []
    overheads = []
    for opcode in cycle_counts:
        origvtransformed = cycle_counts[opcode]
        
        orig = list(remove_measurement_overhead(origvtransformed['original'],
                                                measurement_overhead,
                                                amortization_count))
        tran = list(remove_measurement_overhead(origvtransformed['transformed'],
                                                measurement_overhead,
                                                amortization_count))

        overhead_ratios = list(map(lambda x : 1 if x <= 0.0 else x,
                                   ratio(tran, orig)))
        
        orig_avg, orig_pstd = statistics.fmean(orig), statistics.pstdev(orig)
        transformed_avg, transformed_pstd = statistics.fmean(tran), statistics.pstdev(tran)
        geomean_overhead = statistics.geometric_mean(overhead_ratios)

        #         argparser.add_argument('--overhead-out-csv-file',
        #                        action='store',
        #                        default=None,
        #                        type=str)
        # argparser.add_argument('--avg-cycles-csv-file',
        overheads.append((opcode, geomean_overhead))
        orig_avg_cycles.append((opcode, orig_avg, orig_pstd))
        trans_avg_cycles.append((opcode, transformed_avg, transformed_pstd))
        print(f"{opcode}:")
        print(f"\toriginal: {orig_avg} ± {orig_pstd}")
        print(f"\ttransformed: {transformed_avg} ± {transformed_pstd}")
        print(f"\tgeomean_overhead: {geomean_overhead}")
    if args.overhead_out_csv_file is not None:
        with open(args.overhead_out_csv_file, 'w') as fl:
            for ohd in overheads:
                fl.write(f"{ohd[0]},{ohd[1]}\n")
