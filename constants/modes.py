from enum import Enum
from constants.mods import Mods

class osuModes(Enum):
    std = 0
    taiko = 1
    catch = 2
    mania = 3

    std_rx = 4
    taiko_rx = 5
    catch_rx = 6
    std_ap = 7

def lbModes(mode: int, mods: int):
    if mods & Mods.RELAX:
        return osuModes(mode + 4)
    elif mods & Mods.AUTOPILOT:
        return osuModes(7)
   
    return osuModes(mode)

