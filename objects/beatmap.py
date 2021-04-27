from constants.modes import osuModes
from constants.statuses import mapStatuses, apiStatuses
from objects import glob

from cmyui import log, Ansi

import time

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

    @staticmethod
    def md5_cache(md5: str):
        if (bmap := glob.cache['maps'].get(md5)):
            return bmap

        return # not in cache, return nothing so we know to get from sql/api

    @classmethod
    async def md5_sql(self, md5: str):
        bmap = await glob.db.fetchrow('SELECT * FROM maps WHERE md5 = $1', md5)
        if not bmap:
            return

        return self(**bmap)

    @classmethod
    async def md5_api(self, md5: str):
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
        b.id = int(bmap['beatbmap_id'])
        b.sid = int(bmap['beatbmapset_id'])
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
        b.bmapper = bmap['creator']

        b.status = int(apiStatuses(int(bmap['approved'])))

        await b.save()
        log(b.status)

        log(f'Retrieved Set ID {b.sid} from osu!api', Ansi.LCYAN)
        return b

    @classmethod
    async def cache(self, sid: int):
        api = 'https://old.ppy.sh/api/get_beatmaps'
        params = {'k': glob.config.api_key, 's': sid}

        async with glob.web.get(api, params=params) as resp:
            if resp.status != 200 or not resp:
                return # request failed, map prob doesnt exist
            
            data = await resp.json()
            if not data:
                return

        bmap = await glob.db.fetch('SELECT id, status FROM maps WHERE sid = $1', sid)

        exist = {m['id']: {v: m[v] for v in set(m) - {'id'}} for m in bmap}

        for m in data:
            mid = int(m['beatmap_id'])
            if mid in exist:
                status = apiStatuses(int(m['approved']))

                if status != exist[mid]['status']:
                    m['approved'] = status
            else:
                m['approved'] = apiStatuses(int(m['approved']))

            b = self()
            b.id = mid
            b.sid = sid
            b.md5 = m['file_md5']

            b.bpm = float(m['bpm'])
            b.cs = float(m['diff_size'])
            b.ar = float(m['diff_approach'])
            b.od = float(m['diff_overall'])
            b.hp = float(m['diff_drain'])
            b.sr = float(m['difficultyrating'])
            b.mode = osuModes(int(m['mode']))

            b.artist = m['artist']
            b.title = m['title']
            b.diff = m['version']
            b.mper = m['creator']

            b.status = m['approved']

            glob.cache['maps'][b.md5] = b

            await b.save()

        log(f'Retrieved Set ID {b.sid} from osu!api', Ansi.LCYAN)

    async def save(self):
        await glob.db.execute('INSERT INTO maps (id, sid, md5, bpm, cs, ar, od, hp, sr, mode, artist, title, diff, mapper, status) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15)', self.id, self.sid, self.md5, self.bpm, self.cs, self.ar, self.od, self.hp, self.sr, self.mode.value, self.artist, self.title, self.diff, self.mapper, self.status)