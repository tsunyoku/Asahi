from objects import glob
from objects.channel import Channel
from objects.beatmap import Beatmap
from constants.privs import Privileges, ClientPrivileges
from constants.modes import osuModes
from typing import Optional
from dataclasses import dataclass
from cmyui import log, Ansi
import queue
import packets

@dataclass
class Stats:
    rscore: int
    acc: float
    pc: int
    tscore: int
    rank: int
    pp: int

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
        self.friends: set[int] = set()
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

        self.np: Optional[Beatmap] = None

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

        p.friends = {}
        async with glob.db.transaction():
            async for user in glob.db.cursor("SELECT user2 FROM friends WHERE user1 = $1", p.id):
                p.friends |= user['row2']

        return p

    async def set_stats(self):
        for mode in osuModes:
            stat = await glob.db.fetchrow('SELECT rscore_{0} rscore, acc_{0} acc, pc_{0} pc, tscore_{0} tscore, rank_{0} rank, pp_{0} pp FROM stats WHERE id = $1'.format(mode.name), self.id)
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

        await glob.db.execute('UPDATE stats SET rscore_{0} = $1, acc_{0} = $2, pc_{0} = $3, tscore_{0} = $4, pp_{0} = $5 WHERE id = $6'.format(mode_name), stats.rscore, stats.acc, stats.pc, stats.tscore, stats.pp, self.id)

        rank = await glob.db.fetchrow('SELECT COUNT(*) AS r FROM stats LEFT OUTER JOIN users ON users.id = stats.id WHERE stats.pp_{0} > $1 AND users.priv & 1 > 0'.format(mode_name), stats.pp)
        stats.rank = rank['r'] + 1
        await glob.db.execute('UPDATE stats SET rank_{0} = $1 WHERE id = $2'.format(mode_name), stats.rank, self.id)

        self.enqueue(packets.userStats(self))
        for o in glob.players.values():
            o.enqueue(packets.userStats(self))

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
        joiner = packets.spectatorJoined(user.id)
        sname = f'#spec_{self.id}'

        if not (spec := glob.channels.get(sname)):
            spec = Channel(name='#spectator', desc=f'Spectator chat for {self.name}', auto=False, perm=False)
            self.join_chan(spec)
            glob.channels[spec.name] = spec
        
        user.join_chan(spec)

        for u in self.spectators:
            u.enqueue(joiner)
            user.enqueue(packets.spectatorJoined(u.id))
        
        self.spectators.append(user)
        user.spectating = self
        self.enqueue(packets.hostSpectatorJoined(user.id))
        log(f'{user.name} started spectating {self.name}.', Ansi.LBLUE)

    def remove_spectator(self, user):
        self.spectators.remove(user)
        user.spectating = None

        spec = glob.channels.get(f'#spec_{self.id}')
        user.leave_chan(spec)

        if not self.spectators:
            self.leave_chan(spec)
        else:
            cinfo = packets.channelInfo(spec)
            for u in self.spectators:
                u.enqueue(packets.spectatorLeft(user.id))
                u.enqueue(cinfo)
            self.enqueue(cinfo)
        
        self.enqueue(packets.hostSpectatorLeft(user.id))
        log(f'{user.name} stopped spectating {self.name}.', Ansi.LBLUE)

    def join_chan(self, chan):
        if self in chan.players:
            return
        
        chan.add_player(self)
        self.channels.append(chan)

        self.enqueue(packets.channelJoin(chan.name))
        for o in chan.players:
            o.enqueue(packets.channelInfo(chan))
        
        log(f'{self.name} joined channel {chan.name}', Ansi.LBLUE)

    def leave_chan(self, chan):
        if not glob.channels.get(chan.name):
            return

        if self not in chan.players:
            return

        chan.remove_player(self)
        self.channels.remove(chan)

        self.enqueue(packets.channelKick(chan.name))
        for o in chan.players:
            o.enqueue(packets.channelInfo(chan))

        log(f'{self.name} left channel {chan.name}', Ansi.LBLUE)

    def logout(self):
        glob.players.pop(self.token)
        glob.players_name.pop(self.name)

        if host := self.spectating:
            host.remove_spectator(self)

        for o in glob.players.values():
            o.enqueue(packets.logout(self.id))

        while self.channels:
            self.leave_chan(self.channels[0])

    def enqueue(self, b: bytes):
        self.queue.put_nowait(b)

    def dequeue(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            pass

    def queue_empty(self):
        return self.queue.empty()
