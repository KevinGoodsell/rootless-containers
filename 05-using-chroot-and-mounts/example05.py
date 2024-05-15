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


def read_subuids(uid: int) -> range:
    name = pwd.getpwuid(uid)[0]
    return read_ids(uid, name, '/etc/subuid')


def read_subgids(gid: int) -> range:
    name = grp.getgrgid(gid)[0]
    return read_ids(gid, name, '/etc/subgid')


def read_ids(id_: int, name: str, filename: str) -> range:
    # subuid/subgid can use names or numbers, so we check for both.
    names = [str(id_), name]
    with open(filename, 'r') as f:
        for line in f:
            entry, start, count = line.split(':')
            if entry in names:
                return range(int(start), int(start) + int(count))

    raise Exception(f'User {name} not found in {filename}')


def make_id_maps(
        subids: range,
        cont_id: int | None,
        host_id: int) -> list[str]:
    '''
    Return a set of mappings formatted for use with newuidmap/newgidmap. subids
    is a set of host ids (uids or gids) for the namespace ids to be mapped to.
    Inside the namespace these will be mapped to 0.. until all have been used.
    If cont_id is provided, it is skipped in this step.

    cont_id and host_id define an extra mapping for one host id to one
    container id, generally used for mapping the user's own uid and primary
    gid. If cont_id is None no additional mapping is added.
    '''
    # Use an arbitrary large upper value for container ids, we'll just go until
    # host ids are exhausted.
    container_ids = range(10_000_000)
    container_ranges: list[range] = []
    host_ranges: list[range] = []
    if cont_id is None:
        container_ranges.append(container_ids)
        host_ranges.append(subids)
    else:
        container_ranges.append(range(cont_id, cont_id + 1))
        host_ranges.append(range(host_id, host_id + 1))

        # Make sure to exclude cont_id from container_ranges.
        c1 = range(container_ids.start, cont_id)
        c2 = range(cont_id + 1, container_ids.stop)

        # c1 and c2 can be 0-length ranges in some cases, such as cont_id == 0.
        if c1:
            container_ranges.append(c1)

        if c2:
            container_ranges.append(c2)

        host_ranges.append(subids)

    result: list[int] = []

    while host_ranges:
        # Take the first range from each, produce a mapping using as many
        # elements of both as possible, reinsert any remainder and repeat until
        # host_ranges is exhausted.
        crange = container_ranges.pop(0)
        hrange = host_ranges.pop(0)

        length = min(len(crange), len(hrange))
        result.extend([crange.start, hrange.start, length])

        # Update crange and hrange
        crange = range(crange.start + length, crange.stop)
        hrange = range(hrange.start + length, hrange.stop)

        if crange:
            container_ranges.insert(0, crange)

        if hrange:
            host_ranges.insert(0, hrange)

    return [str(x) for x in result]


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
            '--map-uid', '-m',
            type=int,
            default=1100,
            help="uid inside the container to which the current user's uid "
                 "should be mapped")
    parser.add_argument(
            '--map-gid', '-g',
            type=int,
            default=1100,
            help="gid inside the container to which the current user's gid "
                 "should be mapped")
    parser.add_argument(
            '--root', '-r',
            help='root file system')
    parser.add_argument(
            'cmd',
            nargs='+',
            help='command (and arguments) to run')

    args = parser.parse_args(sys.argv[1:])

    uid = os.geteuid()
    gid = os.getegid()

    uid_maps = make_id_maps(read_subuids(uid), args.map_uid, uid)
    gid_maps = make_id_maps(read_subgids(gid), args.map_gid, gid)

    # Make a shared memory semaphore
    sem = mmap.mmap(
            -1,
            libc.SIZEOF_SEM_T,
            mmap.MAP_SHARED | mmap.MAP_ANONYMOUS)

    libc.sem_init(sem, True, 0)

    def child() -> int:
        # Wait for parent to set up uidmap and gidmap.
        libc.sem_wait(sem)

        # Set the hostname
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

        if args.root:
            os.chroot(args.root)
            # chroot doesn't actually change the current directory:
            os.chdir(args.root)

        os.setuid(0)
        os.setgid(0)

        os.execvp(args.cmd[0], args.cmd)

    child_pid = libc.clone(
            child,
            100_000,
            signal.SIGCHLD | libc.CLONE_NEWUSER | libc.CLONE_NEWPID |
            libc.CLONE_NEWUTS | libc.CLONE_NEWNS)

    subprocess.run(['newuidmap', str(child_pid)] + uid_maps, check=True)
    subprocess.run(['newgidmap', str(child_pid)] + gid_maps, check=True)

    # Signal child that its environment is ready
    libc.sem_post(sem)

    (_, status) = os.waitpid(child_pid, 0)
    exitcode = os.waitstatus_to_exitcode(status)

    if exitcode < 0:
        print(f'child process exited with signal {-exitcode}', file=sys.stderr)
        return 1

    return exitcode


if __name__ == '__main__':
    sys.exit(main())
