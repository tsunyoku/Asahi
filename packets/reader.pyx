import struct

from constants.types import osuTypes, winConditions, teamTypes
from constants.modes import osuModes
from constants.mods import Mods
from objects.match import Match, slotStatus, Teams
from objects import glob

from collections import namedtuple

Message = namedtuple('Message', ['fromname', 'msg', 'tarname', 'fromid'])
Channel = namedtuple('Channel', ['name', 'desc', 'players'])

types = { # lambda = cursed lmfao
    osuTypes.i8: lambda rd: rd.read_i8(),
    osuTypes.u8: lambda rd: rd.read_u8(),
    osuTypes.i16: lambda rd: rd.read_i16(),
    osuTypes.u16: lambda rd: rd.read_u16(),
    osuTypes.i32: lambda rd: rd.read_i32(),
    osuTypes.u32: lambda rd: rd.read_u32(),
    osuTypes.f32: lambda rd: rd.read_f32(),
    osuTypes.i64: lambda rd: rd.read_i64(),
    osuTypes.u64: lambda rd: rd.read_u64(),
    osuTypes.f64: lambda rd: rd.read_f64(),
    osuTypes.message: lambda rd: rd.read_msg(),
    osuTypes.channel: lambda rd: rd.read_chan(),
    osuTypes.match: lambda rd: rd.read_match(),
    osuTypes.i32_list: lambda rd: rd.read_i32l(),
    osuTypes.i32_list4l: lambda rd: rd.read_i32l_4(),
    osuTypes.string: lambda rd: rd.read_string(),
    osuTypes.raw: lambda rd: rd.read_raw()
}

cpdef dict handle_packet(data: bytes, struct: tuple):
    rd = Reader(data)
    d = {}

    for s in struct:
        t = s[1]
        r = types.get(t, None)

        if not r:
            d[s[0]] = b''

        d[s[0]] = r(rd)

    return d

cdef class Reader:
    cpdef public bytes data
    cpdef public int offset
    cpdef public int pid
    cpdef public int length

    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0
        self.pid, self.length = self.packet_lid()

    cpdef packet_lid(self):
        d = struct.unpack('<HxI', self.data[self.offset:self.offset + 7])

        self.offset += 7
        return d[0], d[1]

    cpdef read_i8(self):
        d = self.data[self.offset:self.offset + 1]

        self.offset += 1

        if d[0] > 127:
            return d[0] - 256

        return d[0]

    cpdef read_u8(self):
        d = self.data[self.offset:self.offset + 1]

        self.offset += 1

        return d[0]

    cpdef read_i16(self):
        d = struct.unpack('<h', self.data[self.offset:self.offset + 2])

        self.offset += 2

        return d[0]

    cpdef read_u16(self):
        d = struct.unpack('<H', self.data[self.offset:self.offset + 2])

        self.offset += 2

        return d[0]

    cpdef read_i32(self):
        d = struct.unpack('<i', self.data[self.offset:self.offset + 4])

        self.offset += 4

        return d[0]

    cpdef read_u32(self):
        d = struct.unpack('<I', self.data[self.offset:self.offset + 4])

        self.offset += 4

        return d[0]

    cpdef read_f32(self):
        d = struct.unpack('<f', self.data[self.offset:self.offset + 4])

        self.offset += 4

        return d

    cpdef read_i64(self):
        d = struct.unpack('<q', self.data[self.offset:self.offset + 8])

        self.offset += 8

        return d[0]

    cpdef read_u64(self):
        d = struct.unpack('<Q', self.data[self.offset:self.offset + 8])

        self.offset += 8

        return d[0]

    cpdef read_f64(self):
        d = struct.unpack('<d', self.data[self.offset:self.offset + 8])

        self.offset += 8

        return d

    cpdef read_msg(self): # namedtuple = supreme
        return Message(
            fromname = self.read_string(),
            msg = self.read_string(),
            tarname = self.read_string(),
            fromid = self.read_i32()
        )

    cpdef read_chan(self): # once again, namedtuple is base
        return Channel(
            name = self.read_string(),
            desc = self.read_string(),
            players = self.read_i32()
        )

    cpdef read_match(self): # this is going to take a LOT of work to be functional i think
        match = Match()

        self.data = self.data[3:]

        self.read_i8()

        match.id = len(glob.matches) + 1

        match.mods = Mods(self.read_i32())
        match.name = self.read_string()
        match.pw = self.read_string()

        match.bname = self.read_string()
        match.bid = self.read_i32()
        match.bmd5 = self.read_string()

        for slot in match.slots:
            slot.status = slotStatus(self.read_i8())

        for slot in match.slots:
            slot.team = Teams(self.read_i8())

        for slot in match.slots:
            if slot.status & slotStatus.has_player:
                self.data = self.data[4:]

        uid = self.read_i32()
        match.host = glob.players.get_online(id=uid)
        match.first_host = glob.players.get_online(id=uid)

        match.mode = osuModes(self.read_i8())
        match.win_cond = winConditions(self.read_i8())
        match.type = teamTypes(self.read_i8())

        match.fm = self.read_i8() == 1

        if match.fm:
            for slot in match.slots:
                slot.mods = Mods(self.read_i32())

        match.seed = self.read_i32()

        return match

    cpdef read_i32l(self):
        l = self.read_i16()

        d = struct.unpack(f'<{"I" * l}', self.data[self.offset:self.offset + l * 4])

        self.offset += l * 4

        return d

    cpdef read_i32l_4(self): # i dont think this is correct but whatev
        l = self.read_i32()

        d = struct.unpack(f'<{"I" * l}', self.data[self.offset:self.offset + l * 4])

        self.offset += l * 4

        return d

    cpdef read_uleb128(self, val): # fuck me
        s = 0
        b = 0
        a = [0, 0]

        while True:
            b = val[a[1]]
            a[1] += 1
            a[0] |= int(b & 127) << s

            if b & 128 == 0:
                break

            s += 7

        return a

    cpdef read_string(self):
        val = self.read_uleb128(self.data[self.offset + 1:])

        # i would like to report a bruh moment
        d = self.data[self.offset + val[1]:self.offset + val[0] + val[1] + 1]
        d = d[1:].decode()

        if d == '\x00':
            return b''

        self.offset += val[0] + val[1] + 1

        return d

    cpdef read_raw(self):
        d = self.data[self.offset:self.offset + self.length]

        self.offset += self.length

        return d
