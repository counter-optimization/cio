#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <assert.h>
#include <string.h>

#include "eval_util.h"

#define EXPECTED_ARGC 5
#define NUM_BENCH_ITER_ARG_IDX 1
#define NUM_WARMUP_ITER_ARG_IDX 2
#define MSG_SIZE_ARG_IDX 3
#define AD_SIZE_ARG_IDX 4

extern int strncmp(const char *str1, const char *str2, size_t n);
extern size_t crypto_aead_aes256gcm_keybytes(void);
extern size_t crypto_aead_aes256gcm_npubbytes(void);
extern size_t crypto_aead_aes256gcm_abytes(void);
extern int sodium_init();
extern void randombytes_buf(void * const buf, const size_t size);
extern int crypto_aead_aes256gcm_is_available(void);
extern int crypto_aead_aes256gcm_keygen(unsigned char *k);
extern int crypto_aead_aes256gcm_encrypt(unsigned char *c,
          unsigned long long *clen_p, const unsigned char *m,
          unsigned long long m_len, const unsigned char *ad,
          unsigned long long ad_len, const unsigned char *nsec,
          const unsigned char *npub, const unsigned char *k);
extern int crypto_aead_aes256gcm_decrypt(unsigned char *m,
          unsigned long long *mlen_p, unsigned char *nsec,
          const unsigned char *c, unsigned long long clen,
          const unsigned char *ad, unsigned long long adlen,
          const unsigned char *npub, const unsigned char *k);

int
main(int argc, char** argv)
{
  if (argc != EXPECTED_ARGC) {
    printf("Usage: %s <num_benchmark_iterations> <num_warmup_iterations>"
	   " <size_of_message>"
	   " <size_of_associated_data>\n", argv[0]);
    exit(-1);
  }

  // seed non-crypto-secure PRNG, for generating message contents
  srand(EVAL_UTIL_H_SEED);

  // parse args
  int num_iter = strtol(/*src=*/ argv[NUM_BENCH_ITER_ARG_IDX],
			/*endptr=*/ (char**) NULL,
			/*base=*/ 10);
  
  int num_warmup = strtol(/*src=*/ argv[NUM_WARMUP_ITER_ARG_IDX],
			/*endptr=*/ (char**) NULL,
			/*base=*/ 10);

  unsigned long long msg_sz = strtol(argv[MSG_SIZE_ARG_IDX], (char**) NULL, 10);
  unsigned long long additional_data_sz = strtol(argv[AD_SIZE_ARG_IDX], (char**) NULL, 10);

  // init libsodium, must be called before other libsodium functions are called
  const int sodium_init_success = 0;
  const int sodium_already_initd = 1;
  int sodium_init_result = sodium_init();
  assert((sodium_init_success == sodium_init_result ||
	  sodium_already_initd == sodium_init_result) &&
	 "Error initializing lib sodium");

  // Make sure AES is available
  assert(crypto_aead_aes256gcm_is_available() && "AES not available on this CPU");

  // allocate space for message
  unsigned char* msg = malloc(msg_sz);
  assert(msg && "Couldn't allocate msg bytes in eval_aesni256gcm_encrypt.c");

  // allocate space for additional data
  unsigned char* additional_data = malloc(additional_data_sz);
  assert(additional_data && "Couldn't allocate msg bytes in eval_aesni256gcm_encrypt.c");

  // allocate space for decrypted message
  unsigned char* decrypted_msg = malloc(msg_sz);
  assert(decrypted_msg &&
    "Couldn't allocate decrypted_msg bytes in eval_aesni256gcm_encrypt.c");

  // allocate space for ciphertext
  unsigned long long ciphertext_sz = msg_sz + crypto_aead_aes256gcm_abytes();
  unsigned char* ciphertext = malloc(ciphertext_sz);
  assert(msg && "Couldn't allocate ciphertext bytes in eval_aesni256gcm_encrypt.c");

  // allocate space for key
  unsigned char* key = malloc(crypto_aead_aes256gcm_keybytes());
  assert(key && "Couldn't allocate key bytes in eval_aesni256gcm_encrypt.c");

  // allocate space for nonce
  unsigned char* nonce = malloc(crypto_aead_aes256gcm_npubbytes());
  assert(nonce && "Couldn't allocate key bytes in eval_aesni256gcm_encrypt.c");

  // allocate space for timer reads
  uint64_t* times = calloc(num_iter, sizeof(uint64_t));
  assert(times &&
	 "Couldn't allocate array for encrypt benchmark times in eval_aesni256gcm_encrypt.c");

  volatile uint64_t start_time = 0;
  volatile uint64_t end_time = 0;

  // main loop
  for (int cur_iter = 0; cur_iter < num_iter + num_warmup; ++cur_iter) {
    // generate key
    // generate nonce
    crypto_aead_aes256gcm_keygen(key);
    randombytes_buf(nonce, sizeof nonce);

    // generate message
    ciocc_eval_rand_fill_buf(msg, msg_sz);

    // start counting cycles
    start_time = START_CYCLE_TIMER;

    // encrypt message
    int encrypt_result = crypto_aead_aes256gcm_encrypt(ciphertext, &ciphertext_sz,
          msg, msg_sz, additional_data, additional_data_sz, NULL, nonce, key);

    // stop counting cycles
    end_time = STOP_CYCLE_TIMER;

    assert(-1 != encrypt_result);
    
    if (cur_iter >= num_warmup) {
      times[cur_iter - num_warmup] = end_time - start_time;
    }

    // sanity check: verify message decrypts correctly and is same as original
    int decrypt_result = crypto_aead_aes256gcm_decrypt(decrypted_msg, &msg_sz,
          NULL, ciphertext, ciphertext_sz, additional_data, additional_data_sz,
          nonce, key);

    // assert(-1 != decrypt_result);

    int cmp_result = memcmp(msg, decrypted_msg, msg_sz);
    // assert(0 == cmp_result &&
          // "in eval_aesni256gcm_encrypt.c, error validating decrypted msg = msg");
  }

  // output the timer results
  printf("eval_aesni256gcm_encrypt cycle counts for %d iterations\n", num_iter);
  for (int ii = 0; ii < num_iter; ++ii) {
    printf("%" PRIu64 "\n", times[ii]);
  }
}
