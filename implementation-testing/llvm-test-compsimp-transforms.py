import os
import re
import subprocess
import argparse
import sys 
from enum import Enum
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)

argparser = argparse.ArgumentParser('generate test harnesses')

argparser.add_argument('--record-cycle-counts',
                       default=False, type=bool)
argparser.add_argument('test_dir')

# some commented out. always an overapprox
# since the BAP IR contains no info
# e.g., about LEA, so heuristics have to be
# used, and it's not worth tuning to all
# of these
sets_flags = {
    "ADD64rm": ['CF'],
    "ADD64rr": ['CF'],
    "AND64rr": ['CF'],
    "XOR64rm": ['CF'],
    "XOR64rr": ['CF'],
    "CMP64rm": ['ZF'],
    "CMP32rm": ['CF'],
    "CMP32rr": ['CF'],
    "ADD64mr": ['CF'],
    "ADD32mi8": ['ZF'],
    "ADD32ri8": ['CF', 'ZF'],
    "ADD64ri8": ['ZF'],
    "AND64ri8": ['ZF'],
    "CMP64rr": ['CF', 'ZF'],
    "TEST8ri": ['ZF'],
    "XOR32rm": ['CF'],
    "XOR32rr": ['CF'],
    "CMP64mr": ['CF', 'ZF'],
    "TEST8mi": ['ZF'],
    "TEST8i8": ['ZF'],
    "ADD64mi32": ['CF'],
    "SUB64rr": ['CF', 'ZF'],
    "OR64rr": ['ZF'],
    "IMUL64rr": ['CF'],
    "AND32ri8": ['ZF'],
}

# this is really "flags live in", so some commented out
# that don't need to preserve
preserves_flags = {
    'LEA64r': ['CF'],
    "MOV64mr": ['ZF', 'CF'],
    # "ROL64ri": ['CF'],
    # "ROR64r1": ['CF'],
    # "SHR64ri": ['ZF'],
    # "ROL64r1": ['CF'],
    "MOV32mi": ['ZF'],
    # "ADC32ri8": ['CF'],
    # "ROL32ri": ['CF'],
    "MOV32mr": ['CF', 'ZF'],
    "MOVDQAmr": ['ZF'],
    # "ADC64mi8": ['CF'],
    # "ADC64mr": ['CF'],
    # "SBB32rr": ['CF'],
    # "ADC64ri8": ['CF'],
    # "ADC64rm": ['CF'],
    # "ADC64rr": ['CF'],
    # "SBB32ri8": ['CF']    
}

