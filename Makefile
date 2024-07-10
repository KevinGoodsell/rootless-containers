.PHONY: all check clean

all: lib/libc_gen.py

tools/libc-vals: tools/libc-vals.c
	gcc --std=c17 -Wall -Wextra -o $@ $^

lib/libc_gen.py: tools/libc-vals
	./tools/libc-vals > $@

check:
	mypy --strict --exclude alpine .

clean:
	rm -f tools/libc-vals
	rm -rf lib/__pycache__
	rm -rf .mypy_cache
