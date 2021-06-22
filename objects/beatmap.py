from constants.modes import osuModes
from constants.statuses import mapStatuses, apiStatuses
from objects import glob, pp

from cmyui import log, Ansi
from pathlib import Path

import time
from datetime import datetime as dt
from typing import Optional
import asyncio
import orjson

class Beatmap:
    def __init__(self, **minfo):
        self.md5 = minfo.get('md5', '')
        self.id = minfo.get('id', 0)
        self.sid = minfo.get('sid', 0)

        self.bpm = minfo.get('bpm', 0.0)
        self.cs = minfo.get('cs', 0.0)
        self.ar = minfo.get('ar', 0.0)
        self.od = minfo.get('od', 0.0)
        self.hp = minfo.get('hp', 0.0)
        self.sr = minfo.get('sr', 0.00)
        self.mode = osuModes(minfo.get('mode', 0))

        self.artist = minfo.get('artist', '')
        self.title = minfo.get('title', '')
        self.diff = minfo.get('diff', '')
        self.mapper = minfo.get('mapper', '')

        self.status = mapStatuses(minfo.get('status', 0))
        self.frozen = minfo.get('frozen', 'False') == 1
        self.update = minfo.get('update', 0)

        self.nc = minfo.get('nc', 0) # nc = next check (for status update)
        self.pp_cache = minfo.get('pp_cache', {})

        self.lb = minfo.get('lb', None)

    @property
    def name(self):
        return f'{self.artist} - {self.title} [{self.diff}]'

    @property
    def url(self):
        return f'https://osu.{glob.config.domain}/b/{self.id}'

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

    @property
    async def np_msg(self):
        if not (n99 := self.pp_cache.get(99)):
            n99 = await self.calc_acc(99)
        if not (n98 := self.pp_cache.get(98)):
            n98 = await self.calc_acc(98)
        if not (n95 := self.pp_cache.get(95)):
            n95 = await self.calc_acc(95)
        if not (n100 := self.pp_cache.get(100)):
            n100 = await self.calc_acc(100)

        return f'{self.embed}  // 95%: {n95}pp | 98%: {n98}pp | 99%: {n99}pp | 100%: {n100}pp // {self.sr:.2f}★ | {self.bpm:.0f}BPM | CS {self.cs}, AR {self.ar}, OD {self.od}'

    async def calc_acc(self, acc: float):
        path = Path.cwd() / f'resources/maps/{self.id}.osu'
        if not path.exists():
            url = f'https://old.ppy.sh/osu/{self.id}'

            async with glob.web.get(url) as resp:
                if not resp or resp.status != 200:
                    return 0.0

                m = await resp.read()
                path.write_bytes(m)

        p = asyncio.subprocess.PIPE
        pr = await asyncio.create_subprocess_shell(f'./osu-tools/compiled/PerformanceCalculator simulate osu {str(path)} -a {acc} -j', stdout=p, stderr=p)
        ot, _ = await pr.communicate()
        o = orjson.loads(ot.decode('utf-8'))
        ppv = round(o['pp'])

        self.pp_cache[acc] = ppv
        return ppv
    
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
    async def cache_set(self, sid):
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
            await glob.db.execute('INSERT INTO maps (id, sid, md5, bpm, cs, ar, od, hp, sr, mode, artist, title, diff, mapper, status, frozen, update, nc) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18)', self.id, self.sid, self.md5, self.bpm, self.cs, self.ar, self.od, self.hp, self.sr, self.mode.value, self.artist, self.title, self.diff, self.mapper, self.status, self.frozen, self.update, self.nc)
        except Exception: # sadly there is no good way to update on duplicate like there is with mysql
            await glob.db.execute('UPDATE maps SET id = $1, sid = $2, bpm = $3, cs = $4, ar = $5, od = $6, hp = $7, sr = $8, mode = $9, artist = $10, title = $11, diff = $12, mapper = $13, status = $14, frozen = $15, update = $16, nc = $17 WHERE md5 = $18', self.id, self.sid, self.bpm, self.cs, self.ar, self.od, self.hp, self.sr, self.mode.value, self.artist, self.title, self.diff, self.mapper, self.status, self.frozen, self.update, self.nc, self.md5)