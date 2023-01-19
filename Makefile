CFLAGS=-O0 -Werror -std=c18 # for the eval code, don't optimize anything

OUR_CC=$(HOME)/llvm-project/build/bin/clang
CC=$(OUR_CC) # default to our fork of llvm's clang

LIBSODIUM_DIR=./libsodium
LIBSODIUM_AR=$(LIBSODIUM_DIR)/src/libsodium/.libs/libsodium.a
LIBSODIUM_TARGET_RELEASE_TAG=1.0.18-RELEASE

EVAL_ED25519=eval_ed25519.o
ED25519_MSG_LEN=100
ED25519_NUM_ITER=1000

.PHONY: clean libsodium eval_prereqs

all: eval_ed25519

eval_ed25519: eval_prereqs
	$(CC) $(EVAL_ED25519) $(LIBSODIUM_AR) -o $@
	./eval_ed25519  $(ED25519_NUM_ITER) $(ED25519_MSG_LEN)

eval_prereqs: libsodium

libsodium:
	git submodule init -- $(LIBSODIUM_DIR)
	git submodule update --remote -- $(LIBSODIUM_DIR)
	git submodule foreach 'git fetch --tags'
	cd $(LIBSODIUM_DIR); \
	  	git checkout $(LIBSODIUM_TARGET_RELEASE_TAG); \
		./configure CC=$(CC)
	$(MAKE) -C $(LIBSODIUM_DIR)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	-rm *.o
	-rm eval_ed25519
	-$(MAKE) -C $(LIBSODIUM_DIR) clean
