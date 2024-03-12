.PHONY: clean all

all: libc-vals

libc-vals: libc-vals.c
	gcc --std=c17 -Wall -Wextra -o $@ $^

clean:
	rm -f libc-vals
