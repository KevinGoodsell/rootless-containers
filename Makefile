.PHONY: all clean

all: lib/libc_gen.py

tools/libc-vals: tools/libc-vals.c
	gcc --std=c17 -Wall -Wextra -o $@ $^

lib/libc_gen.py: tools/libc-vals
	./tools/libc-vals > $@

clean:
	rm -f tools/libc-vals
	rm -rf lib/__pycache__
