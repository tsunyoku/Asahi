import struct

from objects import glob
from constants.types import osuTypes
from objects.match import slotStatus, Teams, Match

from enum import IntEnum, unique

_spec = ('<b', '<B', '<h', '<H', '<i', '<I', '<f', '<q', '<Q', '<d')

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

cpdef bytearray write_uleb128(int val):
    if val == 0:
        return bytearray(b'\x00')

    d = bytearray()
    l = 0

    while val > 0:
        d.append(val & 0x7F)
        val >>= 7
        if val != 0:
            d[l] |= 0x80

        l += 1

    return d

cpdef bytearray write_string(str s):
    if not s:
        return bytearray(b"\x00")

    d = bytearray(b"\x0B")
    byte = s.encode("utf-8", "ignore")
    d += write_uleb128(len(byte))
    d += byte

    return d

cpdef bytearray write_i32_list(l):
    d = bytearray(len(l).to_bytes(2, 'little'))

    for i in l:
        d += i.to_bytes(4, 'little')

    return d

cpdef bytearray write_message(tuple args):
    cpdef str fr = args[0]
    cpdef str msg = args[1]
    cpdef str to = args[2]
    cpdef int fromid = args[3]

    d = bytearray(write_string(fr))

    d += write_string(msg)
    d += write_string(to)

    d += fromid.to_bytes(4, 'little', signed=True)

    return d

cpdef bytearray write_channel(tuple args):
    cpdef str name = args[0]
    cpdef str desc = args[1]
    cpdef int p = args[2]

    d = bytearray(write_string(name))

    d += write_string(desc)
    d += p.to_bytes(2, 'little')

    return d

cpdef bytearray write_match(tuple args):
    cpdef m = args[0]
    cpdef send_pw = args[1]

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

    r.extend([m.mode.value, m.win_cond, m.type, m.fm])

    if m.fm:
        for slot in m.slots:
            r += (slot.mods).to_bytes(4, 'little')

    r += (m.seed).to_bytes(4, 'little') # seed is troll

    return r

# CURSED
def write(pid: int, *args) -> bytes:
    return cp_write(pid, args)

cdef bytes cp_write(int pid, tuple args):
    d = bytearray(struct.pack('<Hx', pid))

    for a, t in args:
        if t == osuTypes.raw:
            d += a
        elif t == osuTypes.string:
            d += write_string(a)
        elif t == osuTypes.i32_list:
            d += write_i32_list(a)
        elif t == osuTypes.message:
            d += write_message(a)
        elif t == osuTypes.channel:
            d += write_channel(a)
        elif t == osuTypes.match:
            d += write_match(a)
        else:
            d += struct.pack(_spec[t], a)

    d[3:3] = struct.pack('<I', len(d) - 3)
    return bytes(d)

cpdef bytes userID(int id):
    return write(Packets.CHO_USER_ID, (id, osuTypes.i32))

cpdef bytes protocolVersion(int ver):
    return write(Packets.CHO_PROTOCOL_VERSION, (ver, osuTypes.i32))

cpdef bytes banchoPrivileges(int priv):
    return write(Packets.CHO_PRIVILEGES, (priv, osuTypes.i32))

cpdef bytes botPresence(player):
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

cpdef bytes userPresence(player):
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

cpdef bytes botStats():
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

cpdef bytes userStats(player):
    if player is glob.bot:
        return botStats()

    stats = player.current_stats
    if stats.pp > 0x7fff:
        rscore = stats.pp
        pp = 0
    else:
        rscore = stats.rscore
        pp = stats.pp

    return write(
        Packets.CHO_USER_STATS,
        (player.id, osuTypes.i32),
        (player.action, osuTypes.u8), # action
        (player.info, osuTypes.string), # info text
        (player.map_md5, osuTypes.string), # map md5
        (player.mods, osuTypes.i32), # mods
        (player.mode_vn, osuTypes.u8), # game mode
        (player.map_id, osuTypes.i32), # map id
        (rscore, osuTypes.i64), # ranked score
        (stats.acc / 100.0, osuTypes.f32), # accuracy
        (stats.pc, osuTypes.i32), # playcount
        (stats.tscore, osuTypes.i64), # total score
        (stats.rank, osuTypes.i32), # rank
        (pp, osuTypes.i16) # pp
    )

cpdef bytes notification(str msg):
    return write(Packets.CHO_NOTIFICATION, (msg, osuTypes.string))

