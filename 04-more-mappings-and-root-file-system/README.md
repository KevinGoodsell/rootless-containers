# Part 4: More User Mappings, Creating a Root File System

In this part we'll update the example program to map more user and group IDs,
then we'll use the update example program to build a root file system to use in
the next parts.

## Updating the Example Program With Additional Mappings

The example program updates the uid and gid mapping in a few ways. First, it
switches to using `newuidmap` and `newgidmap`. Second, it reads the `subuid` and
`subgid` files and uses them to map multiple IDs. Additionally, and unrelated to
the ID mappings, this example program incorporates mounting the `/proc` file
system, fixing the `ps` problems that were noted in the previous example.

The `newuidmap` and `newgidmap` programs are used instead of directly writing to
`/proc/self/uid_map` and `/proc/self/gid_map`. This is because there are
restrictions on writing to `uid_map` and `gid_map` that make it impossible to
map multiple IDs without having elevated permissions, as described in
`user_namespaces(7)`. `newuidmap` and `newgidmap` bypass the need for elevated
permissions because they are setuid binaries.

Using these programs requires that they be invoked in the parent namespace,
after the child namespace and process have been created, so the example program
uses a semaphore to block the child process until the parent finishes setting up
the mappings.

`newuidmap` is invoked with the child process PID and the UID mappings this way:

    $ newuidmap PID USER_NS_UID PARENT_NS_UID COUNT [USER_NS_UID PARENT_NS_UID COUNT [...]]

This maps `COUNT` uids starting at `USER_NS_UID` in the user namespace and
`PARENT_NS_UID` in the parent namespace. The uids in the parent namespace have
to be uids that the user is allowed to use, which includes the user's own uid,
and the set of uids granted to the user in the `/etc/subuid` file.

The same applies to `newgidmap`, and the `/etc/subgid` file.

For more information, see the man pages `newuidmap(1)`, `newgidmap(1)`,
`subuid(5)`, and `subgid(5)`.

## Using the Example Program to Create a Root File System

Now that the example program maps additional uids and gids, it can be used to
set up a root file system that can serve as the root for our pseudo-containers
going forward. We'll follow (more or less) the instructions here for [creating
an Alpine Linux chroot](https://wiki.alpinelinux.org/wiki/Alpine_Linux_in_a_chroot).

First, choose a mirror from [this
list](https://dl-cdn.alpinelinux.org/alpine/MIRRORS.txt). I'm using
http://mirrors.edge.kernel.org/alpine/.

From that mirror, navigate to the list of packages for your architecture to find
the `apk-tools-static` package and copy the link.

Download the file:

    $ curl -LO http://mirrors.edge.kernel.org/alpine/latest-stable/main/x86_64/apk-tools-static-2.14.0-r5.apk

Unpack the file:

    $ tar -xzf apk-tools-static-2.14.0-r5.apk

Next we'll install the Alpine base system. Since this will need to perform
privileged actions, we'll do it inside the namespace our example program
creates:

    $ python3 04-more-mappings-and-root-file-system/example04.py -- bash

Now that we have root access, install the base system:

    # ./sbin/apk.static -X http://mirrors.edge.kernel.org/alpine/latest-stable/main -U --allow-untrusted -p alpine-root --initdb add alpine-base

The next step in the document is creating device nodes. We won't do that because
adding device nodes in a rootless user namespace isn't permitted. We'll see the
alternative approach for this in the next part.

Likewise, we will leave out mounts and name resolution. These will be handled in
the next part using a similar approach to device nodes.

For now, we will create some files that we'll need later:

    # touch alpine-root/etc/resolv.conf
    # touch alpine-root/dev/{null,full,ptmx,random,urandom,zero,tty}

Prepare APK repositories:

    # echo http://mirrors.edge.kernel.org/alpine/latest-stable/main > alpine-root/etc/apk/repositories

That's it for setting up the root file system.

So what did the extra uid and gid mappings do for us? Well, not much that you've
been able to see yet. You would probably see some errors during the base system
installation if you didn't have the extra mappings because some of the
installation needs to do things like changing file ownership, and this can only
work if there are other ids to own the files. If you check the ownership of the
`/etc/shadow` file inside and outside the user namespace, you'll see one small
effect of having the extra mappings:

    # stat alpine-root/etc/shadow
      File: alpine-root/etc/shadow
      Size: 421       	Blocks: 8          IO Block: 4096   regular file
    Device: 253,2	Inode: 2129703     Links: 1
    Access: (0640/-rw-r-----)  Uid: (    0/    root)   Gid: (   42/  shadow)
    Access: 2023-09-26 23:14:36.000000000 -0700
    Modify: 2023-09-26 23:14:36.000000000 -0700
    Change: 2024-03-25 15:45:16.155725465 -0700
     Birth: 2024-03-25 15:45:15.783734801 -0700

    # exit

    $ stat alpine-root/etc/shadow
      File: alpine-root/etc/shadow
      Size: 421       	Blocks: 8          IO Block: 4096   regular file
    Device: 253,2	Inode: 2129703     Links: 1
    Access: (0640/-rw-r-----)  Uid: ( 1000/   kevin)   Gid: (1410761/ UNKNOWN)
    Access: 2023-09-26 23:14:36.000000000 -0700
    Modify: 2023-09-26 23:14:36.000000000 -0700
    Change: 2024-03-25 15:45:16.155725465 -0700
     Birth: 2024-03-25 15:45:15.783734801 -0700

Inside the user namespace the file has ownership root:shadow, as it should.
Outside the user namespace the owner is the current user, because that user is
mapped to root inside the user namespace, and the group is a large number with
no name. This is one of the current user's subgids that was mapped to the shadow
group inside the user namespace.
