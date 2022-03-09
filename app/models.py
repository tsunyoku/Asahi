from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Any
from typing import Callable
from typing import TypedDict

import app.state
from app.constants.action import Action
from app.constants.countries import OSU_GEOLOC
from app.constants.mode import Mode
from app.constants.mods import Mods
from app.objects.beatmap import Beatmap
from app.typing import i32
from app.typing import String
from app.typing import u32
from app.typing import u8


class LoginData(TypedDict):
    token: str
    body: bytes


class ActionPacket:
    action_id: u8  # TODO: switch out with action enum1
    info_text: String
    map_md5: String
    mods: u32  # TODO: switch out with mods enum
    mode: u8  # TODO: switch out with mode enum
    map_id: i32


@dataclass
class Stats:
    tscore: int
    rscore: int
    pp: int
    acc: float
    plays: int
    playtime: int
    max_combo: int
    total_hits: int

    rank: int
    country_rank: int

    # TODO: grades


@dataclass
class Status:  # NOTE: maybe use bmap object over id & md5?
    action: Action = Action.IDLE
    info_text: str = ""
    map_md5: str = ""
    mods: Mods = Mods.NOMOD
    mode: Mode = Mode.STD
    map_id: int = 0


@dataclass
class Country:
    code: int
    acronym: str


class Geolocation:
    def __init__(
        self,
        long: float = 0.0,
        lat: float = 0.0,
        country: Country = Country(0, "xx"),
        ip: str = "",
    ) -> None:
        self.long = long
        self.lat = lat
        self.country = country

        self.ip = ip

    @classmethod
    def from_ip(self, headers: dict[str, Any]) -> Geolocation:
        if not (ip := headers.get("CF-Connecting-IP")):
            forwards = headers["X-Forwarded-For"].split(",")

            if len(forwards) != 1:
                ip = forwards[0]
            else:
                ip = headers["X-Real-IP"]

        if not (geoloc := app.state.cache.geoloc.get(ip)):
            city = app.state.services.geoloc.city(ip)

            iso_code = city.country.iso_code.lower()
            country = Country(OSU_GEOLOC[iso_code], iso_code)
            geoloc = Geolocation(
                city.location.longitude,
                city.location.latitude,
                country,
                ip,
            )

            app.state.cache.geoloc[ip] = geoloc

        return geoloc


@dataclass
class LastBeatmap:
    bmap: Beatmap
    mode: Mode


@dataclass
class Achievement:
    id: int
    file: str
    name: str
    desc: str
    condition: Callable

    @cache
    def __repr__(self) -> str:
        return f"{self.file}+{self.name}+{self.desc}"
