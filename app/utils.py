import log
import sys
import os


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
            "If you use Windows, you should try WSL2 to run Asahi."
        )

        return 1

    if sys.version_info < (3, 9):
        log.error(
            "Asahi currently only supports Python versions 3.9 and greater. "
            "Please upgrade your Python."
        )

        return 1

    return 0


def ensure_directories() -> int:
    return 0  # TODO


def ensure_dependencies() -> int:
    return 0  # TODO
