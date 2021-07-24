from . import glob
from .channel import Channel
from .beatmap import Beatmap
from .clan import Clan
from .match import slotStatus, Teams, Match
from packets import writer
from constants.privs import Privileges, ClientPrivileges
from constants.modes import osuModes
from constants.types import teamTypes
from constants.mods import Mods

from typing import Optional, TYPE_CHECKING, Union
from dataclasses import dataclass
from cmyui import log, Ansi
from cmyui.discord import Webhook, Embed
from datetime import datetime, timedelta

import queue
import time

if TYPE_CHECKING:
    from objects.score import Score

@dataclass
class Stats:
    rscore: int
    acc: float
    pc: int
    tscore: int
    rank: int
    country_rank: int
    pp: int
    max_combo: int
    playtime: int

class Player:
    def __init__(self, **uinfo):
        self.id: int = uinfo.get('id')
        self.name: str = uinfo.get('name')
        self.token: str = uinfo.get('token', '') # we will set default token in case of bot which won't have a token provided
        self.pw: str = uinfo.get('pw') # used for /web/ auth
        self.offset: int = uinfo.get('offset')
        self.login_time: int = uinfo.get('login_time')
        self.priv = uinfo.get('priv', Privileges(0))
        self.country_iso: str = uinfo.get('country_iso')
        self.country: int = uinfo.get('country')
        self.loc: list[float, float] = uinfo.get('loc', [0.0, 0.0]) # store as list cus y not (long, lat)
        self.friends: list[int] = []
        self.queue = queue.SimpleQueue()
        self.action: int = 0
        self.info: str = ''
        self.map_md5: str = ''
        self.mods: Mods = 0
        self.mode: int = 0
        self.mode_vn: int = 0 
        self.map_id: int = 0
        self.stats: dict[osuModes.value, Stats] = {}
        self.achievements: list = []

        self.spectators: list[Player] = []
        self.spectating: Optional[Player] = None
        self.channels: list[Channel] = []

        self.match: Optional[Match] = None

        self.np: Optional[Beatmap] = None
        self.last_score: Optional[Score] = None

        self.clan: Optional[Clan] = None

        self.last_ping: int = 0
        
        self.restricted: bool = False
        self.frozen: bool = False
        
        self.freeze_timer: int = uinfo.get('freeze_timer', 0)
        
        self.registered_at: int = uinfo.get('registered_at', 0)
        self.silence_end: int = uinfo.get('silence_end', 0)
        self.donor_end: int = uinfo.get('donor_end', 0)

        self.discord: int = uinfo.get('discord', 0)

    @property
    def full_name(self):
        if self.clan:
            return f'[{self.clan.tag}] {self.name}'
        else:
            return self.name

    @classmethod
    async def login(self, user: dict):
        p = self(
            id=user['id'], 
            name=user['name'], 
            token=user['token'], 
            offset=user['offset'], 
            login_time=user['ltime'],
            country_iso=user['country_iso'],
            country=user['country'],
            loc=[user['lon'], user['lat']],
            pw=user['md5'].decode(),
            priv=Privileges(user['priv']),
            freeze_timer=datetime.fromtimestamp(user['freeze_timer']),
            discord=user['discord']
        )

        p.friends = []
        async for user in glob.db.iter("SELECT user2 FROM friends WHERE user1 = %s", [p.id]):
            p.friends.append(user['user2'])

        clan = await glob.db.fetchval('SELECT clan FROM users WHERE id = %s', [p.id])
        if clan:
            p.clan = glob.clans.get(clan)
            
        if p.priv & Privileges.Restricted:
            p.restricted = True
            
        if p.priv & Privileges.Frozen:
            p.frozen = True
            
        db_achs = await glob.db.fetch('SELECT ach FROM user_achievements WHERE uid = %s', [p.id])
        for db in db_achs:
            for ach in glob.achievements:
                if db['ach'] == ach.id:
                    p.achievements.append(ach)
            
        return p
    
    @classmethod
    async def from_sql(self, spc: Union[str, int], discord = False):
        
        if discord:
            typ = 'discord'
        elif isinstance(spc, str):
            typ = 'name'
        elif isinstance(spc, int):
            typ = 'id'
        else:
            return # ?

        user = await glob.db.fetchrow(f'SELECT * FROM users WHERE {typ} = %s', [spc])
        
        if not user:
            return
        
        p = self(
            id=user['id'],
            name=user['name'],
            token='',
            offset=0,
            login_time=0,
            country_iso=user['country'],
            country=0,
            loc=[0, 0],
            pw='',
            priv=Privileges(user['priv']),
            freeze_timer=datetime.fromtimestamp(user['freeze_timer']),
            discord=user['discord']
        )

        if (clan := user['clan']):
            p.clan = glob.clans.get(clan)
        
        if p.priv & Privileges.Disallowed:
            p.restricted = True
            
        if p.priv & Privileges.Frozen:
            p.frozen = True
            
        await p.set_stats()
        
        return p

    async def set_stats(self) -> None:
        for mode in osuModes:
            stat = await glob.db.fetchrow('SELECT rscore_{0} rscore, acc_{0} acc, pc_{0} pc, tscore_{0} tscore, pp_{0} pp, mc_{0} max_combo, pt_{0} playtime FROM stats WHERE id = %s'.format(mode.name), [self.id])

            stat['rank'] = 0
            stat['country_rank'] = 0

            if not self.restricted: # might do my own aioredis wrapper just to solve this ugly
                r = await glob.redis.zrevrank(f'asahi:leaderboard:{mode.name}', self.id)
    
                if r is None:
                    if stat['pp'] > 0:
                        stat['rank'] = 1
                else:
                    stat['rank'] += 1
    
                cr = await glob.redis.zrevrank(f'asahi:leaderboard:{mode.name}:{self.country_iso}', self.id)
    
                if cr is None:
                    if stat['pp'] > 0:
                        stat['country_rank'] = 1
                else:
                    stat['country_rank'] =  cr + 1
                
            self.stats[mode.value] = Stats(**stat)

    async def update_stats(self, mode: osuModes, table: str, mode_vn: int) -> None:
        stats = self.stats[mode.value]
        mode_name = mode.name

        s = await glob.db.fetch(
            f'SELECT {table}.acc, {table}.pp FROM {table} '
            f'LEFT OUTER JOIN maps ON maps.md5 = {table}.md5 '
            f'WHERE {table}.uid = %s AND {table}.mode = %s AND {table}.status = 2 AND maps.status IN (2, 3) '
            f'ORDER BY {table}.pp DESC', 
            [self.id, mode_vn]
        )

        if not s:
            return # no scores xd

        t100 = s[:100]

        stats.acc = sum([row['acc'] for row in s[:50]]) / min(50, len(t100))
        weighted = sum([row['pp'] * 0.95 ** i for i, row in enumerate(t100)])
        bonus = 416.6667 * (1 - 0.9994 ** len(s))
        stats.pp = round(weighted + bonus)

        if not self.restricted:
            await glob.redis.zadd(f'asahi:leaderboard:{mode_name}', stats.pp, self.id)
            await glob.redis.zadd(f'asahi:leaderboard:{mode_name}:{self.country_iso}', stats.pp, self.id)

            r = await glob.redis.zrevrank(f'asahi:leaderboard:{mode_name}', self.id)
            cr = await glob.redis.zrevrank(f'asahi:leaderboard:{mode_name}:{self.country_iso}', self.id)
            
            stats.rank = 0
            stats.country_rank = 0
    
            if r is None:
                if stats.pp > 0:
                    stats.rank = 1
            else:
                stats.rank = r + 1
    
            if cr is None:
                if stats.pp > 0:
                    stats.country_rank = 1
            else:
                stats.country_rank = cr + 1

        await glob.db.execute(
            'UPDATE stats SET rscore_{0} = %s, acc_{0} = %s, pc_{0} = %s, tscore_{0} = %s,'
            ' pp_{0} = %s, mc_{0} = %s, pt_{0} = %s WHERE id = %s'.format(mode_name), 
            [stats.rscore, stats.acc, stats.pc, stats.tscore, 
             stats.pp, stats.max_combo, stats.playtime, self.id]
        )

        self.enqueue(writer.userStats(self))
        
        if not self.restricted:
            glob.players.enqueue(writer.userStats(self))

    @property
    def current_stats(self):
        return self.stats[self.mode]

    @property
    def safe_name(self) -> str:
        return self.name.lower().replace(' ', '_').rstrip()

    @property
    def url(self) -> str:
        return f'https://{glob.config.domain}/u/{self.id}'

    @property
    def embed(self) -> str:
        return f'[{self.url} {self.name}]'

    @property
    def client_priv(self) -> ClientPrivileges:
        priv = ClientPrivileges(0)
        priv |= ClientPrivileges.Player
        
        if self.restricted:
            return priv

        if self.priv & Privileges.Admin:
            priv |= ClientPrivileges.Moderator
        if self.priv & Privileges.Developer:
            priv |= ClientPrivileges.Developer
        if self.priv & Privileges.Owner:
            priv |= ClientPrivileges.Owner
        
        return priv

    async def add_priv(self, priv: Privileges) -> None:
        self.priv |= priv
        await glob.db.execute('UPDATE users SET priv = %s WHERE id = %s', [int(self.priv), self.id])

    async def remove_priv(self, priv: Privileges) -> None:
        self.priv &= ~priv
        await glob.db.execute('UPDATE users SET priv = %s WHERE id = %s', [int(self.priv), self.id])

    async def set_priv(self, priv: Privileges) -> None:
        self.priv = priv
        await glob.db.execute('UPDATE users SET priv = %s WHERE id = %s', [int(self.priv), self.id])

    def add_spectator(self, user) -> None:
        joiner = writer.spectatorJoined(user.id)
        sname = f'#spec_{self.id}'

        if not (spec := glob.channels.get(sname)):
            spec = Channel(name='#spectator', desc=f'Spectator chat for {self.name}', auto=False, perm=False)
            self.join_chan(spec)
            glob.channels[sname] = spec
        
        user.join_chan(spec)

        for u in self.spectators:
            u.enqueue(joiner)
            user.enqueue(writer.spectatorJoined(u.id))
        
        self.spectators.append(user)
        user.spectating = self
        self.enqueue(writer.hostSpectatorJoined(user.id))
        log(f'{user.name} started spectating {self.name}.', Ansi.LBLUE)

    def remove_spectator(self, user):
        self.spectators.remove(user)
        user.spectating = None

        spec = glob.channels.get(f'#spec_{self.id}')

        user.leave_chan(spec)

        if not self.spectators:
            self.leave_chan(spec)
        else:
            cinfo = writer.channelInfo(spec)
            for u in self.spectators:
                u.enqueue(writer.spectatorLeft(user.id))
                u.enqueue(cinfo)

            self.enqueue(cinfo)
        
        self.enqueue(writer.hostSpectatorLeft(user.id))
        log(f'{user.name} stopped spectating {self.name}.', Ansi.LBLUE)

    def join_chan(self, chan: Channel) -> None:
        if self in chan.players:
            return
        
        chan.add_player(self)
        self.channels.append(chan)

        self.enqueue(writer.channelJoin(chan.name))
        for o in chan.players:
            o.enqueue(writer.channelInfo(chan))
        
        log(f'{self.name} joined channel {chan.name}', Ansi.LBLUE)

    def leave_chan(self, chan: Channel) -> None:
        if not glob.channels.get(chan.name) or self not in chan.players:
            return

        chan.remove_player(self)
        self.channels.remove(chan)

        self.enqueue(writer.channelKick(chan.name))
        for o in chan.players:
            o.enqueue(writer.channelInfo(chan))

        log(f'{self.name} left channel {chan.name}', Ansi.LBLUE)

    def join_match(self, match: Match, pw: str) -> None:
        if self.match:
            self.enqueue(writer.matchJoinFail())
            return

        if self is not match.host:
            if pw != match.pw:
                log(f'{self.name} tried to join multiplayer {match.name} with incorrect password', Ansi.LRED)
                self.enqueue(writer.matchJoinFail())
                return

            if not (id := match.next_free()):
                self.enqueue(writer.matchJoinFail())
                return
        else:
            id = 0

        self.join_chan(match.chat)

        slot = match.slots[id]

        if match.type in (teamTypes.team, teamTypes.tag_team) and not match.clan_battle:
            slot.team = Teams.red

        if match.clan_battle:
            if self.clan is match.clan_1:
                slot.team = Teams.red
            else:
                slot.team = Teams.blue

        slot.status = slotStatus.not_ready
        slot.player = self

        self.match = match

        self.enqueue(writer.matchJoinSuccess(match))

        match.enqueue_state()

    def leave_match(self) -> None:
        if not self.match:
            return

        if (slot := self.match.get_slot(self)):
            slot.reset()

        self.leave_chan(self.match.chat)

        if all((s.empty for s in self.match.slots)):
            glob.matches.pop(self.match.id)
            glob.channels.pop(f'#multi_{self.match.id}')
            glob.channels['#lobby'].enqueue(writer.disposeMatch(self.match.id))
        else:
            if self is self.match.host:
                for s in self.match.slots:
                    if s.status & slotStatus.has_player:
                        self.match.host = s.player
                        self.match.host.enqueue(writer.matchTransferHost())
                        break

            self.match.enqueue_state()
        
        self.match = None

    def logout(self) -> None:
        glob.players.remove(self)
        
        self.token = ''

        if host := self.spectating:
            host.remove_spectator(self)

        if self.match:
            self.leave_match()

        if not self.restricted:
            glob.players.enqueue(writer.logout(self.id))

        for chan in self.channels:
            self.leave_chan(chan)

    async def ban(self, reason: str, fr) -> None:
        if self.priv & Privileges.Banned:
            return # ?

        await self.add_priv(Privileges.Banned)

        if self.token:
            self.enqueue(writer.userID(-3))
            
        await glob.db.execute(
            'INSERT INTO punishments (`type`, `reason`, `target`, `from`, `time`) VALUES '
            '(%s, %s, %s, %s, %s)', 
            ['ban', reason, self.id, fr.id, time.time()]
        )

        for mode, stat in self.stats.items():
            mode_name = osuModes(mode).name

            await glob.redis.zrem(f'asahi:leaderboard:{mode_name}', self.id)
            await glob.redis.zrem(f'asahi:leaderboard:{mode_name}:{self.country_iso}', self.id)
            
            stat.rank = 0
            stat.country_rank = 0

        if (wh_url := glob.config.webhooks['anticheat']):
            wh = Webhook(url=wh_url)
            embed = Embed(title=f'')
            
            embed.set_author(url=f'https://{glob.config.domain}/u/{self.id}', name=self.name, icon_url=f'https://a.{glob.config.domain}/{self.id}')
            embed.add_field(name='New banned user', value=f'{self.name} has been banned by {fr.name} for {reason}.', inline=True)
            
            wh.add_embed(embed)
            await wh.post()
            
        log(f'{self.name} has been banned for {reason}.', Ansi.LBLUE)
        
    async def freeze(self, reason: str, fr) -> None:
        expire = datetime.now() + timedelta(days=7)
        
        if self.frozen:
            return # ?
        
        self.frozen = True
        self.freeze_timer = expire
        
        await self.add_priv(Privileges.Frozen)
        await glob.db.execute('UPDATE users SET freeze_timer = %s WHERE id = %s', [self.freeze_timer.timestamp(), self.id])

        await glob.db.execute(
            'INSERT INTO punishments (`type`, `reason`, `target`, `from`, `time`) VALUES '
            '(%s, %s, %s, %s, %s)', 
            ['freeze', reason, self.id, fr.id, time.time()]
        )
        
        if self.token:
            self.enqueue(writer.restartServer(0))

        if (wh_url := glob.config.webhooks['anticheat']):
            wh = Webhook(url=wh_url)
            embed = Embed(title=f'')
    
            embed.set_author(url=f'https://{glob.config.domain}/u/{self.id}', name=self.name, icon_url=f'https://a.{glob.config.domain}/{self.id}')
            embed.add_field(name='New frozen user', value=f'{self.name} has been frozen by {fr.name} for {reason}.', inline=True)
    
            wh.add_embed(embed)
            await wh.post()
        
        log(f'{self.name} has been frozen for {reason}.', Ansi.LBLUE)
        
    async def flag(self, reason: str, fr) -> None:
        await glob.db.execute(
            'INSERT INTO punishments (`type`, `reason`, `target`, `from`, `time`) VALUES '
            '(%s, %s, %s, %s, %s)', 
            ['flag', reason, self.id, fr.id, time.time()]
        )

        if (wh_url := glob.config.webhooks['anticheat']):
            wh = Webhook(url=wh_url)
            embed = Embed(title=f'')
        
            embed.set_author(url=f'https://{glob.config.domain}/u/{self.id}', name=self.name, icon_url=f'https://a.{glob.config.domain}/{self.id}')
            embed.add_field(name='New flagged user', value=f'{self.name} has been flagged by {fr.name} for {reason}.', inline=True)
        
            wh.add_embed(embed)
            await wh.post()
        
        log(f'{self.name} has been flagged for {reason}.', Ansi.LBLUE)

    async def unfreeze(self, reason: str, fr) -> None:
        if not self.frozen:
            return # ?

        self.frozen = False
        self.freeze_timer = 0
        
        await self.remove_priv(Privileges.Frozen)
        await glob.db.execute('UPDATE users SET freeze_timer = 0 WHERE id = %s', [self.id])

        await glob.db.execute(
            'INSERT INTO punishments (`type`, `reason`, `target`, `from`, `time`) VALUES '
            '(%s, %s, %s, %s, %s)', 
            ['unfreeze', reason, self.id, fr.id, time.time()]
        )
        
        if self.token:
            self.enqueue(writer.restartServer(0))

        if (wh_url := glob.config.webhooks['anticheat']):
            wh = Webhook(url=wh_url)
            embed = Embed(title=f'')
    
            embed.set_author(url=f'https://{glob.config.domain}/u/{self.id}', name=self.name, icon_url=f'https://a.{glob.config.domain}/{self.id}')
            embed.add_field(name='New unfrozen user', value=f'{self.name} has been unfrozen by {fr.name} for {reason}.', inline=True)
    
            wh.add_embed(embed)
            await wh.post()
        
        log(f'{self.name} has been unfrozen for {reason}.', Ansi.LBLUE)
        
    async def unban(self, reason: str, fr) -> None:
        await self.remove_priv(Privileges.Banned)

        await glob.db.execute(
            'INSERT INTO punishments (`type`, `reason`, `target`, `from`, `time`) VALUES '
            '(%s, %s, %s, %s, %s)', 
            ['unban', reason, self.id, fr.id, time.time()]
        )

        if (wh_url := glob.config.webhooks['anticheat']):
            wh = Webhook(url=wh_url)
            embed = Embed(title=f'')
        
            embed.set_author(url=f'https://{glob.config.domain}/u/{self.id}', name=self.name, icon_url=f'https://a.{glob.config.domain}/{self.id}')
            embed.add_field(name='New unbanned user', value=f'{self.name} has been unbanned by {fr.name} for {reason}.', inline=True)
        
            wh.add_embed(embed)
            await wh.post()

        log(f'{self.name} has been unbanned for {reason}.', Ansi.LBLUE)
        
    async def restrict(self, reason: str, fr) -> None:
        if self.restricted:
            return # ?

        await self.add_priv(Privileges.Restricted)
        
        self.restricted = True

        if self.token:
            self.enqueue(writer.restartServer(0)) # force relog if they're online

        await glob.db.execute(
            'INSERT INTO punishments (`type`, `reason`, `target`, `from`, `time`) VALUES '
            '(%s, %s, %s, %s, %s)', 
            ['restrict', reason, self.id, fr.id, time.time()]
        )

        for mode, stat in self.stats.items():
            mode_name = osuModes(mode).name

            await glob.redis.zrem(f'asahi:leaderboard:{mode_name}', self.id)
            await glob.redis.zrem(f'asahi:leaderboard:{mode_name}:{self.country_iso}', self.id)

            stat.rank = 0
            stat.country_rank = 0

        if (wh_url := glob.config.webhooks['anticheat']):
            wh = Webhook(url=wh_url)
            embed = Embed(title=f'')
    
            embed.set_author(url=f'https://{glob.config.domain}/u/{self.id}', name=self.name, icon_url=f'https://a.{glob.config.domain}/{self.id}')
            embed.add_field(name='New restricted user', value=f'{self.name} has been restricted by {fr.name} for {reason}.', inline=True)
    
            wh.add_embed(embed)
            await wh.post()

        log(f'{self.name} has been restricted for {reason}.', Ansi.LBLUE)

    async def unrestrict(self, reason: str, fr) -> None:
        await self.remove_priv(Privileges.Restricted)
        
        self.restricted = False

        if self.token:
            self.enqueue(writer.restartServer(0)) # force relog if they're online

            await glob.db.execute(
                'INSERT INTO punishments (`type`, `reason`, `target`, `from`, `time`) VALUES '
                '(%s, %s, %s, %s, %s)',
                ['unrestrict', reason, self.id, fr.id, time.time()]
            )

        if (wh_url := glob.config.webhooks['anticheat']):
            wh = Webhook(url=wh_url)
            embed = Embed(title=f'')
    
            embed.set_author(url=f'https://{glob.config.domain}/u/{self.id}', name=self.name, icon_url=f'https://a.{glob.config.domain}/{self.id}')
            embed.add_field(name='New unrestricted user', value=f'{self.name} has been unrestricted by {fr.name} for {reason}.', inline=True)
    
            wh.add_embed(embed)
            await wh.post()

        log(f'{self.name} has been unrestricted for {reason}.', Ansi.LBLUE)
        
    async def unlock_ach(self, ach) -> None:
        await glob.db.execute('INSERT INTO user_achievements (uid, ach) VALUES (%s, %s)', [self.id, ach.id])
        self.achievements.append(ach)

    def enqueue(self, b: bytes) -> None:
        self.queue.put_nowait(b)

    def dequeue(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            pass
