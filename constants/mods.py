from enum import IntFlag

class Mods(IntFlag):
    NOMOD       = 0
    NOFAIL      = 1 << 0
    EASY        = 1 << 1
    TOUCHSCREEN = 1 << 2
    HIDDEN      = 1 << 3
    HARDROCK    = 1 << 4
    SUDDENDEATH = 1 << 5
    DOUBLETIME  = 1 << 6
    RELAX       = 1 << 7
    HALFTIME    = 1 << 8
    NIGHTCORE   = 1 << 9
    FLASHLIGHT  = 1 << 10
    AUTOPLAY    = 1 << 11
    SPUNOUT     = 1 << 12
    AUTOPILOT   = 1 << 13
    PERFECT     = 1 << 14
    KEY4        = 1 << 15
    KEY5        = 1 << 16
    KEY6        = 1 << 17
    KEY7        = 1 << 18
    KEY8        = 1 << 19
    FADEIN      = 1 << 20
    RANDOM      = 1 << 21
    CINEMA      = 1 << 22
    TARGET      = 1 << 23
    KEY9        = 1 << 24
    KEYCOOP     = 1 << 25
    KEY1        = 1 << 26
    KEY3        = 1 << 27
    KEY2        = 1 << 28
    SCOREV2     = 1 << 29
    MIRROR      = 1 << 30

    SPEED_MODS = DOUBLETIME | NIGHTCORE | HALFTIME
    GAME_CHANGING = RELAX | AUTOPILOT
    
    UNRANKED = SCOREV2 | AUTOPLAY | TARGET
    
    @classmethod
    def convert_str(self, mods: str):
        _mods = self.NOMOD # in case theres none to match
        
        if not mods or mods == 'NM':
            return _mods
        
        split_mods = [mods[char:char + 2].upper() for char in range(0, len(mods), 2)]
        
        for mod in split_mods:
            if mod in mods_str:
                _mods |= mods_str[mod]
                
        return _mods

def convert(m: int):
    if not m:
        return 'NM'

    r = []

    if m & Mods.NOFAIL:      r.append('NF')
    if m & Mods.EASY:        r.append('EZ')
    if m & Mods.HIDDEN:      r.append('HD')
    if m & Mods.NIGHTCORE:   r.append('NC')
    elif m & Mods.DOUBLETIME:  r.append('DT')
    if m & Mods.HARDROCK:    r.append('HR')
    if m & Mods.HALFTIME:    r.append('HT')
    if m & Mods.FLASHLIGHT:  r.append('FL')
    if m & Mods.SPUNOUT:     r.append('SO')
    if m & Mods.RELAX:       r.append('RX')
    if m & Mods.AUTOPILOT:       r.append('AP')
    if m & Mods.TOUCHSCREEN: r.append('TD')
    if m & Mods.SCOREV2:     r.append('V2')
    return ''.join(r)

mods_str = {
    'NF': Mods.NOFAIL,
    'EZ': Mods.EASY,
    'TD': Mods.TOUCHSCREEN,
    'HD': Mods.HIDDEN,
    'HR': Mods.HARDROCK,
    'SD': Mods.SUDDENDEATH,
    'DT': Mods.DOUBLETIME,
    'RX': Mods.RELAX,
    'HT': Mods.HALFTIME,
    'NC': Mods.NIGHTCORE,
    'FL': Mods.FLASHLIGHT,
    'AU': Mods.AUTOPLAY,
    'SO': Mods.SPUNOUT,
    'AP': Mods.AUTOPILOT,
    'PF': Mods.PERFECT,
    'FI': Mods.FADEIN,
    'RN': Mods.RANDOM,
    'CN': Mods.CINEMA,
    'TP': Mods.TARGET,
    'V2': Mods.SCOREV2,
    'MR': Mods.MIRROR,

    '1K': Mods.KEY1,
    '2K': Mods.KEY2,
    '3K': Mods.KEY3,
    '4K': Mods.KEY4,
    '5K': Mods.KEY5,
    '6K': Mods.KEY6,
    '7K': Mods.KEY7,
    '8K': Mods.KEY8,
    '9K': Mods.KEY9,
    'CO': Mods.KEYCOOP
}