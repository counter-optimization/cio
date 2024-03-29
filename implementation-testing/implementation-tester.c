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

#define BYTES_IN_XMM (128 / 8)

#define GPR_ARG_SIZE_IN_BYTES 8
#define TEST_GPR_ARG_SIZE_IN_BYTES 16
#define TESTING_ABI_NUM_GPR_ARGS 6

#define VECTOR_ARG_SIZE_IN_BYTES 32
#define TESTING_ABI_NUM_VECTOR_ARGS 8

#define INPUT_STATE_SIZE ((TESTING_ABI_NUM_GPR_ARGS) * (TEST_GPR_ARG_SIZE_IN_BYTES) + \
			  (VECTOR_ARG_SIZE_IN_BYTES) * (TESTING_ABI_NUM_VECTOR_ARGS))

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
	uint64_t rax; // 0
	uint64_t rbx; // 8
	uint64_t rcx; // 10
	uint64_t rdx; // 18
	uint64_t rsp; // 20
	uint64_t rbp; // 28
	uint64_t rsi; // 30
	uint64_t rdi; // 38
	uint64_t r8; // 40
	uint64_t r9; // 48
	uint64_t r10; // 50
	uint64_t r11; // 58
	uint64_t r12; // 60
	uint64_t r13; // 68
	uint64_t r14; // 70
	uint64_t r15; // 78

	uint64_t lahf_rax_res; // idx 16 at 8 scale (80)
	uint64_t padding;

	uint64_t xmm0lo; // idx 17 at 8 scale (90
	uint64_t xmm0hi; //

	uint64_t xmm1lo; // A0
	uint64_t xmm1hi; // 

	uint64_t xmm2lo; // b0
	uint64_t xmm2hi;

	uint64_t xmm3lo; // c0
	uint64_t xmm3hi;

	uint64_t xmm4lo; // d0
	uint64_t xmm4hi;

	uint64_t xmm5lo; // e0
	uint64_t xmm5hi;

	uint64_t xmm6lo; // f0
	uint64_t xmm6hi;

	uint64_t xmm7lo; // 100
	uint64_t xmm7hi; // 

	uint64_t cyclecount; // 110
};

static _Alignas(16) struct OutState original_state = { 0 };
static _Alignas(16) struct OutState transformed_state = { 0 };

#define ORIG_CC_CAPACITY 10000

static uint64_t* orig_cycles;
static uint64_t capacity_orig_cycles = 0;
static uint64_t num_orig_cycles = 0;

static uint64_t* transformed_cycles;
static uint64_t capacity_transformed_cycles = 0;
static uint64_t num_transformed_cycles = 0;

static int measure_cycle_run = 0;

static void
print_cycle_counts()
{
	if (!measure_cycle_run) {
		return;
	}
	
	assert(num_transformed_cycles == num_orig_cycles);
	printf("orig,transformed\n");
	for (uint64_t ii = 0; ii < num_orig_cycles; ++ii) {
		printf("%" PRIu64 ",%" PRIu64 "\n",
		       orig_cycles[ii],
		       transformed_cycles[ii]);
	}
}

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

