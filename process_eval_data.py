import argparse
import os
import matplotlib.pyplot as plt
import matplotlib
matplotlib.rcParams['pdf.fonttype'] = 42
matplotlib.rcParams['ps.fonttype'] = 42
import statistics as stat
import numpy as np

CRYPTO_FNS = dict({
    'libsodium':
    [   'argon2id'
    ,   'ed25519'
    ,   'aesni256gcm-decrypt'
    ,   'aesni256gcm-encrypt'
    ,   'chacha20-poly1305-decrypt'
    ,   'chacha20-poly1305-encrypt' 
    ]
})

Y_BOUNDS = dict({
    'ed25519': (40000, 220000),
    'aesni256gcm-decrypt': (0, 1000),
    'aesni256gcm-encrypt': (0, 1000),
    'argon2id': (10**8, 2 * 10**8),
    'chacha20-poly1305-decrypt': (0, 2500),
    'chacha20-poly1305-encrypt': (0, 2500),
})

TITLE = 'title'
RAW_CYCLES = 'raw_cycles'
DYN_HITS = 'dynamic_hit_counts'
MEAN = 'mean_cycles'
STD = 'std'
OVERHEAD = 'overhead'
OVERHEAD_STD = 'overhead_std'
BINARY_SIZE = 'binary_size'

