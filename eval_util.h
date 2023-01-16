#ifndef EVAL_UTIL_H
#define EVAL_UTIL_H

#include <stdlib.h>
#include <limits.h>
#include <stdint.h>

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
    buf[ii] = rand() % UCHAR_MAX;
  }
}

#endif // EVAL_UTIL_H
