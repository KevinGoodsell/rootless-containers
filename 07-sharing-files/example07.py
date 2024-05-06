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


def parse_volumes(volumes: list[str] | None) -> list[tuple[str, str, int]]:
    if volumes is None:
        return []

    result: list[tuple[str, str, int]] = []
    for volume_arg in volumes:
        parts = volume_arg.split(':')

        match parts:
            case [host_part, cont_part] | [host_part, cont_part, 'ro']:
                result.append((host_part, cont_part, libc.MS_RDONLY))
            case [host_part, cont_part, 'rw']:
                result.append((host_part, cont_part, 0))
            case _:
                raise Exception(
                        f'Failed parsing --volume argument value {volume_arg}')

    return result


def main() -> int:
    parser = argparse.ArgumentParser(
            description='Run a command in a new namespace')
    parser.add_argument(
            '--hostname',
            help='set hostname in the new namespace')
    parser.add_argument(
            '--root', '-r',
            help='root file system')
    parser.add_argument(
            '--user', '-u',
            help='set user (name or UID) inside the namespace')
    parser.add_argument(
            '--volume', '-v',
            action='append',
            metavar='HOST_VOL:CONT_VOL[:MODE]',
            help='mount HOST_VOL from the host as CONT_VOL in the container '
                 'using MODE (ro or rw)')
    parser.add_argument(
            'cmd',
            nargs='+',
            help='command (and arguments) to run')

    args = parser.parse_args(sys.argv[1:])
    volumes = parse_volumes(args.volume)

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

        mounts = [
                # (source, target, type, flags)
                ('proc', 'proc', 'proc', proc_flags),
        ]

        chroot_mounts = [
                # (source, target, type, flags)
                ('/dev/null', 'dev/null', '', libc.MS_BIND),
                ('/dev/full', 'dev/full', '', libc.MS_BIND),
                ('/dev/ptmx', 'dev/ptmx', '', libc.MS_BIND),
                ('/dev/random', 'dev/random', '', libc.MS_BIND),
                ('/dev/urandom', 'dev/urandom', '', libc.MS_BIND),
                ('/dev/zero', 'dev/zero', '', libc.MS_BIND),
                ('/dev/tty', 'dev/tty', '', libc.MS_BIND),
                # Sysfs can't be mounted in a user namespace unless it's also
                # in a network namespace. Apparently this has something to do
                # with accessing network devices via /sys/class/net.
                # For some reason bind mount /sys requires recursive.
                ('/sys', 'sys', '', libc.MS_BIND | libc.MS_REC),
                ('/etc/resolv.conf', 'etc/resolv.conf', '', libc.MS_BIND),
        ]

        if args.root:
            mount_root = args.root
            mounts += chroot_mounts
        else:
            mount_root = '/'

        for host_dir, cont_dir, fstype, flags in mounts:
            full_target = str(Path(mount_root) / cont_dir)
            mount(host_dir, full_target, fstype, flags)

        # Mount --volumes
        for host_dir, cont_dir, flags in volumes:
            full_target = str(Path(mount_root) / cont_dir.lstrip('/'))
            mount(host_dir, full_target, '', libc.MS_BIND | flags)

        if args.root:
            os.chroot(args.root)
            # chroot doesn't actually change the current directory:
            os.chdir(args.root)

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
                os.setgid(user_info.pw_gid)
                os.initgroups(user_info.pw_name, user_info.pw_gid)
                # Change to the user's home dir, but only if we're in a chroot.
                # Without a chroot this is likely to fail due to permissions.
                if args.root:
                    os.chdir(user_info.pw_dir)
            except KeyError:
                # Don't require the uid to be found in passwd.
                pass
            os.setuid(uid)

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
