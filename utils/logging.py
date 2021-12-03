from functools import cache
from enum import IntEnum

from objects import glob

import time
import sys

def formatted_time() -> str: return time.strftime("%I:%M:%S%p", time.localtime())

class Ansi(IntEnum): # https://github.com/cmyui/cmyui_pkg/blob/master/cmyui/logging.py#L20-L45
    BLACK   = 30
    RED     = 31
    GREEN   = 32
    YELLOW  = 33
    BLUE    = 34
    MAGENTA = 35
    CYAN    = 36
    WHITE   = 37

    GRAY     = 90
    LRED     = 91
    LGREEN   = 92
    LYELLOW  = 93
    LBLUE    = 94
    LMAGENTA = 95
    LCYAN    = 96
    LWHITE   = 97

    RESET = 0

    @cache
    def __repr__(self) -> str: return f'\x1b[{self.value}m'

def log(content: str, log_type: str, colour: Ansi = Ansi.WHITE) -> None:
    """Logs a message to stdout with a given Ansi colour."""

    sys.stdout.write(
        f"\033[37m{Ansi.GRAY!r}\033[49m[{formatted_time()} - {log_type}]" 
        f"\033[37m{colour!r}\033[49m {content}"
        "\033[39m\n"
    )

def debug(message: str) -> None:
    if glob.config.debug: return log(message, "DEBUG", Ansi.LGREEN)

def info(message: str) -> None: return log(message, "INFO", Ansi.LBLUE)
def error(message: str) -> None: return log(message, "ERROR", Ansi.LRED)
def warning(message: str) -> None: return log(message, "WARNING", Ansi.LYELLOW)