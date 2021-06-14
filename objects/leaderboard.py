from objects.beatmap import Beatmap
from objects.player import Player
from objects.score import Score
from constants.modes import osuModes
from constants.statuses import mapStatuses

from objects import glob

from functools import cached_property

class Leaderboard:
    def __init__(self, bmap: Beatmap, mode: osuModes):
        self.map = bmap
        self.mode = mode

        self.user_cache = {}
        self.score_cache = []

    @cached_property
    def base_body(self):
        return f'{self.map.status}|false|{self.map.id}|{self.map.sid}'

    @cached_property
    def map_body(self):
        return f'0\n{self.map.name}\n10.0'

    async def return_leaderboard(self, user: Player):
        if self.map.status < mapStatuses.Ranked:
            return f'{self.map.status}|false'.encode()

        if self.mode.value > 3 and self.mode.value < 7:
            mode_vn = self.mode.value - 4
        elif self.mode == 7:
            mode_vn = 0
        else:
            mode_vn = self.mode.value

        scores = await glob.db.fetch(f'SELECT t.id, {self.mode.sort} as s FROM {self.mode.table} t LEFT OUTER JOIN users ON users.id = t.uid WHERE md5 = $1 AND mode = $2 AND status = 2 AND users.priv & 1 > 0 ORDER BY s DESC LIMIT 100', self.map.md5, mode_vn)

        mbody = self.base_body + f'|{len(scores)}'

        base = []
        base.append(mbody)
        base.append(self.map_body)

        pb = await self.get_personal(user)

        if pb:
            base.append(pb.calc_lb_format())
        else:
            base.append('')

        scrs = []

        if self.score_cache:
            scrs.extend(self.score_cache)
        else:
            for s in scores:
                score = await Score.sql(s['id'], self.mode.table, self.mode.sort, s['s'], ensure=True)
                scrs.append(score)

        s = [s.calc_lb_format() for s in scrs]

        if self.score_cache != scrs:
            self.score_cache = scrs

        return '\n'.join(base + s).encode()

    def set_user_pb(self, user: Player, score: Score):
        self.user_cache[user.name] = score

        for s in self.score_cache:
            if s.user.name == user.name:
                self.score_cache.remove(s)
                break

        self.score_cache.append(score)

    async def get_personal(self, user: Player):
        if user.name in self.user_cache:
            return self.user_cache[user.name]

        if self.mode.value > 3 and self.mode.value < 7:
            mode_vn = self.mode.value - 4
        elif self.mode == 7:
            mode_vn = 0
        else:
            mode_vn = self.mode.value

        pbd = await glob.db.fetchrow(f'SELECT {self.mode.table}.id, {self.mode.sort} as s FROM {self.mode.table} WHERE md5 = $1 AND mode = $2 AND status = 2 AND uid = $3 ORDER BY s DESC LIMIT 1', self.map.md5, mode_vn, user.id)

        if pbd:
            # score found xd
            pb = await Score.sql(pbd['id'], self.mode.table, self.mode.sort, pbd['s'])
        else:
            pb = None

        self.user_cache[user.name] = pb
        return pb