#ifndef EVAL_UTIL_H
#define EVAL_UTIL_H

#include <stdlib.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <assert.h>

#define EVAL_UTIL_H_SEED 172812

/* uint32_t _eval_cycles_high; */
/* uint32_t _eval_cycles_low; */

#define START_CYCLE_TIMER						\
  ({									\
    uint32_t _eval_cycles_low = 0;					\
   uint32_t _eval_cycles_high = 0;					\
   __asm__ volatile("cpuid\n\t"						\
		    "rdtsc\n\t"						\
		    "mov %%edx, %[cycles_high]\n\t"			\
		    "mov %%eax, %[cycles_low]\n\t"			\
		    : [cycles_low] "=r" (_eval_cycles_low),		\
		       [cycles_high] "=r" (_eval_cycles_high)		\
		    :							\
		    : "%rax", "%rbx", "%rcx", "%rdx");			\
   (((uint64_t)_eval_cycles_high) << 32 | (uint64_t)_eval_cycles_low);	\
})

#define STOP_CYCLE_TIMER						\
  ({									\
    uint32_t _eval_cycles_low = 0;					\
    uint32_t _eval_cycles_high = 0;					\
    __asm__ volatile(							\
        "rdtscp\n\t"                                                           \
        "mov %%edx, %[cycles_high]\n\t"                                        \
        "mov %%eax, %[cycles_low]\n\t"                                         \
        "cpuid\n\t"                                                            \
        : [cycles_low] "=r"(_eval_cycles_low),				\
          [cycles_high] "=r"(_eval_cycles_high)					\
        :                                                                      \
        : "%rax", "%rbx", "%rcx", "%rdx");                                     \
    (((uint64_t)_eval_cycles_high) << 32 | (uint64_t)_eval_cycles_low);        \
  })

// https://www.intel.com/content/dam/www/public/us/en/documents/white-papers/ia-32-ia-64-benchmark-code-execution-paper.pdf
uint64_t ciocc_eval_rdtsc() {
  uint32_t _eval_cycles_low = 0;
  uint32_t _eval_cycles_high = 0;
  __asm__ volatile("CPUID\n\t"
		   "RDTSC\n\t"
		   "mov %%edx, %[cycles_high]\n\t"
		   "mov %%eax, %[cycles_low]\n\t" 
		   : [cycles_low] "=r" (_eval_cycles_low),
		     [cycles_high] "=r" (_eval_cycles_high)
		   :
		   : "%rax", "%rbx", "%rcx", "%rdx");
  return (((uint64_t)_eval_cycles_high) << 32 | (uint64_t)_eval_cycles_low);
}

uint64_t ciocc_eval_rdtscp() {
    uint32_t _eval_cycles_low = 0;
    uint32_t _eval_cycles_high = 0;
    __asm__ volatile("RDTSCP\n\t"
		 "mov %%edx, %[cycles_high]\n\t"
		 "mov %%eax, %[cycles_low]\n\t"
		 "CPUID\n\t"
		 : [cycles_low] "=r" (_eval_cycles_low),
		 [cycles_high] "=r" (_eval_cycles_high)
		 :
		 : "%rax", "%rbx", "%rcx", "%rdx");
    return (((uint64_t)_eval_cycles_high) << 32 | (uint64_t)_eval_cycles_low);
}

void
ciocc_eval_rand_fill_buf(unsigned char* buf, int buf_len)
{
	for (int ii = 0; ii < buf_len; ++ii) {
		buf[ii] = rand();
	}
}

/* this needs to be kept in sync with X86CompSimpMap.csv 
   in llvm-project repo. to avoid more csv parsing scripts
   or csv parsing here, i generated the below with emacs macros.
   if you make breaking changes for this and don't
   want to tweak by hand, lmk and i can run it -michael */
