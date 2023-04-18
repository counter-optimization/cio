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
    'ed25519': (40000, 100000),
    'aesni256gcm-decrypt': (0, 1000),
    'aesni256gcm-encrypt': (0, 1000),
    'argon2id': (10**8, 2 * 10**8),
    'chacha20-poly1305-decrypt': (0, 2500),
    'chacha20-poly1305-encrypt': (0, 2500),
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


def gen_pretty_data_string(data: dict):
    result = ''
    for lib in data.keys():
        result += f'{lib}:\n'
        for abl in data[lib].keys():
            result += f'{abl}:\n'
            for fn in data[lib][abl].keys():
                title = data[lib][abl][fn]['title']
                result += f'\t{title}:\n'
                for stat in data[lib][abl][fn].keys():
                    if stat != 'raw cycles' and stat != 'title':
                        result += f'\t\t{stat}: {data[lib][abl][fn][stat]}\n'
    return result


def gen_cycle_curves(eval_dir, data):
    ''' 
    Generate cycle line charts for each crypto func test case in a subdirectory.
    Useful for gauging number of warmup iterations.
    '''
    for lib in data.keys():
        for abl in data[lib].keys():
            for fn in data[lib][abl].keys():
                title = data[lib][abl][fn]['title']
                cycles_data = data[lib][abl][fn]['raw cycles']

                # # Calculate reasonable bounds for y-axis
                # quartiles = np.quantile(cycles_data, [0.25, 0.75])
                # iqr = quartiles[1] - quartiles[0]
                # upper_bound = quartiles[1] + iqr * 4
                # lower_bound = quartiles[0] - iqr * 2

                # Plot
                fig, ax = plt.subplots()
                ax.plot(cycles_data)
                ax.set_ylim(bottom=Y_BOUNDS[fn][0], top=Y_BOUNDS[fn][1])
                ax.set_title(title)
                ax.set_ylabel('Cycles')
                ax.set_xlabel('Iteration')
                fig.savefig(os.path.join(eval_dir, abl, f'{lib}-{fn}-cycles.png'))
                plt.close()


def gen_overhead_plot(eval_dir, baseline_dir, data):
    ''' Create plot of runtime overhead for each ablation vs baseline.'''
    for lib in data.keys():
        for abl in data[lib].keys():
            if abl == baseline_dir:
                continue
            fns = []
            fn_ohs = []
            fn_stds = []
            for fn in data[lib][abl].keys():
                fns += [fn]
                fn_ohs += [data[lib][abl][fn]['overhead']]
                fn_stds += [data[lib][abl][fn]['overhead std']]
            
            x = np.arange(len(fns))
            fig, ax = plt.subplots()
            ax.yaxis.grid(True)
            ax.bar(x, fn_ohs, yerr=fn_stds, align='center', alpha=0.5, capsize=4)
            ax.set_ylabel('Overhead')
            ax.set_xlabel('Crypto func')
            plt.xticks(x, labels=fns, rotation=45, ha='right')
            plt.axhline(y=1.0, linestyle='-')
            plt.savefig(
                os.path.join(eval_dir, abl, 'overhead_bar_plot.png'),
                bbox_inches='tight')
            plt.close()


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
                
                data[lib][abl][fn] = dict()
                data[lib][abl][fn]['title'] = fn_data[0]
                data[lib][abl][fn]['raw cycles'] = np.array(fn_data[1:])
                data[lib][abl][fn]['mean'] = np.mean(data[lib][abl][fn]['raw cycles'])
                data[lib][abl][fn]['std'] = np.std(data[lib][abl][fn]['raw cycles'])
    
    # Calculate cycle overheads vs baseline
    for lib in data.keys():
        for abl in data[lib].keys():
            if abl == args.baseline_dir:
                continue
            for fn in data[lib][abl].keys():
                baseline = data[lib][args.baseline_dir][fn]
                fn_data = data[lib][abl][fn]
                fn_data['overhead'] = fn_data['mean'] / baseline['mean']
                fn_data['overhead std'] = fn_data['std'] / baseline['mean']
    
    # Save calculated data
    data_str = gen_pretty_data_string(data)
    data_filepath = os.path.join(args.eval_dir, 'calculated_data.txt')
    data_file = open(data_filepath, 'w')
    print(data_str, file=data_file)
    data_file.close()
    print(f'Saved calculated results to {data_filepath}')
    
    # Plot cycles for each eval run (line charts)
    gen_cycle_curves(args.eval_dir, data)

    # Plot overheads (bar charts)
    gen_overhead_plot(args.eval_dir, args.baseline_dir, data)


if __name__ == "__main__":
    main()
