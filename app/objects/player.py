from __future__ import annotations

import time
import uuid
from functools import cache
from functools import cached_property
from typing import Optional
from typing import Union

import app.config
from app.constants.mode import Mode
from app.constants.privileges import BanchoPrivileges
from app.constants.privileges import Privileges
from app.models import Achievement
from app.models import Geolocation
from app.models import LastBeatmap
from app.models import Stats
from app.models import Status
from app.objects.channel import Channel
from app.objects.clan import Clan
from app.objects.match import Match


class Player:
    def __init__(
        self,
        id: int,
        name: str,
        priv: Union[int, Privileges],
        **extras,
    ) -> None:
        self.id = id
        self.name = name

        self.pw: Optional[bytes] = extras.get("pw", None)
        self.password_md5: Optional[str] = extras.get("password_md5", None)

        self.token: str = extras.get("token", None) or self.generate_token()
        self.priv = priv if isinstance(priv, Privileges) else Privileges(priv)

        self.stats: dict[Mode, Stats] = {}
        self.status = Status()

        self.friends: set[int] = set()
        self.channels: list[Channel] = []
        self.spectators: list[Player] = []
        self.achievements: set[Achievement] = set()
        self.spectating: Optional[Player] = None
        self.match: Optional[Match] = None

        c = extras.get("clan", 0)
        self.clan: Optional[Clan] = (
            c if isinstance(c, Clan) else app.state.sessions.clans.get(c)
        )

        self.geoloc: Geolocation = extras.get("geoloc", Geolocation())
        self.utc_offset = extras.get("utc_offset", 0)

        self.friend_only_dms = extras.get("friend_only_dms", False)

        self.silence_end = extras.get("silence_end", 0)

        self.lobby = False
        self.osu_ver: str = extras.get("osu_ver", None)  # XX: date?

        login_time = extras.get("login_time", 0.0)
        self.login_time = login_time
        self.last_ping = login_time

        self.last_np: LastBeatmap = LastBeatmap()
        self.tourney_client = extras.get("tourney_client", False)

        self._queue = bytearray()

    @cache
    def __repr__(self) -> str:
        return f"<{self.name} ({self.id})>"

    @cached_property
    def safe_name(self) -> str:
        return self.name.replace(" ", "_").lower()

    @cached_property
    def online(self) -> bool:
        return self.token != ""

    @cached_property
    def url(self) -> str:
        return f"https://{app.config.SERVER_DOMAIN}/u/{self.id}"

    @cached_property
    def embed(self) -> str:
        return f"[{self.url} {self.name}]"

    @cached_property
    def avatar_url(self) -> str:
        return f"https://a.{app.config.SERVER_DOMAIN}/{self.id}"

    @cached_property
    def full_name(self) -> str:
        if self.clan:
            return f"[{self.clan.tag}] {self.name}"

        return self.name

    @cached_property
    def bancho_priv(self) -> BanchoPrivileges:
        priv = BanchoPrivileges(0)

        if not self.priv & Privileges.DISALLOWED:
            priv |= BanchoPrivileges.PLAYER

        if self.priv & Privileges.SUPPORTER:
            priv |= BanchoPrivileges.SUPPORTER

        if self.priv & Privileges.ADMIN:
            priv |= BanchoPrivileges.MODERATOR

        if self.priv & Privileges.DEVELOPER:
            priv |= BanchoPrivileges.DEVELOPER

        if self.priv & Privileges.OWNER:
            priv |= BanchoPrivileges.OWNER

        return priv

    @property
    def remaining_silence(self) -> int:
        return max(0, int(self.silence_end - time.time()))

    @property
    def silenced(self) -> bool:
        return self.remaining_silence != 0

    @property
    def restricted(self) -> bool:
        return self.priv & Privileges.DISALLOWED

    @property
    def banned(self) -> bool:
        return self.priv & Privileges.BANNED

    @property
    def current_stats(self) -> Stats:
        return self.stats[self.status.mode]

    @staticmethod
    def generate_token() -> str:
        return str(uuid.uuid4())

    def enqueue(self, data: bytes) -> None:
        self._queue += data

    def dequeue(self) -> Optional[bytes]:
        if self._queue:
            data = bytes(self._queue)
            self._queue.clear()

            return data
