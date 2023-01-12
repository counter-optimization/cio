from typing import List
import sys
import os
import logging
import subprocess
from pathlib import Path

l = logging.getLogger("sac-llvm")
l.setLevel(logging.DEBUG)

# clang_path = Path("~/repos/llvm-project/build/bin/clang").expanduser()
# llc_path = Path("~/repos/llvm-project/build/bin/llc").expanduser()
clang_path = Path("clang").expanduser()
llc_path = Path("llc").expanduser()
# assert(clang_path.exists())
# assert(llc_path.exists())
clang = str(clang_path)
llc = str(llc_path)
checker_argv = "bap --plugin-path=. --pass=cfg --no-optimization --bil-optimization=0".split()

class Command():
    def __init__(self, cmd: str):
        self.__cmd = cmd
        self.__args = cmd.split()
        
        self.__gen_obj_flag = '-c'
        self.__target_file_flag = '-o'
        
        self.__obj_file_suffix = '.o'
        self.__ll_file_suffix = '.ll'
        self.__mir_file_suffix = '.mir'
        self.__source_file_name_suffixes = ['.c']

        self.__silent_stores_flag = '--harden-silent-stores'
        self.__comp_simp_flag = '--harden-comp-simp'
        self.__dmp_flag = '--harden-dmp'

    def __should_harden_silent_stores(self) -> bool:
        return self.__silent_stores_flag in self.__args

    def __should_harden_comp_simp(self) -> bool:
        return self.__comp_simp_flag in self.__args

    def __should_harden_dmp(self) -> bool:
        return self.__dmp_flag in self.__args
        
    def __is_generating_obj(self) -> bool:
        return self.__gen_obj_flag in self.__args

    def __get_target_file_name(self) -> str:
        if not self.__target_file_flag in self.__args:
            raise SacLLVMParseError("couldn't find '%s' flag in CL args" % self.__target_file_flag)

        flag_idx = self.__args.index(self.__target_file_flag)
        target_file_name = self.__args[flag_idx + 1]
        l.debug("Target file name is %s" % target_file_name)

        if not '.o' in target_file_name:
            err_msg = ".o not in target file name, this command is not supported yet"
            l.critical(err_msg)
            raise SacLLVMNotSupportedException(err_msg)

        return target_file_name

    def __get_target_for_ll_gen(self) -> str:
        target_file_name = self.__get_target_file_name()
        target_file_base = target_file_name.removesuffix(self.__obj_file_suffix)
        return target_file_base + self.__ll_file_suffix

    def __get_target_for_mir_gen(self) -> str:
        target_file_name = self.__get_target_file_name()
        target_file_base = target_file_name.removesuffix(self.__obj_file_suffix)
        return target_file_base + self.__mir_file_suffix

    def __get_source_file_name(self) -> str:
        for arg in self.__args:
            for suffix in self.__source_file_name_suffixes:
                if suffix in arg:
                    return arg
        error_msg = "Couldn't find source file name with prefixes: %s" % self.__source_file_name_suffixes 
        raise SacLLVMParseError(error_msg)

    def __run_and_check_cmd(self, cmd: List[str]):
        try:
            subprocess.run(cmd, timeout=60, check=True, env=os.environ)
        except subprocess.CalledProcessError as ex:
            err_msg = "error running compiler cmd: %s" % cmd
            l.critical(err_msg)
            raise SacLLVMCommandRunError(err_msg)

    def get_passthrough_args_for_ll_gen(self) -> List[str]:
        # don't pass through the -c -o args or their targets
        filter_out = []
        filter_out.append(self.__get_source_file_name())
        filter_out.append(self.__get_target_file_name())
        filter_out.append(self.__gen_obj_flag)
        filter_out.append(self.__target_file_flag)

        args = list(filter(lambda arg: arg not in filter_out, self.__args))
        l.debug("passthrough args: %s" % args)
        return args

    def build_ll_gen_cmd(self) -> List[str]:
        cmd = []
        cmd.append(clang)
        
        cmd.extend(self.get_passthrough_args_for_ll_gen())

        cmd.append('-S')
        cmd.append('-emit-llvm')

        cmd.append('-c')
        cmd.append(self.__get_source_file_name())

        cmd.append(self.__target_file_flag)
        target_file = self.__get_target_for_ll_gen()
        l.debug("target file is %s" % target_file)
        cmd.append(target_file)

        return cmd

    def build_mir_gen_cmd(self) -> List[str]:
        cmd = []
        cmd.append(clang)

        cmd.extend(self.get_passthrough_args_for_ll_gen())

        cmd.append('-mllvm')
        cmd.append('-stop-after=x86-fixup-LEAs')

        cmd.append('-c')
        cmd.append(self.__get_source_file_name())

        cmd.append(self.__target_file_flag)
        target_file = self.__get_target_for_mir_gen()
        l.debug("target file is %s" % target_file)
        cmd.append(target_file)

        return cmd

    def build_orig_cmd(self) -> List[str]:
        cmd = []
        cmd.append(clang)
        cmd.extend(self.__args)
        return cmd

    def run_ll_gen_cmd(self):
        cmd = self.build_ll_gen_cmd()
        self.__run_and_check_cmd(cmd)

    def run_mir_gen_cmd(self):
        cmd = self.build_mir_gen_cmd()
        self.__run_and_check_cmd(cmd)

    def run_orig_cmd(self):
        cmd = self.build_orig_cmd()
        self.__run_and_check_cmd(cmd)

class SacLLVMNotSupportedException(Exception):
    pass

class SacLLVMParseError(Exception):
    pass

class SacLLVMCommandRunError(Exception):
    pass

if __name__ == '__main__':
    cl = " ".join(sys.argv[1:])
    l.debug("cl is %s" % cl)

    cmd = Command(cl)
    args = cmd.get_passthrough_args_for_ll_gen()
    l.debug("pass through args are %s" % args)

    mir_gen_cmd = cmd.build_mir_gen_cmd()
    l.debug("ll_gen_cmd is %s" % mir_gen_cmd)
    cmd.run_mir_gen_cmd()

    cmd.run_orig_cmd()
