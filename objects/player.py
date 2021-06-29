from objects import glob
from objects.channel import Channel
from objects.beatmap import Beatmap
from objects.clan import Clan
from objects.match import Slot, slotStatus, Teams, Match
from packets import writer
from constants.privs import Privileges, ClientPrivileges
from constants.modes import osuModes
from constants.types import teamTypes
from typing import Optional
from dataclasses import dataclass
from cmyui import log, Ansi
import queue

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
        self.mods: int = 0
        self.mode: int = 0
        self.mode_vn: int = 0 
        self.map_id: int = 0
        self.stats: dict[osuModes.value, Stats] = {}

        self.spectators: list[Player] = []
        self.spectating: Optional[Player] = None
        self.channels: list[Channel] = []

        self.match: Optional[Match] = None

        self.np: Optional[Beatmap] = None

        self.clan: Optional[Clan] = None

        self.last_ping: int = 0
        
        self.restricted: bool = False

    @property
    def full_name(self):
        if self.clan:
            return f'[{self.clan.tag}] {self.name}'
        else:
            return self.name

    @classmethod
    async def login(self, user):
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
            priv=Privileges(user['priv'])
        )

        p.friends = []
        async with glob.db.transaction():
            async for user in glob.db.cursor("SELECT user2 FROM friends WHERE user1 = $1", p.id):
                p.friends.append(user['user2'])

        clan = await glob.db.fetchval('SELECT clan FROM users WHERE id = $1', p.id)
        if clan:
            p.clan = glob.clans.get(clan)
            
        if p.priv & Privileges.Restricted:
            p.restricted = True

        return p
    
    @classmethod
    async def from_sql(self, id):
        user = await glob.db.fetchrow('SELECT * FROM users WHERE id = $1', id)
        
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
            priv=Privileges(user['priv']) 
        )
        
        if p.priv & Privileges.Disallowed:
            p.restricted = True
        
        return p

    async def set_stats(self):
        for mode in osuModes:
            stat = dict(await glob.db.fetchrow('SELECT rscore_{0} rscore, acc_{0} acc, pc_{0} pc, tscore_{0} tscore, pp_{0} pp, mc_{0} max_combo FROM stats WHERE id = $1'.format(mode.name), self.id))

            if not self.restricted:
                stat['rank'] = await glob.redis.zrevrank(f'asahi:leaderboard:{mode.name}', self.id)
    
                if stat['rank'] is None:
                    if stat['pp'] > 0:
                        stat['rank'] = 1
                    else:
                        stat['rank'] = 0
                else:
                    stat['rank'] += 1
    
                stat['country_rank'] = await glob.redis.zrevrank(f'asahi:leaderboard:{mode.name}:{self.country_iso}', self.id)
    
                if stat['country_rank'] is None:
                    if stat['pp'] > 0:
                        stat['country_rank'] = 1
                    else:
                        stat['country_rank'] = 0
                else:
                    stat['country_rank'] += 1
            else:
                stat['rank'] = 0
                stat['country_rank'] = 0
                
            self.stats[mode.value] = Stats(**stat)

    async def update_stats(self, mode: osuModes, table: str, mode_vn: int):
        stats = self.stats[mode.value]
        mode_name = mode.name

        t100 = await glob.db.fetch(f'SELECT {table}.acc, {table}.pp FROM {table} LEFT OUTER JOIN maps ON maps.md5 = {table}.md5 WHERE {table}.uid = $1 AND {table}.mode = $2 AND {table}.status = 2 AND maps.status IN (1, 2) ORDER BY {table}.pp DESC LIMIT 100', self.id, mode_vn)
        s = await glob.db.fetch(f'SELECT {table}.acc, {table}.pp FROM {table} LEFT OUTER JOIN maps ON maps.md5 = {table}.md5 WHERE {table}.uid = $1 AND {table}.mode = $2 AND {table}.status = 2 AND maps.status IN (1, 2) ORDER BY {table}.pp DESC', self.id, mode_vn)

        if not t100:
            return # no scores xd

        stats.acc = sum([row['acc'] for row in s[:50]]) / min(50, len(t100))
        weighted = sum([row['pp'] * 0.95 ** i for i, row in enumerate(t100)])
        bonus = 416.6667 * (1 - 0.9994 ** len(s))
        stats.pp = round(weighted + bonus)

        if not self.restricted:
            await glob.redis.zadd(f'asahi:leaderboard:{mode_name}', stats.pp, self.id)
            await glob.redis.zadd(f'asahi:leaderboard:{mode_name}:{self.country_iso}', stats.pp, self.id)
            stats.rank = await glob.redis.zrevrank(f'asahi:leaderboard:{mode_name}', self.id)
            stats.country_rank = await glob.redis.zrevrank(f'asahi:leaderboard:{mode_name}:{self.country_iso}', self.id)
    
            if stats.rank is None:
                if stats.pp > 0:
                    stats.rank = 1
                else:
                    stats.rank = 0
            else:
                stats.rank += 1
    
            if stats.country_rank is None:
                if stats.pp > 0:
                    stats.country_rank = 1
                else:
                    stats.country_rank = 0
            else:
                stats.country_rank += 1

        await glob.db.execute('UPDATE stats SET rscore_{0} = $1, acc_{0} = $2, pc_{0} = $3, tscore_{0} = $4, pp_{0} = $5, mc_{0} = $6 WHERE id = $7'.format(mode_name), stats.rscore, stats.acc, stats.pc, stats.tscore, stats.pp, stats.max_combo, self.id)

        self.enqueue(writer.userStats(self))
        
        if not self.restricted:
            for o in glob.players.values():
                o.enqueue(writer.userStats(self))

    @property
    def current_stats(self):
        return self.stats[self.mode]

    @property
    def safe_name(self):
        return self.name.lower().replace(' ', '_')

    @property
    def url(self):
        return f'https://{glob.config.domain}/u/{self.id}'

    @property
    def embed(self):
        return f'[{self.url} {self.name}]'

    @property
    def client_priv(self):
        priv = ClientPrivileges(0)

        if self.priv & Privileges.Normal:
            priv |= ClientPrivileges.Player
        if self.priv & Privileges.Admin:
            priv |= ClientPrivileges.Moderator
        if self.priv & Privileges.Developer:
            priv |= ClientPrivileges.Developer
        if self.priv & Privileges.Owner:
            priv |= ClientPrivileges.Owner
        
        return priv

    async def add_priv(self, priv):
        self.priv |= priv
        await glob.db.execute('UPDATE users SET priv = $1 WHERE id = $2', int(self.priv), self.id)

    async def remove_priv(self, priv):
        self.priv &= ~priv
        await glob.db.execute('UPDATE users SET priv = $1 WHERE id = $2', int(self.priv), self.id)

    async def set_priv(self, priv):
        self.priv = priv
        await glob.db.execute('UPDATE users SET priv = $1 WHERE id = $2', int(self.priv), self.id)

    def add_spectator(self, user):
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

    def join_chan(self, chan):
        if self in chan.players:
            return
        
        chan.add_player(self)
        self.channels.append(chan)

        self.enqueue(writer.channelJoin(chan.name))
        for o in chan.players:
            o.enqueue(writer.channelInfo(chan))
        
        log(f'{self.name} joined channel {chan.name}', Ansi.LBLUE)

    def leave_chan(self, chan):
        if not glob.channels.get(chan.name):
            return

        if self not in chan.players:
            return

        chan.remove_player(self)
        self.channels.remove(chan)

        self.enqueue(writer.channelKick(chan.name))
        for o in chan.players:
            o.enqueue(writer.channelInfo(chan))

        log(f'{self.name} left channel {chan.name}', Ansi.LBLUE)

    def join_match(self, match, pw):
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

    def leave_match(self):
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

    def logout(self):
        glob.players.pop(self.token)
        glob.players_name.pop(self.name)
        glob.players_id.pop(self.id)
        
        self.token = ''

        if host := self.spectating:
            host.remove_spectator(self)

        if self.match:
            self.leave_match()

        if not self.restricted:
            for o in glob.players.values():
                o.enqueue(writer.logout(self.id))

        for chan in self.channels:
            self.leave_chan(chan)

    async def ban(self, reason):
        await self.add_priv(Privileges.Banned)

        if self.token:
            self.enqueue(writer.userID(-3))

        log(f'{self.name} has been banned for {reason}')
        
    async def unban(self, reason):
        await self.remove_priv(Privileges.Banned)

        await glob.db.execute('UPDATE users SET priv = $1 WHERE id = $2', self.priv, self.id)

        log(f'{self.name} has been unbanned for {reason}')
        
    async def restrict(self, reason):
        await self.add_priv(Privileges.Restricted)

        log(f'{self.name} has been restricted for {reason}')
        
        self.restricted = True

        if self.token:
            self.enqueue(writer.restartServer(0)) # force relog if they're online

    async def unrestrict(self, reason):
        await self.remove_priv(Privileges.Restricted)

        log(f'{self.name} has been unrestricted for {reason}')
        
        self.restricted = False

        if self.token:
            self.enqueue(writer.restartServer(0)) # force relog if they're online

    def enqueue(self, b: bytes):
        self.queue.put_nowait(b)

    def dequeue(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            pass

    def queue_empty(self):
        return self.queue.empty()
