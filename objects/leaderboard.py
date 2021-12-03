from typing import Optional

from .beatmap import Beatmap
from .player import Player
from .score import Score
from constants.modes import osuModes
from constants.privs import Privileges
from constants.statuses import mapStatuses
from objects import glob


class Leaderboard:
    __slots__ = (
        "map",
        "mode",
        "user_cache",
        "score_cache",
        "mods_cache",
        "country_cache",
    )

    def __init__(self, bmap: Beatmap, mode: osuModes):
        self.map = bmap
        self.mode = mode

        self.user_cache = {}
        self.score_cache = []

        self.mods_cache = {}
        self.country_cache = {}

    @property
    def base_body(self) -> str:
        return f"{self.map.status}|false|{self.map.id}|{self.map.sid}"

    @property
    def map_body(self) -> str:
        return f"0\n{self.map.name}\n"

    async def return_leaderboard(self, user: Player, lb: int, mods: int) -> bytes:
        if self.map.status < mapStatuses.Ranked:
            return f"{self.map.status}|false".encode()

        mode_vn = self.mode.as_vn

        query = [
            f"SELECT t.id, {self.mode.sort} as s FROM {self.mode.table} t "
            f"LEFT OUTER JOIN users ON users.id = t.uid "
            f"WHERE md5 = %s AND mode = %s AND status = 2 AND "
            f"(NOT users.priv & {int(Privileges.Disallowed)} OR users.id = {user.id})",
        ]

        p = [self.map.md5, mode_vn]

        score_cache = None  # init value, some lb types won't provide a cache anyways

        if lb == 2:
            query.append("AND t.mods = %s")
            p.append(mods)

            score_cache = self.mods_cache.get(mods)
        elif lb == 3:
            f = user.friends + [user.id]
            query.append(f'AND t.uid IN ({",".join(str(e) for e in f)})')
        elif lb == 4:
            query.append("AND users.country = %s")
            p.append(user.country_iso.lower())

            score_cache = self.country_cache.get(user.country_iso)
        else:
            score_cache = self.score_cache  # global lb so just get all scores lol

        query.append(
            "ORDER BY s DESC LIMIT 100",
        )  # we only want the top 100, maybe ill increase this for donators?

        scores = await glob.db.fetch(" ".join(query), p)

        map_body = self.base_body + f"|{len(scores)}"  # basic info about the map

        base = []  # base info to return (map info + score count)

        base.append(map_body)

        rating = await glob.db.fetchval(
            "SELECT AVG(rating) AS rating FROM ratings WHERE md5 = %s",
            [self.map.md5],
        )
        if not rating:
            rating = 10.0

        base.append(
            self.map_body + f"{rating:.1f}",
        )  # could be confusing considering we have map_body above... this one is static while the other is not (amount of scores changes)

        pb = await self.get_personal(user)  # user's best score (if any)

        if pb:
            base.append(pb.calc_lb_format(user))
        else:
            base.append(
                "",
            )  # osu! client still expects an empty return if they have no pb

        scrs = []  # full list of scores to return

        if score_cache:
            scrs.extend(
                score_cache,
            )  # add the cached scores to our list of scores to return if there's any
        else:
            for s in scores:
                score = await Score.from_sql(
                    s["id"],
                    self.mode.table,
                    self.mode.sort,
                    s["s"],
                    ensure=True,
                )  # get score objects from sql, useful for cache

                scrs.append(score)  # add to list to return

        if not score_cache:
            if lb == 2:
                self.mods_cache[mods] = scrs
            elif lb == 4:
                self.country_cache[user.country_iso] = scrs
            elif lb == 1:
                self.score_cache = scrs

        s = [s.calc_lb_format(user) for s in scrs]

        return "\n".join(base + s).encode()

    def set_user_pb(self, user: Player, score: Score) -> None:
        self.user_cache[user.name] = score  # set personal cached score

        if score_cache := self.score_cache:
            for s in score_cache:
                if s.user.name == user.name:
                    score_cache.remove(s)
                    break

        if mods_cache := self.mods_cache.get(score.mods):
            for s in self.mods_cache.get(score.mods) or {}:
                if s.user.name == user.name:
                    self.mods_cache[score.mods].remove(s)
                    break

        if country_cache := self.country_cache.get(user.country_iso):
            for s in country_cache:
                if s.user.name == user.name:
                    country_cache.remove(s)
                    break

        if score_cache:
            score_cache.append(score)

        if mods_cache:
            mods_cache.append(score)

        if country_cache:
            country_cache.append(score)

    async def get_personal(self, user: Player) -> Optional[Score]:
        if user.name in self.user_cache:
            return self.user_cache[user.name]

        pbd = await glob.db.fetchrow(
            f"SELECT {self.mode.table}.id, {self.mode.sort} as s FROM {self.mode.table} "
            f"WHERE md5 = %s AND mode = %s AND status = 2 AND uid = %s "
            f"ORDER BY s DESC LIMIT 1",
            [self.map.md5, self.mode.as_vn, user.id],
        )

        if pbd:
            # score found xd
            pb = await Score.from_sql(
                pbd["id"],
                self.mode.table,
                self.mode.sort,
                pbd["s"],
            )
        else:
            pb = None

        self.user_cache[user.name] = pb
        return pb
