import os
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
    args = sys.argv[1:]

    if len(args) == 0:
        print('Need at least 1 arg', file=sys.stderr)
        return 1

    uid = os.geteuid()
    gid = os.getegid()

    libc.unshare(libc.CLONE_NEWUSER)

    # We have to disable setgroups in order to write a gid_map.
    deny_setgroups()
    write_id_map(uid, b'/proc/self/uid_map')
    write_id_map(gid, b'/proc/self/gid_map')

    os.execvp(args[0], args)


if __name__ == '__main__':
    sys.exit(main())
