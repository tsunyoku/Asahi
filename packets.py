# reader/writer is taken from cmyui's gulag until i can write my own however the packet handlers are my own

import struct
import asyncio

from collections import namedtuple
from enum import IntEnum
from enum import unique
from functools import cache
from functools import partialmethod
from typing import Any, Optional

from constants.types import osuTypes, winConditions, teamTypes
from constants.modes import osuModes
from constants.mods import Mods
from objects import glob

from objects.match import Match, slotStatus, Teams
from objects.beatmap import Beatmap

_specifiers = (
    '<b', '<B', # 8
    '<h', '<H', # 16
    '<i', '<I', '<f', # 32
    '<q', '<Q', '<d'  # 64
)

Message = namedtuple('Message', ['fromname', 'msg', 'tarname', 'fromid'])
Channel = namedtuple('Channel', ['name', 'desc', 'players'])

@unique
class Packets(IntEnum):
    OSU_CHANGE_ACTION = 0
    OSU_SEND_PUBLIC_MESSAGE = 1
    OSU_LOGOUT = 2
    OSU_REQUEST_STATUS_UPDATE = 3
    OSU_PING = 4
    CHO_USER_ID = 5
    CHO_SEND_MESSAGE = 7
    CHO_PONG = 8
    CHO_HANDLE_IRC_CHANGE_USERNAME = 9
    CHO_HANDLE_IRC_QUIT = 10
    CHO_USER_STATS = 11
    CHO_USER_LOGOUT = 12
    CHO_SPECTATOR_JOINED = 13
    CHO_SPECTATOR_LEFT = 14
    CHO_SPECTATE_FRAMES = 15
    OSU_START_SPECTATING = 16
    OSU_STOP_SPECTATING = 17
    OSU_SPECTATE_FRAMES = 18
    CHO_VERSION_UPDATE = 19
    OSU_ERROR_REPORT = 20
    OSU_CANT_SPECTATE = 21
    CHO_SPECTATOR_CANT_SPECTATE = 22
    CHO_GET_ATTENTION = 23
    CHO_NOTIFICATION = 24
    OSU_SEND_PRIVATE_MESSAGE = 25
    CHO_UPDATE_MATCH = 26
    CHO_NEW_MATCH = 27
    CHO_DISPOSE_MATCH = 28
    OSU_PART_LOBBY = 29
    OSU_JOIN_LOBBY = 30
    OSU_CREATE_MATCH = 31
    OSU_JOIN_MATCH = 32
    OSU_PART_MATCH = 33
    CHO_TOGGLE_BLOCK_NON_FRIEND_DMS = 34
    CHO_MATCH_JOIN_SUCCESS = 36
    CHO_MATCH_JOIN_FAIL = 37
    OSU_MATCH_CHANGE_SLOT = 38
    OSU_MATCH_READY = 39
    OSU_MATCH_LOCK = 40
    OSU_MATCH_CHANGE_SETTINGS = 41
    CHO_FELLOW_SPECTATOR_JOINED = 42
    CHO_FELLOW_SPECTATOR_LEFT = 43
    OSU_MATCH_START = 44
    CHO_ALL_PLAYERS_LOADED = 45
    CHO_MATCH_START = 46
    OSU_MATCH_SCORE_UPDATE = 47
    CHO_MATCH_SCORE_UPDATE = 48
    OSU_MATCH_COMPLETE = 49
    CHO_MATCH_TRANSFER_HOST = 50
    OSU_MATCH_CHANGE_MODS = 51
    OSU_MATCH_LOAD_COMPLETE = 52
    CHO_MATCH_ALL_PLAYERS_LOADED = 53
    OSU_MATCH_NO_BEATMAP = 54
    OSU_MATCH_NOT_READY = 55
    OSU_MATCH_FAILED = 56
    CHO_MATCH_PLAYER_FAILED = 57
    CHO_MATCH_COMPLETE = 58
    OSU_MATCH_HAS_BEATMAP = 59
    OSU_MATCH_SKIP_REQUEST = 60
    CHO_MATCH_SKIP = 61
    CHO_UNAUTHORIZED = 62 # unused
    OSU_CHANNEL_JOIN = 63
    CHO_CHANNEL_JOIN_SUCCESS = 64
    CHO_CHANNEL_INFO = 65
    CHO_CHANNEL_KICK = 66
    CHO_CHANNEL_AUTO_JOIN = 67
    OSU_BEATMAP_INFO_REQUEST = 68
    CHO_BEATMAP_INFO_REPLY = 69
    OSU_MATCH_TRANSFER_HOST = 70
    CHO_PRIVILEGES = 71
    CHO_FRIENDS_LIST = 72
    OSU_FRIEND_ADD = 73
    OSU_FRIEND_REMOVE = 74
    CHO_PROTOCOL_VERSION = 75
    CHO_MAIN_MENU_ICON = 76
    OSU_MATCH_CHANGE_TEAM = 77
    OSU_CHANNEL_PART = 78
    OSU_RECEIVE_UPDATES = 79
    CHO_MONITOR = 80 # unused
    CHO_MATCH_PLAYER_SKIPPED = 81
    OSU_SET_AWAY_MESSAGE = 82
    CHO_USER_PRESENCE = 83
    OSU_IRC_ONLY = 84
    OSU_USER_STATS_REQUEST = 85
    CHO_RESTART = 86
    OSU_MATCH_INVITE = 87
    CHO_MATCH_INVITE = 88
    CHO_CHANNEL_INFO_END = 89
    OSU_MATCH_CHANGE_PASSWORD = 90
    CHO_MATCH_CHANGE_PASSWORD = 91
    CHO_SILENCE_END = 92
    OSU_TOURNAMENT_MATCH_INFO_REQUEST = 93
    CHO_USER_SILENCED = 94
    CHO_USER_PRESENCE_SINGLE = 95
    CHO_USER_PRESENCE_BUNDLE = 96
    OSU_USER_PRESENCE_REQUEST = 97
    OSU_USER_PRESENCE_REQUEST_ALL = 98
    OSU_TOGGLE_BLOCK_NON_FRIEND_DMS = 99
    CHO_USER_DM_BLOCKED = 100
    CHO_TARGET_IS_SILENCED = 101
    CHO_VERSION_UPDATE_FORCED = 102
    CHO_SWITCH_SERVER = 103
    CHO_ACCOUNT_RESTRICTED = 104
    CHO_RTX = 105 # unused
    CHO_MATCH_ABORT = 106
    CHO_SWITCH_TOURNAMENT_SERVER = 107
    OSU_TOURNAMENT_JOIN_MATCH_CHANNEL = 108
    OSU_TOURNAMENT_LEAVE_MATCH_CHANNEL = 109

    def __repr__(self) -> str:
        return f'<{self.name} ({self.value})>'