def flag(name):
    """
    indices of the flag name str correspond to C enum values
    of enum EFLAGS in ./implementation-tester.c
    """
    flags_at_indices_of_enum_val = [None, 'SF', 'ZF', 'AF', 'PF', 'CF']
    return flags_at_indices_of_enum_val.index(name)

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
    x86silentstorestest_MOV8mr_NOREX_original
    x86silentstorestest_LEA64_32r_original
    but these are special cased
    """
     # split on all whitespace
    v_addr, _, func_name = line.split()
    
    # version is one of ['original', 'transformed']
    if "NOREX" in func_name:
        testtype, mir_opcode, dontcare, version = func_name.split('_')
        mir_opcode = mir_opcode + '_NOREX'
    elif "LEA64_32r" in func_name:
        testtype, mir_opcode, dontcare, version = func_name.split('_')
        mir_opcode = mir_opcode + '_32r'
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

        self.preserve_flags = None
        self.set_flags = None
        
        self.bitwidth = None
        self.opcode = None
        self.operand_info_str = None
        self.operand_types = []

        self.__parse()
        self.__set_sets_flags()
        self.__set_preserves_flags()

    def must_preserve_flags(self):
        return self.preserve_flags is not None

    def must_set_flags(self):
        return self.set_flags is not None

    def __set_sets_flags(self):
        """
        precondition: self.string already set
        """
        if self.string in sets_flags:
            flags_need_to_be_set = sets_flags[self.string]
            self.set_flags = list(map(flag, flags_need_to_be_set))

    def __set_preserves_flags(self):
        """
        precondition: self.string already set
        """
        if self.string in preserves_flags:
            flags_preserved = preserves_flags[self.string]
            self.preserve_flags = list(map(flag, flags_preserved))

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
            # find first lower case letter
            idx_start_operand_types = None
            for idx, letter in enumerate(self.string):
                if letter.islower():
                    idx_start_operand_types = idx
                    break
                
            if idx_start_operand_types is None:
                logging.critical(f"couldnt parse vector MIR opcode string: {self.string}")
                
            self.opcode = self.string[:idx_start_operand_types]
            self.operand_info_str = self.string[idx_start_operand_types:]
            logging.debug(f"all: {self.string}; opcode: {self.opcode}; bitwidth: ?; operand_info: {self.operand_info_str}")
                

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

        self.__split_opcode_str()

        self.__set_depends_on_carry_flag()
        
        self.__parse_operand_info_str()
        
        logging.debug(f"operand types are: {self.operand_types}")

def read_test_harness_template(filename):
    with open(filename, "r") as f:
        return f.read()

def generate_finalized_code_for_opcode(opcode_str, file_contents, orig_sym_name, trans_sym_name):
    opcode = MirOpcode(opcode_str)

    prototypes = [
        f"void {orig_sym_name}(struct OutState* outstate, uint64_t i0, uint64_t i1, uint64_t i2, uint64_t i3, uint64_t i4);",
        f"void {trans_sym_name}(struct OutState* outstate, uint64_t i0, uint64_t i1, uint64_t i2, uint64_t i3, uint64_t i4);"
    ]
    prototypes_str = "\n".join(prototypes)

    operand_types = list(map(lambda optype: str(optype), opcode.operand_types))
    operand_types_str = ", ".join(operand_types)
    operand_types_defines_str = "const char* operand_types[5] = { " + operand_types_str + " };"

    preserve_flags_str = "int must_preserve_flags = 0;\n" + \
        "enum EFLAGS preserves[5] = {0};\n"
    if opcode.must_preserve_flags():
        preserve_flags_str = "int must_preserve_flags = 1;\n"
        flags_str = ", ".join(map(str, opcode.preserve_flags))
        preserve_flags_str += "enum EFLAGS preserves[5] = {" + flags_str + ", 0, };\n"

    set_flags_str = "int must_set_flags = 0;\n" + \
        "enum EFLAGS sets[5] = {0};\n"
    if opcode.must_set_flags():
        set_flags_str = "int must_set_flags = 1;\n"
        flags_str = ", ".join(map(str, opcode.set_flags))
        set_flags_str += "enum EFLAGS sets[5] = {" + flags_str + ", 0, };\n"

    is_vector_op_str = f"int is_vector = {1 if opcode.is_vector else 0};"

    all_filler_code = preserve_flags_str + '\n' + \
        set_flags_str + '\n' + \
        prototypes_str + '\n' + \
        operand_types_defines_str + '\n' + \
        is_vector_op_str + '\n'

    file_contents = file_contents.replace("AUTOMATICALLY_REPLACE_ME_PROTOTYPES",
                                          all_filler_code)

    # use last arg (r9) as implicit arg value in rax
    orig_set_eax_for_implicit_calls = """\
                __asm__ __inline__ __volatile__(
			"movq %[arg4], %%rax"
			:
			: [arg4] "rm" (orig_arg4)
			: "rax"
		);
    """

    trans_set_eax_for_implicit_calls = """\
                __asm__ __inline__ __volatile__(
			"movq %[arg4], %%rax"
			:
			: [arg4] "rm" (trans_arg4)
			: "rax"
		);
    """

    set_eflags = """\
    __asm__ __inline__ __volatile__(
                "movq %%rax, %[rax_save]\\r\\n"
		"movq %[lahf_load], %%rax\\r\\n"
		"sahf\\r\\n"
                "movq %[rax_save], %%rax\\r\\n"
		:
		: [lahf_load] "rm" (lahf_load),
                  [rax_save] "rm" (rax_save)
		: "rax", "cc" );
    """

    orig_calls = [
        orig_set_eax_for_implicit_calls if opcode.is_implicit_first_arg else "\n",
        set_eflags + "\n"
        f"{orig_sym_name}(&original_state, orig_arg0, orig_arg1, orig_arg2, orig_arg3, orig_arg4);\n"
    ]
    
    trans_calls = [
        trans_set_eax_for_implicit_calls if opcode.is_implicit_first_arg else "\n",
        set_eflags + "\n"
        f"{trans_sym_name}(&transformed_state, trans_arg0, trans_arg1, trans_arg2, trans_arg3, trans_arg4);\n",
    ]
    
    file_contents = file_contents.replace("AUTOMATICALLY_REPLACE_ME_ORIG_CALLS",
                                          "".join(orig_calls))

    file_contents = file_contents.replace("AUTOMATICALLY_REPLACE_ME_TRANS_CALLS",
                                          "".join(trans_calls))
    
    return file_contents

if __name__ == '__main__':
    args = argparser.parse_args()
    
    # if len(sys.argv) != 2:
    #     print(f"usage: LLVM_HOME=/path/to/dir/holding/clang python3 this_file.py <dir_to_put_test_files>")
    #     sys.exit(1)

    # test_dir = Path(sys.argv[1])

    test_dir = Path(args.test_dir)
    
    if not test_dir.exists():
        test_dir.mkdir()
        
    tempFile = "test.c"
    tempObjFile = "test.o"
    test = open(tempFile, "w+")
    test.write("int test(){return 0;}")
    test.close()

    CC = os.environ["LLVM_HOME"] + "/bin/clang"

    cc_optional_flags = "-mllvm -x86-cs-test-cycle-counts" if args.record_cycle_counts else ""

    compile_cmd = f"{CC} -O0 -mllvm -x86-ss -mllvm -x86-cs -mllvm -x86-cs-test {cc_optional_flags} -c {tempFile} -o {tempObjFile}"
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
