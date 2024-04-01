# Part 6: Setting User and Groups

In this part we'll introduce an option for setting the user to run as within the
container. The updated example program adds the `--user` option and uses the
provided value to call `setuid(2)`.

In addition to setting the UID, it also attempts to set the user's home
directory, primary group, and supplementary groups. This part only works if the
user is found in the `passwd` database inside the container.

The updated program also sets up the environment variables inside the container.

Here's an example using the latest example program:

    $ python3 06-set-user-and-groups/example06.py --user alpine --hostname container alpine/alpine-root -- bash -l

    container:~$ id
    uid=1000(alpine) gid=1000(alpine) groups=1000(alpine)

    container:~$ pwd
    /home/alpine

    container:~$ env
    CHARSET=UTF-8
    PWD=/home/alpine
    HOME=/home/alpine
    LANG=C.UTF-8
    TERM=xterm-kitty
    SHLVL=1
    PAGER=less
    LC_COLLATE=C
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
    _=/usr/bin/env