class BanchoPacket:
    """Abstract base class for bancho packets."""
    type: Optional[Packets] = None
    args: Optional[tuple[osuTypes]] = None
    length: Optional[int] = None

    def __init_subclass__(cls, type: Packets) -> None:
        super().__init_subclass__()

        cls.type = type
        cls.args = cls.__annotations__

        for x in ('type', 'args', 'length'):
            if x in cls.args:
                del cls.args[x]

    async def handle(self, player) -> None: ...

class BanchoPacketReader:
    """\
    A class for reading bancho packets sequentially.
    Attributes
    -----------
    view: `memoryview`
        A low-level view to the underlying buffer passed in.
    packet_map: `dict[Packets (packet id), BanchoPacket (handler)]`
        The map of packets the packet reader will handle.
    _current: Optional[`BanchoPacket`]
        The current packet being read by the reader, if any.
    Intended Usage:
    ```
      for packet in BanchoPacketReader(conn.body):
          # once you're ready to handle the packet,
          # simply call it's .handle() method.
          await packet.handle()
    ```
    """
    __slots__ = ('view', 'packet_map', '_current')
    def __init__(self, data: bytes, packet_map: dict) -> None:
        self.view = memoryview(data)
        self.packet_map = packet_map

        self._current: Optional[BanchoPacket] = None

    def __iter__(self):
        return self

    def __next__(self):
        # do not break until we've read the
        # header of a packet we can handle.
        while True:
            p_type, p_len = self.read_header()

            if p_type == Packets.OSU_PING:
                continue # we can ignore this, client is just telling us its still alive

            if p_type not in self.packet_map:
                # packet type not handled, remove
                # from internal buffer and continue.
                if p_len != 0:
                    self.view = self.view[p_len:]
            else:
                # we can handle this one.
                break

        # we have a packet handler for this.
        self._current = self.packet_map[p_type]()
        self._current.length = p_len

        if self._current.args:
            self.read_arguments()

        return self._current

    def read_arguments(self) -> None:
        """Read all arguments from the internal buffer."""
        for arg_name, arg_type in self._current.args.items():
            # read value from buffer
            val: Any = None

            # non-osu! datatypes
            if arg_type == osuTypes.i8:
                val = self.read_i8()
            elif arg_type == osuTypes.i16:
                val = self.read_i16()
            elif arg_type == osuTypes.i32:
                val = self.read_i32()
            elif arg_type == osuTypes.i64:
                val = self.read_i64()
            elif arg_type == osuTypes.u8:
                val = self.read_i8()
            elif arg_type == osuTypes.u16:
                val = self.read_u16()
            elif arg_type == osuTypes.u32:
                val = self.read_u32()
            elif arg_type == osuTypes.u64:
                val = self.read_u64()

            # osu!-specific data types
            elif arg_type == osuTypes.string:
                val = self.read_string()
            elif arg_type == osuTypes.i32_list:
                val = self.read_i32_list_i16l()
            elif arg_type == osuTypes.i32_list4l:
                val = self.read_i32_list_i32l()
            elif arg_type == osuTypes.message:
                val = self.read_message()
            elif arg_type == osuTypes.channel:
                val = self.read_channel()
            elif arg_type == osuTypes.match:
                val = self.read_match()

            elif arg_type == osuTypes.raw:
                # return all packet data raw.
                val = self.view[:self._current.length]
                self.view = self.view[self._current.length:]
            else:
                # should never happen?
                raise ValueError

            # add to our packet object
            setattr(self._current, arg_name, val)

    def read_header(self) -> tuple[int, int]:
        """Read the header of an osu! packet (id & length)."""
        if len(self.view) < 7:
            # not even minimal data
            # remaining in buffer.
            raise StopIteration

        # read type & length from the body
        data = struct.unpack('<HxI', self.view[:7])
        self.view = self.view[7:]
        return Packets(data[0]), data[1]

    def ignore_packet(self) -> None:
        """Skip the current packet in the buffer."""
        self.view = self.view[self._current.length:]
        self._current = None

    """ type readers (functions to read different types from buf) """

    """ basic integral types (signed & unsigned) """
    def _read_integral(self, size: int, signed: bool) -> int:
        val = int.from_bytes(self.view[:size], 'little', signed=signed)
        self.view = self.view[size:]
        return val

    read_i8 = partialmethod(_read_integral, size=1, signed=True)
    read_u8 = partialmethod(_read_integral, size=1, signed=False)
    read_i16 = partialmethod(_read_integral, size=2, signed=True)
    read_u16 = partialmethod(_read_integral, size=2, signed=False)
    read_i32 = partialmethod(_read_integral, size=4, signed=True)
    read_u32 = partialmethod(_read_integral, size=4, signed=False)
    read_i64 = partialmethod(_read_integral, size=8, signed=True)
    read_u64 = partialmethod(_read_integral, size=8, signed=False)

    """ floating point types """
    def read_f32(self) -> float:
        val, = struct.unpack_from('<f', self.view[:4])
        self.view = self.view[4:]
        return val

    def read_f64(self) -> float:
        val, = struct.unpack_from('<d', self.view[:8])
        self.view = self.view[8:]
        return val

    """ integral list types """
    # XXX: some osu! packets use i16 for
    # array length, while others use i32
    def _read_i32_list(self, len_size: int) -> tuple[int]:
        length = int.from_bytes(self.view[:len_size], 'little')
        self.view = self.view[len_size:]

        val = struct.unpack(f'<{"I" * length}', self.view[:length * 4])
        self.view = self.view[length * 4:]
        return val

    read_i32_list_i16l = partialmethod(_read_i32_list, len_size=2)
    read_i32_list_i32l = partialmethod(_read_i32_list, len_size=4)

    """ string type (variable length encoding w/ uleb128) """
    def read_string(self) -> str:
        exists = self.view[0] == 0x0b
        self.view = self.view[1:]

        if not exists:
            # no string sent.
            return ''

        # non-empty string, decode str length (uleb128)
        length = shift = 0

        while True:
            b = self.view[0]
            self.view = self.view[1:]

            length |= (b & 0b01111111) << shift
            if (b & 0b10000000) == 0:
                break

            shift += 7

        val = self.view[:length].tobytes().decode() # copy
        self.view = self.view[length:]
        return val

    def read_message(self) -> Message: # namedtuple
        """Read an osu! message from the internal buffer."""
        return Message(
            fromname = self.read_string(),
            msg = self.read_string(),
            tarname = self.read_string(),
            fromid = self.read_i32()
        )

    def read_channel(self) -> Channel:
        return Channel(
            name = self.read_string(),
            desc = self.read_string(),
            players = self.read_i32()
        )
    
    def read_match(self) -> Match:
        match = Match()

        self.view = self.view[3:]

        self.read_i8()

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
                self.view = self.view[4:]

        match.host = glob.players_id[self.read_i32()]

        match.mode = osuModes(self.read_i8())
        match.win_cond = winConditions(self.read_i8())
        match.type = teamTypes(self.read_i8())

        match.fm = self.read_i8() == 1

        if match.fm:
            for slot in match.slots:
                slot.mods = Mods(self.read_i32())

        match.seed = self.read_i32()

        return match

