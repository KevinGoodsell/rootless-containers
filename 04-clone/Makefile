.PHONY: clean check

example04: example04.cpp
	g++ --std=c++20 -Wall -Wextra -o $@ $^

check:
	#clang-tidy --extra-arg=-std=c++17 "--checks=*,-llvmlibc-*,-modernize-use-trailing-return-type,-altera-struct-pack-align" example04.cpp
	clang-tidy --extra-arg=-std=c++20 "--checks=*,-llvmlibc-*,-fuchsia-*,-altera-*" example04.cpp

clean:
	rm example04
