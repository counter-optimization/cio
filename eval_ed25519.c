#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <assert.h> 
#include <string.h>

#include "eval_util.h"

#define EXPECTED_ARGC 4
#define NUM_BENCH_ITER_ARG_IDX 1
#define NUM_WARMUP_ITER_ARG_IDX 2
#define MSG_ARG_IDX 3

extern int sodium_init(void);
extern size_t crypto_sign_secretkeybytes(void);
extern size_t crypto_sign_publickeybytes(void);
extern size_t crypto_sign_bytes(void);
extern int crypto_sign_keypair(unsigned char *pk, unsigned char *sk);
extern int crypto_sign(unsigned char *sm, unsigned long long *smlen_p,
                       const unsigned char *m, unsigned long long mlen,
                       const unsigned char *sk);
extern int crypto_sign_open(unsigned char *m, unsigned long long *mlen_p,
			    const unsigned char *sm, unsigned long long smlen,
			    const unsigned char *pk);

int
main(int argc, char** argv)
{
  if (argc != EXPECTED_ARGC) {
    printf("Usage: %s <num_benchmark_iterations> <num_warmup_iterations>"
	   " <size_of_message>\n", argv[0]);
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

  unsigned char* msg = (unsigned char*)argv[MSG_ARG_IDX];
  unsigned long long msg_sz = strlen(argv[MSG_ARG_IDX]);

  // allocate space for opened message
  unsigned char* opened_msg = malloc(msg_sz);
  assert(opened_msg && "Couldn't allocate opened_msg bytes in eval_ed25519.c");

  // allocate space for signed message buffer
  unsigned long long signed_msg_sz = msg_sz + crypto_sign_bytes();
  unsigned char* signed_msg = malloc(signed_msg_sz);
  assert(msg && "Couldn't allocate signed msg bytes in eval_ed25519.c");
    
  // allocate space for secret and private keys
  unsigned char* privk = malloc(crypto_sign_secretkeybytes());
  unsigned char* pubk = malloc(crypto_sign_publickeybytes());
  assert(privk && "Couldn't allocate private key bytes in eval_ed25519.c");
  assert(pubk && "Couldn't allocate pub key bytes in eval_ed25519.c");

  // allocate space for timer reads
  uint64_t* times = calloc(num_iter, sizeof(uint64_t));
  assert(times &&
	 "Couldn't allocate array for benchmark times in eval_ed25519.c");

  volatile uint64_t start_time = 0;
  volatile uint64_t end_time = 0;

  // main loop
  for (int cur_iter = 0; cur_iter < num_iter + num_warmup; ++cur_iter) {
    // generate private key
    // generate public key
    int _eval_unused = crypto_sign_keypair(/*public=*/ pubk, /*secret=*/ privk);

    // start counting cycles
    start_time = START_CYCLE_TIMER;
    
    // sign the message
    int sign_result = crypto_sign(/*signed msg buf=*/ signed_msg,
				  /*signed msg sz=*/ &signed_msg_sz,
				  /*msg buf=*/ msg,
				  /*msg sz=*/ msg_sz,
				  /*secret key=*/ privk);

    // stop counting cycles
    end_time = STOP_CYCLE_TIMER;

    assert(-1 != sign_result); // -1 on err, 0 on ok

    if (cur_iter >= num_warmup) {
      times[cur_iter - num_warmup] = end_time - start_time;
    }

    // verify the message for sanity check
    int open_result = crypto_sign_open(opened_msg, &msg_sz,
				       signed_msg, signed_msg_sz, pubk);
    // assert(0 == open_result && "in eval_ed25519.c, error verifying sign of msg");
  }

  // output the timer results
  printf("eval_ed25519 cycle counts for %d iterations\n", num_iter);
  for (int ii = 0; ii < num_iter; ++ii) {
    printf("%" PRIu64 "\n", times[ii]);
  }

  return 0;
}
