import argparse
import csv

CASES_FILEPATH = "cmov_transform_cases.csv"

# r10 is used for comparisons, r11 for misc scratch work
SCRATCH_REGS = ['r12', 'r13', 'r14', 'r15']

class CompSimpCase:
    '''
    Represents a single computation simplification case for an instruction.
    One CS case is one `(cs_operand, cs_value)` pair, where `cs_operand` is
    the operand which can take a potentially dangerous value, and `cs_value`
    is the dangerous value itself. A CompSimpCase instance also encapsulates
    the information needed to emit a cmov-based transform for its CS case.
    '''
    def __init__(self, insn, data):
        self.insn = insn


def int_or_str(s : str):
    return int(s) if s.isdigit() else s


def get_cases(insn : str, ops : list[str]):
    '''
    Retrieve computation simplification case data from `CASES_FILEPATH`.
    Returns a list of dicts, where each dict contains data for a single
    CS case corresponding to `insn`.
    '''
    case_data = []
    cases_file = open(CASES_FILEPATH, newline='')
    reader = csv.DictReader(cases_file)

    # parse data
    for row in reader:
        if row['instruction'] != insn:
            continue

        # parse expected number of operands and compare to len(ops)
        n_ops = int(row['n_operands'])
        assert(n_ops == len(ops))

        # parse comma-separated list of additional sources, i.e., sources not
        # given as operands. Assumed to be strings representing valid registers
        other_srcs = row['other_srcs']
        other_srcs = other_srcs.split(',') if len(other_srcs) > 0 else []
        
        # parse comma-separated list of destination(s). If dests are
        # integers, they are interpreted as operand indices; otherwise,
        # as strings representing valid registers.
        dests = row['dests'].split(',')
        dests = list(map(
            lambda s: ops[int(s)] if s.isdigit() else s
            , dests
        ))

        # parse cs_operand: if integer, interpreted as operand index;
        # otherwise, as a string representing a valid argument
        cs_op = row['cs_operand']
        cs_op = ops[int(cs_op)] if cs_op.isdigit() else cs_op

        # parse cs_value and cs_safe_value: always ints
        cs_val = int(row['cs_value'])
        cs_safe_val = int(row['cs_safe_value'])

        # parse cs_solutions: comma-separated list of expected values in
        # destination(s) when the comp simp case is in effect. Must be 
        # same length as dests. Each entry is either "const:n", interpreted
        # as an immediate of integer value n; "op:n", interpreted as the
        # operand at index n; "src:n", interpreted as the additional source
        # register at index n; or a string representing a valid argument
        cs_solns = row['cs_solutions'].split(',')
        assert(len(cs_solns) == len(dests))
        cs_solns = list(map(
            lambda s:
                int(s[6:]) if s[:6] == 'const:' else
                # scratch regs will hold saved operand and source values
                SCRATCH_REGS[int(s[3:])] if s[:3] == 'op:' else
                SCRATCH_REGS[n_ops + int(s[4:])] if s[:4] == 'src:' else
                s
            , cs_solns
        ))

        case_data.append({
            'n_ops': n_ops,
            'other_srcs': other_srcs,
            'dests': dests,
            'cs_op': cs_op,
            'cs_val': cs_val,
            'cs_safe_val': cs_safe_val,
            'cs_solns': cs_solns
        })
    
    cases_file.close()
    return case_data


def gen_cmov_transform(insn, ops, cases):
    '''
    Recursively generate string cmov transform for the given instruction and
    comp simp cases.
    '''
    # sanity check; should never fail
    assert(len(cases) >= 1)

    # get data for current CS case
    cs_case = cases[0]
    srcs = ops + cs_case['other_srcs']
    dests = cs_case['dests']
    cs_op = cs_case['cs_op']
    cs_val = cs_case['cs_val']
    cs_safe_val = cs_case['cs_safe_val']
    cs_solns = cs_case['cs_solns']

    transform = ''

    # save operands to scratch regs
    for i in range(len(srcs)):
        transform += f'mov-r/m64-r64 {SCRATCH_REGS[i]} {srcs[i]}\n'

    # test for comp simp value
    transform += f'mov-r/m32-imm32 r10d $0\n'
    transform += f'mov-r64-imm64 r11 ${cs_val}\n'
    transform += f'cmp-r/m64-r64 {cs_op} r11\n'
    transform += 'setz r10b\n'

    # if comp simp case is in effect, set op to safe value
    transform += f'mov-r64-imm64 r11 ${cs_safe_val}\n'
    transform += f'cmovz-r64-r64 {cs_op} r11\n'

    # if in base case, perform operation; else recurse
    if len(cases) == 1:
        op_str = f'{insn}'
        for i in range(len(ops)):
            op_str += f' {ops[i]}'
        transform += f'{op_str}\n'

    else:
        # save r10, scratch regs
        transform += f'push-r/m64 r10\n'
        for i in range(len(srcs)):
            transform += f'push-r/m64 {SCRATCH_REGS[i]}\n'

        # recurse
        transform += gen_cmov_transform(insn, ops, cases[1:])

        # restore regs
        for i in range(len(srcs)).__reversed__():
            transform += f'pop-r/m64 {SCRATCH_REGS[i]}\n'
        transform += f'pop-r/m64 r10\n'

    # if comp simp case in effect, set dest(s) to trivial solution
    transform += 'cmp-r/m32-imm8 r10d $1\n'
    for i in range(len(dests)):
        if isinstance(cs_solns[i], int):
            transform += f'mov-r64-imm64 r11 ${cs_solns[i]}\n'
            transform += f'cmovz-r64-r64 {dests[i]} r11\n'
        else:
            transform += f'cmovz-r64-r64 {dests[i]} {cs_solns[i]}\n'

    # restore source operands, only if not also dests
    for i in range(len(srcs)):
        if srcs[i] not in dests:
            transform += f'mov-r/m64-r64 {srcs[i]} {SCRATCH_REGS[i]}\n'

    return transform


def main():
    '''
    Generates cmov-based transform for the specified instruction, using
    computation simplification cases specified in `CASES_FILEPATH`.

    Usage: `python3 gen_cmov_transform.py <insn> [<op1> ... <opn>]`
    '''
    parser = argparse.ArgumentParser()

    # Parse arguments
    parser.add_argument(
        'insn',
        help='text of the opcode of the instruction to be transformed. \
              Must exactly match the name used in `CASES_FILEPATH`. \
              Example: "add-r\m64-r64"'
    )
    parser.add_argument(
        'ops',
        help='textual operands for the instruction to be transformed. \
              Examples: "eax", "rax rcx"',
        nargs='+'
    )

    args = parser.parse_args()
    cs_cases = get_cases(args.insn, args.ops)
    if len(cs_cases) == 0:
        print(f"No computation simplification cases found for {args.insn}. "
                "Make sure the instruction name exactly matches the contents "
              f"of {CASES_FILEPATH}.")
        return
    print(cs_cases)
    
    transform = gen_cmov_transform(args.insn, args.ops, cs_cases)
    print(f'Emitting transform for {args.insn}\n')
    print(transform)


if __name__ == "__main__":
    main()
