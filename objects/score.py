from objects.beatmap import Beatmap
from objects.player import Player
from constants.mods import Mods, convert
from constants.modes import osuModes, lbModes
from constants.statuses import scoreStatuses, mapStatuses
from constants.grades import Grade
from objects import glob, pp

from base64 import b64decode
from py3rijndael import RijndaelCbc, ZeroPadding
from pathlib import Path
from cmyui import log

import time
import re
import asyncio
import orjson

class Score:
    def __init__(self):
        self.id: int = None
        self.map: Beatmap = None
        self.user: Player = None

        self.score: int = None
        self.acc: float = None
        self.n300: int = None
        self.n100: int = None
        self.n50: int = None
        self.miss: int = None
        self.geki: int = None
        self.katu: int = None
        self.grade: Grade = None
        self.mods: Mods = None
        self.readable_mods: str = None
        self.combo: int = None
        self.mode: osuModes = None
        self.mode_vn: osuModes = None

        self.rank: int = None
        self.pp: float = None

        self.fc: bool = None
        self.passed: bool = None
        self.status: scoreStatuses = None
        self.time: int = None

        self.old_best: Score = None

    @classmethod
    async def sql(self, sid: int, table: str, sort: str, t: int, ensure: bool = False):
        score = await glob.db.fetchrow(f'SELECT * FROM {table} WHERE id = $1', sid)

        if not score:
            return
        
        s = self()

        s.id = sid

        if not Beatmap.md5_cache(score['md5']): # it should have the map in cache already for global lbs, but if not we can just grab from sql
            s.map = await Beatmap.md5_sql(score['md5'])
        else:
            s.map = Beatmap.md5_cache(score['md5'])

        s.user = glob.players_id.get(score['uid'])

        if not s.user and not ensure:
            return s # even if user isnt found, may be related to connection and we want to tell the client to retry
        
        if not s.user and ensure:
            # construct user from sql
            info = await glob.db.fetchrow('SELECT * FROM users WHERE id = $1', score['uid'])
            user = {
                'id': info['id'],
                'name': info['name'],
                'token': '',
                'offset': 24,
                'ltime': 0,
                'country_iso': info['country'],
                'country': 0,
                'lon': 0,
                'lat': 0,
                'md5': b'',
                'priv': info['priv']
            }

            s.user = await Player.login(user)

        if not s.map:
            return # ??

        s.pp = score['pp']
        s.score = score['score']
        s.combo = score['combo']
        s.mods = Mods(score['mods'])
        s.acc = score['acc']
        s.n300 = score['n300']
        s.n100 = score['n100']
        s.n50 = score['n50']
        s.miss = score['miss']
        s.geki = score['geki']
        s.katu = score['katu']
        s.grade = score['grade']
        s.fc = score['fc']
        s.status = scoreStatuses(score['status'])
        s.mode_vn = score['mode']
        s.mode = lbModes(s.mode_vn, s.mods)

        s.time = score['time']
        s.passed = s.status.value != 0
        s.rank = await s.calc_lb(table, sort, t)

        if s.mode.value > 3:
            val = s.pp
        else:
            val = s.score

        s.lb_format = f'{s.id}|{s.user.name}|{val}|{s.combo}|{s.n50}|{s.n100}|{s.n300}|{s.miss}|{s.katu}|{s.geki}|{int(s.fc)}|{s.mods}|{s.user.id}|{s.rank}|{s.time}|1'

        return s

    @classmethod
    async def submission(self, base: str, iv: str, pw: str, ver: str):
        iv = b64decode(iv).decode('latin_1')
        d = b64decode(base).decode('latin_1')
        key = f'osu!-scoreburgr---------{ver}'
        a = RijndaelCbc(key, iv, ZeroPadding(32), 32)

        data = a.decrypt(d).decode().split(':')

        s = self()

        if not Beatmap.md5_cache(data[0]): # it should have the map in cache already for global lbs, but if not we can just grab from sql
            s.map = await Beatmap.md5_sql(data[0])
        else:
            s.map = Beatmap.md5_cache(data[0])

        # i need to find a faster way to do this some day
        for o in glob.players.values():
            if o.pw == pw:
                s.user = o
        
        if not s.user:
            return s # even if user isnt found, may be related to connection and we want to tell the client to retry

        if not s.map:
            return # ??

        # i wanted to make everything be set in the same order as init but some require all score info to exist first so sadly not :c
        s.score = int(data[9])
        s.n300 = int(data[3])
        s.n100 = int(data[4])
        s.n50 = int(data[5])
        s.miss = int(data[8])
        s.geki = int(data[6])
        s.katu = int(data[7])
        s.mods = Mods(int(data[13]))
        s.readable_mods = convert(int(data[13]))
        s.combo = int(data[10])
        s.mode = lbModes(int(data[15]), s.mods)

        s.fc = data[11] == 'True' # WHY IS OSU GIVING STRING FOR BOOL!!!!!!
        s.passed = data[14] == 'True' # AGAIN OSU WHY!!!!
        s.time = round(time.time()) # have to add round cast cus it gives float smh

        s.grade = data[12] if s.passed else 'F'

        if s.mods & Mods.RELAX:
            s.mode_vn = s.mode.value - 4
        elif s.mods & Mods.AUTOPILOT:
            s.mode_vn = 0
        else:
            s.mode_vn = s.mode.value

        s.pp = await s.calc_pp()
        await s.calc_info()

        return s

    def calc_lb_format(self):
        if self.mode.value > 3:
            val = self.pp
        else:
            val = self.score

        return f'{self.id}|{self.user.name}|{val}|{self.combo}|{self.n50}|{self.n100}|{self.n300}|{self.miss}|{self.katu}|{self.geki}|{int(self.fc)}|{self.mods}|{self.user.id}|{self.rank}|{self.time}|1'

    async def calc_lb(self, table, sort, value):
        lb = await glob.db.fetchrow(f'SELECT COUNT(*) AS r FROM {table} LEFT OUTER JOIN users ON users.id = {table}.uid WHERE {table}.md5 = $1 AND {table}.mode = $2 AND {table}.status = 2 AND users.priv & 1 > 0 AND {table}.{sort} > $3', self.map.md5, self.mode.value, value)
        return lb['r'] + 1 if lb else 1

    async def calc_pp(self):
        path = Path.cwd() / f'resources/maps/{self.map.id}.osu'
        if not path.exists():
            url = f'https://old.ppy.sh/osu/{self.map.id}'

            async with glob.web.get(url) as resp:
                if not resp or resp.status != 200:
                    return 0.0

                m = await resp.read()
                path.write_bytes(m)

        if self.mode.value in [4, 7]:
            p = pp.parser()
            bmap = pp.beatmap()
            stars = pp.diff_calc()

            with open(path, 'r') as f:
                p.map(f, bmap=bmap)

            stars.calc(bmap, self.mods)
            ppv, _, _, _, _ = pp.ppv2(stars.aim, stars.speed, bmap=bmap, mods=self.mods, n300=self.n300, n100=self.n100, n50=self.n50, nmiss=self.miss, combo=self.combo)

            return ppv
        else:
            if self.mode.name == 'std':
                nm = 'osu' # fucking osu-tools why
            else:
                nm = self.mode.name

            cmd = [f'./osu-tools/compiled/PerformanceCalculator simulate {nm} {str(path)}']
            if self.mode.value == 0:
                cmd.append(f'-M {self.n50}') # 50s
            
            if self.mode.value == 3:
                cmd.append(f'-s {self.score}') # mania = score game xd
            else:
                cmd.append(f'-c {self.combo}') # max combo
                cmd.append(f'-X {self.miss}') # miss count

            if self.mode.value == 2:
                cmd.append(f'-D {self.n50}') # 50s equivalent for catch?
            else:
                cmd.append(f'-G {self.n100}') # 100s

            for mod in re.findall('.{1,2}', self.readable_mods):
                if mod != 'NM': # will confuse osu-tools xd
                    cmd.append(f'-m {mod}') # osu tool expects 1 arg per mod so we have to do this gay regex

            cmd.append('-j') # json formatting is godsend thank u peppy

            p = asyncio.subprocess.PIPE
            comp = ' '.join(cmd)
            pr = await asyncio.create_subprocess_shell(comp, stdout=p, stderr=p)
            ot, _ = await pr.communicate()
            o = orjson.loads(ot.decode('utf-8'))
            return o['pp']

    async def calc_info(self):
        mode = self.mode_vn

        if mode == 0:
            hits = self.n300 + self.n100 + self.n50 + self.miss

            if hits == 0:
                self.acc = 0.0
            else:
                self.acc = 100.0 * ((self.n50 * 50.0) + (self.n100 * 100.0) + (self.n300 * 300.0)) / (hits * 300.0) # ugly asffffff
        elif mode == 1:
            hits = self.n300 + self.n100 + self.miss

            if hits == 0:
                self.acc = 0.0
            else:
                self.acc = 100.0 * ((self.n100 * 0.5) + self.n300) / hits
        elif mode == 2:
            hits = self.n300 + self.n100 + self.n50 + self.katu + self.miss

            if hits == 0:
                self.acc = 0.0
            else:
                self.acc = 100.0 * (self.n300 + self.n100 + self.n50) / hits
        elif mode == 3:
            hits = self.n300 + self.n100 + self.n50 + self.geki + self.katu + self.miss

            if hits == 0:
                self.acc = 0.0
            else:
                self.acc = 100.0 * ((self.n50 * 50.0) + (self.n100 * 100.0) + (self.katu * 200.0) + ((self.n300 + self.geki) * 300.0)) / (hits * 300.0)

        if self.mods & Mods.RELAX:
            t = self.pp
        elif self.mods & Mods.AUTOPILOT:
            t = self.pp
        else:
            t = self.score

        lb = await glob.db.fetchrow(f'SELECT COUNT(*) AS r FROM {self.mode.table} t LEFT OUTER JOIN users ON users.id = t.uid WHERE t.md5 = $1 AND t.mode = $2 AND t.status = 2 AND users.priv & 1 > 0 AND t.{self.mode.sort} > $3', self.map.md5, mode, t)
        self.rank = lb['r'] + 1 if lb else 1

        score = await glob.db.fetchrow(f'SELECT id, pp FROM {self.mode.table} WHERE uid = $1 AND md5 = $2 AND mode = $3 AND status = 2', self.user.id, self.map.md5, mode)
        if score: # they already have a (best) submitted score
            self.old_best = await Score.sql(score['id'], self.mode.table, self.mode.sort, t)

            if self.pp > score['pp']:
                self.status = scoreStatuses.Best
                self.old_best.status = scoreStatuses.Submitted
            else:
                self.status = scoreStatuses.Submitted # not best submitted score
        else:
            self.status = scoreStatuses.Best # no previous scores on the map
        
        if not self.passed:
            self.status = scoreStatuses.Failed