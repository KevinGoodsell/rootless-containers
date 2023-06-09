# Part 3: More Namespaces

In this part we'll add two additional namespaces, the UTS namespace and the PID
namespace.

UTS namespaces allow setting the hostname and domain name. See
`uts_namespaces(7)`.

PID namespaces allow the contained processes to have their own set of Process
IDs, numbered from 1. The first process created in the new namespace will have
PID 1. If the namespace was created with `clone(2)` then PID 1 will be the
cloned process. If the namespace was created with `unshare(2)` then PID 1 wil be
the first child created in the namespace after the unshare call. See
`pid_namespaces(7)`.

This example program expands on the previous example by adding the PID and UTS
namespaces and adds more argument parsing so that the hostname can be provided
as a command line argument. It also adds a `fork(2)` call to establish PID 1 in
the new PID namespace, so the provided command runs as PID 1.

    $ ./example03 --hostname container -- bash

hostname reports the hostname that we provided as an argument:

    # hostname
    container

Since we are running as root inside the container, we also have permissions
Change the hostname ourselves, but this won't work later when we are running as
a normal user:

    # hostname newcontainer

    # hostname
    newcontainer

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