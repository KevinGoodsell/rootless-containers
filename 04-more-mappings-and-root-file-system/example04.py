import argparse
import grp
import mmap
import os
import pwd
import signal
from socket import sethostname
import subprocess
import sys

from lib import libc


def read_subuids(uid: int) -> tuple[int, int]:
    name = pwd.getpwuid(uid)[0]
    return read_ids(uid, name, '/etc/subuid')


def read_subgids(gid: int) -> tuple[int, int]:
    name = grp.getgrgid(gid)[0]
    return read_ids(gid, name, '/etc/subgid')


def read_ids(id_: int, name: str, filename: str) -> tuple[int, int]:
    # subuid/subgid can use names or numbers, so we check for both.
    names = [str(id_), name]
    with open(filename, 'r') as f:
        for line in f:
            entry, start, count = line.split(':')
            if entry in names:
                return (int(start), int(count))

    raise Exception(f'User {name} not found in {filename}')


def mount(source: str, target: str, filesystemtype: str,
          mountflags: int) -> None:
    '''
    Like mount(2), with the added step of remounting read-only for bind mounts
    with the MS_RDONLY flag, similar to what mount(8) does. mount(2) ignores
    most other flags (MS_RDONLY included) when MS_BIND is present.
    '''

    libc.mount(source, target, filesystemtype, mountflags)

    ro_bind = libc.MS_BIND | libc.MS_RDONLY
    if mountflags & ro_bind == ro_bind:
        libc.mount('', target, '',
                   libc.MS_REMOUNT | libc.MS_BIND | libc.MS_RDONLY)


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

    subuids = read_subuids(uid)
    subgids = read_subgids(gid)

    uid_maps = [
            '0', str(uid), '1',
            '1', str(subuids[0]), str(subuids[1]),
    ]

    gid_maps = [
            '0', str(gid), '1',
            '1', str(subgids[0]), str(subgids[1]),
    ]

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

        proc_flags = (libc.MS_NOSUID | libc.MS_NODEV | libc.MS_RELATIME |
                      libc.MS_NOEXEC)

        mount('proc', '/proc', 'proc', proc_flags)

        os.execvp(args.cmd[0], args.cmd)

    pid = libc.clone(
            child,
            100_000,
            signal.SIGCHLD | libc.CLONE_NEWUSER | libc.CLONE_NEWPID |
            libc.CLONE_NEWUTS | libc.CLONE_NEWNS)

    subprocess.run(['newuidmap', str(pid)] + uid_maps, check=True)
    subprocess.run(['newgidmap', str(pid)] + gid_maps, check=True)

    # Signal child that its environment is ready
    libc.sem_post(sem)

    (_, status) = os.waitpid(pid, 0)
    exitcode = os.waitstatus_to_exitcode(status)

    if exitcode < 0:
        print(f'child process exited with signal {-exitcode}', file=sys.stderr)
        return 1

    return exitcode


if __name__ == '__main__':
    sys.exit(main())
