# Part 2: UID Mapping

`user_namespaces(7)` describes how uids (and gids) in the container can be
mapped to the host system:

> When a user namespace is created, it starts out without a mapping of user IDs (group  IDs)
> to  the  parent  user  namespace.   The  /proc/[pid]/uid_map and /proc/[pid]/gid_map files
> (available since Linux 3.5) expose the mappings for user and group  IDs  inside  the  user
> namespace  for  the  process  pid.  These files can be read to view the mappings in a user
> namespace and written to (once) to define the mappings.

This example program writes to the `uid_map` and `gid_map` files to map id 0 in
the user namespace to the invoking user on the host. This effectively makes the
user root inside the user namespace.

Like the previouse example, this one accepts a program to run with arguments.

With these mappings, the `id` program shows that we are root:

    $ ./example02 id
    uid=0(root) gid=0(root) groups=0(root),65534(nogroup)

The host user's files also appear to be owned by root, while root-owned files on
the host are still owned by nobody because there's no uid in the container
mapped to 0 on the host:

    $ ./example02 ls -l example02.c  /etc/passwd
    -rw-r--r-- 1 nobody nogroup 2758 Apr 29 18:14 /etc/passwd
    -rw-r--r-- 1 root   root    1910 Jun  2 19:16 example02.c

In order to write `gid_map`, we have to disable setgroups by writing "deny" to
the `/proc/self/setgroups` file. This is also described in `user_namespaces(7)`.
