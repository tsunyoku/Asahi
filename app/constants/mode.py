from __future__ import annotations

from enum import Enum
from functools import cache
from functools import cached_property

from app.constants.mods import Mods
from app.utils import escape_enum
from app.utils import pymysql_encode

mode_str = (
    "osu!std",
    "osu!taiko",
    "osu!catch",
    "osu!mania",
    "std!rx",
    "taiko!rx",
    "catch!rx",
    "std!ap",
)


@pymysql_encode(escape_enum)
class Mode(Enum):
    STD = 0
    TAIKO = 1
    CATCH = 2
    MANIA = 3

    STD_RX = 4
    TAIKO_RX = 5
    CATCH_RX = 6
    STD_AP = 7

    def __repr__(self) -> str:
        return mode_str[self.value]

    @cached_property
    def as_vn(self) -> int:
        if self.value in (0, 4, 7):
            return 0
        elif self.value in (1, 5):
            return 1
        elif self.value in (2, 6):
            return 2
        else:
            return self.value

    @cached_property
    def redis_name(self) -> str:
        return self.name.lower()

    @cached_property
    def sort(self) -> str:
        return "pp" if self.value > 3 else "score"

    @classmethod
    def from_lb(cls, mode: int, mods: int) -> Mode:
        if mods & Mods.RELAX:
            if mode == 3:
                return Mode.MANIA

            return Mode(mode + 4)
        elif mods & Mods.AUTOPILOT:
            if mode != 0:
                return Mode.STD

            return Mode.STD_AP

        return Mode(mode)
