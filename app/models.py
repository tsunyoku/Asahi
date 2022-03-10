from __future__ import annotations

from dataclasses import dataclass
from functools import cache
from typing import Callable
from typing import TypedDict

from app.constants.countries import OSU_GEOLOC
from app.constants.mode import Mode
from app.objects.beatmap import Beatmap


class LoginData(TypedDict):
    token: str
    body: bytearray


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
