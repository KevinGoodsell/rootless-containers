import ctypes
from contextlib import contextmanager
from collections.abc import Iterator

from .common import load_lib, get_os_error

_libcap = load_lib('cap')


class _cap_t(ctypes.c_void_p):
    pass


_libcap.cap_get_proc.argtypes = []
_libcap.cap_get_proc.restype = _cap_t


@contextmanager
def cap_get_proc() -> Iterator[_cap_t]:
    caps = _libcap.cap_get_proc()
    if caps is None:
        raise get_os_error()

    yield caps

    _cap_free(caps)


_libcap.cap_to_text.argtypes = [
        _cap_t,
        ctypes.POINTER(ctypes.c_ssize_t)]
_libcap.cap_to_text.restype = ctypes.POINTER(ctypes.c_char)


def cap_to_text(caps: _cap_t) -> bytes:
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
