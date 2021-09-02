from constants.modes import osuModes
from constants.statuses import mapStatuses
from constants.privs import Privileges
from . import glob
from .menu import Menu

from cmyui.logging import log, Ansi
from cmyui.osu.oppai_ng import OppaiWrapper
from pathlib import Path
from peace_performance_python.objects import Beatmap as CalcBeatmap, Calculator

import time
from datetime import datetime as dt
import asyncio
import orjson
import math
from typing import Optional

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .leaderboard import Leaderboard

class Beatmap:
    __slots__ = (
        'md5', 'id', 'sid', 'bpm',
        'cs', 'ar', 'od', 'hp', 'sr',
        'mode', 'artist', 'title', 'diff', 'mapper',
        'status', 'frozen', 'update', 'nc',
        'lb', 'lb_rx', 'lb_ap', 'plays', 'passes'
    )
    def __init__(self, **kwargs) -> None:
        self.md5: str = kwargs.get('md5', '')
        self.id: int = kwargs.get('id', 0)
        self.sid: int = kwargs.get('sid', 0)
        self.bpm: float = kwargs.get('bpm', 0.0)
        self.cs: float = kwargs.get('cs', 0.0)
        self.ar: float = kwargs.get('ar', 0.0)
        self.od: float = kwargs.get('od', 0.0)
        self.hp: float = kwargs.get('hp', 0.0)
        self.sr: float = kwargs.get('sr', 0.00)
        self.mode: int = osuModes(kwargs.get('mode', 0))
        self.artist: str = kwargs.get('artist', '')
        self.title: str = kwargs.get('title', '')
        self.diff: str = kwargs.get('diff', '')
        self.mapper: str = kwargs.get('mapper', '')
        self.status: 'mapStatuses' = mapStatuses(kwargs.get('status', 0))
        self.frozen: bool = kwargs.get('frozen', 0) == 1
        self.update: int = kwargs.get('update', 0)
        self.nc: int = kwargs.get('nc', 0) # nc = next check (for status update)
        self.lb: 'Leaderboard' = kwargs.get('lb')
        self.lb_rx: 'Leaderboard' = kwargs.get('lb_rx')
        self.lb_ap: 'Leaderboard' = kwargs.get('lb_ap')
        self.plays: int = kwargs.get('plays', 0)
        self.passes: int = kwargs.get('passes', 0)

    @property
    def name(self) -> str:
        return f'{self.artist} - {self.title} [{self.diff}]'

    @property
    def url(self) -> str:
        return f'https://osu.{glob.config.domain}/beatmaps/{self.id}'

    @property
    def set_url(self) -> str:
        return f'https://osu.{glob.config.domain}/beatmapsets/{self.sid}'

    @property
    def embed(self) -> str:
        return f'[{self.url} {self.name}]'

    @classmethod
    async def bid_fetch(cls, bid: int) -> 'Beatmap':
        for c in glob.cache['maps'].values():
            if bid == c.id:
                return c

        row = await glob.db.fetchrow('SELECT * FROM maps WHERE id = %s', [bid])
        if not row:
            await cls.cache_from_map(bid)
            row = await glob.db.fetchrow('SELECT * FROM maps WHERE id = %s', [bid])

        return cls(**row)

    @staticmethod
    def from_cache(md5: str) -> Optional['Beatmap']:
        if (bmap := glob.cache['maps'].get(md5)):
            return bmap

    async def np_msg(self, user) -> str:
        pp = {acc: await self.calc_acc(acc)
              for acc in (95, 97, 99, 100)}

        msg = (f'{self.embed}  // 95%: {pp[95]}pp | 97%: {pp[97]}pp | 99%: {pp[99]}pp | 100%: {pp[100]}pp'
              f' // {self.sr:.2f}★ | {self.bpm:.0f}BPM | CS {self.cs}, AR {self.ar}, OD {self.od}')

        # TODO: CLEAN!!!!!
        if not user.priv & Privileges.Staff:
            if self.status < mapStatuses.Ranked:
                from constants.commands import req

                _id_reqr = self.sid + 1
                _id_reql = self.sid + 2

                request_rank = Menu(
                    id=_id_reqr,
                    name='Request to get Ranked',
                    callback=req,
                    args=(user, ('rank',)),
                    destroy=True
                )

                glob.menus[_id_reqr] = request_rank

                request_love = Menu(
                    id=_id_reql,
                    name='Request to get Loved',
                    callback=req,
                    args=(user, ('love',)),
                    destroy=True
                )

                glob.menus[_id_reql] = request_love

                msg += f' // {request_rank.embed}  {request_love.embed}'
        else:
            from constants.commands import _map

            if self.status < mapStatuses.Ranked:
                _id_rank = self.sid + self.id + 1
                _id_love = self.sid + self.id + 2

                rank = Menu(
                    id=_id_rank,
                    name='Rank',
                    callback=_map,
                    args=(user, ('rank', 'set',)),
                    destroy=True
                )

                glob.menus[_id_rank] = rank

                love = Menu(
                    id=_id_love,
                    name='Love',
                    callback=_map,
                    args=(user, ('love', 'set',)),
                    destroy=True
                )

                glob.menus[_id_love] = love

                msg += f' // {rank.embed}  {love.embed}'
            else:
                _id_unrank = self.sid + self.id + 3

                unrank = Menu(
                    id=_id_unrank,
                    name='Unrank',
                    callback=_map,
                    args=(user, ('unrank', 'set',)),
                    destroy=True
                )

                glob.menus[_id_unrank] = unrank

                msg += f' // {unrank.embed}'

        return msg

    async def calc_acc(self, acc: float) -> float:
        path = Path.cwd() / f'resources/maps/{self.id}.osu'
        if not path.exists():
            url = f'https://old.ppy.sh/osu/{self.id}'

            async with glob.web.get(url) as resp:
                if not resp or resp.status != 200:
                    return 0.0

                m = await resp.read()
                path.write_bytes(m)

        if self.mode.as_vn <= 1:
            with OppaiWrapper('oppai-ng/liboppai.so') as ezpp:
                ezpp.set_accuracy_percent(acc)
                ezpp.set_mode(self.mode.as_vn)

                ezpp.calculate(path)
                return round(ezpp.get_pp()) # returning sr soontm
        else:
            if self.mode.as_vn == 3:
                if acc == 100: score = 1000000
                elif acc == 99: score = 990000
                elif acc == 97: score = 970000
                elif acc == 95: score = 950000
            else: score = 0

            _map = CalcBeatmap(path)
            calc = Calculator(acc=acc, miss=0, mode=self.mode.as_vn, score=score).calculate(_map)

            pp = calc.pp
            if pp in (math.inf, math.nan): pp = 0
            else: pp = round(pp)

            return pp

    @classmethod
    async def from_md5(cls, md5: str) -> Optional['Beatmap']:
        if (bmap := cls.from_cache(md5)): # first attempt cache
            return bmap

        if (bmap := await cls.from_sql(md5)): # next, attempt from sql
            return bmap

        if (bmap := await cls.from_api(md5)):
            return bmap

        return # can't find from cache, sql or api so map must be unsubmitted by this point

    @classmethod
    async def from_sql(cls, md5: str) -> Optional['Beatmap']:
        row = await glob.db.fetchrow('SELECT * FROM maps WHERE md5 = %s', [md5])

        if not row:
            return # not in sql so we know to attempt from api next

        self = cls(**row)

        glob.cache['maps'][row['md5']] = self # cache the map now we have it from sql

        return self

    @classmethod
    async def from_api(cls, md5: str) -> Optional['Beatmap']:
        api = 'https://old.ppy.sh/api/get_beatmaps'
        params = {'k': glob.config.api_key, 'h': md5}

        async with glob.web.get(api, params=params) as resp:
            if resp.status != 200 or not resp:
                return # request failed, map prob doesnt exist

            data = await resp.json()
            if not data:
                return

            bmap = data[0] # i hate this idea but o well

        self = cls()
        self.id = int(bmap['beatmap_id'])
        self.sid = int(bmap['beatmapset_id'])
        self.md5 = md5

        self.bpm = float(bmap['bpm'])
        self.cs = float(bmap['diff_size'])
        self.ar = float(bmap['diff_approach'])
        self.od = float(bmap['diff_overall'])
        self.hp = float(bmap['diff_drain'])
        self.sr = float(bmap['difficultyrating'])
        self.mode = osuModes(int(bmap['mode']))

        self.artist = bmap['artist']
        self.title = bmap['title']
        self.diff = bmap['version']
        self.mapper = bmap['creator']

        self.status = mapStatuses.from_api(int(bmap['approved']))
        self.update = dt.strptime(bmap['last_update'], '%Y-%m-%d %H:%M:%S').timestamp()

        self.nc = time.time()
        e = await glob.db.fetchrow('SELECT frozen, status, `update` FROM maps WHERE id = %s', [self.id])

        if e:
            if self.update > e['update']:
                if e['frozen'] and self.status != e['status']:
                    self.status = e['status']
                    self.frozen = e['frozen'] == 1
                    self.lb = None # status has changed, lets reset lb cache in case

                await self.save()
            else:
                pass
        else:
            self.frozen = False # don't freeze by default, we can override if someone manually edits the map status
            await self.save()

        glob.cache['maps'][md5] = self # cache the map now we have it from api & saved in sql

        await cls.cache_set(self.sid)

        log(f'Retrieved Set ID {self.sid} from osu!api', Ansi.LCYAN)
        return self

    @classmethod
    async def cache_set(cls, sid: int) -> None:
        api = 'https://old.ppy.sh/api/get_beatmaps'
        params = {'k': glob.config.api_key, 's': sid}

        async with glob.web.get(api, params=params) as resp:
            if resp.status != 200 or not resp:
                return

            data = await resp.json()
            if not data:
                return

        for bmap in data:
            self = cls()
            self.id = int(bmap['beatmap_id'])
            self.sid = int(bmap['beatmapset_id'])
            self.md5 = bmap['file_md5']

            self.bpm = float(bmap['bpm'])
            self.cs = float(bmap['diff_size'])
            self.ar = float(bmap['diff_approach'])
            self.od = float(bmap['diff_overall'])
            self.hp = float(bmap['diff_drain'])
            self.sr = float(bmap['difficultyrating'])
            self.mode = osuModes(int(bmap['mode']))

            self.artist = bmap['artist']
            self.title = bmap['title']
            self.diff = bmap['version']
            self.mapper = bmap['creator']

            self.status = mapStatuses.from_api(int(bmap['approved']))
            self.update = dt.strptime(bmap['last_update'], '%Y-%m-%d %H:%M:%S').timestamp()
            self.frozen = True

            self.nc = time.time()

            await self.save()
            glob.cache['maps'][self.md5] = self

    @classmethod
    async def cache_from_map(cls, bid: int) -> None:
        api = 'https://old.ppy.sh/api/get_beatmaps'
        params = {'k': glob.config.api_key, 'b': bid}

        async with glob.web.get(api, params=params) as resp:
            if resp.status != 200 or not resp:
                return

            data = await resp.json()
            if not data:
                return

        for bmap in data:
            self = cls()
            self.id = int(bmap['beatmap_id'])
            self.sid = int(bmap['beatmapset_id'])
            self.md5 = bmap['file_md5']

            self.bpm = float(bmap['bpm'])
            self.cs = float(bmap['diff_size'])
            self.ar = float(bmap['diff_approach'])
            self.od = float(bmap['diff_overall'])
            self.hp = float(bmap['diff_drain'])
            self.sr = float(bmap['difficultyrating'])
            self.mode = osuModes(int(bmap['mode']))

            self.artist = bmap['artist']
            self.title = bmap['title']
            self.diff = bmap['version']
            self.mapper = bmap['creator']

            self.status = mapStatuses.from_api(int(bmap['approved']))
            self.update = dt.strptime(bmap['last_update'], '%Y-%m-%d %H:%M:%S').timestamp()
            self.frozen = True

            self.nc = time.time()

            await self.save()
            glob.cache['maps'][self.md5] = self

    async def check_status(self):
        api = 'https://old.ppy.sh/api/get_beatmaps'
        params = {'k': glob.config.api_key, 's': self.sid}

        async with glob.web.get(api, params=params) as resp:
            if resp.status != 200 or not resp:
                for _type in ('lb', 'lb_rx', 'lb_ap'):
                    setattr(self, _type, None)

                glob.cache['unsub'].append(self.md5)
                await glob.db.execute('DELETE FROM maps WHERE md5 = %s', [self.md5])

                for table in ('scores', 'scores_rx', 'scores_ap'):
                    await glob.db.execute(f'DELETE FROM {table} WHERE md5 = %s', [self.md5])

                return # request failed, map prob doesnt exist anymore

            data = await resp.json()
            if not data:
                for _type in ('lb', 'lb_rx', 'lb_ap'):
                    setattr(self, _type, None)

                glob.cache['unsub'].append(self.md5)
                await glob.db.execute('DELETE FROM maps WHERE md5 = %s', [self.md5])

                for table in ('scores', 'scores_rx', 'scores_ap'):
                    await glob.db.execute(f'DELETE FROM {table} WHERE md5 = %s', [self.md5])

                return # request failed, map prob doesnt exist anymore

        if self.frozen: return

        bmap = await glob.db.fetchrow('SELECT id, status, frozen, `update` FROM maps WHERE id = %s', [self.id])

        in_db = {bmap['id']: {k: v for k, v in bmap.items()}}

        for m in data:
            mid = int(m['beatmap_id'])

            if mid in in_db:
                current = in_db[mid]['status']
                api = mapStatuses.from_api(int(m['approved']))

                if current != api and m['file_md5'] == self.md5:
                    self.status = api

                    self.nc = time.time() + 3600

                    await glob.db.execute('UPDATE maps SET status = %s, nc = %s WHERE md5 = %s', [self.status, self.nc, self.md5])
                    if (cached := glob.cache['maps'].get(self.md5)):
                        cached.status = self.status
                        cached.nc = self.nc

    async def save(self):
        await glob.db.execute(
            'REPLACE INTO maps (id, sid, md5, bpm, cs, ar, od, hp, sr, mode, artist, title, diff, mapper, status, frozen, `update`, nc, plays, passes) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
            [self.id, self.sid, self.md5, self.bpm, self.cs, self.ar, self.od, self.hp, self.sr, self.mode.value,
            self.artist, self.title, self.diff, self.mapper, int(self.status), self.frozen, self.update, self.nc,
            self.plays, self.passes]
        )
