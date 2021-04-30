from constants.modes import osuModes
from constants.statuses import mapStatuses, apiStatuses
from objects import glob

from cmyui import log, Ansi

import time
from datetime import datetime as dt

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

    @property
    def name(self):
        return f'{self.artist} - {self.title} [{self.diff}]'

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

        m = self(**bmap)
        glob.cache['maps'][bmap['md5']] = m

        return m

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
        b.bmapper = bmap['creator']

        b.status = int(apiStatuses(int(bmap['approved'])))
        b.update = dt.strptime(bmap['last_update'], '%Y-%m-%d %H:%M:%S').timestamp()

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
            await b.save()

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

        bmap = await glob.db.fetchrow('SELECT id, status, frozen, update FROM maps WHERE sid = $1', sid)

        exist = {}
        try:
            exist[bmap['id']] = {}
            for k, v in bmap.items():
                exist[bmap['id']][k] = v
        except (AttributeError, TypeError): # incase map aint in db, we dont wanna stop it from loading
            pass

        for m in data:
            mid = int(m['beatmap_id'])
            m['last_update'] = dt.strptime(m['last_update'], '%Y-%m-%d %H:%M:%S').timestamp()
            if mid in exist:
                if m['last_update'] > exist[mid]['update']:
                    status = apiStatuses(int(m['approved']))

                    if exist[mid]['frozen'] and status != exist[mid]['status']:
                        m['approved'] = exist[mid]['status']
                        m['frozen'] = True
                    else:
                        m['approved'] = status
                        m['frozen'] = False
                else:
                    continue
            else:
                m['approved'] = apiStatuses(int(m['approved']))
                m['frozen'] = False

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
            b.frozen = m['frozen']
            b.update = m['last_update']

            glob.cache['maps'][b.md5] = b

            await b.save()

        log(f'Cached Set ID {b.sid} from osu!api', Ansi.LCYAN)

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

                        await glob.db.execute('UPDATE maps SET status = $1 WHERE md5 = $2', self.status, self.md5)
                        if (cached := glob.cache['maps'].get(self.md5)):
                            cached.status = self.status

    async def save(self):
        await glob.db.execute('INSERT INTO maps (id, sid, md5, bpm, cs, ar, od, hp, sr, mode, artist, title, diff, mapper, status, frozen, update) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17)', self.id, self.sid, self.md5, self.bpm, self.cs, self.ar, self.od, self.hp, self.sr, self.mode.value, self.artist, self.title, self.diff, self.mapper, self.status, self.frozen, self.update)