from __future__ import annotations

import hashlib
import os
import sys
from typing import Any
from typing import Callable
from typing import Optional
from typing import TypeVar

import pymysql

import log


def socket_in_use(socket_str: str) -> bool:
    with open("/proc/net/unix") as unix:
        socket_data = unix.read().splitlines(keepends=False)

    for line in socket_data[1:]:
        tokens = line.split()

        if len(tokens) == 8 and tokens[7] == socket_str:
            return True

    return False


def ensure_platform() -> int:
    if os.name != "posix":
        log.error(
            "Asahi currently only supports POSIX systems. "
            "If you use Windows, you should try WSL2 to run Asahi.",
        )

        return 1

    if sys.version_info < (3, 9):
        log.error(
            "Asahi currently only supports Python versions 3.9 and greater. "
            "Please upgrade your Python.",
        )

        return 1

    return 0


def ensure_directories() -> int:
    return 0  # TODO


def ensure_dependencies() -> int:
    return 0  # TODO


T = TypeVar("T")


def pymysql_encode(
    conv: Callable[[Any, Optional[dict[object, object]]], str],
) -> Callable[[T], T]:
    def wrapper(cls: T) -> T:
        pymysql.converters.encoders[cls] = conv
        return cls

    return wrapper


def escape_enum(
    val: Any,
    _: Optional[dict[object, object]] = None,
) -> str:
    return str(int(val))


def make_safe(name: str) -> str:
    return name.replace(" ", "_").lower()


def generate_md5(text: str) -> bytes:
    return hashlib.md5(text.encode()).hexdigest().encode()
