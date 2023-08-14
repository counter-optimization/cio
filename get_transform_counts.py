import sys
from pathlib import Path
import argparse
import re

usage_msg = """
after running cio or an inner cio run of ./eval.sh with one job slot (-j 1),
parse the compiler output to get the counts of num opcodes transformed out of those
considered and
num of insns transformed out of those considered
"""

argparser = argparse.ArgumentParser(usage_msg)
argparser.add_argument('log_file_to_parse')

args = argparser.parse_args()
log_file = Path(args.log_file_to_parse)

if not log_file.exists():
    print(f"error: log file {log_file} doesn't exist")
    sys.exit(1)

OPCODES_RE = re.compile("^\[(?P<ss_or_cs>CS|SS)\] for function (?P<subname>\S+) transforming (?P<transformed>\d+) out of (?P<total>\d+) insns.$")
INSNS_RE = re.compile("^\[(?P<ss_or_cs>CS|SS)\] for function (?P<subname>\S+) transformed (?P<transformed>\d+) out of (?P<total>\d+) mir opcodes.$")

# opcodes a list of 4-tuples: {SS, CS} * subname_str * transformed_int * total_int
opcodes = []

# insns a list of 4-tuples: {SS, CS} * subname_str * transformed_int * total_int
insns = []

with log_file.open(mode='r') as lf:
    for line in lf:
        opcode_match = OPCODES_RE.match(line)
        if opcode_match:
            opcodes.append((opcode_match.group('ss_or_cs'),
                            opcode_match.group('subname'),
                            int(opcode_match.group('transformed')),
                            int(opcode_match.group('total'))))
            continue
        
        insn_match = INSNS_RE.match(line)
        if insn_match:
            insns.append((insn_match.group('ss_or_cs'),
                          insn_match.group('subname'),
                          int(insn_match.group('transformed')),
                          int(insn_match.group('total'))))
            continue

# print all records:

for opc in sorted(opcodes):
    print(f"Opcode: {opc}")

for insn in sorted(insns):
    print(f"Insn: {insn}")

# now compute aggregate stats over the data

total_opcodes_transformed = 0
total_opcodes_considered = 0
cs_opcodes_transformed = 0
cs_opcodes_considered = 0
ss_opcodes_transformed = 0
ss_opcodes_considered = 0

total_insns_transformed = 0
total_insns_considered = 0
cs_insns_transformed = 0
cs_insns_considered = 0
ss_insns_transformed = 0
ss_insns_considered = 0

for ss_or_cs, subname, transformed, total in opcodes:
    if 'SS' == ss_or_cs:
        ss_opcodes_considered += total
        ss_opcodes_transformed += transformed
    elif 'CS' == ss_or_cs:
        cs_opcodes_considered += total
        cs_opcodes_transformed += transformed
    total_opcodes_considered += total
    total_opcodes_transformed += transformed

for ss_or_cs, subname, transformed, total in insns:
    if 'SS' == ss_or_cs:
        ss_insns_considered += total
        ss_insns_transformed += transformed
    elif 'CS' == ss_or_cs:
        cs_insns_considered += total
        cs_insns_transformed += transformed
    total_insns_considered += total
    total_insns_transformed += transformed

print("Total: transformed {} out of {} opcodes".format(total_opcodes_transformed,
                                                       total_opcodes_considered))
print("CS: transformed {} out of {} opcodes".format(cs_opcodes_transformed,
                                                    cs_opcodes_considered))
print("SS: transformed {} out of {} opcodes".format(ss_opcodes_transformed,
                                                    ss_opcodes_considered))

print("Total: transformed {} out of {} insns".format(total_insns_transformed,
                                                     total_insns_considered))
print("CS: transformed {} out of {} insns".format(cs_insns_transformed,
                                                  cs_insns_considered))
print("SS: transformed {} out of {} insns".format(ss_insns_transformed,
                                                  ss_insns_considered))
