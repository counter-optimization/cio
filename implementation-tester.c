#include <stdint.h>
#include <stdio.h>
#include <assert.h>
#include <inttypes.h>

/* OUR TESTING ABI

   1. Input states

   no instructions should use more than 5 registers,
   so the registers an operand uses are assigned in order of the arguments
   into a function: 
   RSI, RDX, RCX, R8, R9
   or ... for vector instructions

   the first argument RDI normally used in AMD64 systemV ABI is reserved for 
   the functions to save output state into. see section 2 below for more on this.

   so the original function for ADD64rr using intel notation (dest reg first):
   x86compsimptesting-ADD64rr-original:
      add rsi, rdx
      ...
      ret

   the transformed version of this instruction is in function:
   x86compsimptesting-ADD64rr-transformed:
      <`add rsi, rdx`'s transform sequence>
      ...
      ret

   likewise, the original function for SHR8rCL is:
   x86compsimptesting-SHR8rCL-original:
      shl    sil, cl
      ret

   and for IMUL32rm:
   x86compsimptesting-IMUL32rm-original:
      imul   esi, edx
      ret
   
   2. Output states

   since none of these functions use more than 5 registers, we use the first
   argument RDI as a pointer to 624 bytes of memory to hold the CPU output state.

   this resulting CPU state is what is checked for semantic equivalence.
   currently, this code does not test the results of FLAGS out of the instruction
   or transform.
   so the original function for ADD64rr is actually (not eliding with dots):

   x86compsimptesting-ADD64rr-original:
      add rsi, rdx
      mov %[rdi+8], rax
      mov %[rdi+16], rbx
      mov %[rdi+24], rcx
      mov %[rdi+32], rcx
      mov %[rdi+40], rdx
      mov %[rdi+48], rsp
      mov %[rdi+56], rbp
      mov %[rdi+64], rsi
      mov %[rdi+72], rdi
      mov %[rdi+80], r8
      mov %[rdi+88], r9
      mov %[rdi+96], r10
      mov %[rdi+104], r11
      mov %[rdi+112], r12
      mov %[rdi+120], r13
      mov %[rdi+128], r14
      mov %[rdi+136], r15
      mov %[rdi+144], ymm0 //todo
      mov %[rdi+176], ymm1 //todo
      mov %[rdi+208], ymm2 //todo
      mov %[rdi+240], ymm3 //todo
      mov %[rdi+272], ymm4 //todo
      mov %[rdi+304], ymm5 //todo
      mov %[rdi+336], ymm6 //todo
      mov %[rdi+368], ymm7 //todo
      mov %[rdi+400], ymm8 //todo
      mov %[rdi+432], ymm9 //todo
      mov %[rdi+464], ymm10 //todo
      mov %[rdi+496], ymm11 //todo
      mov %[rdi+528], ymm12 //todo
      mov %[rdi+560], ymm13 //todo
      mov %[rdi+592], ymm14 //todo
      mov %[rdi+624], ymm15 //todo
      ret

   *though the stores for vector registers haven't been added yet*

 */

#define GPR_ARG_SIZE_IN_BYTES 8
#define TESTING_ABI_NUM_GPR_ARGS 5
/* todo, must be changed to handle vector ops */
#define INPUT_STATE_SIZE ((TESTING_ABI_NUM_GPR_ARGS * GPR_ARG_SIZE_IN_BYTES))

struct __attribute__((__packed__)) OutState {
	uint64_t rax;
	uint64_t rbx;
	uint64_t rcx;
	uint64_t rdx;
	uint64_t rsp;
	uint64_t rbp;
	uint64_t rsi;
	uint64_t rdi;
	uint64_t r8;
	uint64_t r9;
	uint64_t r10;
	uint64_t r11;
	uint64_t r12;
	uint64_t r13;
	uint64_t r14;
	uint64_t r15;
	/* todo, must be changed to handle vector ops */
      /* mov %[rdi+144], ymm0 //todo */
      /* mov %[rdi+176], ymm1 //todo */
      /* mov %[rdi+208], ymm2 //todo */
      /* mov %[rdi+240], ymm3 //todo */
      /* mov %[rdi+272], ymm4 //todo */
      /* mov %[rdi+304], ymm5 //todo */
      /* mov %[rdi+336], ymm6 //todo */
      /* mov %[rdi+368], ymm7 //todo */
      /* mov %[rdi+400], ymm8 //todo */
      /* mov %[rdi+432], ymm9 //todo */
      /* mov %[rdi+464], ymm10 //todo */
      /* mov %[rdi+496], ymm11 //todo */
      /* mov %[rdi+528], ymm12 //todo */
      /* mov %[rdi+560], ymm13 //todo */
      /* mov %[rdi+592], ymm14 //todo */
      /* mov %[rdi+624], ymm15 //todo */
};

