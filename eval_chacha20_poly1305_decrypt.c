#include <stdio.h>
#include <stdlib.h>
#include <inttypes.h>
#include <assert.h> 
#include <string.h> 

#include "eval_util.h"

#define EXPECTED_ARGC 4
#define NUM_BENCH_ITER_ARG_IDX 1
#define MSG_SIZE_ARG_IDX 2
#define AD_SIZE_ARG_IDX 3

extern int sodium_init();
extern size_t crypto_aead_chacha20poly1305_ietf_npubbytes(void);
extern size_t crypto_aead_chacha20poly1305_ietf_keybytes(void);
extern size_t crypto_aead_chacha20poly1305_ietf_abytes(void);
extern int crypto_aead_chacha20poly1305_ietf_encrypt(
    unsigned char *c, unsigned long long *clen_p, const unsigned char *m,
    unsigned long long mlen, const unsigned char *ad, unsigned long long adlen,
    const unsigned char *nsec, const unsigned char *npub,
    const unsigned char *k);
extern int crypto_aead_aes256gcm_decrypt(unsigned char *m,
          unsigned long long *mlen_p, unsigned char *nsec,
          const unsigned char *c, unsigned long long clen,
          const unsigned char *ad, unsigned long long adlen,
          const unsigned char *npub, const unsigned char *k);
extern void crypto_aead_chacha20poly1305_ietf_keygen(unsigned char *);

int
main(int argc, char** argv)
{
  if (argc != EXPECTED_ARGC) {
    printf("Usage: %s <num_benchmark_iterations>"
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

  // init libsodium, must be called before other libsodium functions are called
  const int sodium_init_success = 0;
  const int sodium_already_initd = 1;
  int sodium_init_result = sodium_init();
  assert((sodium_init_success == sodium_init_result ||
	  sodium_already_initd == sodium_init_result) &&
	 "Error initializing lib sodium");

  unsigned long long msg_sz = strtol(argv[MSG_SIZE_ARG_IDX], (char**) NULL, 10);
  unsigned long long additional_data_sz = strtol(argv[AD_SIZE_ARG_IDX], (char**) NULL, 10);

  // allocate space for message
  unsigned char* msg = malloc(msg_sz);
  assert(msg && "Couldn't allocate msg bytes in eval_chacha20-poly1305-decrypt.c");

  // allocate space for opened message
  unsigned char* opened_msg = malloc(msg_sz);
  assert(opened_msg && "Couldn't allocate opened_msg bytes in eval_chacha20-poly1305-decrypt.c");

  // allocate space for additional data
  unsigned char* additional_data = malloc(additional_data_sz);
  assert(additional_data && "Couldn't allocate msg bytes in eval_aesni256gcm_encrypt.c");

  // allocate space for signed message buffer
  unsigned long long ciphertext_sz = msg_sz + crypto_aead_chacha20poly1305_ietf_abytes();
  unsigned char* ciphertext = malloc(ciphertext_sz);
  assert(msg && "Couldn't allocate signed msg bytes in eval_chacha20-poly1305-decrypt.c");
    
  // allocate space for secret and private keys
  unsigned char* privk = malloc(crypto_aead_chacha20poly1305_ietf_keybytes());
  assert(privk && "Couldn't allocate private key bytes in eval_chacha20-poly1305-decrypt.c");


  // allocate space for decrypted message
  unsigned char* decrypted_msg = malloc(msg_sz);
  assert(decrypted_msg &&
    "Couldn't allocate decrypted_msg bytes in eval_chacha20-poly1305-decrypt.c");

  // allocate space for nonce
  unsigned char* nonce = malloc(crypto_aead_chacha20poly1305_ietf_npubbytes());

  // allocate space for timer reads
  uint64_t* times = calloc(num_iter, sizeof(uint64_t));
  assert(times &&
	 "Couldn't allocate array for benchmark times in eval_chacha20-poly1305-decrypt.c");

  volatile uint64_t start_time = 0;
  volatile uint64_t end_time = 0;

  // main loop
  for (int cur_iter = 0; cur_iter < num_iter; ++cur_iter) {
    // generate private key
    crypto_aead_chacha20poly1305_ietf_keygen(privk);

    // generate message
    ciocc_eval_rand_fill_buf(msg, msg_sz);

    // generate nonce
    ciocc_eval_rand_fill_buf(nonce, sizeof nonce);

    int encrypt_result = crypto_aead_chacha20poly1305_ietf_encrypt(
        /*signed msg buf=*/ciphertext,
        /*signed msg sz=*/&ciphertext_sz,
        /*msg buf=*/msg,
        /*msg sz=*/msg_sz,
        /*additional data=*/additional_data,
        /*additional data sz=*/additional_data_sz, NULL, nonce, privk);

    assert(-1 != encrypt_result); // -1 on err, 0 on ok

    // start counting cycles
    start_time = START_CYCLE_TIMER;

    int decrypt_result = crypto_aead_aes256gcm_decrypt(decrypted_msg, &msg_sz,
						       NULL, ciphertext,
						       ciphertext_sz, additional_data,
						       additional_data_sz,
						       nonce, privk);

    // stop counting cycles
    end_time = STOP_CYCLE_TIMER;

    times[cur_iter] = end_time - start_time;

    int cmp_result = memcmp(msg, decrypted_msg, msg_sz);
    assert(0 == cmp_result &&
          "in eval-chacha20-poly1305-decrypt.c, error validating decrypted msg = msg");
  }

  // output the timer results
  printf("eval_chacha20-poly1305-decrypt cycle counts for %d iterations\n", num_iter);
  for (int ii = 0; ii < num_iter; ++ii) {
    printf("%" PRIu64 "\n", times[ii]);
  }
}
