from enum import Enum
from functools import cached_property

from .mods import Mods

m_str = (
    "osu!std",
    "osu!taiko",
    "osu!catch",
    "osu!mania",
    "std!rx",
    "taiko!rx",
    "catch!rx",
    "std!ap",
)


class osuModes(Enum):
    std = 0
    taiko = 1
    catch = 2
    mania = 3

    std_rx = 4
    taiko_rx = 5
    catch_rx = 6
    std_ap = 7

    def __repr__(self) -> str:
        return m_str[self.value]

    @cached_property
    def table(self) -> str:
        if self.value in (4, 5, 6):
            return "scores_rx"
        elif self.value in (0, 1, 2, 3):
            return "scores"
        else:
            return "scores_ap"

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
    def sort(self) -> str:
        if self.value > 3:
            return "pp"
        else:
            return "score"

    @cached_property
    def leaderboard(self) -> str:
        if self.value in (4, 5, 6):
            return "lb_rx"
        elif self.value in (0, 1, 2, 3):
            return "lb"
        else:
            return "lb_ap"


def lbModes(mode: int, mods: int) -> osuModes:
    if mods & Mods.RELAX:
        if mode == 3:
            return osuModes(3)

        return osuModes(mode + 4)
    elif mods & Mods.AUTOPILOT:
        if mode != 0:
            return osuModes(mode)

        return osuModes(7)

    return osuModes(mode)
