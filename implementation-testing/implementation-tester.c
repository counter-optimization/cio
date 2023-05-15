#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <inttypes.h>
#include <string.h>

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
      mov %[rdi+0], rax
      mov %[rdi+8], rbx
      mov %[rdi+16], rcx
      mov %[rdi+24], rcx
      mov %[rdi+32], rdx
      mov %[rdi+40], rsp
      mov %[rdi+48], rbp
      mov %[rdi+56], rsi
      mov %[rdi+64], rdi
      mov %[rdi+72], r8
      mov %[rdi+80], r9
      mov %[rdi+88], r10
      mov %[rdi+96], r11
      mov %[rdi+104], r12
      mov %[rdi+112], r13
      mov %[rdi+120], r14
      mov %[rdi+128], r15
      mov %[rdi+136], ymm0 //todo
      mov %[rdi+168], ymm1 //todo
      mov %[rdi+200], ymm2 //todo
      mov %[rdi+232], ymm3 //todo
      mov %[rdi+264], ymm4 //todo
      mov %[rdi+296], ymm5 //todo
      mov %[rdi+328], ymm6 //todo
      mov %[rdi+360], ymm7 //todo
      mov %[rdi+392], ymm8 //todo
      mov %[rdi+424], ymm9 //todo
      mov %[rdi+458], ymm10 //todo
      mov %[rdi+488], ymm11 //todo
      mov %[rdi+520], ymm12 //todo
      mov %[rdi+552], ymm13 //todo
      mov %[rdi+584], ymm14 //todo
      mov %[rdi+616], ymm15 //todo
      ret

   *though the stores for vector registers haven't been added yet*

 */

#define GPR_ARG_SIZE_IN_BYTES 8
#define TESTING_ABI_NUM_GPR_ARGS 6
/* todo, must be changed to handle vector ops */
#define INPUT_STATE_SIZE ((TESTING_ABI_NUM_GPR_ARGS * GPR_ARG_SIZE_IN_BYTES))

#define LAHF_SF(rax) (((rax) & 0x80ull) >> 7ull)
#define LAHF_ZF(rax) (((rax) & 0x40ull) >> 6ull)
#define LAHF_AF(rax) (((rax) & 0x10ull) >> 4ull)
#define LAHF_PF(rax) (((rax) & 0x4ull) >> 2ull)
#define LAHF_CF(rax) ((rax) & 0x1ull)

#define PUT_LAHF_SF(rax,val) ((val) == 1 ? (rax) | 0x80ull : (rax) & ~0x80ull)
#define PUT_LAHF_ZF(rax,val) ((val) == 1 ? (rax) | 0x40ull : (rax) & ~0x40ull)
#define PUT_LAHF_AF(rax,val) ((val) == 1 ? (rax) | 0x10ull : (rax) & ~0x10ull)
#define PUT_LAHF_PF(rax,val) ((val) == 1 ? (rax) | 0x4ull : (rax) & ~0x4ull)
#define PUT_LAHF_CF(rax,val) ((val) == 1 ? (rax) | 0x1ull : (rax) & ~0x1ull)

#define PRINT_LAHF(rax) {\
		printf("SF: %llu, ZF: %llu, AF: %llu, PF: %llu, CF: %llu\n",	\
		       LAHF_SF(rax), LAHF_ZF(rax), LAHF_AF(rax), LAHF_PF(rax), LAHF_CF(rax)); \
	}

enum EFLAGS {
	SF = 1,
	ZF = 2,
	AF = 3,
	PF = 4,
	CF = 5,
};

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

	uint64_t lahf_rax_res; // idx 16 at 8 scale
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

struct OutState original_state = { 0 };
struct OutState transformed_state = { 0 };

AUTOMATICALLY_REPLACE_ME_PROTOTYPES

