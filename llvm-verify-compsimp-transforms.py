import os
import re
import subprocess

tempFile = "/tmp/_425427_test.c"
test = open(tempFile, "w+")

test.write("int main(){return 0;}")
test.close()

CC = os.environ["LLVM_HOME"] + "/bin/clang"
subprocess.Popen(CC + " -mllvm -x86-cs -mllvm -x86-cs-test " + tempFile, shell=True)
proc = subprocess.Popen("nm a.out", shell=True, stdout=subprocess.PIPE)
for line in proc.stdout:
    function = line.decode().split(' ')[2]
    function = re.findall(r".*-original$", function)
    if function:
        inst = function[0].split('-')[1]
        with open(tempFile + ".asm1", "w+") as asm1, open(tempFile + ".asm2", "w+") as asm2:
            subprocess.Popen("objdump -drwC -Mintel --no-show-raw-insn --disassemble=x86compsimptest-" + inst + "-original a.out", shell=True, stdout=asm1)
            subprocess.Popen("objdump -drwC -Mintel --no-show-raw-insn --disassemble=x86compsimptest-" + inst + "-transformed a.out", shell=True, stdout=asm2)
            # original = subprocess.Popen('sed "/:$/d; s/#.*$//; /^$/d; /^[a-z,A-Z]/d; s/.*\t//; /nop/d; /lea/d; /je/d; /jne/d; /jmp/d; /jae/d; /jbe/d" ' + tempFile + ".asm1", shell=True)
            # transformed = subprocess.Popen('sed "/:$/d; s/#.*$//; /^$/d; /^[a-z,A-Z]/d; s/.*\t//; /nop/d; /lea/d; /je/d; /jne/d; /jmp/d; /jae/d; /jbe/d" ' + tempFile + ".asm2", shell=True)
