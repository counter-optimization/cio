* Files

- ./llvm-test-compsimp-transforms.py : python code that drives  the
  generation of a test object file that contains functions for each
  transform implementation; there is one function containing the
  original instruction and one function containing the transformed
  instruction sequence. this also generates one fuzzer for each of
  these functions using the  fuzz harness template file
  ./implementation-tester.c 

- ./implementation-tester.c : C code that uses  LLVM's libFuzzer to
  test an implementation. this file is not compilable/runnable on its
  own, it has `REPLACE_ME' strings that
  ./llvm-test-compsimp-transforms.py replaces these `REPLACE_ME'
  strings with the contents of function prototypes (for linking with
  implementations) and test set up code. *there is  a testing ABI
  defined at the top of this file* that says how original instructions
  and transform implementations should be written (`setupTest`
  function bodies) so that they can be generically written into this
  template file. The main gist of the testing ABI is: rather than func
  arguments being RDI, RSI, RDX, RCX, R8, R9 (in that order), they
  are RSI, RDX, RCX, R8,  R9--leaving RDIoff. RDIis instead a pointer
  to  the output state of the 

* Testing ABI

*there is  a testing ABI defined at the top of the file
 ./implementation-tester.c* that says how original instructions and
 transform implementations should be written (`setupTest` function
 bodies) so that they can be generically written into this template
 file. 

The main gist of the testing ABI is: rather than func arguments being
RDI, RSI, RDX, RCX, R8, R9 (in that order), they  are RSI, RDX, RCX,
R8,  R9--leaving RDI off. RDI is instead a pointer to an output state
struct that the automatically generated test setup fills with code
after the original insn and transformed insn sequence. Instructions
should use function arguments in the order that they need
instructions. In the below ADD64mr example, it  uses RSI as its first
operand and RDX as its  second  operand. Some instructions like MUL,
IMUL, DIV, IDIV (, and  todo, PUSH/POP) need special consideration
with this testing ABI, and they are special cased in
`./llvm-test-compsimp-transforms.py`. 

* Adding new instructions for fuzz testing

1. Add  the MIR opcode to one of the vector of MIR opcode strings in
the function `InsertCompSimpTestFunctions::readIntoList` in the file
`<LLVM-PROJECT>/llvm/lib/Transforms/Scalar/InsertCompSimpTestFunctions.cpp`. This
is used for both silent stores and computation simplification. 

2. Add code to replace the RET64 instruction in the test functions
inthe `setupTest` function in either
`~/llvm-project/llvm/lib/Target/X86/X86CompSimpHardening.cpp` or
`~/llvm-project/llvm/lib/Target/X86/X86SilentStoreHardening.cpp`.
This looks like adding some code like this for e.g., adding ADD64mr to
the silent store test generator: 

```
	if (Op == "ADD64mr") {
	  changedOpcode = X86::ADD64mr;
	  BuildMI(*MBB, &MI, DL, TII->get(X86::ADD64mr), X86::RSI)
	    .addImm(1)
	    .addReg(0)
	    .addImm(0)
	    .addReg(0)
	    .addReg(X86::RDX);
	}
```

3. If the opcode is special like PUSH64 or CMP64mr, then it will need
special casing in the  fuzzer harness generator:
llvm-test-compsimp-transforms.py. You will probably need to edit the
function `generate_finalized_code_for_opcode` and maybe even the
fuzzer harness template file `implementation-tester.c`. 