#define POINTS_TO_MEM(REG_NAME) ((0 == strcmp(#REG_NAME, "rsi") && operand_types[0] && 0 == strcmp(operand_types[0], "MEM")) || \
				 (0 == strcmp(#REG_NAME, "rdx") && operand_types[1] && 0 == strcmp(operand_types[1], "MEM")) || \
				 (0 == strcmp(#REG_NAME, "rcx") && operand_types[2] && 0 == strcmp(operand_types[2], "MEM")) || \
				 (0 == strcmp(#REG_NAME, "r8") && operand_types[3] && 0 == strcmp(operand_types[3], "MEM")) || \
				 (0 == strcmp(#REG_NAME, "r9") && operand_types[4] && 0 == strcmp(operand_types[4], "MEM")))

#define CHECK_GPRS_EQUIV(REG_NAME, S1, S2, OK)				\
	{								\
	if (POINTS_TO_MEM(REG_NAME)) {					\
		if (0 != memcmp((const void*) S1->REG_NAME, (const void*) S2->REG_NAME,	GPR_ARG_SIZE_IN_BYTES)) { \
			    OK = 0;					\
			    printf("Output states differed on memory pointed to by register %s: expected %" PRIu64 ", given %" PRIu64 "\n", \
				   #REG_NAME, *(const uint64_t*) S1->REG_NAME, *(const uint64_t*) S2->REG_NAME); \
		    }							\
		    } else {						\
				if (S1->REG_NAME != S2->REG_NAME) {	\
					OK = 0;				\
					printf("Output states differed on register %s: expected %" PRIu64 ", given %" PRIu64 "\n", \
					       #REG_NAME, S1->REG_NAME, S2->REG_NAME); \
				}					\
			}						\
	}

int
check_outstates_equivalent(struct OutState* restrict s1,
			   struct OutState* restrict s2,
			   const uint64_t orig_lahf)
{
	// check x86_64 GPRS
	int output_states_equivalent = 1;
	CHECK_GPRS_EQUIV(rax, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(rbx, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(rcx, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(rdx, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(rsp, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(rbp, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(rsi, s1, s2, output_states_equivalent);
	/* don't check RDI since it holds the pointer to OutState struct
	   CHECK_GPRS_EQUIV(rdi, s1, s2, output_states_equivalent); */
	CHECK_GPRS_EQUIV(r8, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(r9, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(r10, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(r11, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(r12, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(r13, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(r14, s1, s2, output_states_equivalent);
	CHECK_GPRS_EQUIV(r15, s1, s2, output_states_equivalent);

	const uint64_t s1_out_lahf = s1->lahf_rax_res;
	const uint64_t s2_out_lahf = s2->lahf_rax_res;

	/* printf("input EFLAGS:"); */
	/* PRINT_LAHF(orig_lahf); */

	/* printf("orig EFLAGS out:"); */
	/* PRINT_LAHF(s1_out_lahf); */

	/* printf("transformed EFLAGS out:"); */
	/* PRINT_LAHF(s2_out_lahf); */

#define PRESERVED(ORIG, TRANS, GET, OK) \
	{				\
		if (GET(ORIG) != GET(TRANS)) {	\
			OK = 0;					\
			printf("transform did not preserve flag: %s\n", #GET); \
		}\
	}

#define SETTED(ORIG, TRANS, GET, OK) \
	{				\
		if (GET(ORIG) != GET(TRANS)) {	\
			OK = 0;					\
			printf("transform did not set flag %s. expected: %llu, given %llu\n", #GET, GET(ORIG), GET(TRANS)); \
		}\
	}
	
	if (must_preserve_flags) {
		for (int ii = 0; ii < 5; ++ii) {
			if (0 == preserves[ii]) {
				break;
			}
			
			switch (preserves[ii]) {
			case SF:
				PRESERVED(s1_out_lahf, s2_out_lahf, LAHF_SF, output_states_equivalent);
				break;
			case ZF:
				PRESERVED(s1_out_lahf, s2_out_lahf, LAHF_ZF, output_states_equivalent);
				break;
			case AF:
				PRESERVED(s1_out_lahf, s2_out_lahf, LAHF_AF, output_states_equivalent);
				break;
			case PF:
				PRESERVED(s1_out_lahf, s2_out_lahf, LAHF_PF, output_states_equivalent);
				break;
			case CF:
				PRESERVED(s1_out_lahf, s2_out_lahf, LAHF_CF, output_states_equivalent);
				break;
			default:
				assert(0 && "unreachable");
			}
		}
	}

	if (must_set_flags) {
		for (int ii = 0; ii < 5; ++ii) {
			if (0 == sets[ii]) {
				break;
			}
			
			switch (sets[ii]) {
			case SF:
				SETTED(s1_out_lahf, s2_out_lahf, LAHF_SF, output_states_equivalent);
				break;
			case ZF:
				SETTED(s1_out_lahf, s2_out_lahf, LAHF_ZF, output_states_equivalent);
				break;
			case AF:
				SETTED(s1_out_lahf, s2_out_lahf, LAHF_AF, output_states_equivalent);
				break;
			case PF:
				SETTED(s1_out_lahf, s2_out_lahf, LAHF_PF, output_states_equivalent);
				break;
			case CF:
				SETTED(s1_out_lahf, s2_out_lahf, LAHF_CF, output_states_equivalent);
				break;
			default:
				assert(0 && "unreachable");
			}
		}
	}
	
	return output_states_equivalent;
}

void
print_mismatch_instate(uint64_t rsi, uint64_t rdx, uint64_t rcx, uint64_t r8, uint64_t r9)
{
#define PRINT(REG_NAME) \
	{\
		if (POINTS_TO_MEM(REG_NAME)) {\
			uint64_t* ptr = (uint64_t*) REG_NAME;\
			printf("\t*%s -points-to-64-bits->: %" PRIu64 "\n", #REG_NAME, *ptr);	\
		}\
		else {\
			printf("\t%s: %" PRIu64 "\n", #REG_NAME, REG_NAME); \
		}\
	}
	
	printf("In state causing mismatch:\n");
	PRINT(rsi);
	PRINT(rdx);
	PRINT(rcx);
	PRINT(r8);
	PRINT(r9);
}

uint64_t orig_memory_args[5] = { 0 };
uint64_t trans_memory_args[5] = { 0 };

int
LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
	if (size < INPUT_STATE_SIZE) {
		return -1;
	}

	/* todo, must be changed to handle vector ops */
	const uint64_t* data_as_gprs = (const uint64_t*) data;

	/* todo, must be changed to handle vector ops */
	uint64_t orig_arg0 = data_as_gprs[0];
	uint64_t orig_arg1 = data_as_gprs[1];
	uint64_t orig_arg2 = data_as_gprs[2];
	uint64_t orig_arg3 = data_as_gprs[3];
	uint64_t orig_arg4 = data_as_gprs[4];

	uint64_t trans_arg0 = data_as_gprs[0];
	uint64_t trans_arg1 = data_as_gprs[1];
	uint64_t trans_arg2 = data_as_gprs[2];
	uint64_t trans_arg3 = data_as_gprs[3];
	uint64_t trans_arg4 = data_as_gprs[4];

	volatile uint64_t rax_save = 0;
	volatile uint64_t lahf_load = data_as_gprs[5];

	const size_t num_memory_args = sizeof(orig_memory_args) / sizeof(uint64_t);
	memcpy(orig_memory_args, data_as_gprs, sizeof(uint64_t) * num_memory_args);
	memcpy(trans_memory_args, data_as_gprs, sizeof(uint64_t) * num_memory_args);

	for (int ii = 0; ii < sizeof(operand_types) / sizeof(const char*); ++ii) {
		const char* cur_type = operand_types[ii];
		
		if (0 == cur_type) {
			break;
		}

		uint64_t* orig_which_arg = 0;
		uint64_t* trans_which_arg = 0;
		if (0 == strcmp(cur_type, "MEM")) {
			switch (ii) {
			case 0:
				orig_which_arg = &orig_arg0;
				trans_which_arg = &trans_arg0;
				break;
			case 1:
				orig_which_arg = &orig_arg1;
				trans_which_arg = &trans_arg1;
				break;
			case 2:
				orig_which_arg = &orig_arg2;
				trans_which_arg = &trans_arg2;
				break;
			case 3:
				orig_which_arg = &orig_arg3;
				trans_which_arg = &trans_arg3;
				break;
			case 4:
				orig_which_arg = &orig_arg4;
				trans_which_arg = &trans_arg4;
				break;
			default:
				assert(0 && "unreachable");
			}

			*orig_which_arg = (uint64_t) &orig_memory_args[ii];
			*trans_which_arg = (uint64_t) &trans_memory_args[ii];
		}
	}

	AUTOMATICALLY_REPLACE_ME_CALLS

		int is_equivalent = check_outstates_equivalent(&original_state, &transformed_state, lahf_load);
	
	if (!is_equivalent) {
		print_mismatch_instate(orig_arg0, orig_arg1, orig_arg2, orig_arg3, orig_arg4);
		fflush(stdout);
		assert(is_equivalent);
	}

	return 0;
}
