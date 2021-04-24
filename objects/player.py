from objects import glob
from objects.channel import Channel
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
        self.mods = int = 0
        self.mode: int = 0
        self.mode_vn: int = 0 
        self.map_id: int = 0
        self.stats: dict[osuModes.value, Stats] = {}

        self.spectators: list[Player] = []
        self.spectating: Optional[Player] = None
        self.channels: list[Channel] = []

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

        p.friends = {row['user2'] async for row in glob.db.iterall('SELECT user2 FROM friends WHERE user1 = %s', [user['id']])} # select all friends from db

        return p

    async def set_stats(self):
        for mode in osuModes:
            stat = await glob.db.fetch(f'SELECT rscore_{mode.name} rscore, acc_{mode.name} acc, pc_{mode.name} pc, tscore_{mode.name} tscore, rank_{mode.name} rank, pp_{mode.name} pp FROM stats WHERE id = %s', [self.id])
            self.stats[mode.value] = Stats(**stat)

    @property
    def current_stats(self):
        return self.stats[self.mode]

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
        await glob.db.execute('UPDATE users SET priv = %s WHERE id = %s', [int(self.priv), self.id])

    async def remove_priv(self, priv):
        self.priv &= ~priv
        await glob.db.execute('UPDATE users SET priv = %s WHERE id = %s', [int(self.priv), self.id])

    async def set_priv(self, priv):
        self.priv = priv
        await glob.db.execute('UPDATE users SET priv = %s WHERE id = %s', [int(self.priv), self.id])

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