def write_uleb128(num: int) -> bytearray:
    """ Write `num` into an unsigned LEB128. """
    if num == 0:
        return bytearray(b'\x00')

    ret = bytearray()
    length = 0

    while num > 0:
        ret.append(num & 0b01111111)
        num >>= 7
        if num != 0:
            ret[length] |= 0b10000000
        length += 1

    return ret

def write_string(s: str) -> bytearray:
    """ Write `s` into bytes (ULEB128 & string). """
    if s:
        encoded = s.encode()
        ret = bytearray(b'\x0b')
        ret += write_uleb128(len(encoded))
        ret += encoded
    else:
        ret = bytearray(b'\x00')

    return ret

def write_i32_list(l: tuple[int, ...]) -> bytearray:
    """ Write `l` into bytes (int32 list). """
    ret = bytearray(len(l).to_bytes(2, 'little'))

    for i in l:
        ret += i.to_bytes(4, 'little')

    return ret

def write_message(sender: str, msg: str, recipient: str,
                  sender_id: int) -> bytearray:
    """ Write params into bytes (osu! message). """
    ret = bytearray(write_string(sender))
    ret += write_string(msg)
    ret += write_string(recipient)
    ret += sender_id.to_bytes(4, 'little', signed=True)
    return ret

def write_channel(name: str, desc: str,
                  players: int) -> bytearray:
    """ Write params into bytes (osu! channel). """
    ret = bytearray(write_string(name))
    ret += write_string(desc)
    ret += players.to_bytes(2, 'little')
    return ret

