from __future__ import annotations

import struct
from enum import IntEnum
from functools import cache
from typing import Iterator
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.objects.channel import Channel
    from app.objects.player import Player

from app.typing import Channel as osuChannel
from app.typing import f32
from app.typing import i16
from app.typing import i32
from app.typing import i32_list
from app.typing import i64
from app.typing import Message
from app.typing import PacketHandler
from app.typing import String
from app.typing import u32
from app.typing import u8


class Packet:
    def __init__(self, packet_id: int, length: int, data: bytearray):
        self.data: bytearray = data
        self.packet_id: int = packet_id
        self.length: int = length

    def read_header(self) -> None:
        array = self.read(7)
        data = struct.unpack("<HxI", array)

        self.packet_id = data[0]
        self.length = data[1]

    @classmethod
    def from_data(self, data: bytearray) -> Packet:
        packet = Packet(0, 0, data)

        packet.read_header()
        return packet

    @classmethod
    def from_id(self, packet_id: int) -> Packet:
        return Packet(packet_id, 0, bytearray())

    def offset(self, count: int) -> None:
        self.data = self.data[count:]

    def read(self, count: int) -> bytearray:
        data = self.data[:count]
        self.offset(count)

        return data

    def __iadd__(self, other: bytearray) -> Packet:
        self.write(other)
        return self

    def write(self, data: bytearray) -> None:
        self.data += data

    def serialize(self) -> bytearray:
        return_data = bytearray()

        return_data += i16.write(self.packet_id)
        return_data += u8.write(0)  # padding byte

        # actual packet data
        return_data += u32.write(len(self.data))
        return_data += self.data

        return return_data


def parse_header(data: bytearray) -> tuple[int, int]:
    header = data[:7]
    data = struct.unpack("<HxI", header)

    return data[0], data[1]  # packet id, length


class PacketArray:
    def __init__(self, data: bytearray, packet_map: dict[int, PacketHandler]) -> None:
        self.data = data
        self.packets: list[Packet] = []
        self.packet_map = packet_map

        self._split_data()

    def __iter__(self) -> Iterator[Packet]:
        return self.packets.__iter__()

    def __next__(self) -> tuple[Packet, PacketHandler]:
        packet = self.packets.__next__()
        handler = self.packet_map[packet.packet_id]

        return packet, handler

    def _split_data(self) -> None:
        while self.data:
            packet_id, length = parse_header(self.data)

            if packet_id not in self.packet_map.keys():
                self.data = self.data[7 + length :]
                continue

            packet_data = self.data[: 7 + length]
            packet = Packet.from_data(packet_data)
            self.packets.append(packet)

            self.data = self.data[7 + length :]


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
    CHO_UNAUTHORIZED = 62  # unused
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
    CHO_MONITOR = 80  # unused
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
    CHO_RTX = 105  # unused
    CHO_MATCH_ABORT = 106
    CHO_SWITCH_TOURNAMENT_SERVER = 107
    OSU_TOURNAMENT_JOIN_MATCH_CHANNEL = 108
    OSU_TOURNAMENT_LEAVE_MATCH_CHANNEL = 109


@cache
def user_id(id: int) -> bytearray:
    packet = Packet.from_id(Packets.CHO_USER_ID)
    packet += i32.write(id)
    return packet.serialize()


@cache
def protocol_version(version: int) -> bytearray:
    packet = Packet.from_id(Packets.CHO_PROTOCOL_VERSION)
    packet += i32.write(version)
    return packet.serialize()


@cache
def bancho_privileges(priv: int) -> bytearray:
    packet = Packet.from_id(Packets.CHO_PRIVILEGES)
    packet += i32.write(priv)
    return packet.serialize()


def user_presence(player: Player) -> bytearray:
    packet = Packet.from_id(Packets.CHO_USER_PRESENCE)

    packet += i32.write(player.id)
    packet += String.write(player.name)
    packet += u8.write(player.utc_offset + 24)
    packet += u8.write(player.geoloc.country.code)
    packet += u8.write(player.bancho_priv | (player.status.mode.as_vn << 5))
    packet += f32.write(player.geoloc.long)
    packet += f32.write(player.geoloc.lat)
    packet += i32.write(player.current_stats.rank)

    return packet.serialize()


