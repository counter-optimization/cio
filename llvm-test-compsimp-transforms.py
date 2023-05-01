import os
import re
import subprocess

tempFile = "test.c"
test = open(tempFile, "w+")
test.write("int main(){return 0;}")
test.close()

CC = os.environ["LLVM_HOME"] + "/bin/clang"

subprocess.run(CC + " -mllvm -x86-cs -mllvm -x86-cs-test " + tempFile, shell=True, check=True)

nm_process = subprocess.run("nm a.out", check=True, shell=True, text=True, stdout=subprocess.PIPE)

def is_compsimp_test_line(line):
    return "x86compsimptest" in line

def parse_nm_stdout(line):
    """
    lines of nm's stdout look like this:
    00000000004020e0 t x86compsimptest-XOR16rr-original
    00000000004020f0 t x86compsimptest-XOR16rr-transformed

    precondition: is_compsimp_test_line(line) returns True for this argument line
    returns a tuple of (function_name_str, mir_opcode_str, is_original_bool, is_transformed_bool)
    
    """
     # split on all whitespace
    v_addr, _, func_name = line.split()
    # version is one of ['original', 'transformed']
    _, mir_opcode, version = func_name.split('-')
    is_original = version == 'original'
    is_transformed = version == 'transformed'
    return (func_name, mir_opcode, is_original, is_transformed)
    
for line in nm_process.stdout.split('\n'):
    if not is_compsimp_test_line(line):
        continue
    func_name, mir_opcode, is_original, is_transformed = parse_nm_stdout(line)

    with open(tempFile + ".asm1", "w+") as asm1, open(tempFile + ".asm2", "w+") as asm2:
        subprocess.run("objdump -drwC -Mintel --no-show-raw-insn --disassemble=x86compsimptest-" + mir_opcode + "-original a.out", shell=True, stdout=asm1, check=True)
        subprocess.run("objdump -drwC -Mintel --no-show-raw-insn --disassemble=x86compsimptest-" + mir_opcode + "-transformed a.out", shell=True, stdout=asm2, check=True)
            # original = subprocess.Popen('sed "/:$/d; s/#.*$//; /^$/d; /^[a-z,A-Z]/d; s/.*\t//; /nop/d; /lea/d; /je/d; /jne/d; /jmp/d; /jae/d; /jbe/d" ' + tempFile + ".asm1", shell=True)
            # transformed = subprocess.Popen('sed "/:$/d; s/#.*$//; /^$/d; /^[a-z,A-Z]/d; s/.*\t//; /nop/d; /lea/d; /je/d; /jne/d; /jmp/d; /jae/d; /jbe/d" ' + tempFile + ".asm2", shell=True)
