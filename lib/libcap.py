import ctypes
from contextlib import contextmanager
from collections.abc import Iterator

from .common import load_lib, get_os_error

_libcap = load_lib('cap')

_libcap.cap_get_proc.argtypes = []
_libcap.cap_get_proc.restype = ctypes.c_void_p


@contextmanager
def cap_get_proc() -> Iterator[int]:
    caps = _libcap.cap_get_proc()
    if caps is None:
        raise get_os_error()

    yield caps

    _cap_free(caps)


_libcap.cap_to_text.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_ssize_t)]
_libcap.cap_to_text.restype = ctypes.POINTER(ctypes.c_char)


def cap_to_text(caps: int) -> bytes:
    text = _libcap.cap_to_text(caps, None)
    if not text:
        raise get_os_error()

    res = ctypes.string_at(text)
    _cap_free(text)

    return res


_libcap.cap_free.argtypes = [ctypes.c_void_p]
_libcap.cap_free.restype = ctypes.c_int


def _cap_free(obj_d: int) -> None:
    if _libcap.cap_free(obj_d) < 0:
        raise get_os_error()
