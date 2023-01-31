import argparse
import os
import matplotlib.pyplot as plt
import numpy as np

CRYPTO_FNS = dict({
    'libsodium':
    [   'ed25519'
    ,   'aesni256gcm-decrypt'
    ,   'aesni256gcm-encrypt'
    ,   'argon2id'
    ,   'chacha20-poly1305-decrypt'
    ,   'chacha20-poly1305-encrypt'
    ]
})


def parse_lines(filepath):
    '''
    Get the lines of a file as individual entries in a list, without newlines.
    Entries are strings by default, converted to integers where possible.
    '''
    # read file
    file = open(filepath)
    lines = file.readlines()
    file.close()
    # process lines
    data = list(map(lambda s: s.strip(), lines))
    data = list(map(lambda s: int(s) if s.isdigit() else s, data))
    return data


def gen_cycle_curves(eval_dir, subdir):
    ''' 
    Generate cycle line charts for each crypto func test case in a subdirectory.
    Useful for gauging number of warmup iterations.
    '''
    for lib in CRYPTO_FNS:
        for fn in CRYPTO_FNS[lib]:
            # Get data
            logfile = os.path.join(eval_dir, subdir, f'{lib}-{fn}.log')
            raw_data = parse_lines(logfile)
            title = f'{subdir}: {raw_data[0]}'
            cycles_data = raw_data[1:]

            min_cycles = min(cycles_data)
            min_idx = cycles_data.index(min_cycles)
            print(f'min of {lib}-{fn} is {min_cycles} at {min_idx}')

            # # Calculate reasonable bounds for y-axis
            # quartiles = np.quantile(cycles_data, [0.25, 0.75])
            # iqr = quartiles[1] - quartiles[0]
            # upper_bound = quartiles[1] + iqr * 4
            # lower_bound = quartiles[0] - iqr * 2

            # Plot
            fig, ax = plt.subplots()
            ax.clear()
            ax.plot(cycles_data)
            # ax.set_ylim(bottom=lower_bound, top=upper_bound)
            ax.set_title(title)
            ax.set_ylabel('Cycles')
            ax.set_xlabel('Iteration')
            fig.savefig(os.path.join(eval_dir, subdir, f'{lib}-{fn}-cycles.png'))


def get_avg_cycles(eval_dir, subdir, test_case):
    ''' Get average cycle counts for a single test case. '''
    # TODO: geomean?
    logfile = os.path.join(eval_dir, subdir, f'{test_case}.log')
    raw_data = parse_lines(logfile)
    cycles_data = raw_data[1:]
    return sum(cycles_data) / len(cycles_data)


def get_cycle_overheads(eval_dir, baseline, ablations):
    ''' Calculate runtime cycle overheads for all '''
    # Calculate baseline average cycles for each crypto func
    baseline_avgs = dict()
    for lib in CRYPTO_FNS:
        lib_avgs = dict()
        for fn in CRYPTO_FNS[lib]:
            test_case = f'{lib}-{fn}'
            lib_avgs[fn] = get_avg_cycles(eval_dir, baseline, test_case)
        baseline_avgs[lib] = lib_avgs

    # Calculate overheads for each ablation and crypto func
    overheads = dict()
    for lib in CRYPTO_FNS:
        lib_ohs = dict()
        for fn in CRYPTO_FNS[lib]:
            fn_ohs = dict()
            for abl in ablations:
                test_case = f'{lib}-{fn}'
                avg_cycles = get_avg_cycles(eval_dir, abl, test_case)
                fn_ohs[abl] = avg_cycles / baseline_avgs[lib][fn]
            lib_ohs[fn] = fn_ohs
        overheads[lib] = lib_ohs

    return overheads


def gen_overhead_plot(eval_dir, baseline, ablations, out_dir):
    ''' Create plot of runtime overhead for each ablation vs baseline.'''
    overheads = get_cycle_overheads(eval_dir, baseline, ablations)
    print(overheads)
    
    # Plot overheads
    fig, ax = plt.subplots()
    lib_ohs = overheads['libsodium']

    for fn in lib_ohs:
        fn_ohs = lib_ohs[fn]
        ax.bar(fn_ohs.keys(), fn_ohs.values())
        print(fn_ohs)
        fig.savefig(os.path.join(out_dir, f'{fn}-plot.png'))
        ax.clear()


def main():
    # Parse user arguments
    parser = argparse.ArgumentParser()

    parser.add_argument('eval_dir', help='directory containing the raw eval data')
    parser.add_argument('baseline_dir',
        help='subdirectory of eval_dir containing baseline data for comparison')
    parser.add_argument(
        'ablations',
        nargs='+',
        help='list of mitigation versions to compare. Example: `cs ss` would generate '
             'a comparison between cs and ss only. Each ablation MUST have a '
             'subdirectory with the same name in `eval_dir`.'
    )
    parser.add_argument('-o', '--out', help="output directory. Defaults to `eval_dir`")

    args = parser.parse_args()

    # Generate cycle overhead plot
    out_dir = args.out if args.out is not None else args.eval_dir
    gen_overhead_plot(args.eval_dir, args.baseline_dir, args.ablations, out_dir)
    gen_cycle_curves(args.eval_dir, args.baseline_dir)


if __name__ == "__main__":
    main()
