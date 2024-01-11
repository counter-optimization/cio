export CC=clang
export CFLAGS=-O0

.PHONY: clean

all: adder.o

adder.o: adder.c
	$(CC) $(CFLAGS) -c adder.c

test: test.c adder.o
	$(CC) $(CFLAGS) test.c adder.o -o test

clean:
	-rm *.o
	-rm test
	-rm -rf cio-build
