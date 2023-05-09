import os
import re
import subprocess
import sys 
from enum import Enum
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

def is_duplicate_fn_def(symname):
    if "." in symname:
        logging.critical(f"symbol name {symname} is duplicate, not generating tests for it")
        return True
    return False

def is_test_fn_line(line):
    return "x86compsimptest" in line or \
        "x86silentstorestest" in line

def parse_nm_stdout(line):
    """
    lines of nm's stdout look like this:
    00000000004020e0 t x86compsimptest_XOR16rr_original
    00000000004020f0 t x86compsimptest_XOR16rr_transformed
    OR
    0000000000005a50 T x86silentstorestest_ADD64mr_original
    0000000000005a60 T x86silentstorestest_ADD64mr_transformed

    precondition: is_test_fn_line(line) returns True for this argument line
    returns a tuple of (function_name_str, mir_opcode_str, is_cs, is_ss, s_original_bool, is_transformed_bool)

    some functions have names like 
    x86silentstorestest_MOV8mr_NOREX_original, but these
    are special cased
    
    """
     # split on all whitespace
    v_addr, _, func_name = line.split()
    
    # version is one of ['original', 'transformed']
    if "NOREX" in func_name:
        testtype, mir_opcode, dontcare, version = func_name.split('_')
        mir_opcode = mir_opcode + '_NOREX'
    else:
        testtype, mir_opcode, version = func_name.split('_')

    is_ss = "silentstorestest" in testtype
    is_cs = "compsimptest" in testtype
    
    is_original = version == 'original'
    is_transformed = version == 'transformed'
    
    return (func_name, mir_opcode, is_cs, is_ss, is_original, is_transformed)

class OperandType(Enum):
    UNDEF = 0
    REG = 1
    IMM = 2
    MEM = 3
    def __str__(self):
        if self.name == "UNDEF":
            return "0"
        else:
            return f"\"{self.name}\""

class MirOpcode():
    def __init__(self, opcode_string):
        self.string = opcode_string

        self.is_vector = False
        self.is_push = False
        self.is_implicit_first_arg = False # like MUL, IMUL, DIV, IDIV
        self.is_test = False
        self.is_cmp = False
        self.depends_on_carry_flag = False
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

    def __handle_IMUL_special_case(self):
        """
        special casing for IMUL which can be implicit or explicit
        depending on operand types

        precondition: self.__set_is_implicit_first_arg() already ran
        
        to be called in self.__parse_operand_info_str()
        """
        if "IMUL" in self.string:
            self.is_implicit_first_arg = 1 == len(self.operand_types)

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
            # this prints twice currently, but leaving it in just in case it isn't fixed in both places
            logging.warning(f"testing of vector insns not yet implmented. skipping insn w/ opcode: {self.string}")
            pass

    def __set_depends_on_carry_flag(self):
        """
        precondition: self.__split_opcode_str() already ran
        """
        self.depends_on_carry_flag = self.opcode == "SBB" or self.opcode == "ADC"
        return self.depends_on_carry_flag

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

        self.__handle_IMUL_special_case()

        if self.is_implicit_first_arg:
            # like MUL, IMUL (conditionally),
            # DIV, IDIV: dst is REG, first src is REG
            self.operand_types.insert(0, OperandType.REG)
            self.operand_types.insert(0, OperandType.REG)

        while len(self.operand_types) < 5:
            self.operand_types.append(OperandType.UNDEF)
        
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

        self.__set_depends_on_carry_flag()
        
        self.__parse_operand_info_str()
        
        logging.debug(f"operand types are: {self.operand_types}")

def read_test_harness_template(filename):
    with open(filename, "r") as f:
        return f.read()

