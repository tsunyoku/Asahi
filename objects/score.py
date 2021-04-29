from objects.beatmap import Beatmap
from objects.player import Player
from constants.mods import Mods
from constants.modes import osuModes, lbModes
from constants.statuses import scoreStatuses
from constants.grades import Grade

from base64 import b64decode
from py3rijndael import RijndaelCbc, ZeroPadding

class Score:
    def __init__(self):
        self.id: int = None
        self.map: Beatmap = None
        self.user: Player = None

        self.score: int = None
        self.acc: float = None
        self.300: int = None
        self.100: int = None
        self.50: int = None
        self.miss: int = None
        self.geki: int = None
        self.katu: int = None
        self.grade: Grade = None
        self.mods: Mods = None
        self.combo: int = None
        self.mode: osuModes = None
        self.mode_vn: osuModes = None

        self.rank: int = None
        self.fc: bool = None
        self.passed: bool = None
        self.status: scoreStatuses = None
        self.time: int = None

    @classmethod
    async def submission(self, base: str, iv: str, pw: str, ver: str):
        iv = b64decode(iv).decode('latin_1')
        d = b64decode(base).decode('latin_1')
        key = f'osu!-scoreburgr---------{ver}'
        a = RijndaelCbc(key, iv, ZeroPadding(32), 32)

        data = a.decrypt(d).decode().split(':')

        s = self()

        player = data[1].rstrip()

        if not (s.bmap := Beatmap.md5_cache(data[0])): # it should have the map in cache already for global lbs, but if not we can just grab from sql
            if not(s.bmap := await Beatmap.md5_sql(data[0])):
                return # ??

        # i need to find a faster way to do this some day
        for o in glob.players.values():
            if o.md5 == pw:
                s.user = o
        
        if not s.user:
            return s # even if user isnt found, may be related to connection and we want to tell the client to retry

        # i wanted to make everything be set in the same order as init but some require all score info to exist first so sadly not :c
        s.score = data[9]
        s.300 = data[3]
        s.100 = data[4]
        s.50 = data[5]
        s.miss = data[8]
        s.geki = data[6]
        s.katu = data[7]
        s.mods = Mods(int(data[13]))
        s.combo = data[10]
        s.mode = lbModes(int(data[15]), s.mods)

        s.fc = data[11] == 'True' # WHY IS OSU GIVING STRING FOR BOOL!!!!!!
        s.passed = data[14] == 'True' # AGAIN OSU WHY!!!!
        s.time = round(time.time()) # have to add round cast cus it gives float smh

        s.grade = data[12] if s.passed else 'F'

        if s.mods & Mods.RELAX:
            self.mode_vn = self.mode - 4
        elif s.mods & Mods.AUTOPILOT:
            self.mode_vn = 0
        else:
            self.mode_vn = self.mode

        s.acc, s.pp, s.sr, s.rank, s.status = s.calc_info()

        return s

    async def calc_info(self):
        mode = self.mode_vn

        if mode == 0:
            hits = self.300 + self.100 + self.50 + self.miss

            if hits == 0:
                self.acc = 0.0
            else:
                self.acc = 100.0 * ((self.50 * 50.0) + (self.100 * 100.0) + (self.300 * 300.0)) / (hits * 300.0) # ugly asffffff
        elif mode == 1:
            hits = self.300 + self.100 + self.miss

            if hits == 0:
                self.acc = 0.0
            else:
                self.acc = 100.0 * ((self.100 * 0.5) + self.300) / hits
        elif mode == 2:
            hits = self.300 + self.100 + self.50 + self.katu + self.miss

            if hits == 0:
                self.acc = 0.0
            else:
                self.acc = 100.0 * (self.300 + self.100 + self.50) / hits
        elif mode == 3:
            hits = self.300 + self.100 + self.50 + self.geki + self.katu + self.miss

            if hits == 0:
                self.acc = 0.0
            else:
                self.acc = 100.0 * ((self.50 * 50.0) + (self.100 * 100.0) + (self.katu * 200.0) + ((self.300 + self.geki) * 300.0)) / (hits * 300.0)

        self.pp = 0 # until we have calculator xd
        self.sr = 0.0 # same reason xd

        if mods & Mods.RELAX:
            table = 'scores_rx'
            sort = 'pp'
        elif mods & Mods.AUTOPILOT:
            table = 'scores_ap'
            sort = 'pp'
        else:
            table = 'scores'
            sort = 'score'

        # we will force score sort regardless of rx/ap for now until we have pp calc
        lb = await glob.db.fetchrow(f'SELECT COUNT(*) AS r FROM {table} LEFT OUTER JOIN users ON users.id = {table}.uid WHERE {table}.md5 = $1 AND {table}.mode = $2 AND {table}.status = 2 AND users.priv & 1 AND {table}.score > $3', self.map.md5, mode_vn, self.score)
        self.rank = lb['c'] + 1 if lb else 1

        if not self.passed:
            self.status = scoreStatuses.Failed

        score = await glob.db.fetchrow(f'SELECT id, score FROM {table} WHERE uid = $1 AND md5 = $2 AND mode = $3 AND status = 2', self.user.id, self.map.md5, mode_vn)
        if score: # they already have a (best) submitted score
            if self.score > score['score']: # once again score-based overwrite til i add working pp system
                self.status = scoreStatuses.Best
                await glob.db.execute(f'UPDATE {table} SET status = $1 WHERE id = $2', scoreStatuses.Submitted.value, score['id'])
            else:
                self.status = scoreStatuses.Submitted # not best submitted score
        else:
            self.status = scoreStatuses.Best # no previous scores on the map



