# XXX As we're implementing this, consider the motivation for switching to
# clone, or rather, the motivation for not using clone in the first place.
# Supposedly clone is more complicated. Does that actually end up being true in
# python?
#
# Another consideration here: part of why clone seemed complicated was the use
# of mmap for the stack, which isn't actually necesasry and we're not doing it
# anymore.
#
# But there are a lot of complications, such as having to bundle up child
# arguments into something that can be passed as void*.
#
# Still, with the python version of clone it might actually be easier than
# unshare/fork.


import argparse
import mmap
import os
import signal
from socket import sethostname
import subprocess
import sys

from lib import libc


def main() -> int:
    parser = argparse.ArgumentParser(
            description='Run a command in a new namespace')
    parser.add_argument(
            '--hostname',
            help='set hostname in the new namespace')
    # Unfortunately there doesn't seem to be an option to allow all arguments
    # after cmd to be part of cmd, so "ls -l" has to be written as "-- ls -l"
    parser.add_argument(
            'cmd',
            nargs='+',
            help='command (and arguments) to run')

    args = parser.parse_args(sys.argv[1:])

    # Make a shared memory semaphore
    sem = mmap.mmap(
            -1,
            libc.SIZEOF_SEM_T,
            mmap.MAP_SHARED | mmap.MAP_ANONYMOUS)

    libc.sem_init(sem, True, 0)

    def child() -> int:
        # Wait for parent to set up uidmap and gidmap.
        libc.sem_wait(sem)

        if args.hostname is not None:
            sethostname(args.hostname)

        os.execvp(args.cmd[0], args.cmd)

    pid = libc.clone(
            child,
            100_000,
            signal.SIGCHLD | libc.CLONE_NEWUSER | libc.CLONE_NEWPID |
            libc.CLONE_NEWUTS)

    uid = os.geteuid()
    gid = os.getegid()

    subprocess.run(['newuidmap', str(pid), '0', str(uid), '1'], check=True)
    subprocess.run(['newgidmap', str(pid), '0', str(gid), '1'], check=True)

    # Signal child that its environment is ready
    libc.sem_post(sem)

    (_, status) = os.waitpid(pid, 0)

    return os.waitstatus_to_exitcode(status)


if __name__ == '__main__':
    sys.exit(main())