LEGEND = dict({
    'ss+cs': 'SS and CS',
    'ss': 'SS only',
    'cs': 'CS only (all categories)',
    'cs_mul64': 'CS for 64-bit multiplication',
    'cs_lea': 'CS for LEA instructions',
    'cs_vector': 'CS for vector instructions',
    'cs_other_64': 'CS for all other 64-bit instructions',
    'cs_other': 'CS for all other instructions (32-bit or less)',
    'rr': 'No transformations, but registers reserved'
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


def get_data(args):
    data = dict()
    for lib in CRYPTO_FNS:
        data[lib] = dict()
        for abl in [args.baseline_dir] + args.ablations:
            data[lib][abl] = dict()
            for fn in CRYPTO_FNS[lib]:
                # Read cycles data
                cycles_filepath = os.path.join(args.eval_dir, abl, f'{lib}-{fn}-cyclecounts.csv')
                if not os.path.exists(cycles_filepath):
                    print(f"Couldn't find cycle counts file {cycles_filepath}. Skipping")
                    continue
                
                cycles_data = parse_lines(cycles_filepath)
                if len(cycles_data) <= 1:
                    # No data, skip
                    continue

                # Filter outliers
                quartiles = np.quantile(cycles_data[1:], [0.25, 0.75])
                iqr = quartiles[1] - quartiles[0]
                upper_bound = quartiles[1] + iqr * 1.5
                cycles_arr = np.array(cycles_data[1:])

                # cycles data
                data[lib][abl][fn] = dict()
                data[lib][abl][fn][TITLE] = cycles_data[0]
                data[lib][abl][fn][RAW_CYCLES] = cycles_arr[cycles_arr < upper_bound]
                data[lib][abl][fn][MEAN] = np.mean(data[lib][abl][fn][RAW_CYCLES])
                data[lib][abl][fn][STD] = np.std(data[lib][abl][fn][RAW_CYCLES])

                # dynamic hit counts data
                dyn_hits_filepath = os.path.join(args.eval_dir, abl, f'{lib}-{fn}-dynhitcounts.csv')
                if not os.path.exists(dyn_hits_filepath):
                    print(f"Couldn't find dynamic hit counts at {dyn_hits_filepath}")
                    data[lib][abl][fn][DYN_HITS] = None
                else:
                    data[lib][abl][fn][DYN_HITS] = dict(map(
                        lambda s: s.split(','), parse_lines(dyn_hits_filepath)
                    ))

                # binary size
                sz_filepath = os.path.join(args.eval_dir, abl, f'{lib}-{fn}-bytesize.txt')
                if not os.path.exists(sz_filepath):
                    print(f"Couldn't find binary size data at {sz_filepath}")
                    data[lib][abl][fn][BINARY_SIZE] = None
                else:
                    fn_file_sz = open(sz_filepath)
                    data[lib][abl][fn][BINARY_SIZE] = fn_file_sz.readline().strip()
                    fn_file_sz.close()
                
    return data


def merge_decrypt_encrypt_data(data: dict):
    merged_data = dict()
    for lib in data.keys():
        merged_data[lib] = dict()
        for abl in data[lib].keys():
            merged_data[lib][abl] = dict()
            for fn in data[lib][abl].keys():
                if fn.find("-encrypt") != -1:
                    fn_name = fn[0:fn.index("-encrypt")]
                    merged_data[lib][abl][fn_name] = data[lib][abl][fn]
                elif fn.find("-decrypt") == -1:
                    merged_data[lib][abl][fn] = data[lib][abl][fn]

    return merged_data


def gen_pretty_data_string(data: dict):
    result = ''
    for lib in data.keys():
        result += f'{lib}:\n'
        for abl in data[lib].keys():
            result += f'{abl}:\n'
            for fn in data[lib][abl].keys():
                title = data[lib][abl][fn][TITLE]
                result += f'\t{title}:\n'
                for stat in data[lib][abl][fn].keys():
                    if stat != RAW_CYCLES and stat != TITLE:
                        result += f'\t\t{stat}: {data[lib][abl][fn][stat]}\n'
    return result


def gen_cycle_curves(eval_dir, data):
    ''' 
    Generate cycle line charts for each crypto func test case in a subdirectory.
    Useful for gauging number of warmup iterations.
    '''
    print("Generating cycle graphs for each benchmark...")
    for lib in data.keys():
        for abl in data[lib].keys():
            for fn in data[lib][abl].keys():
                title = data[lib][abl][fn][TITLE]
                cycles_data = data[lib][abl][fn][RAW_CYCLES]

                # Calculate reasonable bounds for y-axis
                quartiles = np.quantile(cycles_data, [0.1, 0.9])
                iqr = quartiles[1] - quartiles[0]
                upper_bound = quartiles[1] + iqr * 8
                lower_bound = quartiles[0] - iqr * 2

                # Plot
                fig, ax = plt.subplots()
                ax.plot(cycles_data)
                ax.set_ylim(bottom=lower_bound, top=upper_bound)
                ax.set_title(title)
                ax.set_ylabel('Cycles')
                ax.set_xlabel('Iteration')
                fig.savefig(os.path.join(eval_dir, abl, f'{lib}-{fn}-cycles.png'))
                print(f"Saved {abl} {fn} ({lib}) graph to "
                      f"{os.path.join(eval_dir, abl, f'{lib}-{fn}-cycles.png')}")
                plt.close()


def gen_overhead_plot(target_dir, baseline_dir, data):
    ''' Create plot of runtime overhead for each ablation vs baseline.'''
    print("Generating bar chart of normalized overheads...")
    for lib in data.keys():
        abls = list(data[lib].keys())
        abls.remove(baseline_dir)
        
        fns = list(data[lib][abls[0]].keys())
        fn_ohs = dict()
        fn_stds = dict()

        for abl in abls:
            fn_ohs[abl] = []
            fn_stds[abl] = []
            for fn in fns:
                fn_ohs[abl] += [data[lib][abl][fn][OVERHEAD]]
                fn_stds[abl] += [data[lib][abl][fn][OVERHEAD_STD]]
            
        x = np.arange(len(fns))
        width = 1 / (len(fn_ohs.items()) + 1)
        multiplier = 0

        plt.style.use("tableau-colorblind10")
        fig, ax = plt.subplots()
        fig.set_figwidth(16)
        plt.axhline(y=1.0)

        max_oh = 0
        for abl, ohs in fn_ohs.items():
            max_oh = max(max_oh, max(ohs))
            offset = width * multiplier
            legend = LEGEND[abl] if abl in LEGEND.keys() else abl
            rects = ax.bar(x + offset, ohs, width, yerr=fn_stds[abl], capsize=4, label=legend)
            ax.bar_label(rects, [f"{format(oh, '.2f')}x" for oh in ohs], padding=6, rotation="vertical", fontsize=11)
            multiplier += 1

        ax.set_xmargin(0.02)
        ax.set_ylim(top=max_oh+7)
        ax.set_ylabel('Normalized execution time', fontsize=12.5)
        ax.set_xlabel('Cryptographic function', fontsize=12.5)
        ax.set_title('Overhead of libsodium microbenchmarks', fontsize=15)
        plt.xticks(x, labels=fns, fontsize=12)
        ax.legend(bbox_to_anchor=(0.675, 0.99), loc='upper left', fontsize=11)
        ax.set_axisbelow(True)
        ax.yaxis.grid(True)

        plt.savefig(
            os.path.join(target_dir, 'microbench-overheads.pdf'),
            bbox_inches='tight')
        print(f"Saved bar chart to {os.path.join(target_dir, 'microbench-overheads.pdf')}")
        plt.close()


def gen_latex_table_inserts(target_dir, baseline_dir, data):
    lib = 'libsodium'

    for fn in CRYPTO_FNS[lib]:
        filepath = os.path.join(target_dir, f'{fn}.tex')
        output = ''

        # Baseline
        mean = data[lib][baseline_dir][fn][MEAN]
        oh = data[lib][baseline_dir][fn][OVERHEAD]
        output += f"{format(mean, '.4g')} ({format(oh, '.2f')})"
        output += ' & '

        # SS
        if 'ss' in data[lib].keys():
            mean = data[lib]['ss'][fn][MEAN]
            oh = data[lib]['ss'][fn][OVERHEAD]
            output += f"{format(mean, '.4g')} ({format(oh, '.2f')})"
        output += ' & '

        # CS
        if 'cs' in data[lib].keys():
            mean = data[lib]['cs'][fn][MEAN]
            oh = data[lib]['cs'][fn][OVERHEAD]
            output += f"{format(mean, '.4g')} ({format(oh, '.2f')})"
        output += ' & '

        # SS + CS
        if 'ss+cs' in data[lib].keys():
            mean = data[lib]['ss+cs'][fn][MEAN]
            oh = data[lib]['ss+cs'][fn][OVERHEAD]
            output += f"{format(mean, '.4g')} ({format(oh, '.2f')})"
        
        # save output
        file = open(filepath, 'w')
        print(output, file=file)
        file.close()


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

    # Retrieve cycles data
    data = get_data(args)
    
    # Calculate cycle overheads vs baseline
    for lib in data.keys():
        for abl in data[lib].keys():
            for fn in data[lib][abl].keys():
                baseline = data[lib][args.baseline_dir][fn]
                fn_data = data[lib][abl][fn]
                fn_data[OVERHEAD] = fn_data[MEAN] / baseline[MEAN]
                fn_data[OVERHEAD_STD] = fn_data[STD] / baseline[MEAN]
    
    # Save calculated data
    data_str = gen_pretty_data_string(data)
    data_filepath = os.path.join(args.eval_dir, 'calculated_data.txt')
    data_file = open(data_filepath, 'w')
    print(data_str, file=data_file)
    data_file.close()
    print(f'Saved calculated results to {data_filepath}')
    
    # Plot cycles for each eval run (line charts)
    gen_cycle_curves(args.eval_dir, data)

    # Generate data and charts for paper
    target_dir = os.path.join(args.eval_dir, 'benchmarks')
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)

    gen_latex_table_inserts(target_dir, args.baseline_dir, data)
    data = merge_decrypt_encrypt_data(data)
    gen_overhead_plot(target_dir, args.baseline_dir, data)


if __name__ == "__main__":
    main()
