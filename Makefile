CFLAGS=-O0 -Werror -std=c18 # for the eval code, don't optimize anything

OUR_CC=$(HOME)/llvm-project/build/bin/clang
CC=$(OUR_CC) # default to our fork of llvm's clang

TZ='America/Los_Angeles'

LIBSODIUM_DIR=./libsodium
LIBSODIUM_AR=$(LIBSODIUM_DIR)/src/libsodium/.libs/libsodium.a
LIBSODIUM_TARGET_RELEASE_TAG=1.0.18-RELEASE
LIBSODIUM_BUILT=libsodium.built

EVAL_ED25519=eval_ed25519.o
ED25519_MSG_LEN=100
ED25519_NUM_ITER=1000

EVAL_AESNI256GCM_ENCRYPT=eval_aesni256gcm_encrypt.o
EVAL_AESNI256GCM_DECRYPT=eval_aesni256gcm_decrypt.o
AESNI256GCM_MSG_LEN=100
AESNI256GCM_AD_LEN=100
AESNI256GCM_NUM_ITER=1000

EVAL_ARGON2ID=eval_argon2id.o
ARGON2ID_PASSWD_LEN=100
ARGON2ID_OUT_LEN=100
ARGON2ID_NUM_ITER=1000

EVAL_START_TIME=$$(date +%F-%H:%M:%S-%Z)
EVAL_DIR=$(EVAL_START_TIME)-eval

.PHONY: clean eval_prereqs run_eval build_eval

all: build_eval

run_eval: build_eval
	mkdir $(EVAL_DIR)
	./eval_ed25519  $(ED25519_NUM_ITER) $(ED25519_MSG_LEN) > $(EVAL_DIR)/libsodium-ed25519.log 2>&1
	./eval_aesni256gcm_encrypt  $(AESNI256GCM_NUM_ITER) $(AESNI256GCM_MSG_LEN) $(AESNI256GCM_AD_LEN) \
		> $(EVAL_DIR)/libsodium-aesni256gcm-encrypt.log 2>&1
	./eval_aesni256gcm_decrypt  $(AESNI256GCM_NUM_ITER) $(AESNI256GCM_MSG_LEN) $(AESNI256GCM_AD_LEN) \
		> $(EVAL_DIR)/libsodium-aesni256gcm-decrypt.log 2>&1
	./eval_argon2id  $(ARGON2ID_NUM_ITER) $(ARGON2ID_PASSWD_LEN) $(ARGON2ID_OUT_LEN) \
		> $(EVAL_DIR)/libsodium-argon2id.log 2>&1
	echo done

build_eval: eval_ed25519 eval_aesni256gcm_encrypt eval_aesni256gcm_decrypt eval_argon2id eval_chacha20poly1305

eval_ed25519: eval_prereqs $(EVAL_ED25519)
	$(CC) $(EVAL_ED25519) $(LIBSODIUM_AR) -o $@

eval_aesni256gcm_encrypt: eval_prereqs $(EVAL_AESNI256GCM_ENCRYPT)
	$(CC) $(EVAL_AESNI256GCM_ENCRYPT) $(LIBSODIUM_AR) -o $@

eval_aesni256gcm_decrypt: eval_prereqs $(EVAL_AESNI256GCM_DECRYPT)
	$(CC) $(EVAL_AESNI256GCM_DECRYPT) $(LIBSODIUM_AR) -o $@

eval_argon2id: eval_prereqs $(EVAL_ARGON2ID)
	$(CC) $(EVAL_ARGON2ID) $(LIBSODIUM_AR) -o $@

eval_chacha20poly1305: eval_prereqs
	:

eval_prereqs: | $(LIBSODIUM_BUILT)

libsodium.built:
	git submodule init -- $(LIBSODIUM_DIR)
	git submodule update --remote -- $(LIBSODIUM_DIR)
	git submodule foreach 'git fetch --tags'
	cd $(LIBSODIUM_DIR); \
	  	git checkout $(LIBSODIUM_TARGET_RELEASE_TAG); \
		./configure CC=$(CC)
	$(MAKE) -C $(LIBSODIUM_DIR)
	touch $(LIBSODIUM_BUILT)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean_eval:
	-rm *.o
	-rm eval_ed25519
	-rm eval_aesni256gcm_encrypt
	-rm eval_aesni256gcm_decrypt
	-rm eval_argon2id

clean: clean_eval
	-rm $(LIBSODIUM_BUILT)
	-$(MAKE) -C $(LIBSODIUM_DIR) clean
