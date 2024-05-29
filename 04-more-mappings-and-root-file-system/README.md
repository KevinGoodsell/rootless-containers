# Part 4: More User Mappings, Creating a Root File System

In this part we'll update the example program to map more user and group IDs,
then we'll use the updated example program to build a root file system to use in
the next parts.

## Updating the Example Program With Additional Mappings

Let's walk through the changes in the example program that map more UIDs and
GIDs inside the user namespace.

In order to map more IDs, we need some IDs on the host that we can map to IDs
inside the user namespace. The files `/etc/subuid` and `/etc/subgid` provide
these host IDs. You can find details in `subuid(5)` and `subgid(5)`. This will
only work if your user has been assigned a set of subuids and subgids inside
these files. The example program reads these files to find the invoking user's
subuids and subgids.

Instead of writing user and group ID mappings to the `uid_map` and `gid_map`
files as in the previous example, we use the `newuidmap` and `newgidmap`
programs. This is because there are restrictions on writing to `uid_map` and
`gid_map` that make it impossible to map multiple IDs without having elevated
permissions, as described in `user_namespaces(7)`. `newuidmap` and `newgidmap`
bypass the need for elevated permissions because they are setuid binaries.

Using these programs requires that they be invoked in the parent namespace,
after the child namespace and process have been created, so the example program
uses a semaphore to block the child process until the parent finishes setting up
the mappings.

`newuidmap` is invoked with the child process PID and the UID mappings this way:

    $ newuidmap PID USER_NS_UID PARENT_NS_UID COUNT [USER_NS_UID PARENT_NS_UID COUNT [...]]

This maps `COUNT` UIDs starting at `USER_NS_UID` in the user namespace and
`PARENT_NS_UID` in the parent namespace. The UIDs in the parent namespace have
to be UIDs that the user is allowed to use, which includes the user's own UID,
and the set of UIDs granted to the user in the `/etc/subuid` file.

The same applies to `newgidmap`, and the `/etc/subgid` file. See the man pages
`newuidmap(1)` and `newgidmap(1)` for more details.

The previous example program unconditionally mapped the invoking user's UID and
GID to 0 inside the user namespace. This is convenient when you want to be root
inside the new namespace, but inconvenient if you want to be any other user. The
new example program introduces command line options to determine how to map the
invoking user's UID and GID, `--map-uid` and `--map-gid`. For reasons that we'll
see later, these default to 1100. For now just think of this as reserving UID
1100 and GID 1100 for later use.

Since we no longer map the invoking user to UID 0 by default, but we still need
to be able to act as root inside the namespace, new `setuid` and `setgid` calls
have been added to the example program so that we're still running as root
inside the namespace. In the future we'll add more control over this.

## Other Changes in the Example Program

Besides the ID mapping changes, the example program also incorporates mounting
the `/proc` file system, fixing the `ps` problem that was noted in the previous
part.

## Using the Example Program to Create a Root File System

Now that the example program maps additional UIDs and GIDS, it can be used to
set up a root file system that can serve as the root for our pseudo-containers
going forward. We'll follow (more or less) the instructions here for [creating
an Alpine Linux chroot](https://wiki.alpinelinux.org/wiki/Alpine_Linux_in_a_chroot).

For the following steps, we'll use a directory named `alpine` in the
repository root:

    $ mkdir ../alpine ; pushd ../alpine

First, choose a mirror from [this
list](https://dl-cdn.alpinelinux.org/alpine/MIRRORS.txt). I'm using
http://mirrors.edge.kernel.org/alpine/.

From that mirror, navigate to the list of packages for your architecture to find
the `apk-tools-static` package and copy the link.

Download the file:

    $ curl -LO http://mirrors.edge.kernel.org/alpine/latest-stable/main/x86_64/apk-tools-static-2.14.0-r5.apk

Unpack the file, then return no the directory for part 4:

    $ tar -xzf apk-tools-static-2.14.0-r5.apk

    $ popd

Next we'll install the Alpine base system. Since this will need to perform
privileged actions, we'll do it inside the namespace our example program
creates:

    $ python3 example04.py -- bash

Now that we have root access, install the base system. We'll put it in a
subdirectory `alpine/alpine-root`:

    # cd ../alpine

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

So what did the extra UID and GID mappings do for us? Well, not much that you've
been able to see yet. You would probably see some errors during the base system
installation if you didn't have the extra mappings because some of the
installation needs to do things like changing file ownership, and this can only
work if there are other IDs to own the files. If you check the ownership of the
`/etc/shadow` file inside and outside the user namespace, you'll see one small
effect of having the extra mappings:

    # stat alpine-root/etc/shadow
      File: alpine-root/etc/shadow
      Size: 421       	Blocks: 8          IO Block: 4096   regular file
    Device: 253,2	Inode: 2129849     Links: 1
    Access: (0640/-rw-r-----)  Uid: (    0/    root)   Gid: (   42/  shadow)
    Access: 2023-09-26 23:14:36.000000000 -0700
    Modify: 2023-09-26 23:14:36.000000000 -0700
    Change: 2024-05-14 18:36:35.384483358 -0700
     Birth: 2024-05-14 18:36:34.932494784 -0700

    # exit
    exit

    $ stat ../alpine/alpine-root/etc/shadow
      File: ../alpine/alpine-root/etc/shadow
      Size: 421       	Blocks: 8          IO Block: 4096   regular file
    Device: 253,2	Inode: 2129849     Links: 1
    Access: (0640/-rw-r-----)  Uid: (1410720/ UNKNOWN)   Gid: (1410762/ UNKNOWN)
    Access: 2023-09-26 23:14:36.000000000 -0700
    Modify: 2023-09-26 23:14:36.000000000 -0700
    Change: 2024-05-14 18:36:35.384483358 -0700
     Birth: 2024-05-14 18:36:34.932494784 -0700

Inside the user namespace the file has ownership root:shadow, as it should.
Outside the user namespace the owner and group are mapped to large numbers with
no names. These come from the current user's subuids and subgids, and were mapped
to the root user and the shadow group inside the user namespace.

One note about the root file system we've created: if you try to delete it you
will probably get permission errors due to files and directories being owned by
subuids and subgids. You can use these IDs in your own user namespaces, but in
the normal (initial) user namespace they will act like any other UID or GID. In
order to delete the root file system, you can enter the namespace the same way
you did to create it:

    $ python3 example04.py -- bash

    # cd ../alpine/

    # rm -r alpine-root/
