CFLAGS=-O0 -Werror # for the eval code, don't optimize anything
CC=clang

EVAL_ED25519=eval_ed25519.o

.PHONY: clean

eval_ed25519: $(EVAL_ED25519)

%.o: %.c
	$(CC) $(CFLAGS) -c $< -o $@

clean:
	-rm *.o
