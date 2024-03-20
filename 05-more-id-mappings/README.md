# Part 4: Using clone Instead of unshare

Next it would be nice to map more UIDs and GIDs in the container. However, we're
not quite ready for that. Up to this point we've configured UID and GID mappings
by writing to the `uid_map` and `gid_map` files, but there are restrictions on
how these files can be written that will make things difficult for us. In
particular, writing multiple lines is forbidden unless the writing process has
the capability `CAP_SETUID` in the **parent** namespace (this is described in
`user_namespaces(7)`). Having capabilities in the parent namespace isn't an
option for rootless containers. Instead, we'll switch to using the programs
`newuidmap(1)` and `newgidmap(1)` to write our mappings. These binaries are
setuid root, allowing them to use extra capabilities that the invoking user
doesn't possess.

While the documentation isn't explicit about it, `newuidmap` and `newgidmap`
probably have to be run in the parent namespace. Part of what they do is to
check whether the user is allowed to use the subuids and subgids that are
requested (more on that in the next part), and this requires knowing who the
running user is. Since this happens before IDs are mapped in the child
namespace, there's no mapped user to check against.

Running commands in the parent namespace presents a new problem. Up until now
we've used `unshare(2)` to create our new namespaces, and `fork(2)` inside the
namespace to create a process with PID 1. Now we need a parent process that is
in the parent namespace, so we can't unshare before forking. We could possibly
fork, then unshare, then fork again, but this will start to get messy. Instead,
we'll switch to using `clone(2)` to create our namespaces and to create the
first process (PID 1) inside the new namespaces. Calling `clone` is more
involved than calling `unshare` and `fork`, so for simple cases `unshare` and
`fork` might be preferable, but now we're moving beyond such cases.
