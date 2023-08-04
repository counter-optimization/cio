CFLAGS=-O0 -Werror -std=c18 # for the eval code, don't optimize anything

export LLVM_HOME=$(HOME)/llvm-project/build
export OUR_CC=$(HOME)/llvm-project/build/bin/clang
export CC=$(OUR_CC) # default to our fork of llvm's clang

export NUM_MAKE_JOB_SLOTS=8

export IMPLEMENTATION_TESTING_DIR=./implementation-testing

MITIGATIONS=--ss #--cs default to silent store followed by comp simp
MITIGATIONS_STR=$(subst ${null} ${null},,$(subst -,,$(subst ${null} --${null},-,$(MITIGATIONS))))

CHECKER_DIR=./checker
CHECKER_PLUGIN_PATH=$(CHECKER_DIR)/bap/interval
CHECKER_BUILT=checker.built

LIBSODIUM_DIR=./libsodium
LIBSODIUM_AR=$(LIBSODIUM_DIR)/src/libsodium/.libs/libsodium.a
# LIBSODIUM_AR ::= $(shell find $(LIBSODIUM_DIR) -name 'libsodium.a' -o -name 'libsodium.ar')
LIBSODIUM_TARGET_RELEASE_TAG=1.0.18-RELEASE
LIBSODIUM_BUILT=libsodium.built
LIBSODIUM_BUILT_AR=$(LIBSODIUM_BUILT).$(MITIGATIONS_STR)/libsodium.a

EVAL_MSG_LEN=100
EVAL_MSG ::= $(shell timeout 0.01s cat /dev/urandom | tr -dc '[:graph:]' | fold -w $(EVAL_MSG_LEN) | head -n 1)

EVAL_ED25519=eval_ed25519.o
ED25519_NUM_ITER=1000
ED25519_WARMUP_ITER=25

EVAL_AESNI256GCM_ENCRYPT=eval_aesni256gcm_encrypt.o
EVAL_AESNI256GCM_DECRYPT=eval_aesni256gcm_decrypt.o
AESNI256GCM_AD_LEN=100
AESNI256GCM_NUM_ITER=1000
AESNI256GCM_WARMUP_ITER=25

EVAL_ARGON2ID=eval_argon2id.o
ARGON2ID_OUT_LEN=100
ARGON2ID_NUM_ITER=100
ARGON2ID_WARMUP_ITER=25

EVAL_CHACHA20_POLY1305_ENCRYPT=eval_chacha20_poly1305_encrypt.o
EVAL_CHACHA20_POLY1305_DECRYPT=eval_chacha20_poly1305_decrypt.o
CHACHA20_POLY1305_AD_LEN=100
CHACHA20_POLY1305_NUM_ITER=1000
CHACHA20_POLY1305_WARMUP_ITER=25

EVAL_START_TIME ::= $(shell TZ='America/Los_Angeles' date +%F-%H:%M:%S-%Z)
EVAL_DIR=$(EVAL_START_TIME)-eval
CIO_BUILD_DIR=$(EVAL_START_TIME)-cio-build
FILE_EVAL_CMDS=$(EVAL_DIR)/eval-cmds.txt
FILE_WHICH_CC_FOR_EVAL_BUILD=$(EVAL_DIR)/eval-cc.txt
FILE_WHICH_CFLAGS_FOR_EVAL_BUILD=$(EVAL_DIR)/eval-cflags.txt
FILE_WHICH_MITIGATIONS_FOR_EVAL_BUILD=$(EVAL_DIR)/eval-mitigations.txt
FILE_WHICH_CC_FOR_LIBSODIUM_BUILD=$(EVAL_DIR)/libna-cc.txt #todo
FILE_WHICH_CFLAGS_FOR_LIBSODIUM_BUILD=$(EVAL_DIR)/libna-cflags.txt #todo

.PHONY: clean eval_prereqs run_eval build_eval

all: build_eval

