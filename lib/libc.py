from ctypes import (
    CFUNCTYPE,
    byref,
    c_char_p,
    c_int,
    c_ubyte,
    c_uint,
    c_ulong,
    c_void_p,
    create_string_buffer,
)
from mmap import mmap
from typing import Any, Callable, cast

from .common import get_os_error, load_lib
from .libc_gen import *

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


_libc.sem_init.argtypes = [c_void_p, c_int, c_uint]
_libc.sem_init.restype = c_int


def _convert_sem_arg(sem: c_void_p | mmap) -> Any:
    if isinstance(sem, mmap):
        array_type = c_ubyte * len(sem)
        return byref(array_type.from_buffer(sem))

    return sem


# Supports mmap in the sem argument for convenience when using process-shared
# semaphores.
def sem_init(sem: c_void_p | mmap, pshared: bool, value: int) -> None:
    if value < 0:
        raise ValueError(f'value argument must be non-negative, was {value}')

    res = _libc.sem_init(_convert_sem_arg(sem), pshared, value)

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


_libc.mount.argtypes = [c_char_p, c_char_p, c_char_p, c_ulong, c_void_p]
_libc.mount.restype = c_int


def mount(source: str, target: str, filesystemtype: str, mountflags: int,
          data: bytes | None = None) -> None:
    res = _libc.mount(
            source.encode(),
            target.encode(),
            filesystemtype.encode(),
            mountflags,
            data)

    if res < 0:
        raise get_os_error()
