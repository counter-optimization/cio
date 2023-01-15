#!/usr/bin/python
from typing import List
import sys
import os
import logging
import subprocess
from pathlib import Path
import tempfile

"""
Usage:

CC=ciocc.py


This doesn't use argparse, the passthrough and capture of select args
seems hard to implement using argparse compared to substring search
as used here.

from reshabh:
clang -mllvm --x86-ss -mllvm --x86-cs
"""

logfile = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".ciocc.log")

logging.basicConfig(# filename=logfile.name,
                    # filemode="w",
                    level=logging.DEBUG,
                    format="CIOCC:%(module)s:%(levelname)s:%(message)s")

print(f"CIOCC:logging to: {logfile.name}", file=sys.stderr)

l = logging
# l = logging.getLogger("sac-llvm")
# l.setLevel(logging.DEBUG)

# clang_path = Path("~/repos/llvm-project/build/bin/clang").expanduser()
# llc_path = Path("~/repos/llvm-project/build/bin/llc").expanduser()
clang_path = Path("clang").expanduser()
llc_path = Path("llc").expanduser()
checker_plugin_path = Path("~/checker/bap/interval/").expanduser()
clang = str(clang_path)
llc = str(llc_path)

checker_argv = f"bap --plugin-path={checker_plugin_path} --pass=uarch-checker --no-optimization --bil-optimization=0".split()

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

        self.__secrets_csv_file_suffix = '.secrets.csv'
        self.__checker_results_csv_file_suffix = '.checker.results.csv'

        self.__silent_stores_flag = '--harden-silent-stores'
        self.__comp_simp_flag = '--harden-comp-simp'

    def __should_harden_silent_stores(self) -> bool:
        return self.__silent_stores_flag in self.__args

    def __should_harden_comp_simp(self) -> bool:
        return self.__comp_simp_flag in self.__args

    def __is_generating_obj(self) -> bool:
        return self.__gen_obj_flag in self.__args

    def __get_target_file_name(self) -> str:
        """
        look for the -o compiler flag. the target output file's name
        should follow as the next argument, so return that. the code
        assumes this is an object file with the (.o) extension
        """
        if not self.__target_file_flag in self.__args:
            # raise SacLLVMParseError("couldn't find '%s' flag in CL args" % self.__target_file_flag)
            logging.critical("couldn't find '%s' flag in CL args" % self.__target_file_flag)

        flag_idx = self.__args.index(self.__target_file_flag)
        target_file_name = self.__args[flag_idx + 1]
        l.debug("Target file name is %s" % target_file_name)

        if not '.o' in target_file_name:
            err_msg = f".o not in target file name, {target_file_name}, this command is not supported yet"
            l.critical(err_msg)
            # raise SacLLVMNotSupportedException(err_msg)

        return target_file_name

    def __get_target_for_ll_gen(self) -> str:
        """
        gets the file following the -o compiler flag and
        changes its file extension to self.__ll_file_suffix ('.ll')
        """
        target_file_name = self.__get_target_file_name()
        target_file_base = target_file_name.removesuffix(self.__obj_file_suffix)
        return target_file_base + self.__ll_file_suffix

    def __get_target_for_mir_gen(self) -> str:
        """
        gets the file following the -o compiler flag and
        changes its file extension to self.__mir_file_suffix ('.mir')
        """
        target_file_name = self.__get_target_file_name()
        target_file_base = target_file_name.removesuffix(self.__obj_file_suffix) 
        return target_file_base + self.__mir_file_suffix

    def __get_source_file_name(self) -> str:
        source_files = []
        for arg in self.__args:
            for suffix in self.__source_file_name_suffixes:
                if suffix in arg:
                    source_files.append(arg)
        
        if len(source_files) == 0:
            error_msg = f"Couldn't find source file name with prefixes: {self.__source_file_name_suffixes}"
            logging.debug(error_msg)
            # raise SacLLVMParseError(error_msg)
        elif len(source_files) > 1:
            error_msg = f"This command compiles more than one source file: {source_files}"
            logging.debug(error_msg)
            # SacLLVMNotSupportedException(error_msg)
        else:
            return source_files[0]

    def __run_and_check_cmd(self, cmd: List[str]):
        try:
            subprocess.run(cmd, timeout=60, check=True, env=os.environ)
        except subprocess.CalledProcessError as ex:
            err_msg = "error running compiler cmd: %s" % cmd
            logging.critical(err_msg)
            raise SacLLVMCommandRunError(err_msg)

    def should_handle_command_line(self) -> bool:
        # for now, just need to get full passthrough working
        # for ./configure CC=/path/to/ciocc && make && make check
        # for libsodium
        return False
        # self.__gen_obj_flag = '-c'
        # self.__target_file_flag = '-o'
        # return self.__gen_obj_flag in self.__args and \
        #     self.__target_file_flag in self.__args
    
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

    def get_name_of_secrets_csv_dump(self) -> str:
        """
        file.o -> file.secrets.csv
        """
        obj_file_name = self.__get_target_file_name()
        obj_file_base = obj_file_name.removesuffix(self.__obj_file_suffix) 
        return obj_file_base + self.__secrets_csv_file_suffix

    def get_name_of_checker_results_csv_dump(self) -> str:
        """
        file.o -> file.checker.results.csv
        """
        obj_file_name = self.__get_target_file_name()
        obj_file_base = obj_file_name.removesuffix(self.__obj_file_suffix) 
        return obj_file_base + self.__checker_results_csv_file_suffix

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

    def __run_cmd(self, cmd: List[str]):
        try:
            # we don't have smart arg parsing, so gotta put this back
            # together since e.g., "blah blah" will not be handled as
            # one arg when used as a list (a list that was generated by
            # splitting on space)
            cmd_as_single_str = ' '.join(cmd)
            logging.debug(f"cmd as single string is: {cmd_as_single_str}")
            subprocess.run(cmd, shell=True, timeout=60, env=os.environ)
        except subprocess.TimeoutExpired as ex:
            err_msg = f"timeout running cmd: {cmd}"
            logging.critical(err_msg)
            raise SacLLVMCommandRunError(err_msg)

    def passthrough_cmd(self):
        cmd = self.build_orig_cmd()
        logging.debug(f"passing through non-relevant command: {cmd}")
        self.__run_cmd(cmd)

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

    if cmd.should_handle_command_line():
        logging.debug(f"intercepting command line: {cl}")
        args = cmd.get_passthrough_args_for_ll_gen()
        logging.debug("pass through args are %s" % args)

        mir_gen_cmd = cmd.build_mir_gen_cmd()
        logging.debug("ll_gen_cmd is %s" % mir_gen_cmd)
        cmd.run_mir_gen_cmd()

        cmd.run_orig_cmd()
    else:
        cmd.passthrough_cmd()
