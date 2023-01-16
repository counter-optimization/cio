CFLAGS=-O0 -Werror -std=c18 # for the eval code, don't optimize anything

OUR_CC=$(HOME)/llvm-project/build/bin/clang
CC=$(OUR_CC)

LIBSODIUM_DIR=libsodium-stable-1.0.18
LIBSODIUM_AR=./$(LIBSODIUM_DIR)/src/libsodium/.libs/libsodium.a

EVAL_ED25519=eval_ed25519.o
ED25519_MSG_LEN=100
ED25519_NUM_ITER=1000

.PHONY: clean libsodium

all: eval_ed25519

eval_ed25519: $(EVAL_ED25519)
	$(CC) $(EVAL_ED25519) $(LIBSODIUM_AR) -o $@
	./eval_ed25519  $(ED25519_NUM_ITER) $(ED25519_MSG_LEN)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	-rm *.o
	-rm eval_ed25519