run_eval: build_eval
	mkdir $(EVAL_DIR)
	cp Makefile $(EVAL_DIR)
	cp $(LIBSODIUM_BUILT_AR) $(EVAL_DIR)
	cp *.c $(EVAL_DIR)
	echo "$(CC)" > $(FILE_WHICH_CC_FOR_EVAL_BUILD)
	echo "$(CFLAGS)" > $(FILE_WHICH_CFLAGS_FOR_EVAL_BUILD)
	echo "$(MITIGATIONS)" > $(FILE_WHICH_MITIGATIONS_FOR_EVAL_BUILD)
	echo "$(CC)" > $(FILE_WHICH_CC_FOR_LIBSODIUM_BUILD) #todo
	echo "$(CFLAGS)" > $(FILE_WHICH_CFLAGS_FOR_LIBSODIUM_BUILD) #todo

	echo "./eval_ed25519  $(ED25519_NUM_ITER) $(ED25519_WARMUP_ITER) $(EVAL_MSG)"\
		> $(FILE_EVAL_CMDS)
	stat --format="%s" eval_ed25519 > $(EVAL_DIR)/libsodium-ed25519-bytesize.txt
	./eval_ed25519  $(ED25519_NUM_ITER) $(ED25519_WARMUP_ITER) $(EVAL_MSG) \
		$(EVAL_DIR)/libsodium-ed25519-cyclecounts.csv \
		$(EVAL_DIR)/libsodium-ed25519-dynhitcounts.csv \
		> $(EVAL_DIR)/libsodium-ed25519.log 2>&1

	echo "./eval_chacha20_poly1305_encrypt $(CHACHA20_POLY1305_NUM_ITER) $(CHACHA20_POLY1305_WARMUP_ITER) $(EVAL_MSG) $(CHACHA20_POLY1305_AD_LEN)" \
		>> $(FILE_EVAL_CMDS)
	stat --format="%s" eval_chacha20_poly1305_encrypt > $(EVAL_DIR)/libsodium-chacha20-poly1305-encrypt-bytesize.txt
	./eval_chacha20_poly1305_encrypt $(CHACHA20_POLY1305_NUM_ITER) $(CHACHA20_POLY1305_WARMUP_ITER) $(EVAL_MSG) $(CHACHA20_POLY1305_AD_LEN) \
		$(EVAL_DIR)/libsodium-chacha20-poly1305-encrypt-cyclecounts.csv $(EVAL_DIR)/libsodium-chacha20-poly1305-encrypt-dynhitcounts.csv\
		> $(EVAL_DIR)/libsodium-chacha20-poly1305-encrypt.log 2>&1

	echo "./eval_chacha20_poly1305_decrypt $(CHACHA20_POLY1305_NUM_ITER) $(CHACHA20_POLY1305_WARMUP_ITER) $(EVAL_MSG) $(CHACHA20_POLY1305_AD_LEN)" \
		>> $(FILE_EVAL_CMDS)
	stat --format="%s" eval_chacha20_poly1305_decrypt > $(EVAL_DIR)/libsodium-chacha20-poly1305-decrypt-bytesize.txt
	./eval_chacha20_poly1305_decrypt $(CHACHA20_POLY1305_NUM_ITER) $(CHACHA20_POLY1305_WARMUP_ITER) $(EVAL_MSG) $(CHACHA20_POLY1305_AD_LEN) \
		$(EVAL_DIR)/libsodium-chacha20-poly1305-decrypt-cyclecounts.csv $(EVAL_DIR)/libsodium-chacha20-poly1305-decrypt-dynhitcounts.csv \
		> $(EVAL_DIR)/libsodium-chacha20-poly1305-decrypt.log 2>&1

	echo "./eval_aesni256gcm_encrypt  $(AESNI256GCM_NUM_ITER) $(AESNI256GCM_WARMUP_ITER) $(EVAL_MSG) $(AESNI256GCM_AD_LEN)" \
		>> $(FILE_EVAL_CMDS)
	stat --format="%s" eval_aesni256gcm_encrypt > $(EVAL_DIR)/libsodium-aesni256gcm-encrypt-bytesize.txt
	./eval_aesni256gcm_encrypt  $(AESNI256GCM_NUM_ITER) $(AESNI256GCM_WARMUP_ITER) $(EVAL_MSG) $(AESNI256GCM_AD_LEN) \
		$(EVAL_DIR)/libsodium-aesni256gcm-encrypt-cyclecounts.csv $(EVAL_DIR)/libsodium-aesni256gcm-encrypt-dynhitcounts.csv \
		> $(EVAL_DIR)/libsodium-aesni256gcm-encrypt.log 2>&1

	echo "./eval_aesni256gcm_decrypt  $(AESNI256GCM_NUM_ITER) $(AESNI256GCM_WARMUP_ITER) $(EVAL_MSG) $(AESNI256GCM_AD_LEN)" \
		>> $(FILE_EVAL_CMDS)
	stat --format="%s" eval_aesni256gcm_decrypt > $(EVAL_DIR)/libsodium-aesni256gcm-decrypt-bytesize.txt
	./eval_aesni256gcm_decrypt  $(AESNI256GCM_NUM_ITER) $(AESNI256GCM_WARMUP_ITER) $(EVAL_MSG) $(AESNI256GCM_AD_LEN) \
		$(EVAL_DIR)/libsodium-aesni256gcm-decrypt-cyclecounts.csv $(EVAL_DIR)/libsodium-aesni256gcm-decrypt-dynhitcounts.csv \
		> $(EVAL_DIR)/libsodium-aesni256gcm-decrypt.log 2>&1

	echo "./eval_argon2id  $(ARGON2ID_NUM_ITER) $(ARGON2ID_WARMUP_ITER) $(EVAL_MSG) $(ARGON2ID_OUT_LEN)" \
		>> $(FILE_EVAL_CMDS)
	stat --format="%s" eval_argon2id > $(EVAL_DIR)/libsodium-argon2id-bytesize.txt
	./eval_argon2id  $(ARGON2ID_NUM_ITER) $(ARGON2ID_WARMUP_ITER) $(EVAL_MSG) $(ARGON2ID_OUT_LEN) \
		$(EVAL_DIR)/libsodium-argon2id-cyclecounts.csv $(EVAL_DIR)/libsodium-argon2id-dynhitcounts.csv \
		> $(EVAL_DIR)/libsodium-argon2id.log 2>&1
	echo done

