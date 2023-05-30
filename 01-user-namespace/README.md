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
user namespaces at the same time, and receive the privileges granted by doing
so.

The first example program runs a program (specified on the command line) in a
new user namespace.

    $ # Since there are no user mappings yet, we're nobody inside the container
    $ go run main.go id
    uid=65534(nobody) gid=65534(nogroup) groups=65534(nogroup)

    $ # Files are also owned by nobody.
    $ go run main.go ls -l
    total 8
    -rw-r--r-- 1 nobody nogroup 1275 May 28 22:30 main.go
    -rw-r--r-- 1 nobody nogroup 1623 May 29 20:35 README.md

    $ # We should also have a full set of capabilities, but getpcaps doesn't show that. I'm not sure why.
    $ go run main.go getpcaps 0
    0: =