def write_match(m: Match, send_pw) -> bytearray:
    if m.pw:
        if send_pw:
            pw = write_string(m.pw)
        else:
            pw = b'\x0b\x00'
    else:
        pw = b'\x00'

    r = bytearray(struct.pack('<HbbI', m.id, m.in_prog, 0, m.mods))
    r += write_string(m.name)
    r += pw

    r += write_string(m.bname)
    r += (m.bid).to_bytes(4, 'little', signed=True)
    r += write_string(m.bmd5)

    r.extend([slot.status for slot in m.slots])
    r.extend([slot.team for slot in m.slots])

    for slot in m.slots:
        if slot.status & slotStatus.has_player:
            r += (slot.player.id).to_bytes(4, 'little')

    r += (m.host.id).to_bytes(4, 'little')

    r.extend((m.mode.value, m.win_cond, m.type, m.fm))

    if m.fm:
        for slot in m.slots:
            r += (slot.mods).to_bytes(4, 'little')

    r += (m.seed).to_bytes(4, 'little') # seed is troll

    return r

def write(packid: int, *args: tuple[Any, ...]) -> bytes:
    """ Write `args` into bytes. """
    ret = bytearray(struct.pack('<Hx', packid))

    for p_args, p_type in args:
        if p_type == osuTypes.raw:
            ret += p_args
        elif p_type == osuTypes.string:
            ret += write_string(p_args)
        elif p_type == osuTypes.i32_list:
            ret += write_i32_list(p_args)
        elif p_type == osuTypes.message:
            ret += write_message(*p_args)
        elif p_type == osuTypes.channel:
            ret += write_channel(*p_args)
        elif p_type == osuTypes.match:
            ret += write_match(*p_args)
        else:
            # not a custom type, use struct to pack the data.
            ret += struct.pack(_specifiers[p_type], p_args)

    # add size
    ret[3:3] = struct.pack('<I', len(ret) - 3)
    return bytes(ret)

