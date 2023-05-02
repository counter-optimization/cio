import os
import re
import subprocess
from enum import Enum
import logging

logging.basicConfig(level=logging.INFO)

tempFile = "test.c"
tempObjFile = "test.o"
test = open(tempFile, "w+")
test.write("int test(){return 0;}")
test.close()

CC = os.environ["LLVM_HOME"] + "/bin/clang"

compile_cmd = f"{CC} -mllvm -x86-cs -mllvm -x86-cs-test -c {tempFile} -o {tempObjFile}"
subprocess.run(compile_cmd, shell=True, check=True)

nm_process = subprocess.run(f"nm {tempObjFile}", check=True, shell=True, text=True, stdout=subprocess.PIPE)

def is_compsimp_test_line(line):
    return "x86compsimptest" in line

def parse_nm_stdout(line):
    """
    lines of nm's stdout look like this:
    00000000004020e0 t x86compsimptest_XOR16rr_original
    00000000004020f0 t x86compsimptest_XOR16rr_transformed

    precondition: is_compsimp_test_line(line) returns True for this argument line
    returns a tuple of (function_name_str, mir_opcode_str, is_original_bool, is_transformed_bool)
    
    """
     # split on all whitespace
    v_addr, _, func_name = line.split()
    # version is one of ['original', 'transformed']
    _, mir_opcode, version = func_name.split('_')
    is_original = version == 'original'
    is_transformed = version == 'transformed'
    return (func_name, mir_opcode, is_original, is_transformed)

def generate_implementations_header(obj_file_name):
    # header_file_contents = f"
    # #ifndef IMPLEMENTATIONS_H
    # #define IMPLEMENTATIONS_H

    # {}

    # #endif // IMPLEMENTATIONS_H
    # "
    return

class OperandType(Enum):
    REG = 1
    IMM = 2
    MEM = 3

