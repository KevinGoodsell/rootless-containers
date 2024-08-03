# Rootless Containers

Inspired by Liz Rice's presentation
[Rootless Containers From Scratch](https://www.youtube.com/watch?v=jeTKgAEyhsA).

This is a series of README files presenting the ideas behind rootless containers
and examples implementing those ideas.

This isn't necessarily the *right* way to do these things, or the way they are
done in any particular software, it's just a way they might be done. My goal was
to try it out myself to better understand how things work, without much
reference to any existing solution.

# Requirements

The examples were tested on Debian Linux using Python 3.11 on x86_64, but should
probably work on any Linux with at least Python 3.11 on x86_64. Other
architectures might work, but may require regenerating the `libc_gen.py` file,
instructions below.

# How To Use The Examples

Each part is in its own directory, and the shell commands in the `README.md`
files assume that the shell session starts in the same directory as the
`README.md` and example Python file.

To run the examples you'll need the repository root directory in your
`PYTHONPATH` environment variable, so that Python can find the utility libraries
under the `lib` directory. You can do this manually by doing something like this
in the repository root:

    $ export PYTHONPATH=$(pwd)

If your shell is bash, you can instead run the `shell` program in the root of
the repository, which starts a subshell with `PYTHONPATH` already set, and adds
`(rootless)` to the prompt so that you can see that you're in this subshell. To
return to your original shell just use `exit`.

# Python Libraries

The `lib` subdirectory contains some Python utility libraries used in the
examples. Most of these are wrappers for functions that are not available in the
Python standard library (as of Python 3.11). Examples include `cap_get_proc`
from `libcap`, and `clone`, `unshare`, and `mount` from `libc`.

Several constants that are used with these functions are included in
`libc_gen.py`. This file is generated from a small C program to make it easy to
collect the constants. It might be necessary to regenerate this file at some
point if things change, or on architectures other than the original (x86_64).

# Building

Though the examples should run without a build step, if you need to regenerate
`libc_gen.py` you can use the included Makefile:

    $ make all

There's also a `check` target to run static checking on the Python code.
