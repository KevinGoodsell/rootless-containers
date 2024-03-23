import argparse
import os
import signal
import socket
import sys

from lib import libc


# Write a single string to the named file.
def write_bytes_to(b: bytes, path: bytes) -> None:
    with open(path, mode='wb') as f:
        f.write(b)


# Write an id map to the named file. The id map will map 0 in the user
# namespace to the given host_id in the host.
def write_id_map(host_id: int, path: bytes) -> None:
    line = b'0 %d 1\n' % host_id
    write_bytes_to(line, path)


# Write "deny" to the setgroups file, see user_namespace(7).
def deny_setgroups() -> None:
    write_bytes_to(b'deny', b'/proc/self/setgroups')


def main() -> int:
    parser = argparse.ArgumentParser(
            description='Run a command in a new namespace')
    parser.add_argument(
            '--hostname',
            help='set hostname in the new namespace')
    parser.add_argument(
            'cmd',
            nargs='+',
            help='command (and arguments) to run')

    args = parser.parse_args(sys.argv[1:])

    uid = os.geteuid()
    gid = os.getegid()

    def child() -> int:
        # We have to disable setgroups in order to write a gid_map.
        deny_setgroups()
        write_id_map(uid, b'/proc/self/uid_map')
        write_id_map(gid, b'/proc/self/gid_map')

        # Set the hostname
        if args.hostname:
            socket.sethostname(args.hostname)

        # Run the command
        os.execvp(args.cmd[0], args.cmd)

    child_pid = libc.clone(
            child,
            100_000,
            signal.SIGCHLD | libc.CLONE_NEWUSER | libc.CLONE_NEWPID |
            libc.CLONE_NEWUTS | libc.CLONE_NEWNS)

    (_, status) = os.waitpid(child_pid, 0)
    exitcode = os.waitstatus_to_exitcode(status)

    if exitcode < 0:
        print(f'child process exited with signal {-exitcode}', file=sys.stderr)
        return 1

    return exitcode


if __name__ == '__main__':
    sys.exit(main())
