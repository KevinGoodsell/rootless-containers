# Part 5: Using chroot and Mounts

In this part we'll use the root file system we set up in Part 4 as the file
system for our container. We'll add mounts, and use `chroot(2)` to make it the
root for processes running inside the container.

Most of what we mount in the container will be bind mounts, which means we're
just sharing part of a file system from the host inside the container. `/proc`
will be a new mount, not a bind mount (which is necessary in order to have a
view of our own PID namespace rather than the parent namespace, as we saw back
in Part 3).

The example program also bind mounts `/etc/resolv.conf` from the host system to
enable name resolution by just mirroring what the host is using. A static copy
of the file could also work depending on the situation, but this approach causes
the container file to be updated when the host file is updated, since they are
just different views of the same file.

The updated example program accepts a new option to specify the path to the root
file system:

    $ python3 example05.py --hostname container --root ../alpine/alpine-root/ -- ash -l

Note that now the program to run is `ash` instead of `bash`. The shell in the
base Alpine system is `ash`, and `bash` isn't available unless you install it
separately. 

Now that we're inside the container with the new root file system, we can do
things like install additional software:

    # apk update
    fetch http://mirrors.edge.kernel.org/alpine/latest-stable/main/x86_64/APKINDEX.tar.gz
    v3.19.1-298-g03c4df03632 [http://mirrors.edge.kernel.org/alpine/latest-stable/main]
    OK: 5441 distinct packages available

    # apk add bash
    (1/4) Installing ncurses-terminfo-base (6.4_p20231125-r0)
    (2/4) Installing libncursesw (6.4_p20231125-r0)
    (3/4) Installing readline (8.2.1-r2)
    (4/4) Installing bash (5.2.21-r0)
    Executing bash-5.2.21-r0.post-install
    Executing busybox-1.36.1-r15.trigger
    OK: 12 MiB in 29 packages

We can also add a non-root user to use in future parts:

    # adduser -u 1100 -s /bin/bash alpine

Here we're using 1100 for the new user's UID and GID. This is the same UID and
GID that the `--map-uid` and `--map-gid` options use by default, and we're using
them here so that the invoking user's UID and GID will be mapped to the new
`alpine` user's UID and GID. Later this will make it convenient to share files
from the host system into the container. We could use any UID and GID that is
available inside the container, as long as we specify it with the `--map-uid`
and `--map-gid` options, and then use that ID when creating the user. However,
the UID and GID mappings used with a given chroot should probably remain
consistent throughout the creation and use of the chroot. Once the chroot has
been created, changing the UID and GID mappings can result in unexpected
ownership of files inside the chroot and that could break a lot of things.

You might notice various things that are still leaking in from the host
environment. For example, `env` may show a lot of environment variables that
aren't relevant inside the container. Depending on your groups in the host
system, `id` might show a lot of `nobody` groups:

    # id
    uid=0(root) gid=0(root) groups=65534(nobody),65534(nobody),65534(nobody),65534(nobody),65534(nobody),65534(nobody),65534(nobody),65534(nobody),65534(nobody),65534(nobody),65534(nobody),65534(nobody),65534(nobody),1100(alpine)
