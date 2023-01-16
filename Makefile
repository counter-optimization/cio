CFLAGS=-O0 -Werror # for the eval code, don't optimize anything

OUR_CC=$(HOME)/llvm-project/build/bin/clang
CC=$(OUR_CC)

LIBSODIUM_DIR=libsodium-stable-1.0.18

EVAL_ED25519=eval_ed25519.o

.PHONY: clean libsodium

all: libsodium eval_ed25519_normal

eval_ed25519_hardened: $(EVAL_ED25519)
	LIBSODIUM_ARCHIVES=find $(LIBSODIUM_DIR) -name *.ar

eval_ed25519_normal: $(EVAL_ED25519)
	LIBSODIUM_ARCHIVES=find $(LIBSODIUM_DIR) -name *.ar
	echo $$LIBSODIUM_ARCHIVES

libsodium:
	cd $(LIBSODIUM_DIR); /configure CC=$(CC)
	$(MAKE) -C $(LIBSODIUM_DIR)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	-rm *.o
