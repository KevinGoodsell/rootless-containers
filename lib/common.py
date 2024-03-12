from ctypes.util import find_library
import os
import ctypes


def load_lib(name: str) -> ctypes.CDLL:
    fullname = find_library(name)
    if fullname is None:
        raise Exception(f'Library not found: {name}')

    return ctypes.CDLL(fullname, use_errno=True)


def get_os_error() -> OSError:
    e = ctypes.get_errno()
    return OSError(e, os.strerror(e))