def user_stats(player: Player) -> bytearray:
    packet = Packet.from_id(Packets.CHO_USER_STATS)

    stats = player.current_stats
    if stats.pp > 0x7FFF:
        rscore = stats.pp
        pp = 0
    else:
        rscore = stats.rscore
        pp = stats.pp

    packet += i32.write(player.id)
    packet += u8.write(player.status.action.value)
    packet += String.write(player.status.info_text)
    packet += String.write(player.status.map_md5)
    packet += i32.write(player.status.mods.value)
    packet += u8.write(player.status.mode.as_vn)
    packet += i32.write(player.status.map_id)
    packet += i64.write(rscore)
    packet += f32.write(stats.acc / 100.0)
    packet += i32.write(stats.plays)
    packet += i64.write(stats.tscore)
    packet += i32.write(stats.rank)
    packet += i16.write(pp)

    return packet.serialize()


@cache
def notification(msg: str) -> bytearray:
    packet = Packet.from_id(Packets.CHO_NOTIFICATION)
    packet += String.write(msg)
    return packet.serialize()


@cache
def channel_info_end() -> bytearray:
    packet = Packet.from_id(Packets.CHO_CHANNEL_INFO_END)
    return packet.serialize()


@cache
def restart_server(time: int) -> bytearray:
    packet = Packet.from_id(Packets.CHO_RESTART)
    packet += i32.write(time)
    return packet.serialize()


@cache
def menu_icon() -> bytearray:
    packet = Packet.from_id(Packets.CHO_MAIN_MENU_ICON)
    packet += String.write("|")  # TODO: implement
    return packet.serialize()


@cache
def friends_list(friends_list: list[int]) -> bytearray:
    packet = Packet.from_id(Packets.CHO_FRIENDS_LIST)
    packet += i32_list.write(friends_list)
    return packet.serialize()


@cache
def silence_end(time: int) -> bytearray:
    packet = Packet.from_id(Packets.CHO_SILENCE_END)
    packet += i32.write(time)
    return packet.serialize()


def send_message(message: Message) -> bytearray:
    packet = Packet.from_id(Packets.CHO_SEND_MESSAGE)
    packet += message.serialize()
    return packet.serialize()


@cache
def logout(user_id: int) -> bytearray:
    packet = Packet.from_id(Packets.CHO_USER_LOGOUT)

    packet += i32.write(user_id)
    packet += u8.write(0)  # ?

    return packet.serialize()


@cache
def block_dm() -> bytearray:
    packet = Packet.from_id(Packets.CHO_USER_DM_BLOCKED)
    return packet.serialize()


@cache
def spectator_joined(user_id: int) -> bytearray:
    packet = Packet.from_id(Packets.CHO_FELLOW_SPECTATOR_JOINED)
    packet += i32.write(user_id)
    return packet.serialize()


@cache
def host_spectator_joined(user_id: int) -> bytearray:
    packet = Packet.from_id(Packets.CHO_SPECTATOR_JOINED)
    packet += i32.write(user_id)
    return packet.serialize()


@cache
def spectator_left(user_id: int) -> bytearray:
    packet = Packet.from_id(Packets.CHO_FELLOW_SPECTATOR_LEFT)
    packet += i32.write(user_id)
    return packet.serialize()


@cache
def host_spectator_left(user_id: int) -> bytearray:
    packet = Packet.from_id(Packets.CHO_SPECTATOR_LEFT)
    packet += i32.write(user_id)
    return packet.serialize()


def spectate_frames(frames: bytes) -> bytearray:
    packet = Packet.from_id(Packets.CHO_SPECTATE_FRAMES)
    packet += frames
    return packet.serialize()


@cache
def join_channel(channel: str) -> bytearray:
    packet = Packet.from_id(Packets.CHO_CHANNEL_JOIN_SUCCESS)
    packet += String.write(channel)
    return packet.serialize()


def channel_info(channel: Channel) -> bytearray:
    packet = Packet.from_id(Packets.CHO_CHANNEL_INFO)

    channel = osuChannel(channel.name, channel.topic, channel.player_count)
    return channel.serialize()


@cache
def channel_kick(channel: str) -> bytearray:
    packet = Packet.from_id(Packets.CHO_CHANNEL_KICK)
    packet += String.write(channel)
    return packet.serialize()


@cache
def version_update_forced() -> bytearray:
    packet = Packet.from_id(Packets.CHO_VERSION_UPDATE_FORCED)
    return packet.serialize()


# TODO: match packets