enum StatsOffsetIndices {
	ADD64ri8 = 1,
	ADD64ri32 = 2,
	ADD64mi32 = 3,
	ADD64mi8 = 4,
	ADD64mr = 5,
	ADD64rm = 6,
	ADD64rr = 7,
	ADC64rr = 8,
	ADC64rm = 9,
	ADC64mr = 10,
	ADC64ri8 = 11,
	ADD32rr = 12,
	ADD32rm = 13,
	ADD32ri8 = 14,
	ADD32i32 = 15,
	ADC32mi8 = 16,
	AND64rr = 18,
	AND64i32 = 19,
	AND64ri32 = 20,
	AND64ri8 = 21,
	AND32rr = 22,
	AND32ri8 = 23,
	AND32ri = 24,
	AND32i32 = 25,
	OR64rr = 26,
	OR64rm = 27,
	OR64ri8 = 28,
	OR32rr = 29,
	OR32ri8 = 30,
	OR8rm = 31,
	MUL64m = 32,
	XOR64rr = 34,
	XOR64rm = 35,
	XOR64mr = 36,
	XOR32rr = 37,
	XOR32rm = 38,
	XOR32ri8 = 39,
	XOR8rm = 41,
	SUB64rr = 42,
	SUB64rm = 43,
	SUB32rr = 44,
	TEST32rr = 45,
	AND8rr = 46,
	TEST8ri = 47,
	TEST8i8 = 48,
	TEST8mi = 49,
	SHL8rCL = 50,
	SHR8ri = 51,
	SAR8r1 = 52,
	SHR32rCL = 53,
	SHR32ri = 54,
	SHR32r1 = 55,
	SHL32rCL = 56,
	SHL32ri = 57,
	SAR32r1 = 58,
	SAR64ri = 59,
	SHR64ri = 60,
	SHL64ri = 61,
	AND16rr = 62,
	OR16rr = 64,
	XOR16rr = 65,
	SUB8rr = 66,
	SUB16rr = 67,
	SUB32rm = 68,
	ADD8rr = 69,
	ADD16rr = 70,
	SHR64rCL = 72,
	SHR16rCL = 74,
	SHR8rCL = 75,
	MUL32r = 76,
	CMP64rr = 77,
	CMP64rm = 78,
	CMP32rr = 79,
	CMP32rm = 80,
	CMP32mr = 81,
	CMP8rr = 82,
	SBB32rr = 83,
	IMUL32rr = 84,
	IMUL32rm = 85,
	VPXORrr = 86,
	VPXORrm = 87,
	VPXORYrr = 88,
	VPXORYrm = 89,
	PXORrr = 90,
	PXORrm = 91,
	VPORrr = 92,
	VPORYrr = 93,
	PORrr = 94,
	PORrm = 95,
	VPADDDrr = 96,
	VPADDDrm = 97,
	VPADDDYrr = 98,
	VPADDDYrm = 99,
	VPADDQrr = 100,
	VPADDQrm = 101,
	VPADDQYrr = 102,
	VPADDQYrm = 103,
	PADDQrr = 104,
	PADDQrm = 105,
	VPANDrr = 106,
	VPANDrm = 107,
	PANDrr = 108,
	PANDrm = 109,
	VPSHUFBrr = 110,
	VPSHUFBYrr = 111,
	VPSHUFBYrm = 112,
	LEA64_32r = 113,
	LEA64r = 114,
	ADD32ri = 115,
	ADD8rm = 116,
	AND64rm = 117,
	XOR32ri = 118,
	AND8ri = 119,
	SAR8ri = 120,
	SHR64r1 = 121,
	OR8rr = 122,
	OR8ri = 123,
	ADD8ri = 124,
	MUL64r = 125,
	CMP64mr = 126,
	PADDDrr = 127,
	PADDDrm = 128,
	IMUL64rr = 129,
	IMUL64rm = 130,
	IMUL64rri8 = 131,
	IMUL64rri32 = 132,
	IMUL64rmi32 = 133,
	ADD64i32 = 134,
	AND8i8 = 135,
	OR8i8 = 136,
	IMUL32rri8 = 137,
	SAR32ri = 138,
	SHL8ri = 139,
	OR64ri32 = 140,
};

/* volatile is important, we are breaking
   C boundaries, and making libsodium
   write to this array */
volatile int llvm_stats[300] = {0};

