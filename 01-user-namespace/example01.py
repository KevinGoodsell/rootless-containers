import os
import sys

from lib import libc, libcap


def print_caps() -> None:
    with libcap.cap_get_proc() as caps:
        bytes_caps = libcap.cap_to_text(caps)
        print(f'Capabilities: {bytes_caps.decode()}')


def main() -> int:
    args = sys.argv[1:]

    # unshare(2) moves the process to a new namespace, so it no longer shares
    # its namespace with other processes.
    libc.unshare(libc.CLONE_NEWUSER)

    if len(args) == 0:
        print_caps()
        return 0

    os.execvp(args[0], args)


if __name__ == '__main__':
    sys.exit(main())