@cache
def userID(id: int) -> bytes:
    return write(Packets.CHO_USER_ID, (id, osuTypes.i32))

@cache
def protocolVersion(ver: int) -> bytes:
    return write(Packets.CHO_PROTOCOL_VERSION, (ver, osuTypes.i32))

@cache
def banchoPrivileges(priv: int) -> bytes:
    return write(Packets.CHO_PRIVILEGES, (priv, osuTypes.i32))

def botPresence(player) -> bytes:
    return write(
        Packets.CHO_USER_PRESENCE,
        (player.id, osuTypes.i32),
        (player.name, osuTypes.string),
        (player.offset + 24, osuTypes.u8), # utc offset
        (player.country, osuTypes.u8),
        (31, osuTypes.u8),
        (player.loc[0], osuTypes.f32), # long | off map cus bot
        (player.loc[1], osuTypes.f32), # lat | off map cus bot
        (0, osuTypes.i32)
    )

def userPresence(player) -> bytes:
    if player is glob.bot:
        return botPresence(player)

    return write(
        Packets.CHO_USER_PRESENCE,
        (player.id, osuTypes.i32),
        (player.name, osuTypes.string),
        (player.offset + 24, osuTypes.u8), # utc offset
        (player.country, osuTypes.u8),
        (player.client_priv | (player.mode_vn << 5), osuTypes.u8),
        (player.loc[0], osuTypes.f32), # long
        (player.loc[1], osuTypes.f32), # lat
        (player.current_stats.rank, osuTypes.i32)
    )

def botStats() -> bytes:
    return write(
        Packets.CHO_USER_STATS,
        (1, osuTypes.i32),
        (6, osuTypes.u8), # action, hardcoded for good because its the bot | id 6 = watching
        ('over Asahi...', osuTypes.string), # action text (e.g Watching over Asahi...)
        ('', osuTypes.string), # map md5
        (0, osuTypes.i32), # mods
        (0, osuTypes.u8), # game mode
        (0, osuTypes.i32), # map id
        (0, osuTypes.i64), # ranked score
        (0.00, osuTypes.f32), # accuracy
        (0, osuTypes.i32), # playcount
        (0, osuTypes.i64), # total score
        (0, osuTypes.i32), # rank
        (0, osuTypes.i16) # pp
    )

def userStats(player) -> bytes:
    if player is glob.bot:
        return botStats()

    return write(
        Packets.CHO_USER_STATS,
        (player.id, osuTypes.i32),
        (player.action, osuTypes.u8), # action
        (player.info, osuTypes.string), # info text
        (player.map_md5, osuTypes.string), # map md5
        (player.mods, osuTypes.i32), # mods
        (player.mode_vn, osuTypes.u8), # game mode
        (player.map_id, osuTypes.i32), # map id
        (player.current_stats.rscore, osuTypes.i64), # ranked score
        (player.current_stats.acc / 100.0, osuTypes.f32), # accuracy
        (player.current_stats.pc, osuTypes.i32), # playcount
        (player.current_stats.tscore, osuTypes.i64), # total score
        (player.current_stats.rank, osuTypes.i32), # rank
        (player.current_stats.pp, osuTypes.i16) # pp
    )

def notification(msg: str) -> bytes:
    return write(Packets.CHO_NOTIFICATION, (msg, osuTypes.string))

@cache
def channelInfoEnd() -> bytes:
    return write(Packets.CHO_CHANNEL_INFO_END)

@cache
def restartServer(time: int) -> bytes:
    return write(Packets.CHO_RESTART, (time, osuTypes.i32))

@cache
def menuIcon() -> bytes:
    return write(Packets.CHO_MAIN_MENU_ICON, (f'{glob.config.menu_image}|{glob.config.menu_url}', osuTypes.string))

