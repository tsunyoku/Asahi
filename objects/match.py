from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.player import Player
    from objects.channel import Channel

from constants.modes import osuModes
from constants.mods import Mods
from constants.types import teamTypes, winConditions

from objects import glob

from enum import IntEnum, unique

import packets

@unique
class slotStatus(IntEnum):
    open = 1
    locked = 2
    not_ready = 4
    ready = 8
    no_map = 16
    playing = 32
    complete = 64
    quit = 128

    has_player = not_ready | ready | no_map | playing | complete

@unique
class Teams(IntEnum):
    teamless = 0
    blue = 1
    red = 2

class Slot:
    # i actually kind of like this setup

    def __init__(self):
        self.player: Player = None

        self.status: slotStatus = slotStatus.open
        self.team: Teams = Teams.teamless

        self.mods: Mods = Mods.NOMOD

        self.loaded: bool = False
        self.skipped: bool = False

    @property
    def empty(self):
        return self.player is None

    @property
    def playing(self):
        return self.status is slotStatus.playing and not self.loaded

    def reset(self):
        self.player = None

        self.status = slotStatus.open
        self.team = Teams.teamless

        self.mods = Mods.NOMOD

        self.loaded = False
        self.skipped = False

    def copy(self, s):
        self.player = s.player

        self.status = s.status
        self.team = s.team

        self.mods = s.mods

class Match:
    # I AM IN IMMENSE PAIN SOMEONE DIAL 999

    def __init__(self):
        self.id: int = 0
        self.name: str = ''
        self.pw: str = ''

        self.host: Player = None

        self.mods: Mods = Mods.NOMOD
        self.mode: osuModes = osuModes.std

        self.fm: bool = False

        self.chat: Channel = None

        self.slots: list[Slot] = [Slot() for _ in range(16)] # init match with 16 empty slots
        self.type: teamTypes = teamTypes.head
        self.win_cond: winConditions = winConditions.score

        self.in_prog: bool = False
        self.seed: int = 0 # osu mania players crying rn

        # i fucking HATE this
        self.bid: int = 0
        self.bname: str = ''
        self.bmd5: str = ''
    
    @property
    def invite(self):
        return f'osump://{self.id}/{self.pw}'

    @property
    def embed(self):
        return f'[{self.invite} {self.name}]'

    def next_free(self):
        for sn, s in enumerate(self.slots):
            if s.status == slotStatus.open:
                return sn

    def get_slot(self, user):
        for slot in self.slots:
            if user is slot.player:
                return slot

    def get_slot_id(self, user):
        for sn, slot in enumerate(self.slots):
            if user is slot.player:
                return sn

    def get_host(self):
        for slot in self.slots:
            if slot.player is self.host:
                return slot.player

    def unready_players(self, wanted):
        for slot in self.slots:
            if slot.status is wanted:
                slot.status = slotStatus.not_ready

    def start(self):
        missing_map = []

        for slot in self.slots:
            if slot.status & slotStatus.has_player:
                if slot.status != slotStatus.no_map:
                    slot.status = slotStatus.playing
                else:
                    missing_map.append(slot.player.id)

        self.in_prog = True
        self.enqueue(packets.matchStart(self), ignore=missing_map)
        self.enqueue_state()

    def enqueue_state(self, lobby: bool = True):
        self.chat.enqueue(packets.updateMatch(self, send_pw=True))

        if lobby:
            glob.channels['#lobby'].enqueue(packets.updateMatch(self, send_pw=False))

    def enqueue(self, packet, lobby: bool = True, ignore = []):
        self.chat.enqueue(packet, ignore_list=ignore)

        if lobby:
            glob.channels['#lobby'].enqueue(packet)