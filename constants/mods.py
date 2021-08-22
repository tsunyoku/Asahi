from enum import IntFlag
from functools import cache

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

    @cache
    def __repr__(self) -> str:
        if not self.value:
            return 'NM'

        _str = ''

        for mod in Mods:
            if self.value & mod and (m := str_mods.get(mod)):
                _str += m

        if self.value & Mods.NIGHTCORE: _str = _str.replace('NC', '')
        if self.value & Mods.PERFECT: _str = _str.replace('SD', '')

        return _str

    @classmethod
    def convert_str(cls, mods: str) -> 'Mods':
        _mods = cls.NOMOD # in case theres none to match

        if not mods or mods == 'NM':
            return _mods

        split_mods = [mods[char:char + 2].upper() for char in range(0, len(mods), 2)]

        for mod in split_mods:
            if mod not in mods_str:
                continue

            _mods |= mods_str[mod]

        return _mods

str_mods = {
    Mods.NOFAIL: 'NF',
    Mods.EASY: 'EZ',
    Mods.TOUCHSCREEN: 'TD',
    Mods.HIDDEN: 'HD',
    Mods.HARDROCK: 'HR',
    Mods.SUDDENDEATH: 'SD',
    Mods.DOUBLETIME: 'DT',
    Mods.RELAX: 'RX',
    Mods.HALFTIME: 'HT',
    Mods.NIGHTCORE: 'NC',
    Mods.FLASHLIGHT: 'FL',
    Mods.AUTOPLAY: 'AU',
    Mods.SPUNOUT: 'SO',
    Mods.AUTOPILOT: 'AP',
    Mods.PERFECT: 'PF',
    Mods.FADEIN: 'FI',
    Mods.RANDOM: 'RN',
    Mods.CINEMA: 'CN',
    Mods.TARGET: 'TP',
    Mods.SCOREV2: 'V2',
    Mods.MIRROR: 'MR',
    Mods.KEY1: '1K',
    Mods.KEY2: '2K',
    Mods.KEY3: '3K',
    Mods.KEY4: '4K',
    Mods.KEY5: '5K',
    Mods.KEY6: '6K',
    Mods.KEY7: '7K',
    Mods.KEY8: '8K',
    Mods.KEY9: '9K',
    Mods.KEYCOOP: 'CO'
}

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