def generate_finalized_code_for_opcode(opcode_str, file_contents, orig_sym_name, trans_sym_name):
    opcode = MirOpcode(opcode_str)

    if opcode.is_vector:
        logging.warning(f"skipping generating fuzzer test harnesses for unsupported vector insn: {opcode.string}")
        return None

    prototypes = [
        f"void {orig_sym_name}(struct OutState* outstate, uint64_t i0, uint64_t i1, uint64_t i2, uint64_t i3, uint64_t i4);",
        f"void {trans_sym_name}(struct OutState* outstate, uint64_t i0, uint64_t i1, uint64_t i2, uint64_t i3, uint64_t i4);"
    ]
    prototypes_str = "\n".join(prototypes)

    operand_types = list(map(lambda optype: str(optype), opcode.operand_types))
    operand_types_str = ", ".join(operand_types)
    operand_types_defines_str = "const char* operand_types[5] = { " + operand_types_str + " };"

    all_filler_code = prototypes_str + '\n' + operand_types_defines_str + '\n'

    file_contents = file_contents.replace("AUTOMATICALLY_REPLACE_ME_PROTOTYPES",
                                          all_filler_code)

    # use last arg (r9) as implicit arg value in rax
    orig_set_eax_for_implicit_calls = """\
                __asm__ inline volatile(
			"movq %[arg4], %%rax"
			:
			: [arg4] "rm" (orig_arg4)
			: "rax"
		);
    """

    trans_set_eax_for_implicit_calls = """\
                __asm__ inline volatile(
			"movq %[arg4], %%rax"
			:
			: [arg4] "rm" (trans_arg4)
			: "rax"
		);
    """

    # like ADC, SBB
    # compare last arg (r9) to 10,000 to randomly set CF
    orig_set_cf_for_dependent_insns = """\
    __asm__ inline volatile(
        "cmpq $1000, %[arg4]"
        : 
        : [arg4] "rm" (orig_arg4)
        : 
    );
    """

    trans_set_cf_for_dependent_insns = """\
    __asm__ inline volatile(
        "cmpq $1000, %[arg4]"
        : 
        : [arg4] "rm" (trans_arg4)
        : 
    );
    """

    calls = [
        orig_set_eax_for_implicit_calls if opcode.is_implicit_first_arg else "\n",
        orig_set_cf_for_dependent_insns if opcode.depends_on_carry_flag else "\n",
        f"{orig_sym_name}(&original_state, orig_arg0, orig_arg1, orig_arg2, orig_arg3, orig_arg4);\n",
        trans_set_eax_for_implicit_calls if opcode.is_implicit_first_arg else "\n",
        trans_set_cf_for_dependent_insns if opcode.depends_on_carry_flag else "\n",
        f"{trans_sym_name}(&transformed_state, trans_arg0, trans_arg1, trans_arg2, trans_arg3, trans_arg4);\n",
    ]
    calls_str = "".join(calls)

    file_contents = file_contents.replace("AUTOMATICALLY_REPLACE_ME_CALLS",
                                          calls_str)
    
    return file_contents

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"usage: LLVM_HOME=/path/to/dir/holding/clang python3 this_file.py <dir_to_put_test_files>")
        sys.exit(1)

    test_dir = Path(sys.argv[1])
    if not test_dir.exists():
        test_dir.mkdir()
        
    tempFile = "test.c"
    tempObjFile = "test.o"
    test = open(tempFile, "w+")
    test.write("int test(){return 0;}")
    test.close()

    CC = os.environ["LLVM_HOME"] + "/bin/clang"

    compile_cmd = f"{CC} -O0 -mllvm -x86-ss -mllvm -x86-cs -mllvm -x86-cs-test -c {tempFile} -o {tempObjFile}"
    subprocess.run(compile_cmd, shell=True, check=True)

    nm_process = subprocess.run(f"nm {tempObjFile}", check=True, shell=True, text=True, stdout=subprocess.PIPE)

    test_harness_template_filename = "implementation-tester.c"
    test_harness_template_file_contents = read_test_harness_template(test_harness_template_filename)
    
    for line in nm_process.stdout.split('\n'):
        # this will see each *_original and *_transformed pair. just do this
        # once for each pair by skipping processing the *_transformed string
        if not is_test_fn_line(line) or "_transformed" in line:
            continue
        
        func_name, mir_opcode, is_cs, is_ss, is_original, is_transformed = parse_nm_stdout(line)

        if is_duplicate_fn_def(func_name):
            continue

        original_symbol_name = func_name
        transformed_symbol_name = original_symbol_name.replace("original", "transformed")

        final_code = generate_finalized_code_for_opcode(
            mir_opcode,
            test_harness_template_file_contents,
            original_symbol_name,
            transformed_symbol_name
        )

        if final_code is None:
            continue

        test_type = "cs" if is_cs else "ss"
        new_file_name = f"{str(test_dir)}/{test_type}-{mir_opcode}-{test_harness_template_filename}"
        
        if Path(new_file_name).exists():
            Path(new_file_name).unlink()
            
        with open(new_file_name, "w") as testfile:
            testfile.write(final_code)
