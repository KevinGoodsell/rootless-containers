# Part 3: Clone and More Namespaces

In this part we'll add three additional namespaces: the UTS namespace, the PID
namespace, and the mount namespace.

UTS namespaces allow setting the hostname and domain name. See
`uts_namespaces(7)`.

PID namespaces allow the contained processes to have their own set of Process
IDs, numbered from 1. The first process created in the new namespace will have
PID 1. If the namespace was created with `clone(2)` then PID 1 will be the
cloned process. If the namespace was created with `unshare(2)` then PID 1 will
be the first child created in the namespace after the unshare call. See
`pid_namespaces(7)`.

Mount namespaces allow mounting file systems. These file systems will be visible
to processes within the namespace, but not outside the namespace. Mount
namespaces are created with the flag `CLONE_NEWNS`. Apparently the
non-descriptive name is due to this being the first namespace type to be
introduced, before there were plans for other types of namespaces.

We've used `unshare(2)` in previous examples, but now we'll switch to using
`clone(2)`. This will make it possible for the parent process, running in the
parent namespace, to take additional steps setting up the environment of the
child process. We'll see this starting with the next part, when we begin using
`newuidmap(1)` and `newgidmap(1)`.

In addition to using `clone(2)` and adding the new namespaces, this example
introduces more argument parsing so that the hostname can be provided as a
command line argument:

    $ python3 example03.py --hostname container -- bash

hostname reports the hostname that we provided as an argument:

    # hostname
    container

Since we are running as root inside the container, we also have permission to
change the hostname in the shell:

    # hostname newcontainer

    # hostname
    newcontainer

In future examples we'll have the option of running as a non-privileged user
inside the container, so the ability to set the hostname on the command line
will be more relevant.

The shell reports its PID as 1:

    # echo $$
    1

However, `ps` doesn't show the expected processes or PIDs:

    # ps a
        PID TTY      STAT   TIME COMMAND
        875 tty7     Ssl+ 500:41 /usr/lib/xorg/Xorg :0 -seat seat0 -auth /var/run/lightdm/root/:0 -nolisten tcp vt7 -novtswi
     128771 tty6     Ss+    0:00 /sbin/agetty -o -p -- \u --noclear tty6 linux
     139606 tty1     Ss+    0:00 /sbin/agetty -o -p -- \u --noclear tty1 linux
     139609 tty2     Ss+    0:00 /sbin/agetty -o -p -- \u --noclear tty2 linux
     139610 tty3     Ss+    0:00 /sbin/agetty -o -p -- \u --noclear tty3 linux
     139611 tty4     Ss+    0:00 /sbin/agetty -o -p -- \u --noclear tty4 linux
     139612 tty5     Ss+    0:00 /sbin/agetty -o -p -- \u --noclear tty5 linux
     187808 pts/7    Ss     0:00 bash
     ...

This is because `ps` reads process information from the `/proc` directory, and
at this point that directory is the same on the host and in the container. We
need our own `/proc` inside the container for this to work.

In some cases `ps` will error out with this strange message:

    # ps a
    fatal library error, lookup self

This is also an artifact of `/proc` not matching the running PID namespace, `ps`
fails to look up its own PID. Try running it a few more times, and it will
likely work.

Because we included the mount namespace, we can manually rectify this in the
shell:

    # mount -t proc proc /proc
    # ps a
        PID TTY      STAT   TIME COMMAND
          1 pts/5    S      0:00 bash
         26 pts/5    R+     0:00 ps a

Future examples will include mounting /proc in the code.
