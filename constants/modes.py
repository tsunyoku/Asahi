from enum import Enum
from constants.mods import Mods

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

def lbModes(mode: int, mods: int):
    if mods & Mods.RELAX:
        return osuModes(mode + 4)
    elif mods & Mods.AUTOPILOT:
        return osuModes(7)
   
    return osuModes(mode)