const char* out_state_offset_to_reg_name[sizeof(struct OutState) * sizeof(char*)] = {
	"rax", "rax", "rax", "rax", "rax", "rax", "rax", "rax",
		"rbx", "rbx", "rbx", "rbx", "rbx", "rbx", "rbx", "rbx",
		"rcx", "rcx", "rcx", "rcx", "rcx", "rcx", "rcx", "rcx",
		"rdx", "rdx", "rdx", "rdx", "rdx", "rdx", "rdx", "rdx",
		"rsp", "rsp", "rsp", "rsp", "rsp", "rsp", "rsp", "rsp", 
		"rbp", "rbp", "rbp", "rbp", "rbp", "rbp", "rbp", "rbp", 
		"rsi", "rsi", "rsi", "rsi", "rsi", "rsi", "rsi", "rsi", 
		"rdi", "rdi", "rdi", "rdi", "rdi", "rdi", "rdi", "rdi", 
		"r8", "r8", "r8", "r8", "r8", "r8", "r8", "r8", 
		"r9", "r9", "r9", "r9", "r9", "r9", "r9", "r9", 
		"r10", "r10", "r10", "r10", "r10", "r10", "r10", "r10", 
		"r11", "r11", "r11", "r11", "r11", "r11", "r11", "r11", 
		"r12", "r12", "r12", "r12", "r12", "r12", "r12", "r12", 
		"r13", "r13", "r13", "r13", "r13", "r13", "r13", "r13", 
		"r14", "r14", "r14", "r14", "r14", "r14", "r14", "r14", 
		"r15", "r15", "r15", "r15", "r15", "r15", "r15", "r15",
		/* todo, must be changed to handle vector ops */
};

const char*
map_out_state_offset_to_reg_name(int offs)
{
	return out_state_offset_to_reg_name[offs];
}


int
check_outstates_equivalent(struct OutState* s1, struct OutState* s2)
{
	/* s1 is expected (value from original insn), s2 is given (value from transformed insn seq) */
	uint8_t* s1_bytes = (uint8_t*) s1;
	uint8_t* s2_bytes = (uint8_t*) s2;
	
	const char* which_reg_differed = 0;
	int output_states_equivalent = 1;

	int last_gpr_idx = 0;
	
	for (int state_byte_idx = 0; state_byte_idx < (int) sizeof(struct OutState); ++state_byte_idx) {
		/* todo must be changed to handle vector ops */
		last_gpr_idx = 0 == (state_byte_idx % GPR_ARG_SIZE_IN_BYTES) ? state_byte_idx : last_gpr_idx;
			
		if (s1_bytes[state_byte_idx] != s2_bytes[state_byte_idx]) {
			which_reg_differed = map_out_state_offset_to_reg_name(state_byte_idx);

			/* todo must be changed to handle vector ops */
			const uint64_t expected_value = s1_bytes[last_gpr_idx];
			const uint64_t given_value = s2_bytes[last_gpr_idx];

			/* todo must be changed to handle vector ops */
			printf("Output states differed on register %s: expected %" PRIu64 ", given %" PRIu64 "\n",
			       which_reg_differed, expected_value, given_value);
			
			output_states_equivalent = 0;
		}
	}

	return output_states_equivalent;
}

/* todo, must be changed to handle vector ops */
void x86compsimptest_ADD64rr_original(struct OutState* outstate, uint64_t i0, uint64_t i1, uint64_t i2, uint64_t i3, uint64_t i4);

void x86compsimptest_ADD64rr_transformed(struct OutState* outstate,  uint64_t i0, uint64_t i1, uint64_t i2, uint64_t i3, uint64_t i4);

int
LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
	if (size < INPUT_STATE_SIZE) {
		return -1;
	}

	/* todo, must be changed to handle vector ops */
	const uint64_t* data_as_gprs = (const uint64_t*) data;

	/* todo, must be changed to handle vector ops */
	uint64_t arg0 = data_as_gprs[0];
	uint64_t arg1 = data_as_gprs[1];
	uint64_t arg2 = data_as_gprs[2];
	uint64_t arg3 = data_as_gprs[3];
	uint64_t arg4 = data_as_gprs[4];

	struct OutState original_state = { 0 };
	struct OutState transformed_state = { 0 };

	x86compsimptest_ADD64rr_original(&original_state, arg0, arg1, arg2, arg3, arg4);
	x86compsimptest_ADD64rr_transformed(&transformed_state, arg0, arg1, arg2, arg3, arg4);

	int is_equivalent = check_outstates_equivalent(&original_state, &transformed_state);
	assert(is_equivalent);

	return 0;
}
