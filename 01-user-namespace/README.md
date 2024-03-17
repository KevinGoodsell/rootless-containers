# Part 1: User Namespaces

Namespaces provide the isolation for containers, as well as creating an
environment where a non-privileged user can gain apparent privileges. From
`user_namespace(7)`:

> The  child  process created by clone(2) with the CLONE_NEWUSER flag starts out with a com‐
> plete set of capabilities in the new user namespace.  Likewise, a process that  creates  a
> new  user  namespace  using  unshare(2) or joins an existing user namespace using setns(2)
> gains a full set of capabilities in that namespace.
> ...
> Having  a capability inside a user namespace permits a process to perform operations (that
> require privilege) only on resources governed by that namespace.  In other words, having a
> capability  in  a user namespace permits a process to perform privileged operations on re‐
> sources that are governed by (nonuser) namespaces owned  by  (associated  with)  the  user
> namespace (see the next subsection).

So creating a user namespace grants capabilities within that namespace, without
granting any new capabilities in the parent namespace (usually the host system).

Namespaces come in several flavors (see `namespaces(7)`), but unprivileged users
can't create namespaces of any flavor other than "user", unless they create a
user namespace at the same time, and receive the privileges granted by doing
so.

The first example program runs a program (specified on the command line) in a
new user namespace. If no extra arguments are given, it instead prints its
capabilities, so we can see the effect of the new user namespace.

Since there are no uid mappings yet, running the `id` program shows that we're
nobody inside the namespace:

    $ python3 example01.py id
    uid=65534(nobody) gid=65534(nogroup) groups=65534(nogroup)

Apparent file owners are affected in the same way, all files become owned by
nobody:

    $ python3 example01.py ls -l example01.py /etc/passwd
    -rw-r--r-- 1 nobody nogroup 2940 Jun 19  2023 /etc/passwd
    -rw-r--r-- 1 nobody nogroup  564 Mar 14 20:08 example01.py

Running without arguments shows that we have a full set of effective and
permitted capabilities:

    $ python3 example01.py
    Capabilities: =ep

You don't need to know how to interpret the `=ep`, just know that it means the
process effectively has all capabilities. However, if we run getpcaps to see the
process capabilities we'll see something different:

    $ python3 example01.py getpcaps 0
    0: =

This is because the execve syscall that is used to run a different program
resets the capabilities. You can find all the details is `capabilities(7)`.
