# Part 4: Creating a Root File System

In this part we'll explore creating a root file system to use as the file root
inside the container. We'll follow the instructions here for [creating an Alpine
Linux chroot](https://wiki.alpinelinux.org/wiki/Alpine_Linux_in_a_chroot).

XXX I guess what we're doing here is creating the example with more ID mappings
and using it to build the chroot.

First, choose a mirror from the list at https://dl-cdn.alpinelinux.org/alpine/MIRRORS.txt

From that mirror, navigate to the list of packages for your architecture to find
the `apk-tools-static` package and copy the link.

Download the file:

    $ curl -LO http://mirrors.edge.kernel.org/alpine/latest-stable/main/x86_64/apk-tools-static-2.14.0-r5.apk

Unpack the file:

    $ tar -xzf apk-tools-static-2.14.0-r5.apk

Enter our container in order to perform the installation:

    $ # XXX Not the real location
    $ python3 05-more-id-mappings/example04.py -- bash

Now that we have root access, install the base system:

    # ./sbin/apk.static -X http://mirrors.edge.kernel.org/alpine/latest-stable/main -U --allow-untrusted -p alpine-root --initdb add alpine-base
    fetch http://mirrors.edge.kernel.org/alpine/latest-stable/main/x86_64/APKINDEX.tar.gz
    (1/25) Installing alpine-baselayout-data (3.4.3-r2)
    (2/25) Installing musl (1.2.4_git20230717-r4)
    (3/25) Installing busybox (1.36.1-r15)
    Executing busybox-1.36.1-r15.post-install
    (4/25) Installing busybox-binsh (1.36.1-r15)
    (5/25) Installing alpine-baselayout (3.4.3-r2)
    Executing alpine-baselayout-3.4.3-r2.pre-install
    Executing alpine-baselayout-3.4.3-r2.post-install
    (6/25) Installing ifupdown-ng (0.12.1-r4)
    (7/25) Installing libcap2 (2.69-r1)
    (8/25) Installing openrc (0.52.1-r2)
    Executing openrc-0.52.1-r2.post-install
    (9/25) Installing mdev-conf (4.6-r0)
    (10/25) Installing busybox-mdev-openrc (1.36.1-r15)
    (11/25) Installing alpine-conf (3.17.2-r0)
    (12/25) Installing alpine-keys (2.4-r1)
    (13/25) Installing alpine-release (3.19.1-r0)
    (14/25) Installing ca-certificates-bundle (20240226-r0)
    (15/25) Installing libcrypto3 (3.1.4-r5)
    (16/25) Installing libssl3 (3.1.4-r5)
    (17/25) Installing ssl_client (1.36.1-r15)
    (18/25) Installing zlib (1.3.1-r0)
    (19/25) Installing apk-tools (2.14.0-r5)
    (20/25) Installing busybox-openrc (1.36.1-r15)
    (21/25) Installing busybox-suid (1.36.1-r15)
    (22/25) Installing scanelf (1.3.7-r2)
    (23/25) Installing musl-utils (1.2.4_git20230717-r4)
    (24/25) Installing libc-utils (0.7.2-r5)
    (25/25) Installing alpine-base (3.19.1-r0)
    Executing busybox-1.36.1-r15.trigger
    OK: 10 MiB in 25 packages

The next step in the document is creating device nodes. We won't do that because
adding device nodes in a rootless user namespace isn't permitted. We'll use bind
mounts instead, but we'll be doing that in the example program rather than
during the chroot setup, since the bind mounts will go away when the namespace
exits.

Likewise, we will leave out other mounts and name resolution during setup and do
them in the example program.

Prepare APK repositories:

    # echo http://mirrors.edge.kernel.org/alpine/latest-stable/main > alpine-root/etc/apk/repositories


Devices in debian pod:

console
pts (not bind)
mqueue (not bind)
shm (not bind)
null
zero
full
tty
random
urandom

Similarly, there are a number mounts under /proc, some of which are /dev/null.
Not sure if we need to do these.


We should also check the mount permissions for these.

XXX We'll also skip adding procfs since it will be added in the script, and that
seems like it will apply to sysfs also.

XXX Maybe resolv.conf should also be mounted? Looks like podman possibly makes
copies of some things, resolv.conf, hosts, hostname, and bind mounts them into
the container. Not sure if this is under the control of the image.

* The chroot needs additional IDs, for example it won't give the right ownership
  for /etc/shadow
