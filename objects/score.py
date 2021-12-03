import asyncio
import copy
import math
import re
import threading
import time
from base64 import b64decode
from pathlib import Path
from typing import Optional

import orjson
from circleguard import Circleguard
from circleguard import ReplayString
from cmyui.osu.oppai_ng import OppaiWrapper
from peace_performance_python.objects import Beatmap as CalcBeatmap
from peace_performance_python.objects import Calculator
from py3rijndael import Pkcs7Padding
from py3rijndael import RijndaelCbc

from .beatmap import Beatmap
from .player import Player
from constants.grades import Grade
from constants.modes import lbModes
from constants.modes import osuModes
from constants.mods import Mods
from constants.privs import Privileges
from constants.statuses import mapStatuses
from constants.statuses import scoreStatuses
from objects import glob


class Score:
    __slots__ = (
        "id",
        "map",
        "user",
        "score",
        "acc",
        "n300",
        "n100",
        "n50",
        "miss",
        "geki",
        "katu",
        "grade",
        "mods",
        "readable_mods",
        "combo",
        "mode",
        "rank",
        "pp",
        "sr",
        "fc",
        "passed",
        "status",
        "time",
        "old_best",
        "osuver",
        "ur",
    )

    def __init__(self) -> None:
        self.id: Optional[int] = None
        self.map: Optional[Beatmap] = None
        self.user: Optional[Player] = None

        self.score: Optional[int] = None
        self.acc: Optional[float] = None
        self.n300: Optional[int] = None
        self.n100: Optional[int] = None
        self.n50: Optional[int] = None
        self.miss: Optional[int] = None
        self.geki: Optional[int] = None
        self.katu: Optional[int] = None
        self.grade: Optional[Grade] = None
        self.mods: Optional[Mods] = None
        self.readable_mods: Optional[str] = None
        self.combo: Optional[int] = None
        self.mode: Optional[osuModes] = None

        self.rank: Optional[int] = None
        self.pp: Optional[float] = None
        self.sr: Optional[float] = None

        self.fc: Optional[bool] = None
        self.passed: Optional[bool] = None
        self.status: Optional[scoreStatuses] = None
        self.time: Optional[int] = None

        self.old_best: Optional[Score] = None

        self.osuver: Optional[float] = None
        self.ur: Optional[float] = None

    async def format(self) -> str:
        msg = (
            f"{self.user.name} | {self.map.name} +{self.readable_mods} {self.acc:.2f}% "
            f'{"FC" if not self.miss else f"{self.miss}xMiss"} {self.pp:,.0f}pp'
        )

        if self.miss:
            fc_score = copy.copy(self)

            fc_score.fc = True
            fc_score.combo = 0  # oppai will take max combo
            pp, _ = await fc_score.calc_pp(self.mode.as_vn)

            msg += f" (~{round(pp):,}pp for FC)"

        if self.mode.value == 0 and self.ur:
            msg += f" | {self.ur:.2f} (cv)UR"

        return msg

    @classmethod
    async def from_sql(
        cls,
        sid: int,
        table: str,
        sort: str,
        t: int,
        ensure: bool = False,
    ) -> Optional["Score"]:
        score = await glob.db.fetchrow(f"SELECT * FROM {table} WHERE id = %s", [sid])

        if not score:
            return

        self = cls()

        self.id = sid

        self.map = await Beatmap.from_md5(score["md5"])

        if not self.map:
            return  # ?

        self.user = await glob.players.get(id=score["uid"], sql=ensure)

        if not self.user:
            return self

        self.pp = score["pp"]
        self.score = score["score"]
        self.combo = score["combo"]
        self.mods = Mods(score["mods"])
        self.acc = score["acc"]
        self.n300 = score["n300"]
        self.n100 = score["n100"]
        self.n50 = score["n50"]
        self.miss = score["miss"]
        self.geki = score["geki"]
        self.katu = score["katu"]
        self.grade = score["grade"]
        self.fc = score["fc"]
        self.status = scoreStatuses(score["status"])
        self.mode = lbModes(score["mode"], self.mods)

        self.time = score["time"]
        self.passed = self.status.value != 0

        if not self.user.restricted:
            self.rank = await self.calc_lb(table, sort, t)
        else:
            self.rank = 0

        self.osuver = score["osuver"]

        return self

    @classmethod
    async def from_submission(
        cls,
        base: str,
        iv: str,
        pw: str,
        ver: str,
    ) -> Optional["Score"]:
        rijndael = RijndaelCbc(  # much better fuck one liners
            key=f"osu!-scoreburgr---------{ver}".encode(),
            iv=b64decode(iv),
            padding=Pkcs7Padding(32),
            block_size=32,
        )

        data = rijndael.decrypt(b64decode(base)).decode().split(":")

        self = cls()

        self.map = await Beatmap.from_md5(data[0])

        if (u := await glob.players.get(name=data[1].rstrip())) and u.pw == pw:
            self.user = u

        if not self.user:
            return self  # even if user isnt found, may be related to connection and we want to tell the client to retry

        if not self.map:
            return  # ??

        # i wanted to make everything be set in the same order as init but some require all score info to exist first so sadly not :c
        self.score = int(data[9])
        self.n300 = int(data[3])
        self.n100 = int(data[4])
        self.n50 = int(data[5])
        self.miss = int(data[8])
        self.geki = int(data[6])
        self.katu = int(data[7])
        self.mods = Mods(int(data[13]))
        self.readable_mods = repr(Mods(int(data[13])))
        self.combo = int(data[10])
        self.mode = lbModes(int(data[15]), self.mods)

        self.fc = data[11] == "True"  # WHY IS OSU GIVING STRING FOR BOOL!!!!!!
        self.passed = data[14] == "True"  # AGAIN OSU WHY!!!!
        self.time = round(time.time())  # have to add round cast cus it gives float smh

        self.grade = data[12] if self.passed else "F"

        await self.calc_info()
        self.pp, self.sr = await self.calc_pp(self.mode.as_vn)
        await self.score_order()

        if self.user.restricted:
            self.rank = 0

        self.osuver = float(re.sub("[^0-9]", "", ver))  # lol

        return self

    async def analyse(self) -> None:
        # BIG NOTE: THIS IS MORE OF A PREVENTATIVE MEASURE TO STOP BLATANT CHEATERS. SOME VERY GOOD LEGIT PLAYERS COULD GET FLAGGED BY THIS SO PLEASE BE AWARE
        # however: 9 times out of 10 this shouldn't false ban, most players getting e.g sub 60 ur will be relax cheats. but maybe you have umbre playing on your server, i don't know.

        if self.mods & Mods.RELAX:
            rx = 1
        elif self.mods & Mods.AUTOPILOT:
            rx = 2
        else:
            rx = 0

        url = f"https://api.{glob.config.domain}/get_replay?id={self.id}&rx={rx}"

        async with glob.web.get(url) as resp:
            rp = await resp.read()

        threading.Thread(target=self.replay_check, args=(rp,), daemon=True).start()

    def replay_check(self, replay_data_str: str) -> None:
        cg = Circleguard(glob.config.api_key)
        replay = ReplayString(replay_data_str)

        if glob.config.similarity_checks:
            # get bancho leaderboards and compare replay
            # TODO: check replays on private servers
            if self.map.status >= mapStatuses.Ranked:  # has bancho lb
                _map = cg.Map(
                    self.map.id,
                    span="1-100",
                )  # maybe ill increase this to the top 1000?

                for mreplay in _map:
                    sim = cg.similarity(replay, mreplay)
                    if (
                        sim < 17.0
                    ):  # suggested circlecore value, idk if this should change
                        # THIS CAN FLAG LEGIT HENCE WHY IT FLAGS, PLEASE CHECK A REPLAY MANUALLY IF FLAGGED!
                        return asyncio.run(
                            self.user.flag(
                                reason=f"potential replay botting using {mreplay.username}'s bancho replay (similarity: {sim:.2f}) on {self.map.name}",
                                fr=glob.bot,
                            ),
                        )

        self.ur = cg.ur(replay)  # cant do := because class :(
        if self.ur < 70:
            asyncio.run(
                self.user.flag(
                    reason=f"potential relax (ur: {self.ur:.2f}) on {self.map.name}",
                    fr=glob.bot,
                ),
            )

        # this can sometimes be a false positive but its detectable thru a visualized graph (i may send it alongside the embed at some point)
        # there is a fix in the works for detecting false positives
        if (ft := cg.frametime(replay)) < 14:
            asyncio.run(
                self.user.restrict(
                    reason=f"timewarp cheating (frametime: {ft:.2f}) on {self.map.name}",
                    fr=glob.bot,
                ),
            )

    async def announce_n1(self) -> None:
        msg = f"[{self.mode!r}] {self.user.embed} achieved #1 on {self.map.embed} +{self.readable_mods}"

        if self.map.status != mapStatuses.Loved:
            msg += f" worth {self.pp:,.0f}pp"

        prev1 = await glob.db.fetchval(
            f"SELECT users.name FROM users "
            f"LEFT OUTER JOIN {self.mode.table} t ON t.uid = users.id "
            f"WHERE t.md5 = %s AND t.mode = %s AND t.status = 2 "
            f"AND NOT users.priv & {int(Privileges.Disallowed)} AND t.uid != %s "
            f"AND t.id != %s ORDER BY t.{self.mode.sort} DESC LIMIT 1",
            [self.map.md5, self.mode.as_vn, self.user.id, self.id],
        )

        if prev1:
            msg += f" (Previous #1: [https://{glob.config.domain}/u/{prev1} {prev1}])"

        chan = glob.channels["#announce"]
        chan.send(glob.bot, msg, send_self=True)

    def calc_lb_format(self, user: Player) -> str:
        if self.mode.value > 3:
            val = round(self.pp)
        else:
            val = self.score

        if user.id == self.user.id:
            nm = self.user.name
        else:
            nm = self.user.full_name

        return (
            f"{self.id}|{nm}|{val}|{self.combo}|{self.n50}|{self.n100}|{self.n300}|"
            f"{self.miss}|{self.katu}|{self.geki}|{int(self.fc)}|"
            f"{int(self.mods)}|{self.user.id}|{self.rank}|{self.time}|1"
        )

    async def calc_lb(self, table: str, sort: str, value: int) -> int:
        lb = await glob.db.fetchval(
            f"SELECT COUNT(*) AS r FROM {table} "
            f"LEFT OUTER JOIN users ON users.id = {table}.uid "
            f"WHERE {table}.md5 = %s AND {table}.mode = %s AND {table}.status = 2 "
            f"AND NOT users.priv & {int(Privileges.Disallowed)} AND {table}.{sort} > %s",
            [self.map.md5, self.mode.value, value],
        )

        return lb + 1 if lb else 1

    async def calc_pp(self, mode_vn: int) -> tuple[float, float]:
        path = Path.cwd() / f"resources/maps/{self.map.id}.osu"
        if not path.exists():
            url = f"https://old.ppy.sh/osu/{self.map.id}"

            async with glob.web.get(url) as resp:
                if not resp or resp.status != 200:
                    return (0.0, 0.0)

                m = await resp.read()
                path.write_bytes(m)

        if mode_vn <= 1:  # std/taiko: use oppai (cmyui wrapper op)
            with OppaiWrapper("oppai-ng/liboppai.so") as ezpp:
                if self.mods:
                    ezpp.set_mods(int(self.mods))

                ezpp.set_mode(int(mode_vn))

                if self.combo:
                    ezpp.set_combo(int(self.combo))

                if self.miss:
                    ezpp.set_nmiss(int(self.miss))

                ezpp.set_accuracy_percent(float(self.acc))

                ezpp.calculate(path)
                pp = ezpp.get_pp()

                if math.isinf(pp) or math.isnan(pp):
                    return (0.0, 0.0)

                return (pp, ezpp.get_sr())
        else:
            _map = CalcBeatmap(path)
            calc = Calculator(
                acc=self.acc,
                miss=self.miss,
                katu=self.katu,
                score=self.score,
                combo=self.combo,
                mode=mode_vn,
                mods=int(self.mods),
            ).calculate(_map)
            return calc.pp, calc.stars

    async def score_order(self) -> None:
        mode = self.mode.as_vn

        if self.mods & Mods.RELAX:
            t = self.pp
        elif self.mods & Mods.AUTOPILOT:
            t = self.pp
        else:
            t = self.score

        lb = await glob.db.fetchval(
            f"SELECT COUNT(*) AS r FROM {self.mode.table} t "
            f"LEFT OUTER JOIN users ON users.id = t.uid "
            f"WHERE t.md5 = %s AND t.mode = %s AND t.status = 2 "
            f"AND NOT users.priv & {int(Privileges.Disallowed)} AND t.{self.mode.sort} > %s",
            [self.map.md5, mode, t],
        )

        self.rank = lb + 1 if lb else 1

        score = await glob.db.fetchrow(
            f"SELECT id, pp, score FROM {self.mode.table}"
            f" WHERE uid = %s AND md5 = %s AND mode = %s AND status = 2",
            [self.user.id, self.map.md5, mode],
        )

        if score:  # they already have a (best) submitted score
            self.old_best = await Score.from_sql(
                score["id"],
                self.mode.table,
                self.mode.sort,
                t,
            )

            if (
                self.pp == score["pp"] and self.score > score["score"]
            ) or self.pp > score[
                "pp"
            ]:  # allow scores to overwrite if they have higher score but same pp
                self.status = scoreStatuses.Best
                self.old_best.status = scoreStatuses.Submitted
            else:
                self.status = scoreStatuses.Submitted  # not best submitted score
        else:
            self.status = scoreStatuses.Best  # no previous scores on the map

        if not self.passed:
            self.status = scoreStatuses.Failed

    async def calc_info(self) -> None:
        mode = self.mode.as_vn

        if mode == 0:
            hits = self.n300 + self.n100 + self.n50 + self.miss

            if hits == 0:
                self.acc = 0.0
                return
            else:
                self.acc = (
                    100.0
                    * ((self.n50 * 50.0) + (self.n100 * 100.0) + (self.n300 * 300.0))
                    / (hits * 300.0)
                )

        elif mode == 1:
            hits = self.n300 + self.n100 + self.miss

            if hits == 0:
                self.acc = 0.0
                return
            else:
                self.acc = 100.0 * ((self.n100 * 0.5) + self.n300) / hits
        elif mode == 2:
            hits = self.n300 + self.n100 + self.n50 + self.katu + self.miss

            if hits == 0:
                self.acc = 0.0
                return
            else:
                self.acc = 100.0 * (self.n300 + self.n100 + self.n50) / hits
        elif mode == 3:
            hits = self.n300 + self.n100 + self.n50 + self.geki + self.katu + self.miss

            if hits == 0:
                self.acc = 0.0
                return
            else:
                self.acc = (
                    100.0
                    * (
                        (self.n50 * 50.0)
                        + (self.n100 * 100.0)
                        + (self.katu * 200.0)
                        + ((self.n300 + self.geki) * 300.0)
                    )
                    / (hits * 300.0)
                )
