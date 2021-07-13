from enum import Enum
from .mods import Mods
from functools import cache

m_str = (
    'osu!std',
    'osu!taiko',
    'osu!catch',
    'osu!mania',

    'std!rx',
    'taiko!rx',
    'catch!rx',
    'std!ap'
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

    def __repr__(self):
        return m_str[self.value]

    @property
    @cache
    def table(self):
        if self.value in (4, 5, 6):
            return 'scores_rx'
        elif self.value in (0, 1, 2, 3):
            return 'scores'
        else:
            return 'scores_ap'

    @property
    @cache
    def as_vn(self):
        if self.value in (0, 4, 7):
            return 0
        elif self.value in (1, 5):
            return 1
        elif self.value in (2, 6):
            return 2
        else:
            return self.value
    
    @property
    @cache
    def sort(self):
        if self.value > 3:
            return 'pp'
        else:
            return 'score'
        
    @property
    @cache
    def leaderboard(self):
        if self.value in (4, 5, 6):
            return 'lb_rx'
        elif self.value in (0, 1, 2, 3):
            return 'lb'
        else:
            return 'lb_ap'

def lbModes(mode: int, mods: int):
    if mods & Mods.RELAX:
        return osuModes(mode + 4)
    elif mods & Mods.AUTOPILOT:
        return osuModes(7)
   
    return osuModes(mode)