#define CHECK_VECTOR_REG_EQUIV(REGNAME, S1, S2, OK)			\
	{								\
		int is_equal = 0 == memcmp(&S1->REGNAME##lo, &S2->REGNAME##lo, BYTES_IN_XMM); \
		if (!is_equal) {					\
			printf("mismatch on %s, given: %#0lX %#0lX, expected: %#0lX %#0lX\n", \
			       #REGNAME,				\
			       s1->REGNAME ## hi, s1->REGNAME ## lo,	\
			       s2->REGNAME ## hi, s2->REGNAME ## lo);	\
			OK = 0;						\
		}							\
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
		
	CHECK_VECTOR_REG_EQUIV(xmm0, s1, s2, output_states_equivalent);
	CHECK_VECTOR_REG_EQUIV(xmm1, s1, s2, output_states_equivalent);
	CHECK_VECTOR_REG_EQUIV(xmm2, s1, s2, output_states_equivalent);
	CHECK_VECTOR_REG_EQUIV(xmm3, s1, s2, output_states_equivalent);
	CHECK_VECTOR_REG_EQUIV(xmm4, s1, s2, output_states_equivalent);
	CHECK_VECTOR_REG_EQUIV(xmm5, s1, s2, output_states_equivalent);
	CHECK_VECTOR_REG_EQUIV(xmm6, s1, s2, output_states_equivalent);
	CHECK_VECTOR_REG_EQUIV(xmm7, s1, s2, output_states_equivalent);


	const uint64_t s1_out_lahf = s1->lahf_rax_res;
	const uint64_t s2_out_lahf = s2->lahf_rax_res;

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

typedef struct __attribute__((__packed__)) Test128BitType {
	uint64_t hi;
	uint64_t lo;
} Test128BitType;

Test128BitType orig_memory_args[5] = { 0 };
Test128BitType trans_memory_args[5] = { 0 };

int
LLVMFuzzerInitialize(int *argc, char ***argv)
{
	const char* measure_cycle_run_arg = "-measure_cycles";
	
	for (int ii = 0; ii < *argc; ++ii) {
		char* arg = (*argv)[ii];
		if (0 == strcmp(arg, measure_cycle_run_arg)) {
			measure_cycle_run = 1;
			return 0;
		}
	}
	
	return 0;
}

int
LLVMFuzzerTestOneInput(const uint8_t *data, size_t size)
{
	if (size < INPUT_STATE_SIZE) {
		return -1;
	}

	// check alignment of struct OutState to make sure
	// the aligned register indirect vector reads and stores
	// will not cause mysterious segfaults
	assert((uintptr_t) &original_state % 16 == 0 &&
	       (uintptr_t) &transformed_state % 16 == 0 &&
	       "original state or transformed state global structs "
	       "are not 16 byte aligned");

	memset(&original_state, 0, sizeof(struct OutState));
	memset(&transformed_state, 0, sizeof(struct OutState));

	if (measure_cycle_run) {
		if (0 == capacity_transformed_cycles && 0 == capacity_orig_cycles) {
			capacity_orig_cycles = capacity_transformed_cycles = ORIG_CC_CAPACITY;
		
			orig_cycles = calloc(capacity_orig_cycles, sizeof(uint64_t));
			assert(orig_cycles &&
			       "Couldn't allocate space for cycle counts");

			transformed_cycles = calloc(capacity_transformed_cycles, sizeof(uint64_t));
			assert(transformed_cycles &&
			       "Couldn't allocate space for cycle counts");

			// not sure if libfuzzer likes this, but...
			atexit(print_cycle_counts);
		}
	}

	const Test128BitType* data_as_gprs = (const Test128BitType*) data;

	uint64_t orig_arg0 = data_as_gprs[0].lo;
	uint64_t orig_arg1 = data_as_gprs[1].lo;
	uint64_t orig_arg2 = data_as_gprs[2].lo;
	uint64_t orig_arg3 = data_as_gprs[3].lo;
	uint64_t orig_arg4 = data_as_gprs[4].lo;

	uint64_t trans_arg0 = data_as_gprs[0].lo;
	uint64_t trans_arg1 = data_as_gprs[1].lo;
	uint64_t trans_arg2 = data_as_gprs[2].lo;
	uint64_t trans_arg3 = data_as_gprs[3].lo;
	uint64_t trans_arg4 = data_as_gprs[4].lo;

	volatile uint64_t rax_save = 0;
	volatile uint64_t lahf_load = data_as_gprs[5].lo;

	const Test128BitType* vector_arg_data = &data_as_gprs[6];

	const size_t num_memory_args = sizeof(orig_memory_args) / sizeof(Test128BitType);
	memcpy(orig_memory_args,
	       data_as_gprs,
	       sizeof(Test128BitType) * num_memory_args);
	memcpy(trans_memory_args,
	       data_as_gprs,
	       sizeof(Test128BitType) * num_memory_args);

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

	__asm__ __inline__ __volatile__(
		"pushq %%r10\n"
		"movq (%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm0\n"
		"movq 0x8(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm1\n"
		"movq 0x10(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm2\n"
		"movq 0x18(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm3\n"
		"movq 0x20(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm4\n"
		"movq 0x28(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm5\n"
		"movq 0x30(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm6\n"
		"movq 0x38(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm7\n"
		"popq %%r10\n"
		: 
		: "r" (vector_arg_data)
		: "ymm0", "ymm1", "ymm2", "ymm3",
		  "ymm4", "ymm5", "ymm6", "ymm7",
		  "r10", "memory"
		);

	AUTOMATICALLY_REPLACE_ME_ORIG_CALLS

	__asm__ __inline__ __volatile__(
		"pushq %%r10\n"
		"movq (%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm0\n"
		"movq 0x8(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm1\n"
		"movq 0x10(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm2\n"
		"movq 0x18(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm3\n"
		"movq 0x20(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm4\n"
		"movq 0x28(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm5\n"
		"movq 0x30(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm6\n"
		"movq 0x38(%0), %%r10\n"
		"vpbroadcastq %%r10, %%ymm7\n"
		"popq %%r10\n"
		: 
		: "r" (vector_arg_data)
		: "ymm0", "ymm1", "ymm2", "ymm3",
		  "ymm4", "ymm5", "ymm6", "ymm7",
		"r10", "memory"
		);

	AUTOMATICALLY_REPLACE_ME_TRANS_CALLS

		int is_equivalent = check_outstates_equivalent(&original_state, &transformed_state, lahf_load);

	/* Don't check equivalence when measuring cycles. amortization, */
	/* cycle reader, end - start cycle subtraction, all mess with */
	/* equivalence checks. run equivalence checks before measuring */
	/* cycles instead. */
	if (!measure_cycle_run && !is_equivalent) {
		print_mismatch_instate(orig_arg0, orig_arg1, orig_arg2, orig_arg3, orig_arg4);
		fflush(stdout);
		assert(is_equivalent);
	}

	if (measure_cycle_run) {
		orig_cycles[num_orig_cycles++] = original_state.cyclecount;
		transformed_cycles[num_transformed_cycles++] = transformed_state.cyclecount;

		assert(num_transformed_cycles == num_orig_cycles);
		if (num_transformed_cycles == capacity_transformed_cycles) {
			capacity_orig_cycles = capacity_transformed_cycles =
				2 * capacity_transformed_cycles;

			orig_cycles = reallocarray(orig_cycles,
						   capacity_orig_cycles,
						   sizeof(uint64_t));
			assert(orig_cycles &&
			       "Couldn't reallocate space for cycle counts");

			transformed_cycles = reallocarray(transformed_cycles,
							  capacity_transformed_cycles,
							  sizeof(uint64_t));
			assert(transformed_cycles &&
			       "Couldn't reallocate space for cycle counts");
		}
	}

	return 0;
}

#ifdef OUR_MAIN
static int runs = 0;
static int max_len = 0;
static const char* runs_pre = "-runs=";
static const char* max_len_pre = "-max_len=";

static void
fill_buf_rand(uint8_t* restrict bytes, int bytes_len)
{
	for (int ii = 0; ii < bytes_len; ++ii) {
		bytes[ii] = rand();
	}
}

static void
parse_args(int argc, const char** restrict argv)
{
	char* strtol_errs = 0;
	for (int ii = 0; ii < argc; ++ii) {
		if (0 == strncmp(argv[ii], runs_pre, strlen(runs_pre))) {
			const char* runs_s = argv[ii] + strlen(runs_pre);
			runs = strtol(runs_s, &strtol_errs, 10);
			assert(*strtol_errs == '\0' && "-runs=... param is invalid int");
		}

		if (0 == strncmp(argv[ii], max_len_pre, strlen(max_len_pre))) {
			const char* max_len_s = argv[ii] + strlen(max_len_pre);
			max_len = strtol(max_len_s, &strtol_errs, 10);
			assert(*strtol_errs == '\0' && "-max_len=... param is invalid int");
			assert(max_len >= INPUT_STATE_SIZE &&
			       "Max len of fuzz buffer is less than needed");
		}
	}

	assert(max_len != 0 && "Need -max_len=... cl arg");
	assert(runs != 0 && "Need -runs=... cl arg");
}

#define RAND_SEED 172812

int
main(int argc, char** argv)
{
	uint8_t bytes[INPUT_STATE_SIZE] = {0};

	srand(RAND_SEED);
	parse_args(argc, argv);
	LLVMFuzzerInitialize(&argc, &argv);
	
	int fuzz_result = 0;
	for (int ii = 0; ii < runs; ++ii) {
		fill_buf_rand(bytes, INPUT_STATE_SIZE);
		fuzz_result = LLVMFuzzerTestOneInput(bytes, INPUT_STATE_SIZE);
		assert(fuzz_result == 0 && "fuzzer returned non-zero");
	}
	
	return 0;
}
#endif // OUR_MAIN
