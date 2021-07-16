from .beatmap import Beatmap
from .player import Player
from constants.mods import Mods, convert
from constants.modes import osuModes, lbModes
from constants.statuses import scoreStatuses, mapStatuses
from constants.grades import Grade
from constants.privs import Privileges
from objects import glob

from base64 import b64decode
from py3rijndael import RijndaelCbc, Pkcs7Padding
from pathlib import Path
from cmyui.osu.oppai_ng import OppaiWrapper
from maniera.calculator import Maniera
from circleguard import Circleguard, ReplayString

import time
import re
import asyncio
import orjson
import copy

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
        self.sr: float = None

        self.fc: bool = None
        self.passed: bool = None
        self.status: scoreStatuses = None
        self.time: int = None

        self.old_best: Score = None
        
        self.osuver: int = None
        self.ur: float = None

    async def format(self):
        msg = f'{self.user.name} | {self.map.name} +{self.readable_mods} {self.acc:.2f}% {"FC" if not self.miss else f"{self.miss}xMiss"} {round(self.pp):,}pp'
        
        if self.miss:
            fc_score = copy.copy(self)
            
            fc_score.fc = True
            fc_score.combo = 0 # oppai will take max combo
            pp, _ = await fc_score.calc_pp(self.mode.as_vn)
            
            msg += f' (~{round(pp):,}pp for FC)'
            
        if self.mode.value == 0 and self.ur:
            msg += f' | {self.ur:.2f} (cv)UR'
            
        return msg

    @classmethod
    async def sql(self, sid: int, table: str, sort: str, t: int, ensure: bool = False):
        score = await glob.db.fetchrow(f'SELECT * FROM {table} WHERE id = %s', [sid])

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
            
        s.osuver = score['osuver']

        return s

    @classmethod
    async def submission(self, base: str, iv: str, pw: str, ver: str):
        a = RijndaelCbc( # much better fuck one liners
            key=f'osu!-scoreburgr---------{ver}',
            iv=b64decode(iv),
            padding=Pkcs7Padding(32),
            block_size=32
        )

        data = a.decrypt(b64decode(base)).decode().split(':')

        s = self()

        s.map = await Beatmap.from_md5(data[0])

        if (u := glob.players_name.get(data[1].rstrip())): # faster i think?
            if u.pw == pw:
                s.user = u
        
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
        s.pp, s.sr = await s.calc_pp(s.mode.as_vn)
        await s.score_order()
        
        if s.user.restricted:
            s.rank = 0
            
        s.osuver = float(re.sub("[^0-9]", "", ver)) # lol

        return s

    async def analyse(self):
        # BIG NOTE: THIS IS MORE OF A PREVENTATIVE MEASURE TO STOP BLATANT CHEATERS. SOME VERY GOOD LEGIT PLAYERS COULD GET FLAGGED BY THIS SO PLEASE BE AWARE
        # however: 9 times out of 10 this shouldn't false ban, most players getting e.g sub 60 ur will be relax cheats. but maybe you have umbre playing on your server, i don't know.

        if self.mods & Mods.RELAX:
            rx = 1
        elif self.mods & Mods.AUTOPILOT:
            rx = 2
        else:
            rx = 0

        url = f'https://api.{glob.config.domain}/get_replay?id={self.id}&rx={rx}'
        
        async with glob.web.get(url) as resp:
            rp = await resp.read()

        cg = Circleguard(glob.config.api_key)
        replay = ReplayString(rp)

        # TODO: compare replay against bancho leaderboards
        self.ur = cg.ur(replay) # cant do := because class :(
        if self.ur < 70:
            await self.user.flag(reason=f'potential relax (ur: {self.ur:.2f})', fr=glob.bot)

        if (ft := cg.frametime(replay)) < 14: # TODO: check for false positives in frametime
            await self.user.restrict(reason=f'timewarp cheating (frametime: {ft:.2f})', fr=glob.bot)
            
    async def announce_n1(self):
        msg = f'[{self.mode!r}] {self.user.embed} achieved #1 on {self.map.embed} +{self.readable_mods}'

        if self.map.status != mapStatuses.Loved:
            msg += f' worth {round(self.pp):,}pp'

        prev1 = await glob.db.fetchval(f'SELECT users.name FROM users LEFT OUTER JOIN {self.mode.table} t ON t.uid = users.id WHERE t.md5 = %s AND t.mode = %s AND t.status = 2 AND NOT users.priv & {Privileges.Disallowed} AND t.uid != %s AND t.id != %s ORDER BY t.{self.mode.sort} DESC LIMIT 1', [self.map.md5, self.mode.as_vn, self.user.id, self.id])

        if prev1:
            msg += f' (Previous #1: [https://{glob.config.domain}/u/{prev1} {prev1}])'

        chan = glob.channels['#announce']
        chan.send(glob.bot, msg, True)

    def calc_lb_format(self, user):
        if self.mode.value > 3:
            val = round(self.pp)
        else:
            val = self.score

        if user.id == self.user.id:
            nm = self.user.name
        else:
            nm = self.user.full_name

        return f'{self.id}|{nm}|{val}|{self.combo}|{self.n50}|{self.n100}|{self.n300}|{self.miss}|{self.katu}|{self.geki}|{int(self.fc)}|{self.mods}|{self.user.id}|{self.rank}|{self.time}|1'

    async def calc_lb(self, table, sort, value):
        lb = await glob.db.fetchval(f'SELECT COUNT(*) AS r FROM {table} LEFT OUTER JOIN users ON users.id = {table}.uid WHERE {table}.md5 = %s AND {table}.mode = %s AND {table}.status = 2 AND NOT users.priv & {Privileges.Disallowed} AND {table}.{sort} > %s', [self.map.md5, self.mode.value, value])
        return lb + 1 if lb else 1

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
                
                if self.combo:
                    ezpp.set_combo(self.combo)

                ezpp.set_nmiss(self.miss)
                ezpp.set_accuracy_percent(self.acc)

                ezpp.calculate(path)
                return (ezpp.get_pp(), ezpp.get_sr())
        elif self.mode.value == 3: # mania: use maniera
            if self.map.mode != 3:
                return 0.0 # no convert support

            if self.mods != Mods.NOMOD:
                mods = int(self.mods)
            else:
                mods = 0

            c = Maniera(str(path), mods, self.score)
            c.calculate()

            return (c.pp, c.sr)
        else: # ctb: use shitty osu-tools

            cmd = [f'./osu-tools/compiled/PerformanceCalculator simulate {nm} {str(path)}']
            
            if self.combo:
                cmd.append(f'-c {self.combo}') # max combo

            cmd.append(f'-X {self.miss}') # miss count

            cmd.append(f'-D {self.n50}') # 50s equivalent for catch? 
            # hey note from len4ee here 50s for ctb is droplets xd

            for mod in re.findall('.{1,2}', self.readable_mods):
                if mod != 'NM': # will confuse osu-tools xd
                    cmd.append(f'-m {mod}') # osu tool expects 1 arg per mod so we have to do this gay regex

            cmd.append('-j') # json formatting is godsend thank u peppy

            p = asyncio.subprocess.PIPE
            comp = ' '.join(cmd)
            pr = await asyncio.create_subprocess_shell(comp, stdout=p, stderr=p)
            ot, _ = await pr.communicate()
            o = orjson.loads(ot.decode('utf-8'))
            return o['pp'], 0.0

    async def score_order(self):
        mode = self.mode.as_vn

        if self.mods & Mods.RELAX:
            t = self.pp
        elif self.mods & Mods.AUTOPILOT:
            t = self.pp
        else:
            t = self.score

        lb = await glob.db.fetchval(f'SELECT COUNT(*) AS r FROM {self.mode.table} t LEFT OUTER JOIN users ON users.id = t.uid WHERE t.md5 = %s AND t.mode = %s AND t.status = 2 AND NOT users.priv & {Privileges.Disallowed} AND t.{self.mode.sort} > %s', [self.map.md5, mode, t])
        self.rank = lb + 1 if lb else 1

        score = await glob.db.fetchrow(f'SELECT id, pp, score FROM {self.mode.table} WHERE uid = %s AND md5 = %s AND mode = %s AND status = 2', [self.user.id, self.map.md5, mode])
        if score: # they already have a (best) submitted score
            self.old_best = await Score.sql(score['id'], self.mode.table, self.mode.sort, t)

            if (self.pp == score['pp'] and self.score > score['score']) or self.pp > score['pp']: # allow scores to overwrite if they have higher score but same pp
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
