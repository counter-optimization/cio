import argparse
import os
import matplotlib.pyplot as plt
import statistics as stat
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
MEAN = 'mean_cycles'
STD = 'std'
OVERHEAD = 'overhead'
OVERHEAD_STD = 'overhead_std'
BINARY_SIZE = 'binary_size'



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
                fn_data = parse_lines(
                    os.path.join(args.eval_dir, abl, f'{lib}-{fn}.log')
                )
                if len(fn_data) <= 1:
                    # No data, skip
                    continue

                # Filter outliers
                quartiles = np.quantile(fn_data[1:], [0.1, 0.9])
                iqr = quartiles[1] - quartiles[0]
                upper_bound = quartiles[1] + iqr * 8
                cycles_data = np.array(fn_data[1:])
                cycles_data = cycles_data[cycles_data < upper_bound]
                
                # cycles data
                data[lib][abl][fn] = dict()
                data[lib][abl][fn][TITLE] = fn_data[0]
                data[lib][abl][fn][RAW_CYCLES] = cycles_data
                data[lib][abl][fn][MEAN] = np.mean(data[lib][abl][fn][RAW_CYCLES])
                data[lib][abl][fn][STD] = np.std(data[lib][abl][fn][RAW_CYCLES])

                # binary size
                fn_file_sz = open(os.path.join(args.eval_dir, abl, f'{lib}-{fn}-bytesize.txt'))
                data[lib][abl][fn][BINARY_SIZE] = fn_file_sz.readline().strip()
                fn_file_sz.close()
                
    return data


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
        width = 0.25
        multiplier = 0
        fig, ax = plt.subplots()
        plt.axhline(y=1.0)

        for abl, ohs in fn_ohs.items():
            offset = width * multiplier
            rects = ax.bar(x + offset, ohs, width, yerr=fn_stds[abl], capsize=4, label=abl)
            # ax.bar_label(rects, padding=3)
            multiplier += 1

        ax.set_ylabel('Normalized execution time')
        ax.set_xlabel('Cryptographic function')
        ax.set_title('Overhead of libsodium microbenchmarks')
        plt.xticks(x, labels=fns, rotation=45, ha='right')
        ax.legend(bbox_to_anchor=(1.01, 1.0), loc='upper left')
        ax.set_axisbelow(True)
        ax.yaxis.grid(True)

        plt.savefig(
            os.path.join(target_dir, 'microbench-overheads.png'),
            bbox_inches='tight')
        print(f"Saved bar chart to {os.path.join(target_dir, 'microbench-overheads.png')}")
        plt.close()


def gen_latex_table_inserts(target_dir, baseline_dir, data):
    lib = 'libsodium'

    for fn in CRYPTO_FNS[lib]:
        filepath = os.path.join(target_dir, f'{fn}.tex')
        output = ''

        # Baseline
        mean = data[lib][baseline_dir][fn][MEAN]
        output += "{0:4.5g} & ".format(mean)

        # SS
        if 'ss' in data[lib].keys():
            mean = data[lib]['ss'][fn][MEAN]
            output += "{0:4.5g}".format(mean)
        output += ' & '

        # CS
        if 'cs' in data[lib].keys():
            mean = data[lib]['cs'][fn][MEAN]
            output += "{0:4.5g}".format(mean)
        output += ' & '

        # SS + CS
        if 'ss+cs' in data[lib].keys():
            mean = data[lib]['ss+cs'][fn][MEAN]
            output += "{0:4.5g}".format(mean)
        
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
    gen_overhead_plot(target_dir, args.baseline_dir, data)


if __name__ == "__main__":
    main()