void
updateStats(const register int64_t idx)
{
	__asm__ __inline__ __volatile__(
		"addq $0x1, (%0, %1, 4)\n"
		:
		: "r" (llvm_stats),
		  "r" (idx)
		: "memory");
	/* llvm_stats[idx] += 1; */
}

void
print_dynamic_hitcounts(const char* outfilename)
{
#ifndef BASELINE_COMPILE	
#define PRINT_STAT(OPCODE, F) {			\
	int hitcount = 0; \
	hitcount = llvm_stats[(int)OPCODE]; \
	fprintf(F, "%s,%d\n", #OPCODE, hitcount);	\
	}

	FILE* ff = fopen(outfilename, "w");
	assert(ff != NULL && "Couldn't open dynamic hit counts file for writing");
	PRINT_STAT(ADD64ri8, ff);
	PRINT_STAT(ADD64ri32, ff);
	PRINT_STAT(ADD64mi32, ff);
	PRINT_STAT(ADD64mi8, ff);
	PRINT_STAT(ADD64mr, ff);
	PRINT_STAT(ADD64rm, ff);
	PRINT_STAT(ADD64rr, ff);
	PRINT_STAT(ADC64rr, ff);
	PRINT_STAT(ADC64rm, ff);
	PRINT_STAT(ADC64mr, ff);
	PRINT_STAT(ADC64ri8, ff);
	PRINT_STAT(ADD32rr, ff);
	PRINT_STAT(ADD32rm, ff);
	PRINT_STAT(ADD32ri8, ff);
	PRINT_STAT(ADD32i32, ff);
	PRINT_STAT(ADC32mi8, ff);
	PRINT_STAT(AND64rr, ff);
	PRINT_STAT(AND64i32, ff);
	PRINT_STAT(AND64ri32, ff);
	PRINT_STAT(AND64ri8, ff);
	PRINT_STAT(AND32rr, ff);
	PRINT_STAT(AND32ri8, ff);
	PRINT_STAT(AND32ri, ff);
	PRINT_STAT(AND32i32, ff);
	PRINT_STAT(OR64rr, ff);
	PRINT_STAT(OR64rm, ff);
	PRINT_STAT(OR64ri8, ff);
	PRINT_STAT(OR32rr, ff);
	PRINT_STAT(OR32ri8, ff);
	PRINT_STAT(OR8rm, ff);
	PRINT_STAT(MUL64m, ff);
	PRINT_STAT(XOR64rr, ff);
	PRINT_STAT(XOR64rm, ff);
	PRINT_STAT(XOR64mr, ff);
	PRINT_STAT(XOR32rr, ff);
	PRINT_STAT(XOR32rm, ff);
	PRINT_STAT(XOR32ri8, ff);
	PRINT_STAT(XOR8rm, ff);
	PRINT_STAT(SUB64rr, ff);
	PRINT_STAT(SUB64rm, ff);
	PRINT_STAT(SUB32rr, ff);
	PRINT_STAT(TEST32rr, ff);
	PRINT_STAT(AND8rr, ff);
	PRINT_STAT(TEST8ri, ff);
	PRINT_STAT(TEST8i8, ff);
	PRINT_STAT(TEST8mi, ff);
	PRINT_STAT(SHL8rCL, ff);
	PRINT_STAT(SHR8ri, ff);
	PRINT_STAT(SAR8r1, ff);
	PRINT_STAT(SHR32rCL, ff);
	PRINT_STAT(SHR32ri, ff);
	PRINT_STAT(SHR32r1, ff);
	PRINT_STAT(SHL32rCL, ff);
	PRINT_STAT(SHL32ri, ff);
	PRINT_STAT(SAR32r1, ff);
	PRINT_STAT(SAR64ri, ff);
	PRINT_STAT(SHR64ri, ff);
	PRINT_STAT(SHL64ri, ff);
	PRINT_STAT(AND16rr, ff);
	PRINT_STAT(OR16rr, ff);
	PRINT_STAT(XOR16rr, ff);
	PRINT_STAT(SUB8rr, ff);
	PRINT_STAT(SUB16rr, ff);
	PRINT_STAT(SUB32rm, ff);
	PRINT_STAT(ADD8rr, ff);
	PRINT_STAT(ADD16rr, ff);
	PRINT_STAT(SHR64rCL, ff);
	PRINT_STAT(SHR16rCL, ff);
	PRINT_STAT(SHR8rCL, ff);
	PRINT_STAT(MUL32r, ff);
	PRINT_STAT(CMP64rr, ff);
	PRINT_STAT(CMP64rm, ff);
	PRINT_STAT(CMP32rr, ff);
	PRINT_STAT(CMP32rm, ff);
	PRINT_STAT(CMP32mr, ff);
	PRINT_STAT(CMP8rr, ff);
	PRINT_STAT(SBB32rr, ff);
	PRINT_STAT(IMUL32rr, ff);
	PRINT_STAT(IMUL32rm, ff);
	PRINT_STAT(VPXORrr, ff);
	PRINT_STAT(VPXORrm, ff);
	PRINT_STAT(VPXORYrr, ff);
	PRINT_STAT(VPXORYrm, ff);
	PRINT_STAT(PXORrr, ff);
	PRINT_STAT(PXORrm, ff);
	PRINT_STAT(VPORrr, ff);
	PRINT_STAT(VPORYrr, ff);
	PRINT_STAT(PORrr, ff);
	PRINT_STAT(PORrm, ff);
	PRINT_STAT(VPADDDrr, ff);
	PRINT_STAT(VPADDDrm, ff);
	PRINT_STAT(VPADDDYrr, ff);
	PRINT_STAT(VPADDDYrm, ff);
	PRINT_STAT(VPADDQrr, ff);
	PRINT_STAT(VPADDQrm, ff);
	PRINT_STAT(VPADDQYrr, ff);
	PRINT_STAT(VPADDQYrm, ff);
	PRINT_STAT(PADDQrr, ff);
	PRINT_STAT(PADDQrm, ff);
	PRINT_STAT(VPANDrr, ff);
	PRINT_STAT(VPANDrm, ff);
	PRINT_STAT(PANDrr, ff);
	PRINT_STAT(PANDrm, ff);
	PRINT_STAT(VPSHUFBrr, ff);
	PRINT_STAT(VPSHUFBYrr, ff);
	PRINT_STAT(VPSHUFBYrm, ff);
	PRINT_STAT(LEA64_32r, ff);
	PRINT_STAT(LEA64r, ff);
	PRINT_STAT(ADD32ri, ff);
	PRINT_STAT(ADD8rm, ff);
	PRINT_STAT(AND64rm, ff);
	PRINT_STAT(XOR32ri, ff);
	PRINT_STAT(AND8ri, ff);
	PRINT_STAT(SAR8ri, ff);
	PRINT_STAT(SHR64r1, ff);
	PRINT_STAT(OR8rr, ff);
	PRINT_STAT(OR8ri, ff);
	PRINT_STAT(ADD8ri, ff);
	PRINT_STAT(MUL64r, ff);
	PRINT_STAT(CMP64mr, ff);
	PRINT_STAT(PADDDrr, ff);
	PRINT_STAT(PADDDrm, ff);
	PRINT_STAT(IMUL64rr, ff);
	PRINT_STAT(IMUL64rm, ff);
	PRINT_STAT(IMUL64rri8, ff);
	PRINT_STAT(IMUL64rri32, ff);
	PRINT_STAT(IMUL64rmi32, ff);
	PRINT_STAT(ADD64i32, ff);
	PRINT_STAT(AND8i8, ff);
	PRINT_STAT(OR8i8, ff);
	PRINT_STAT(IMUL32rri8, ff);
	PRINT_STAT(SAR32ri, ff);
	PRINT_STAT(SHL8ri, ff);
	PRINT_STAT(OR64ri32, ff);
	assert(EOF != fclose(ff) &&
	       "Couldn't close dynamic hit counts file after writing");
#endif // #ifndef BASELINE_COMPILE
}
#endif // EVAL_UTIL_H