class MirOpcode():
    def __init__(self, opcode_string):
        self.string = opcode_string

        self.is_vector = False
        self.is_push = False
        self.is_implicit_first_arg = False # like MUL, IMUL, DIV, IDIV
        self.is_test = False
        self.is_cmp = False
        self.uses_memory = False
        self.uses_imm = False
        
        self.bitwidth = None
        self.opcode = None
        self.operand_info_str = None
        self.operand_types = []

        self.__parse()

    def __set_is_vector_op(self):
        """
        a vector instruction starts with V... or P... and has no bitwidth
        """
        starts_with_v = self.string[0] == 'V'
        starts_with_p = self.string[0] == 'P'
        
        has_bitwidth = False
        for letter in self.string:
            if letter.isnumeric():
                has_bitwidth = True
                
        self.is_vector = not has_bitwidth and (starts_with_p or starts_with_v)
        return self.is_vector

    def __set_is_push(self):
        self.is_push = self.string.startswith('PUSH')
        return self.is_push

    def __set_is_test(self):
        self.is_test = self.string.startswith('TEST')
        return self.is_test

    def __set_is_cmp(self):
        self.is_cmp = self.string.startswith('CMP')
        return self.is_cmp

    def __set_is_implicit_first_arg(self):
        self.is_implicit_first_arg = self.string.startswith('MUL') or \
            self.string.startswith('IMUL') or \
            self.string.startswith('DIV') or \
            self.string.startswith('IDIV')
        return self.is_implicit_first_arg

    def __find_index_of_insn_bitwidth(self):
        """
        precondition: not self.is_vector
        """
        for idx, letter in enumerate(self.string):
            if letter.isnumeric():
                return idx
        raise Exception(f"couldn't find idx of first number for opcode string: {self.string}")

    def __find_last_index_of_insn_bitwidth(self, start_idx):
        """
        precondition: not self.is_vector
        precondition: start_idx = self.__find_index_of_insn_bitwidth()
        """
        for idx, letter in enumerate(self.string[start_idx:]):
            if not letter.isnumeric():
                return start_idx + idx
        raise Exception(f"couldn't find end of insn bitwidth for opcode string: {self.string}")

    def __split_opcode_str(self):
        """
        precondition: all the __set_is_* functions already ran
        """
        if not self.is_vector:
            bitwidth_start_idx = self.__find_index_of_insn_bitwidth()
            after_bitwidth_idx = self.__find_last_index_of_insn_bitwidth(bitwidth_start_idx)
            logging.debug(f"start idx: {bitwidth_start_idx}; after_idx: {after_bitwidth_idx}")
            
            self.opcode = self.string[:bitwidth_start_idx]
            self.bitwidth = self.string[bitwidth_start_idx:after_bitwidth_idx]
            self.operand_info_str = self.string[after_bitwidth_idx:]
            logging.debug(f"all: {self.string}; opcode: {self.opcode}; bitwidth: {self.bitwidth}; operand_info: {self.operand_info_str}")
        else:
            
            pass

    def __parse_operand_info_str(self):
        imm_width = []

        last_operand_was_imm = False
        for letter in self.operand_info_str:
            if last_operand_was_imm and letter.isnumeric():
                imm_width.append(letter)
                continue
                
            if 'r' == letter:
                last_operand_was_imm = False
                self.operand_types.append(OperandType.REG)
            if 'm' == letter:
                last_operand_was_imm = False
                self.operand_types.append(OperandType.MEM)
            if 'i'  == letter:
                last_operand_was_imm = True
                self.operand_types.append(OperandType.IMM)

        if self.is_implicit_first_arg:
            # like MUL, IMUL, DIV, IDIV: dst is REG, first src is REG
            self.operand_types.insert(0, OperandType.REG)
            self.operand_types.insert(0, OperandType.REG)

        logging.debug(f"imm width was: {''.join(imm_width)}")
        
    def __parse(self):
        """
        opcode seems to be until the first number of the bitwidth for non-vector insns or
           until the first lowercase letter for vector instructions (these vector insns
           have an uppercase letter that indicates the size immediately after the opcode)
        """
        self.__set_is_vector_op()
        self.__set_is_push()
        self.__set_is_test()
        self.__set_is_cmp()
        self.__set_is_implicit_first_arg()

        if self.is_vector:
            logging.warning(f"testing of vector insns not yet implmented. skipping insn w/ opcode: {self.string}")
            return

        self.__split_opcode_str()
        self.__parse_operand_info_str()
        logging.debug(f"operand types are: {self.operand_types}")

if __name__ == '__main__':
    for line in nm_process.stdout.split('\n'):
        if not is_compsimp_test_line(line):
            continue
        
        func_name, mir_opcode, is_original, is_transformed = parse_nm_stdout(line)

        opcode = MirOpcode(mir_opcode)

        with open(tempFile + ".asm1", "w+") as asm1, open(tempFile + ".asm2", "w+") as asm2:
            subprocess.run("objdump -drwC -Mintel --no-show-raw-insn --disassemble=x86compsimptest_" + mir_opcode + f"_original {tempObjFile}", shell=True, stdout=asm1, check=True)
            subprocess.run("objdump -drwC -Mintel --no-show-raw-insn --disassemble=x86compsimptest_" + mir_opcode + f"_transformed {tempObjFile}", shell=True, stdout=asm2, check=True)
        # original = subprocess.Popen('sed "/:$/d; s/#.*$//; /^$/d; /^[a-z,A-Z]/d; s/.*\t//; /nop/d; /lea/d; /je/d; /jne/d; /jmp/d; /jae/d; /jbe/d" ' + tempFile + ".asm1", shell=True)
        # transformed = subprocess.Popen('sed "/:$/d; s/#.*$//; /^$/d; /^[a-z,A-Z]/d; s/.*\t//; /nop/d; /lea/d; /je/d; /jne/d; /jmp/d; /jae/d; /jbe/d" ' + tempFile + ".asm2", shell=True)
