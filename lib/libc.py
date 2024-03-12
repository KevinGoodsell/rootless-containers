from ctypes import CFUNCTYPE, byref, c_int, c_ubyte, c_uint, c_void_p
from ctypes import create_string_buffer
from mmap import mmap
from typing import Any, Callable, cast

from .common import get_os_error, load_lib

_libc = load_lib('c')

# Python 3.12 has unshare in os, but I'm on 3.11.
_libc.unshare.argtypes = [c_int]
_libc.unshare.restype = c_int


def unshare(flags: int) -> None:
    if _libc.unshare(flags) < 0:
        raise get_os_error()


_child_func_type = CFUNCTYPE(c_int, c_void_p)
_libc.clone.argtypes = [_child_func_type, c_void_p, c_int, c_void_p]
_libc.clone.restype = c_int


def clone(
        fn: Callable[[], int],
        stack_or_size: c_void_p | int,
        flags: int) -> int:
    '''
    Call clone(2). fn is the function to call in the new process. stack_or_size
    can be an int giving the size of the stack to create for the child process,
    or a ctypes c_void_p wrapping the void* that will be passed directly to
    clone(2) for the stack argument. flags is passed as the flags argument to
    clone(2). The remaining arguments to clone(2) are not supported.

    Note that fn does not take an argument, and clone also can't be provided
    the arg argument that would normally be passed to fn. Since this is
    Python, you can use lambdas, closures, functools.partial, etc. to include
    any parameters you need.

    Returns the child PID on success, raises OSError on failure.
    '''

    # wrap fn with a function that matches child_func_type, but just ignores
    # the unused argument.
    def fn_wrapper(_: None) -> int:
        return fn()

    if isinstance(stack_or_size, int):
        stack: Any = byref(create_string_buffer(stack_or_size), stack_or_size)
    else:
        stack = stack_or_size

    res = _libc.clone(_child_func_type(fn_wrapper), stack, flags, None)
    if res < 0:
        raise get_os_error()

    # This is typing.cast, not ctypes.cast.
    return cast(int, res)


# XXX Should probably add whatever program we use to generate things for
# ctypes.
CLONE_CHILD_CLEARTID = 0x00200000
CLONE_CHILD_SETTID = 0x01000000
CLONE_DETACHED = 0x00400000
CLONE_FILES = 0x00000400
CLONE_FS = 0x00000200
CLONE_IO = 0x80000000
CLONE_NEWCGROUP = 0x02000000
CLONE_NEWIPC = 0x08000000
CLONE_NEWNET = 0x40000000
CLONE_NEWNS = 0x00020000
CLONE_NEWPID = 0x20000000
CLONE_NEWUSER = 0x10000000
CLONE_NEWUTS = 0x04000000
CLONE_PARENT = 0x00008000
CLONE_PARENT_SETTID = 0x00100000
CLONE_PIDFD = 0x00001000
CLONE_PTRACE = 0x00002000
CLONE_SETTLS = 0x00080000
CLONE_SIGHAND = 0x00000800
CLONE_SYSVSEM = 0x00040000
CLONE_THREAD = 0x00010000
CLONE_UNTRACED = 0x00800000
CLONE_VFORK = 0x00004000
CLONE_VM = 0x00000100

# XXX add whatever we decide is useful for synchronization. Will we just
# provide the primitives here? I guess so. If we go by the python-clone example
# this will be mmap, sem_init, sem_post, sem_wait. Seems we may not worry about
# munmap, sem_destroy.
#
# OK, so are we doing mmap and sem stuff?
#
# - Assuming we want sem, it can be named or unnamed.
# - Named would mean that it's like a file and needs an unlink. Not ideal.
# - Unnamed means it neads shared memory. From sem_init(3), this seems to mean
#   using mmap, shm_open, or shmget. shmget seems a bit weird and archaic.
#   shm_open uses the file system like a named semaphore, so has the same
#   problem. mmap seems sensible.
# - The annoying thing about mmap is that it is already in python, but the
#   returned object might not be usable for sem_init using ctypes.
# - Existing mmap seems to work OK, by using something like this:
#
#     a = (ctypes.c_ubyte * 100).from_buffer(m)
#
#   Now a and m mirror each other. How do we pass this to sem_init? Maybe just
#   ctypes.byref(a)?
#
# - In short, I think we can skip mmap and add sem_init, sem_post, sem_wait.

# XXX Should generate some of this stuff
SIZEOF_SEM_T = 32

_libc.sem_init.argtypes = [c_void_p, c_int, c_uint]
_libc.sem_init.restype = c_int

# XXX Given that we need to pass sem to three different funcs, should we just
# take the c_void_p and provide a way to convert mmap to c_void_p? Kind of
# thinking we'll just allow c_void_p | mmap for all of them.


def _convert_sem_arg(sem: c_void_p | mmap) -> Any:
    if isinstance(sem, mmap):
        array_type = c_ubyte * len(sem)
        # XXX Need to confirm that this works, if not it's stupid to not just
        # use c_void_p as the return type here.
        return byref(array_type.from_buffer(sem))

    return sem


# Supports mmap in the sem argument for convenience when using process-shared
# semaphores.
def sem_init(sem: c_void_p | mmap, pshared: bool, value: int) -> None:
    if value < 0:
        raise ValueError(f'value argument must be non-negative, was {value}')

    p = c_int(1) if pshared else c_int(0)
    res = _libc.sem_init(_convert_sem_arg(sem), p, value)

    if res < 0:
        raise get_os_error()


_libc.sem_wait.argtypes = [c_void_p]
_libc.sem_wait.restype = c_int


def sem_wait(sem: c_void_p | mmap) -> None:
    res = _libc.sem_wait(_convert_sem_arg(sem))

    if res < 0:
        raise get_os_error()


_libc.sem_post.argtypes = [c_void_p]
_libc.sem_post.restype = c_int


def sem_post(sem: c_void_p | mmap) -> None:
    res = _libc.sem_post(_convert_sem_arg(sem))

    if res < 0:
        raise get_os_error()
