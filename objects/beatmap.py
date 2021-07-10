from constants.modes import osuModes
from constants.statuses import mapStatuses, apiStatuses
from . import glob
from .menu import Menu

from cmyui import log, Ansi
from cmyui.osu.oppai_ng import OppaiWrapper
from pathlib import Path
from maniera.calculator import Maniera

import time
from datetime import datetime as dt
import asyncio
import orjson

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .leaderboard import Leaderboard

class Beatmap:
    def __init__(self, **minfo):
        self.md5: str = minfo.get('md5', '')
        self.id: int = minfo.get('id', 0)
        self.sid: int = minfo.get('sid', 0)

        self.bpm: float = minfo.get('bpm', 0.0)
        self.cs: float = minfo.get('cs', 0.0)
        self.ar: float = minfo.get('ar', 0.0)
        self.od: float = minfo.get('od', 0.0)
        self.hp: float = minfo.get('hp', 0.0)
        self.sr: float = minfo.get('sr', 0.00)
        self.mode: int = osuModes(minfo.get('mode', 0))

        self.artist: str = minfo.get('artist', '')
        self.title: str = minfo.get('title', '')
        self.diff: str = minfo.get('diff', '')
        self.mapper: str = minfo.get('mapper', '')

        self.status: int = mapStatuses(minfo.get('status', 0))
        self.frozen: bool = minfo.get('frozen', 'False') == 1
        self.update: int = minfo.get('update', 0)

        self.nc: int = minfo.get('nc', 0) # nc = next check (for status update)

        self.lb: 'Leaderboard' = minfo.get('lb', None)
        
        self.plays: int = minfo.get('plays', 0)
        self.passes: int = minfo.get('passes', 0)

    @property
    def name(self):
        return f'{self.artist} - {self.title} [{self.diff}]'

    @property
    def url(self):
        return f'https://osu.{glob.config.domain}/beatmaps/{self.id}'
    
    @property
    def set_url(self):
        return f'https://osu.{glob.config.domain}/beatmapsets/{self.sid}'

    @property
    def embed(self):
        return f'[{self.url} {self.name}]'

    @classmethod
    async def bid_fetch(self, bid: int):
        for c in glob.cache['maps'].values():
            if bid == c.id:
                return c

        bmap = await glob.db.fetchrow('SELECT * FROM maps WHERE id = $1', bid)
        if not bmap:
            return

        m = self(**bmap)
        return m

    @staticmethod
    def cache(md5: str):
        if (bmap := glob.cache['maps'].get(md5)):
            return bmap

        return # not in cache, return nothing so we know to get from sql/api

    async def np_msg(self, user):
        pp = {}
        for acc in (95, 98, 99, 100):
            pp[acc] = await self.calc_acc(acc)

        from constants.commands import req
        if not (request_rank := glob.menus.get(self.sid + 1)):
            request_rank = Menu(id=self.sid + 1, name='Request to get Ranked', callback=req, args=(user, ('rank',)))
            glob.menus[self.sid + 1] = request_rank

        if not (request_love := glob.menus.get(self.sid + 2)):
            request_love = Menu(id=self.sid + 2, name='Request to get Loved', callback=req, args=(user, ('love',)))
            glob.menus[self.sid + 2] = request_love

        return f'{self.embed}  // 95%: {pp[95]}pp | 98%: {pp[98]}pp | 99%: {pp[99]}pp | 100%: {pp[100]}pp' \
               f' // {self.sr:.2f}★ | {self.bpm:.0f}BPM | CS {self.cs}, AR {self.ar}, OD {self.od} | ' \
               f'{request_rank.embed}  {request_love.embed}'

    async def calc_acc(self, acc: float):
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
        elif self.mode.as_vn == 3: # mania: use maniera
            c = Maniera(str(path), 0, self.score)
            c.calculate()

            return round(c.pp)
        else: # ctb: use shitty osu-tools

            cmd = [f'./osu-tools/compiled/PerformanceCalculator simulate catch {str(path)}']
            cmd.append(f'-a {acc}')

            cmd.append('-j') # json formatting is godsend thank u peppy

            p = asyncio.subprocess.PIPE
            comp = ' '.join(cmd)
            pr = await asyncio.create_subprocess_shell(comp, stdout=p, stderr=p)
            ot, _ = await pr.communicate()
            o = orjson.loads(ot.decode('utf-8'))
            return round(o['pp'])
    
    @classmethod
    async def from_md5(self, md5: str):
        if (bmap := self.cache(md5)): # first attempt cache
            return bmap

        if (bmap := await self.sql(md5)): # next, attempt from sql
            return bmap

        if (bmap := await self.api(md5)):
            return bmap
        
        return # can't find from cache, sql or api so map must be unsubmitted by this point

    @classmethod
    async def sql(self, md5: str):
        bmap = await glob.db.fetchrow('SELECT * FROM maps WHERE md5 = $1', md5)

        if not bmap:
            return # not in sql so we know to attempt from api next

        m = self(**bmap)

        glob.cache['maps'][bmap['md5']] = m # cache the map now we have it from sql

        return m

    @classmethod
    async def api(self, md5: str):
        api = 'https://old.ppy.sh/api/get_beatmaps'
        params = {'k': glob.config.api_key, 'h': md5}

        async with glob.web.get(api, params=params) as resp:
            if resp.status != 200 or not resp:
                return # request failed, map prob doesnt exist
            
            data = await resp.json()
            if not data:
                return

            bmap = data[0] # i hate this idea but o well
        
        b = self()
        b.id = int(bmap['beatmap_id'])
        b.sid = int(bmap['beatmapset_id'])
        b.md5 = md5

        b.bpm = float(bmap['bpm'])
        b.cs = float(bmap['diff_size'])
        b.ar = float(bmap['diff_approach'])
        b.od = float(bmap['diff_overall'])
        b.hp = float(bmap['diff_drain'])
        b.sr = float(bmap['difficultyrating'])
        b.mode = osuModes(int(bmap['mode']))

        b.artist = bmap['artist']
        b.title = bmap['title']
        b.diff = bmap['version']
        b.mapper = bmap['creator']

        b.status = int(apiStatuses(int(bmap['approved'])))
        b.update = dt.strptime(bmap['last_update'], '%Y-%m-%d %H:%M:%S').timestamp()

        b.nc = time.time()
        e = await glob.db.fetchrow('SELECT frozen, status, update FROM maps WHERE id = $1', b.id)

        if e:
            if b.update > e['update']:
                if e['frozen'] and b.status != e['status']:
                    b.status = e['status']
                    b.frozen = e['frozen'] == 1
                    b.lb = None # status has changed, lets reset lb cache in case

                await b.save()
            else:
                pass
        else:
            b.frozen = False # don't freeze by default, we can override if someone manually edits the map status
            await b.save()

        glob.cache['maps'][md5] = b # cache the map now we have it from api & saved in sql

        await self.cache_set(b.sid)

        log(f'Retrieved Set ID {b.sid} from osu!api', Ansi.LCYAN)
        return b

    @classmethod
    async def cache_set(self, sid: int):
        api = 'https://old.ppy.sh/api/get_beatmaps'
        params = {'k': glob.config.api_key, 's': sid}

        async with glob.web.get(api, params=params) as resp:
            if resp.status != 200 or not resp:
                return

            data = await resp.json()
            if not data:
                return

        for bmap in data:
            b = self()
            b.id = int(bmap['beatmap_id'])
            b.sid = int(bmap['beatmapset_id'])
            b.md5 = bmap['file_md5']

            b.bpm = float(bmap['bpm'])
            b.cs = float(bmap['diff_size'])
            b.ar = float(bmap['diff_approach'])
            b.od = float(bmap['diff_overall'])
            b.hp = float(bmap['diff_drain'])
            b.sr = float(bmap['difficultyrating'])
            b.mode = osuModes(int(bmap['mode']))

            b.artist = bmap['artist']
            b.title = bmap['title']
            b.diff = bmap['version']
            b.mapper = bmap['creator']

            b.status = int(apiStatuses(int(bmap['approved'])))
            b.update = dt.strptime(bmap['last_update'], '%Y-%m-%d %H:%M:%S').timestamp()
            b.frozen = True

            b.nc = time.time()

            await b.save()
            glob.cache['maps'][b.md5] = b

    async def check_status(self):
        api = 'https://old.ppy.sh/api/get_beatmaps'
        params = {'k': glob.config.api_key, 's': self.sid}

        async with glob.web.get(api, params=params) as resp:
            if resp.status != 200 or not resp:
                return # request failed, map prob doesnt exist
            
            data = await resp.json()
            if not data:
                return

        bmap = await glob.db.fetchrow('SELECT id, status, frozen, update FROM maps WHERE id = $1', self.id)

        exist = {}
        try:
            exist[bmap['id']] = {}
            for k, v in bmap.items():
                exist[bmap['id']][k] = v
        except (AttributeError, TypeError):
            pass

        for m in data:
            mid = int(m['beatmap_id'])
            if mid in exist:
                current = exist[mid]['status']
                api = apiStatuses(int(m['approved']))

                if current != api:
                    md5 = m['file_md5']
                
                    if md5 == self.md5:
                        self.status = api

                        self.nc = time.time() + 3600

                        await glob.db.execute('UPDATE maps SET status = $1, nc = $2 WHERE md5 = $3', self.status, self.nc, self.md5)
                        if (cached := glob.cache['maps'].get(self.md5)):
                            cached.status = self.status
                            cached.nc = self.nc

    async def save(self):
        try:
            await glob.db.execute(
                'INSERT INTO maps (id, sid, md5, bpm, cs, ar, od, hp, sr, mode, artist, title, diff, mapper, status, frozen, update, nc, plays, passes) '
                'VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19, $20)',
                self.id, self.sid, self.md5, self.bpm, self.cs, self.ar, self.od, self.hp, self.sr, self.mode.value, 
                self.artist, self.title, self.diff, self.mapper, self.status, self.frozen, self.update, self.nc,
                self.plays, self.passes
            )
        except Exception: # sadly there is no good way to update on duplicate like there is with mysql
            await glob.db.execute(
                'UPDATE maps SET id = $1, sid = $2, bpm = $3, cs = $4, ar = $5, od = $6, hp = $7, sr = $8, mode = $9, artist = $10, '
                'title = $11, diff = $12, mapper = $13, status = $14, frozen = $15, update = $16, nc = $17, plays = $18, passes = $19 WHERE md5 = $20', 
                self.id, self.sid, self.bpm, self.cs, self.ar, self.od, self.hp, self.sr, self.mode.value, 
                self.artist, self.title, self.diff, self.mapper, self.status, self.frozen, self.update, self.nc, self.plays, self.passes, self.md5
            )
