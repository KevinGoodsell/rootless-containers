.PHONY: tools clean

all:

tools:
	$(MAKE) -C tools

generate: tools
	./tools/libc-vals > lib/libc_gen.py

clean:
	$(MAKE) -C tools clean
