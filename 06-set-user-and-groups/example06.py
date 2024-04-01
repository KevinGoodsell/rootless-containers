import argparse
import grp
import mmap
import os
from pathlib import Path
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


def get_user_uid(user: str) -> int:
    if user.isdigit():
        return int(user)

    return pwd.getpwnam(user).pw_uid


def main() -> int:
    parser = argparse.ArgumentParser(
            description='Run a command in a new namespace')
    parser.add_argument(
            '--hostname',
            help='set hostname in the new namespace')
    parser.add_argument(
            '--user', '-u',
            help='set user (name or UID) inside the namespace')
    parser.add_argument(
            'root',
            help='root file system')
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

        mounts = [
                ['--bind', '/dev/null', 'dev/null'],
                ['--bind', '/dev/full', 'dev/full'],
                ['--bind', '/dev/ptmx', 'dev/ptmx'],
                ['--bind', '/dev/random', 'dev/random'],
                ['--bind', '/dev/urandom', 'dev/urandom'],
                ['--bind', '/dev/zero', 'dev/zero'],
                ['--bind', '/dev/tty', 'dev/tty'],
                ['-t', 'proc', 'proc', 'proc'],
                # Sysfs can't be mounted in a user namespace unless it's also
                # in a network namespace. Apparently this has something to do
                # with accessing network devices via /sys/class/net.
                # For some reason bind mount /sys requires --rbind.
                ['--rbind', '/sys', 'sys'],
                ['--bind', '/etc/resolv.conf', 'etc/resolv.conf'],
        ]

        for *mount_args, target in mounts:
            full_target = str(Path(args.root) / target)
            subprocess.run(['mount'] + mount_args + [full_target], check=True)

        os.chroot(args.root)
        # chroot doesn't actually change the current directory:
        working_dir = args.root

        env: dict[str, str] = {}

        if 'TERM' in os.environ:
            env['TERM'] = os.environ['TERM']

        # Clear supplementary groups
        os.setgroups([])

        if args.user:
            uid = get_user_uid(args.user)
            try:
                user_info = pwd.getpwuid(uid)
                env['HOME'] = user_info.pw_dir
                working_dir = user_info.pw_dir
                os.setgid(user_info.pw_gid)
                os.initgroups(user_info.pw_name, user_info.pw_gid)
            except KeyError:
                # Don't require the uid to be found in passwd.
                pass
            os.setuid(uid)

        os.chdir(working_dir)

        os.execvpe(args.cmd[0], args.cmd, env)

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