def friends(friends) -> bytes:
    return write(Packets.CHO_FRIENDS_LIST, (friends, osuTypes.i32_list)) # force just user itself for now to make sure it works

@cache
def silenceEnd(unix: int) -> bytes:
    return write(Packets.CHO_SILENCE_END, (unix, osuTypes.i32))

def sendMessage(fromname: str, msg: str, tarname: str, fromid: int) -> bytes:
    return write(Packets.CHO_SEND_MESSAGE, ((fromname, msg, tarname, fromid), osuTypes.message))

@cache
def logout(uid: int) -> bytes:
    return write(Packets.CHO_USER_LOGOUT, (uid, osuTypes.i32), (0, osuTypes.u8)) # delay for logout ????

@cache
def blockDM() -> bytes:
    return write(Packets.CHO_USER_DM_BLOCKED)

@cache
def spectatorJoined(uid: int) -> bytes:
    return write(Packets.CHO_FELLOW_SPECTATOR_JOINED, (uid, osuTypes.i32))

@cache
def hostSpectatorJoined(uid: int) -> bytes:
    return write(Packets.CHO_SPECTATOR_JOINED, (uid, osuTypes.i32))

@cache
def spectatorLeft(uid: int) -> bytes:
    return write(Packets.CHO_FELLOW_SPECTATOR_LEFT, (uid, osuTypes.i32))

@cache
def hostSpectatorLeft(uid: int) -> bytes:
    return write(Packets.CHO_SPECTATOR_LEFT, (uid, osuTypes.i32))

def spectateFrames(frames: bytes) -> bytes:
    return write(Packets.CHO_SPECTATE_FRAMES, (frames, osuTypes.raw))

def channelJoin(chan: str) -> bytes:
    return write(Packets.CHO_CHANNEL_JOIN_SUCCESS, (chan, osuTypes.string))

def channelInfo(chan) -> bytes:
    return write(Packets.CHO_CHANNEL_INFO, ((chan.name, chan.desc, chan.count), osuTypes.channel))

def channelKick(chan: str) -> bytes:
    return write(Packets.CHO_CHANNEL_KICK, (chan, osuTypes.string))

@cache
def matchJoinFail() -> bytes:
    return write(Packets.CHO_MATCH_JOIN_FAIL)

def matchJoinSuccess(match) -> bytes:
    return write(Packets.CHO_MATCH_JOIN_SUCCESS, ((match, True), osuTypes.match))

def updateMatch(match, send_pw) -> bytes:
    return write(Packets.CHO_UPDATE_MATCH, ((match, send_pw), osuTypes.match))

@cache
def disposeMatch(id) -> bytes:
    return write(Packets.CHO_DISPOSE_MATCH, (id, osuTypes.i32))

@cache
def matchTransferHost() -> bytes:
    return write(Packets.CHO_MATCH_TRANSFER_HOST)

def matchStart(match) -> bytes:
    return write(Packets.CHO_MATCH_START, ((match, True), osuTypes.match))

@cache
def matchComplete() -> bytes:
    return write(Packets.CHO_MATCH_COMPLETE)

@cache
def matchAllLoaded() -> bytes:
    return write(Packets.CHO_MATCH_ALL_PLAYERS_LOADED)

@cache
def matchPlayerFailed(sid) -> bytes:
    return write(Packets.CHO_MATCH_PLAYER_FAILED, (sid, osuTypes.i32))

@cache
def matchSkip() -> bytes:
    return write(Packets.CHO_MATCH_SKIP)

@cache
def matchPlayerSkipped(uid) -> bytes:
    return write(Packets.CHO_MATCH_PLAYER_SKIPPED, (uid, osuTypes.i32))

@cache
def matchTransferHost() -> bytes:
    return write(Packets.CHO_MATCH_TRANSFER_HOST)

def matchInvite(f, to) -> bytes:
    msg = f'{f.name} invited you to join {f.match.embed}!'
    return write(Packets.CHO_MATCH_INVITE, ((f.name, msg, to, f.id), osuTypes.message))

def newMatch(m) -> bytes:
    return write(Packets.CHO_NEW_MATCH, ((m, True), osuTypes.match))