from ctypes.util import find_library
import os
import ctypes


def load_lib(name: str) -> ctypes.CDLL:
    '''
    Return a CDLL for the named library, or raise an Exception if it's not
    found.
    '''
    fullname = find_library(name)
    if fullname is None:
        raise Exception(f'Library not found: {name}')

    return ctypes.CDLL(fullname, use_errno=True)


def get_os_error() -> OSError:
    '''
    Fetch errno and return an OSError based on it.
    '''
    e = ctypes.get_errno()
    return OSError(e, os.strerror(e))
