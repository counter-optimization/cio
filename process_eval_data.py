import argparse
import os
import matplotlib.pyplot as plt

EVAL_CASES = [
    'libsodium-ed25519',
    'libsodium-aesni256gcm-decrypt',
    'libsodium-aesni256gcm-encrypt',
    'libsodium-argon2id',
    'libsodium-chacha20-poly1305-decrypt',
    'libsodium-chacha20-poly1305-encrypt'
]


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


def main():
    # Parse argument for eval directory
    parser = argparse.ArgumentParser()
    parser.add_argument('eval_dir', help='directory containing the raw eval data')
    args = parser.parse_args()

    eval_dir = args.eval_dir
    eval_cases = EVAL_CASES

    eval_paths = dict(map(
        lambda case: (case, os.path.join(eval_dir, case + '.log')),
        eval_cases
    ))

    eval_data = dict(map(lambda case: (case, parse_lines(eval_paths[case])), eval_cases))
    eval_avgs = dict(map(
        lambda case: (case, sum(eval_data[case][1:])/len(eval_data[case][1:])),
        eval_cases
    ))

    # Output average cycles for each eval case
    outfile = open(os.path.join(eval_dir, 'avg-cycles.txt'), "w")
    for case in eval_cases:
        header = eval_data[case][0]
        outfile.writelines("Average " + header + "\n")
        outfile.write(str(eval_avgs[case]) + "\n")
    outfile.close()
    
    # Simple bar chart of average cycles
    # warning: ugly/unreadable, partly because argon2id's cycle counts are so high
    fig, ax = plt.subplots()
    ax.bar(eval_avgs.keys(), eval_avgs.values())
    fig.savefig(os.path.join(eval_dir, 'plot.png'))


if __name__ == "__main__":
    main()
