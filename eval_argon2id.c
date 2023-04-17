#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <assert.h> 
#include <string.h>

#include "eval_util.h"

#define EXPECTED_ARGC 5
#define NUM_BENCH_ITER_ARG_IDX 1
#define NUM_WARMUP_ITER_ARG_IDX 2
#define PASSWD_ARG_IDX 3
#define OUT_SIZE_ARG_IDX 4

extern int sodium_init(void);
extern void randombytes_buf(void * const buf, const size_t size);
extern size_t crypto_pwhash_saltbytes(void);
extern size_t crypto_pwhash_passwd_min(void);
extern size_t crypto_pwhash_passwd_max(void);
extern size_t crypto_pwhash_bytes_min(void);
extern size_t crypto_pwhash_bytes_max(void);
extern unsigned long long crypto_pwhash_opslimit_interactive(void);
extern unsigned long long crypto_pwhash_memlimit_interactive(void);
extern int crypto_pwhash_alg_argon2id13(void);
extern int crypto_pwhash(unsigned char * const out, unsigned long long outlen,
                         const char * const passwd, unsigned long long passwdlen,
                         const unsigned char * const salt,
                         unsigned long long opslimit, size_t memlimit, int alg);

int
main(int argc, char** argv)
{
  if (argc != EXPECTED_ARGC) {
    printf("Usage: %s <num_benchmark_iterations> <num_warmup_iterations>"
	   " <size_of_password>"
	   " <size_of_output>\n", argv[0]);
    exit(-1);
  }

  // init libsodium, must be called before other libsodium functions are called
  const int sodium_init_success = 0;
  const int sodium_already_initd = 1;
  int sodium_init_result = sodium_init();
  assert((sodium_init_success == sodium_init_result ||
	  sodium_already_initd == sodium_init_result) &&
	 "Error initializing lib sodium");

  // parse args
  int num_iter = strtol(/*src=*/ argv[NUM_BENCH_ITER_ARG_IDX],
			/*endptr=*/ (char**) NULL,
			/*base=*/ 10);

  int num_warmup = strtol(/*src=*/ argv[NUM_WARMUP_ITER_ARG_IDX],
			/*endptr=*/ (char**) NULL,
			/*base=*/ 10);

  // passwd_sz must be between PASSWD_MIN and PASSWD_MAX (inclusive)
  unsigned char* passwd = (unsigned char*)argv[PASSWD_ARG_IDX];
  unsigned long long passwd_sz = strlen(argv[PASSWD_ARG_IDX]);
  assert(passwd_sz >= crypto_pwhash_passwd_min() &&
    "Password size is less than min in eval_argon2id.c");
  assert(passwd_sz <= crypto_pwhash_passwd_max() &&
    "Password size is greater than max in eval_argon2id.c");

  // out_sz must be between BYTES_MIN and BYTES_MAX (inclusive)
  unsigned long long out_sz = strtol(argv[OUT_SIZE_ARG_IDX], (char**) NULL, 10);
  assert(out_sz >= crypto_pwhash_bytes_min() &&
    "Output size is less than min in eval_argon2id.c");
  assert(out_sz <= crypto_pwhash_bytes_max() &&
    "Output size is greater than max in eval_argon2id.c");

  // allocate space for output
  unsigned char* out = malloc(out_sz);
  assert(out && "Couldn't allocate output bytes in eval_argon2id.c");

  // allocate space for salt
  unsigned char* salt = malloc(crypto_pwhash_saltbytes());
  assert(salt && "Couldn't allocate salt bytes in eval_argon2id.c");

  // set ops limit
  unsigned long long opslimit = crypto_pwhash_opslimit_interactive();

  // set mem limit
  unsigned long long memlimit = crypto_pwhash_memlimit_interactive();

  // set hashing algorithm (argon2id)
  int alg = crypto_pwhash_alg_argon2id13();

  // allocate space for timer reads
  uint64_t* times = calloc(num_iter, sizeof(uint64_t));
  assert(times &&
	 "Couldn't allocate array for benchmark times in eval_argon2id.c");

  volatile uint64_t start_time = 0;
  volatile uint64_t end_time = 0;

  // main loop
  for (int cur_iter = 0; cur_iter < num_iter + num_warmup; ++cur_iter) {
    // generate salt
    randombytes_buf(salt, sizeof salt);

    // start counting cycles
    start_time = START_CYCLE_TIMER;
    
    // generate output
    int pwhash_result = crypto_pwhash(out, out_sz, (const char*)passwd, passwd_sz,
          salt, opslimit, memlimit, alg);

    // stop counting cycles
    end_time = STOP_CYCLE_TIMER;

    assert(-1 != pwhash_result); // -1 on err, 0 on ok

    if (cur_iter >= num_warmup) {
      times[cur_iter - num_warmup] = end_time - start_time;
    }

    // TODO sanity check
  }

  // output the timer results
  printf("eval_argon2id cycle counts for %d iterations\n", num_iter);
  for (int ii = 0; ii < num_iter; ++ii) {
    printf("%" PRIu64 "\n", times[ii]);
  }

  return 0;
}
