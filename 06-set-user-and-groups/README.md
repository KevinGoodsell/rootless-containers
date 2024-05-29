# Part 6: Setting User and Groups

In this part we'll introduce an option for setting the user to run as within the
container. The updated example program adds the `--user` option and uses the
provided value to call `setuid(2)`.

In addition to setting the UID, it also attempts to set the user's home
directory, primary group, and supplementary groups. This part only works if the
user is found in the `passwd` database inside the container.

The updated program also sets up the environment variables inside the container.

Here's an example using the latest example program:

    $ python3 example06.py --hostname container --root ../alpine/alpine-root --user root -- bash -l

    container:~# id
    uid=0(root) gid=0(root) groups=0(root),1(bin),2(daemon),3(sys),4(adm),6(disk),10(wheel),11(floppy),20(dialout),26(tape),27(video)

    container:~# pwd
    /root

    container:~# env
    CHARSET=UTF-8
    PWD=/root
    HOME=/root
    LANG=C.UTF-8
    TERM=xterm-kitty
    SHLVL=1
    PAGER=less
    LC_COLLATE=C
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    _=/usr/bin/env

The default behavior without `--user` is to stick with the invoking user's UID.
Since the invoking user's UID is mapped to 1100 inside the user namespace, and
we created the user `alpine` inside the chroot with that UID, omitting `--user`
makes us `alpine` inside the container:

    $ python3 example06.py --hostname container --root ../alpine/alpine-root -- bash -l

    container:~$ id
    uid=1100(alpine) gid=1100(alpine) groups=1100(alpine)

The same behavior can be seen with `--user alpine` or `--user 1100`.