cpdef bytes channelInfoEnd():
    return write(Packets.CHO_CHANNEL_INFO_END)

cpdef bytes restartServer(int time):
    return write(Packets.CHO_RESTART, (time, osuTypes.i32))

cpdef bytes menuIcon():
    return write(Packets.CHO_MAIN_MENU_ICON, (f'{glob.config.menu_image}|{glob.config.menu_url}', osuTypes.string))

cpdef bytes friends(friendsl):
    return write(Packets.CHO_FRIENDS_LIST, (friendsl, osuTypes.i32_list))

cpdef bytes silenceEnd(int unix):
    return write(Packets.CHO_SILENCE_END, (unix, osuTypes.i32))

cpdef bytes sendMessage(str fromname, str msg, str tarname, int fromid):
    return write(Packets.CHO_SEND_MESSAGE, ((fromname, msg, tarname, fromid), osuTypes.message))

cpdef bytes logout(int uid):
    return write(Packets.CHO_USER_LOGOUT, (uid, osuTypes.i32), (0, osuTypes.u8)) # delay for logout ????

cpdef bytes blockDM():
    return write(Packets.CHO_USER_DM_BLOCKED)

cpdef bytes spectatorJoined(int uid):
    return write(Packets.CHO_FELLOW_SPECTATOR_JOINED, (uid, osuTypes.i32))

cpdef bytes hostSpectatorJoined(int uid):
    return write(Packets.CHO_SPECTATOR_JOINED, (uid, osuTypes.i32))

cpdef bytes spectatorLeft(int uid):
    return write(Packets.CHO_FELLOW_SPECTATOR_LEFT, (uid, osuTypes.i32))

cpdef bytes hostSpectatorLeft(int uid):
    return write(Packets.CHO_SPECTATOR_LEFT, (uid, osuTypes.i32))

cpdef bytes spectateFrames(bytes frames):
    return write(Packets.CHO_SPECTATE_FRAMES, (frames, osuTypes.raw))

cpdef bytes channelJoin(str chan):
    return write(Packets.CHO_CHANNEL_JOIN_SUCCESS, (chan, osuTypes.string))

cpdef bytes channelInfo(chan):
    return write(Packets.CHO_CHANNEL_INFO, ((chan.name, chan.desc, chan.count), osuTypes.channel))

cpdef bytes channelKick(str chan):
    return write(Packets.CHO_CHANNEL_KICK, (chan, osuTypes.string))

cpdef bytes matchJoinFail():
    return write(Packets.CHO_MATCH_JOIN_FAIL)

cpdef bytes matchJoinSuccess(match):
    return write(Packets.CHO_MATCH_JOIN_SUCCESS, ((match, True), osuTypes.match))

cpdef bytes updateMatch(match, send_pw):
    return write(Packets.CHO_UPDATE_MATCH, ((match, send_pw), osuTypes.match))

cpdef bytes disposeMatch(id):
    return write(Packets.CHO_DISPOSE_MATCH, (id, osuTypes.i32))

cpdef bytes matchTransferHost():
    return write(Packets.CHO_MATCH_TRANSFER_HOST)

cpdef bytes matchStart(match):
    return write(Packets.CHO_MATCH_START, ((match, True), osuTypes.match))

cpdef bytes matchComplete():
    return write(Packets.CHO_MATCH_COMPLETE)

cpdef bytes matchAllLoaded():
    return write(Packets.CHO_MATCH_ALL_PLAYERS_LOADED)

cpdef bytes matchPlayerFailed(sid):
    return write(Packets.CHO_MATCH_PLAYER_FAILED, (sid, osuTypes.i32))

cpdef bytes matchSkip():
    return write(Packets.CHO_MATCH_SKIP)

cpdef bytes matchPlayerSkipped(uid):
    return write(Packets.CHO_MATCH_PLAYER_SKIPPED, (uid, osuTypes.i32))

cpdef bytes versionUpdateForced():
    return write(Packets.CHO_VERSION_UPDATE_FORCED)

cpdef bytes matchInvite(f, to):
    msg = f'{f.name} invited you to join {f.match.embed}!'
    return write(Packets.CHO_MATCH_INVITE, ((f.name, msg, to, f.id), osuTypes.message))

cpdef bytes newMatch(m):
    return write(Packets.CHO_NEW_MATCH, ((m, True), osuTypes.match))

cpdef bytes matchAbort():
    return write(Packets.CHO_MATCH_ABORT)
