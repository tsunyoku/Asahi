from objects.beatmap import Beatmap
from objects.player import Player
from constants.mods import Mods, convert
from constants.modes import osuModes, lbModes
from constants.statuses import scoreStatuses
from constants.grades import Grade
from objects import glob

from base64 import b64decode
from py3rijndael import RijndaelCbc, ZeroPadding
from pathlib import Path
from cmyui.osu.oppai_ng import OppaiWrapper
from maniera.calculator import Maniera
from circleguard import Circleguard, ReplayString

import time
import re
import asyncio
import orjson
import requests

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

        s.map = await Beatmap.from_md5(score['md5'])

        if not s.map:
            return # ?

        s.user = glob.players_id.get(score['uid'])

        if not s.user and not ensure:
            return s # even if user isnt found, may be related to connection and we want to tell the client to retry
        
        if not s.user and ensure:
            s.user = await Player.from_sql(score['uid'])

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
        s.mode = lbModes(osuModes(score['mode']).as_vn, s.mods)

        s.time = score['time']
        s.passed = s.status.value != 0
        
        if not s.user.restricted:
            s.rank = await s.calc_lb(table, sort, t)
        else:
            s.rank = 0

        return s

    @classmethod
    async def submission(self, base: str, iv: str, pw: str, ver: str):
        iv = b64decode(iv).decode('latin_1')
        d = b64decode(base).decode('latin_1')
        key = f'osu!-scoreburgr---------{ver}'
        a = RijndaelCbc(key, iv, ZeroPadding(32), 32)

        data = a.decrypt(d).decode().split(':')

        s = self()

        s.map = await Beatmap.from_md5(data[0])

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

        await s.calc_info()
        s.pp = await s.calc_pp(s.mode.as_vn)
        await s.score_order()
        
        if s.user.restricted:
            s.rank = 0

        return s

    def analyse(self):
        # BIG NOTE: THIS IS MORE OF A PREVENTATIVE MEASURE TO STOP BLATANT CHEATERS. SOME VERY GOOD LEGIT PLAYERS COULD GET FLAGGED BY THIS SO PLEASE BE AWARE
        # however: 9 times out of 10 this shouldn't false ban, most players getting e.g sub 60 ur will be relax cheats. but maybe you have umbre playing on your server, i don't know.

        if self.mods & Mods.RELAX:
            rx = 1
        elif self.mods & Mods.AUTOPILOT:
            rx = 2
        else:
            rx = 0

        url = f'https://api.{glob.config.domain}/get_replay?id={self.id}&rx={rx}'
        r = requests.get(url, stream=True)

        cg = Circleguard(glob.config.api_key)
        replay = ReplayString(r.raw.read())

        # TODO: compare replay against bancho leaderboards

        if (ur := cg.ur(replay)) < 60: # TODO: implement freeze system and freeze for unstable rate as its much less conclusive
            asyncio.run(self.user.restrict(reason=f'relax cheating (ur: {ur:.2f})'))

        if (ft := cg.frametime(replay)) < 14:
            asyncio.run(self.user.restrict(reason=f'timewarp cheating (frametime: {ft:.2f})'))

    def calc_lb_format(self):
        if self.mode.value > 3:
            val = self.pp
        else:
            val = self.score

        return f'{self.id}|{self.user.name}|{val}|{self.combo}|{self.n50}|{self.n100}|{self.n300}|{self.miss}|{self.katu}|{self.geki}|{int(self.fc)}|{self.mods}|{self.user.id}|{self.rank}|{self.time}|1'

    async def calc_lb(self, table, sort, value):
        lb = await glob.db.fetchrow(f'SELECT COUNT(*) AS r FROM {table} LEFT OUTER JOIN users ON users.id = {table}.uid WHERE {table}.md5 = $1 AND {table}.mode = $2 AND {table}.status = 2 AND users.priv & 1 > 0 AND {table}.{sort} > $3', self.map.md5, self.mode.value, value)
        return lb['r'] + 1 if lb else 1

    async def calc_pp(self, mode_vn):
        path = Path.cwd() / f'resources/maps/{self.map.id}.osu'
        if not path.exists():
            url = f'https://old.ppy.sh/osu/{self.map.id}'

            async with glob.web.get(url) as resp:
                if not resp or resp.status != 200:
                    return 0.0

                m = await resp.read()
                path.write_bytes(m)

        if mode_vn <= 1: # std/taiko: use oppai (cmyui wrapper op)
            with OppaiWrapper('oppai-ng/liboppai.so') as ezpp:
                if self.mods:
                    ezpp.set_mods(int(self.mods))
                    
                ezpp.set_mode(mode_vn)
                ezpp.set_combo(self.combo)
                ezpp.set_nmiss(self.miss)
                ezpp.set_accuracy_percent(self.acc)

                ezpp.calculate(path)
                return ezpp.get_pp() # returning sr soontm
        elif self.mode.value == 3: # mania: use maniera
            if self.map.mode != 3:
                return 0.0 # no convert support

            if self.mods != Mods.NOMOD:
                mods = int(self.mods)
            else:
                mods = 0

            c = Maniera(str(path), mods, self.score)
            c.calculate()

            return c.pp
        else: # ctb: use shitty osu-tools

            cmd = [f'./osu-tools/compiled/PerformanceCalculator simulate {nm} {str(path)}']
            cmd.append(f'-c {self.combo}') # max combo
            cmd.append(f'-X {self.miss}') # miss count

            cmd.append(f'-D {self.n50}') # 50s equivalent for catch?

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

    async def score_order(self):
        mode = self.mode.as_vn

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

    async def calc_info(self):
        mode = self.mode.as_vn

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