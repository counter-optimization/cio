import os
import argparse
import re

BIN_DIR='fuzz_harnesses'
DUMP_FILE='temp_dump'
BIN_TRANS_FILE='temp_binary_transform'
VER_TRANS_FILE='temp_verified_transform'
VERIFICATION_DIR='../checker/synth'

def get_binary_dump(args):
    # if binary dir is empty, try to build and run tests
    if len(os.listdir(BIN_DIR)) == 0:
        print(f'\nBinary directory {BIN_DIR} is empty. Attempting to build and run tests...')
        os.system('./build_and_run_tests.sh')
        print('\nTests finished successfully. Proceeding\n')
    
    # all binaries contain all insn funcs, so we only need to objdump once
    filepath = os.path.join(BIN_DIR, f'cs-{args.insns[0]}-implementation-tester')
    if not os.path.exists(filepath):
        print(f'Could not find binary file {filepath}.\n'
               'Did you enter the instruction name correctly?\n')
        exit(-1)

    # extract dump
    os.system(f'objdump {filepath} -d --no-addresses --no-show-raw-insn -M suffix > {DUMP_FILE}')
    dump_file = open(DUMP_FILE)
    dump = list(map(lambda s: s.strip(), dump_file.readlines()))
    dump_file.close()
    os.system(f'rm -f {DUMP_FILE}')

    return dump


def get_verified_transforms():
    verification_files = [ 'arith-transforms.rkt'
                         , 'shift-transforms.rkt'
                         , 'bitwise-transforms.rkt'
                         , 'mul-transforms.rkt'
                         ]
    verification_lines = []

    for filename in verification_files:
        path = os.path.join(VERIFICATION_DIR, filename)
        file = open(path)
        verification_lines.extend(file.readlines())
        file.close()

    return verification_lines


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('insns', nargs='*',
                        help='name(s) of the opcode(s) to test. Must exactly '
                             'match the names used in LLVM. Default is to '
                             'test everything.')
    args = parser.parse_args()

    dump = get_binary_dump(args)
    verified = ''.join(get_verified_transforms())

    for insn in args.insns:
        os.system(f'echo "Checking {insn}..."')

        # extract transformed function from binary dump
        trans = f'<x86compsimptest_{insn}_transformed>:'
        if trans not in dump:
            print(f'ERROR: Could not find transform for {insn}. Skipping\n')
            continue

        bin_start = dump.index(trans) + 7 # add prefix lines
        bin_end = dump.index('', bin_start)
        if 'cs nopw 0x0(%rax,%rax,1)' in dump[bin_start:bin_end]:
            bin_end -= 31 # subtract suffix lines
        else:
            bin_end -= 30 # subtract suffix lines

        # dump binary transform
        bin_trans = '\n'.join(dump[bin_start:bin_end])
        os.system(f'echo "{bin_trans}" > {BIN_TRANS_FILE}')

        # extract all possible verified transforms
        ref_insn = re.match('[A-Z]+[0-9]*', insn).group(0).lower()
        ref = f'(define attempt-{ref_insn}'
        num_ref_transforms = verified.count(ref)

        if num_ref_transforms == 0:
            print(f'ERROR: Could not find matching verified transform '
                  f'(searched: {ref_insn}). Skipping\n')
            continue
        else:
            os.system(f'echo "Found {num_ref_transforms} possible verified transforms. Emitting diffs...\n"')

        ver_start = 0
        count = 0
        while ref in verified[ver_start:]:
            ver_start = verified.index(ref, ver_start)
            ver_title = verified[verified.index('attempt', ver_start):verified.index('\n', ver_start)]

            ver_start = verified.index('(list', ver_start) + len('(list\n')
            ver_end = len(verified)
            if '(define' in verified[ver_start + 1:]:
                ver_end = verified.index('(define', ver_start + 1)
            
            # dump verified transform
            ver_trans = verified[ver_start:ver_end]
            os.system(f'echo "{ver_trans}" > {VER_TRANS_FILE}')

            # emit diff
            os.system(f'echo "Diff for verified transform: {ver_title}"')
            os.system(f'diff -y {BIN_TRANS_FILE} {VER_TRANS_FILE}')
            os.system('echo ""')

            count += 1
            if count >= num_ref_transforms:
                break
        # end while
    # end for

    # clean up
    os.system(f'rm -f {BIN_TRANS_FILE}')
    os.system(f'rm -f {VER_TRANS_FILE}')
    

if __name__ == "__main__":
    main()
