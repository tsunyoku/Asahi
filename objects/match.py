from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from .player import Player
    from .channel import Channel

from constants.modes import osuModes
from constants.mods import Mods
from constants.types import teamTypes, winConditions
from objects.clan import Clan

from . import glob
from packets import writer

from enum import IntEnum, unique

import asyncio

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

CLAN_BATTLE_EXPLAIN = (
    "All online clan members have joined! If you're unsure of how clan battles work, here is a rundown. "
    "Clan battles are team vs multiplayer matches against 2 clans. You will take turns picking maps until the first clan reaches 5 wins. Wins are decided by average score/pp. "
    "If you played vanilla then the clan with the highest average score (all clan users participating added up) will gain a win. This is the same for relax/autopilot but with pp. "
    "Once you reach 5 wins, that clan wins and the match is over. When you win a match, your clan gains 'clan score' which is the metric used for clan leaderboards. Have fun!"
)

class Slot:
    # i actually kind of like this setup

    def __init__(self):
        self.player: 'Player' = None

        self.status: slotStatus = slotStatus.open
        self.team: Teams = Teams.teamless

        self.mods: Mods = Mods.NOMOD

        self.loaded: bool = False
        self.skipped: bool = False

    @property
    def empty(self) -> bool:
        return self.player is None

    @property
    def playing(self) -> bool:
        return self.status is slotStatus.playing and not self.loaded

    def reset(self) -> None:
        self.player = None

        self.status = slotStatus.open
        self.team = Teams.teamless

        self.mods = Mods.NOMOD

        self.loaded = False
        self.skipped = False

    def copy(self, s) -> None:
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

        self.first_host: Optional['Player'] = None
        self.host: Optional['Player'] = None

        self.mods: Mods = Mods.NOMOD
        self.mode: osuModes = osuModes.std

        self.fm: bool = False

        self.chat: Optional[Channel] = None

        self.slots: list[Slot] = [Slot() for _ in range(16)] # init match with 16 empty slots
        self.type: teamTypes = teamTypes.head
        self.win_cond: winConditions = winConditions.score

        self.in_prog: bool = False
        self.seed: int = 0 # osu mania players crying rn

        # i fucking HATE this
        self.bid: int = 0
        self.bname: str = ''
        self.bmd5: str = ''

        self.clan_battle: bool = False
        self.clan_1: Optional[Clan] = None
        self.clan_2: Optional[Clan] = None

        self.clan_1_wins: int = 0
        self.clan_2_wins: int = 0

        self.battle_ready: bool = False
        self.clan_1_users: list = []
        self.clan_2_users: list = []

        self.start_task = None
        self.alert_tasks = None

    @property
    def invite(self) -> str:
        return f'osump://{self.id}/{self.pw}'

    @property
    def embed(self):
        return f'[{self.invite} {self.name}]'

    def next_free(self) -> int:
        for sn, s in enumerate(self.slots):
            if s.status == slotStatus.open:
                return sn

    def get_slot(self, user: 'Player') -> Optional[Slot]:
        for slot in self.slots:
            if user is slot.player:
                return slot

    def get_slot_id(self, user: 'Player') -> int:
        for sn, slot in enumerate(self.slots):
            if user is slot.player:
                return sn

    def unready_players(self, wanted: slotStatus) -> None:
        for slot in self.slots:
            if slot.status is wanted:
                slot.status = slotStatus.not_ready

    def start(self) -> None:
        missing_map = []

        for slot in self.slots:
            if slot.status & slotStatus.has_player:
                if slot.status != slotStatus.no_map:
                    slot.status = slotStatus.playing
                else:
                    missing_map.append(slot.player.id)

        self.in_prog = True
        self.enqueue(writer.matchStart(self), ignore=missing_map)
        self.enqueue_state()

    async def start_battle(self) -> None:
        for slot in self.slots:
            if slot.status & slotStatus.has_player:

                if slot.team is Teams.red:
                    self.clan_1_users.append(slot.player)
                else:
                    self.clan_2_users.append(slot.player)

            else:
                slot.status = slotStatus.locked

        if len(self.clan_1_users) != len(self.clan_2_users):
            self.chat.send(glob.bot, 'There is an uneven amount of users on each team! Please make the teams equal before we start the battle.', False)
            return

        self.battle_ready = True

        self.chat.send(
            glob.bot,
            CLAN_BATTLE_EXPLAIN,
            False
        )

        self.chat.send(
            glob.bot,
            f'Players fighting:'
            f'\n{self.clan_1.name}: {", ".join(u.name for u in self.clan_1_users)}'
            f'\n{self.clan_2.name}: {", ".join(u.name for u in self.clan_2_users)}'
            '\n\nAny clan members who come online at this point will be unable to participate!',
            False
        )

    async def clan_scores(self, ignore: list = []) -> None:
        time_waited = 0

        table = self.mode.table
        sort = self.mode.sort

        # average of 1st clan's scores
        clan1_scores = []
        clan1_retry = []
        for m in self.clan_1_users:
            if m.id not in ignore:
                score = await glob.db.fetchval(
                    f'SELECT {sort} FROM {table} WHERE uid = %s AND md5 = %s ORDER BY time DESC LIMIT 1',
                    [m.id, self.bmd5]
                )

                if not score:
                    clan1_retry.append(m.id)
                else:
                    clan1_scores.append(score)

        clan2_scores = []
        clan2_retry = []
        for m in self.clan_2_users:
            if m.id not in ignore:
                score = await glob.db.fetchval(
                    f'SELECT {sort} FROM {table} WHERE uid = %s AND md5 = %s ORDER BY time DESC LIMIT 1',
                    [m.id, self.bmd5]
                )

                if not score:
                    clan2_retry.append(m.id)
                else:
                    clan2_scores.append(score)

        # retry those that missed
        for uid in clan1_retry:
            if uid not in ignore:
                score = await glob.db.fetchval(
                    f'SELECT {sort} FROM {table} WHERE uid = %s AND md5 = %s ORDER BY time DESC LIMIT 1',
                    [m.id, self.bmd5]
                )

                if score:
                    clan1_scores.append(score)
                    clan1_retry.remove(uid)

        for uid in clan2_retry:
            if uid not in ignore:
                score = await glob.db.fetchval(
                    f'SELECT {sort} FROM {table} WHERE uid = %s AND md5 = %s ORDER BY time DESC LIMIT 1',
                    [m.id, self.bmd5]
                )

                if score:
                    clan2_scores.append(score)
                    clan2_retry.remove(uid)

        if not clan1_retry and not clan2_retry:
            return await self.clan_sort(clan1_scores, clan2_scores)

        # still havent got them all we can wait another bit and then give up
        await asyncio.sleep(1)
        time_waited += 1

        while True:
            for uid in clan1_retry:
                if uid not in ignore:
                    score = await glob.db.fetchval(
                        f'SELECT {sort} FROM {table} WHERE uid = %s AND md5 = %s ORDER BY time DESC LIMIT 1',
                        [m.id, self.bmd5]
                    )

                    if score:
                        clan1_scores.append(score)
                        clan1_retry.remove(uid)

            for uid in clan2_retry:
                if uid not in ignore:
                    score = await glob.db.fetchval(
                        f'SELECT {sort} FROM {table} WHERE uid = %s AND md5 = %s ORDER BY time DESC LIMIT 1',
                        [m.id, self.bmd5]
                    )

                    if score:
                        clan2_scores.append(score)
                        clan2_retry.remove(uid)

            if not clan1_retry and not clan2_retry or time_waited > 10:
                await self.clan_sort(clan1_scores, clan2_scores)
                break

    async def clan_sort(self, clan1_scores: list, clan2_scores: list) -> None:
        if len(clan1_scores) == 0 or len(clan2_scores) == 0:
            return

        clan1_avg = sum(clan1_scores) / len(clan1_scores)
        clan2_avg = sum(clan2_scores) / len(clan2_scores)

        if clan1_avg == clan2_avg: # they drew, increment both
            self.clan_2_wins += 1
            self.clan_2_wins += 1
        elif clan1_avg > clan2_avg:
            self.clan_1_wins += 1
        elif clan2_avg > clan1_avg:
            self.clan_2_wins += 1

        winner = None

        if (self.clan_1_wins >= 5 and self.clan_2_wins >= 5) and (self.clan_1_wins == self.clan_2_wins): # they are drawing, lets continue the match
            pass
        elif self.clan_1_wins >= 5:
            winner = self.clan_1
        elif self.clan_2_wins >= 5:
            winner = self.clan_2

        if winner:
            self.chat.send(
                glob.bot,
                f'{winner.name} wins!\n\n'
                f'Final Score: {self.clan_1_wins} - {self.clan_2_wins} ({self.clan_1.name} - {self.clan_2.name})\n\n'
                f'Congratulations! {winner.name} will receive their extra clan points soon.',
                False
            )

            self.clan_battle = False
            self.battle_ready = False

            for clan in (self.clan_1, self.clan_2):
                del glob.clan_battles[clan]
                clan.battle = None

            return await glob.db.execute('UPDATE clans SET score = score + 50 WHERE id = %s', [winner.id])

        if self.host in self.clan_1_users:
            new_host = await glob.players.get(id=self.clan_2.owner)
            next_pick = self.clan_2
        else:
            new_host = await glob.players.get(id=self.clan_1.owner)
            next_pick = self.clan_1

        self.host = new_host # alternate turns for map picks

        self.chat.send(
            glob.bot,
            f'Next Clan to Pick: {next_pick.name}\n\n'
            f'Current Score: {self.clan_1_wins} - {self.clan_2_wins} ({self.clan_1.name} - {self.clan_2.name})',
            False
        )

        self.enqueue_state()

    def enqueue_state(self, lobby: bool = True) -> None:
        self.chat.enqueue(writer.updateMatch(self, send_pw=True))

        if lobby:
            glob.channels['#lobby'].enqueue(writer.updateMatch(self, send_pw=False))

    def enqueue(self, packet, lobby: bool = True, ignore = []) -> None:
        self.chat.enqueue(packet, ignore_list=ignore)

        if lobby:
            glob.channels['#lobby'].enqueue(packet)
