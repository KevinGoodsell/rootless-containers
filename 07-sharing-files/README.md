# Part 7: Sharing files

Next we'll introduce a way to share files from the host system inside the
container. This is closely related to the way devices and the `resolv.conf` file
were previously shared with the container.

The updated example program adds a new option `--volume/-v` which can be given
as many times as needed. The argument takes the form `host-path:container-path`
or `host-path:container-path:mode`. `host-path` is a path to a file or directory
on the host and `container-path` is a path to a file or directory inside the
container (note that this path must already exist, so create it in the chroot
directory first). `mode` must be `rw` or `ro` for read-write or read-only. The
default if `mode` isn't provided is read-only.

The example program uses the provided parameters to bind mount files or
directories from the host similarly to how this was done with device nodes. The
following example session shows a directory and the file it contains being
shared inside the container.

    $ mkdir alpine/alpine-root/home/alpine/shared

    $ mkdir shared

    $ echo "Some text" > shared/shared-file

    $ python3 07-sharing-files/example07.py --hostname container --root alpine/alpine-root/ --volume shared:/home/alpine/shared:rw -- bash -l

    container:~$ cd shared/

    container:~/shared$ cat shared-file 
    Some text

    container:~/shared$ echo "Some new text" >> shared-file 

    container:~/shared$ exit
    logout

    $ cat shared/shared-file 
    Some text
    Some new text

In this example, the invoking user's UID is mapped to 1100 inside the container
because that's the default without a `--map-uid` option provided, and 1100
inside the container is assigned to the `alpine` user. Without a `--user`
option, the invoking user gets UID 1100 inside the container and becomes the
`alpine` user. By the same token, the files that are owned by the invoking user
and get shared inside the container also become owned by `alpine` inside the
container, and this provides the invoking user with permissions to use these
files.