build_eval: eval_ed25519 eval_aesni256gcm_encrypt eval_aesni256gcm_decrypt eval_argon2id eval_chacha20_poly1305_encrypt eval_chacha20_poly1305_decrypt

eval_ed25519: eval_prereqs $(EVAL_ED25519)
	$(CC) $(EVAL_ED25519) $(LIBSODIUM_BUILT_AR) -o $@

eval_aesni256gcm_encrypt: eval_prereqs $(EVAL_AESNI256GCM_ENCRYPT)
	$(CC) $(EVAL_AESNI256GCM_ENCRYPT) $(LIBSODIUM_BUILT_AR) -o $@

eval_aesni256gcm_decrypt: eval_prereqs $(EVAL_AESNI256GCM_DECRYPT)
	$(CC) $(EVAL_AESNI256GCM_DECRYPT) $(LIBSODIUM_BUILT_AR) -o $@

eval_chacha20_poly1305_encrypt: eval_prereqs $(EVAL_CHACHA20_POLY1305_ENCRYPT)
	$(CC) $(EVAL_CHACHA20_POLY1305_ENCRYPT) $(LIBSODIUM_BUILT_AR) -o $@

eval_chacha20_poly1305_decrypt: eval_prereqs $(EVAL_CHACHA20_POLY1305_DECRYPT)
	$(CC) $(EVAL_CHACHA20_POLY1305_DECRYPT) $(LIBSODIUM_BUILT_AR) -o $@

eval_argon2id: eval_prereqs $(EVAL_ARGON2ID)
	$(CC) $(EVAL_ARGON2ID) $(LIBSODIUM_BUILT_AR) -o $@

eval_prereqs: $(LIBSODIUM_BUILT_AR) $(CHECKER_BUILT)

libsodium_init:
	git submodule init -- $(LIBSODIUM_DIR)
	git submodule update --remote -f -- $(LIBSODIUM_DIR)
	git submodule foreach 'git fetch --tags'
	cd $(LIBSODIUM_DIR); \
		git checkout $(LIBSODIUM_TARGET_RELEASE_TAG); \
		git apply ../chacha20_impl_renames.patch; \
		git apply ../poly1305_impl_renames.patch; \
		git apply ../chacha20_refref_rename.patch; \
		git apply ../argon2_impl_renames.patch; \
		git apply ../salsa20_ref_impl.patch
	touch libsodium_init

$(LIBSODIUM_BUILT_AR): checker
	$(MAKE) clean_libsodium
	./cio --skip-double-check --is-libsodium $(MITIGATIONS) --crypto-dir=./libsodium --config-file=./libsodium.uarch_checker.config -j 1 -b $(CIO_BUILD_DIR) -c $(CC)
	mkdir $(LIBSODIUM_BUILT).$(MITIGATIONS_STR)
	cp $(LIBSODIUM_AR) $(LIBSODIUM_BUILT_AR)

checker: $(CHECKER_BUILT)

checker_init:
	git submodule init -- $(CHECKER_DIR)
	git submodule update --remote -- $(CHECKER_DIR)
	touch checker_init

$(CHECKER_BUILT): checker_init
	$(MAKE) -e -C $(CHECKER_PLUGIN_PATH) BAPBUILD_JOB_SLOTS=$(NUM_MAKE_JOB_SLOTS) debug
	touch $(CHECKER_BUILT)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean_eval:
	-rm *.o
	-rm eval_ed25519
	-rm eval_aesni256gcm_encrypt
	-rm eval_aesni256gcm_decrypt
	-rm eval_argon2id
	-rm -f eval_chacha20_poly1305_encrypt
	-rm -f eval_chacha20_poly1305_decrypt

clean_libsodium:
	find libsodium -type f -name '*.secrets.csv' -delete
	find libsodium -type f -name '*.ciocc' -delete
	find libsodium -type f -name '*.ll' -delete
	find libsodium -type f -name '*.mir' -delete
	find libsodium -type f -name '*.s' -delete
	-rm libsodium_init
	$(MAKE) libsodium_init

clean_checker:
	-rm $(CHECKER_BUILT)
	-$(MAKE) -C $(CHECKER_PLUGIN_PATH) clean

clean: clean_eval clean_libsodium


