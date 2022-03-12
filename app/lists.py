from __future__ import annotations

from typing import Iterator
from typing import Optional
from typing import Union

import app.state
import app.utils
from app.constants.privileges import Privileges
from app.objects.channel import Channel
from app.objects.clan import Clan
from app.objects.player import Player
from app.state.services import Country
from app.state.services import Geolocation


class PlayerList(list[Player]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __iter__(self) -> Iterator[Player]:
        return super().__iter__()

    def __contains__(self, player: Union[Player, str, int]) -> bool:
        if isinstance(player, str):
            return player in [name for name in self.names]
        elif isinstance(player, int):
            return player in [id for id in self.ids]
        else:
            return super().__contains__(player)

    def __repr__(self) -> str:
        return f"[{', '.join(map(repr, self))}]"

    @property
    def ids(self) -> list[int]:
        return [p.id for p in self]

    @property
    def names(self) -> list[str]:
        return [p.name for p in self]

    @property
    def staff(self) -> list[Player]:
        return [p for p in self if p.priv & Privileges.STAFF]

    @property
    def restricted(self) -> list[Player]:
        return [p for p in self if p.priv & Privileges.RESTRICTED]

    @property
    def unrestricted(self) -> list[Player]:
        return [p for p in self if not p.priv & Privileges.RESTRICTED]

    def enqueue(self, data: bytes, immune: list[int] = []) -> None:
        for p in self:
            if p.id not in immune:
                p.enqueue(data)

    @staticmethod
    def _parse_kwargs(
        kwargs: dict[str, Union[str, int]],
    ) -> tuple[str, Union[str, int]]:
        for attr in ("token", "id", "name"):
            if (val := kwargs.pop(attr, None)) is not None:
                if attr == "name":
                    attr = "safe_name"
                    val = app.utils.make_safe(val)

                return attr, val
        else:
            raise ValueError("No valid keyword arg passed to PlayerList.get()")

    def _get(self, **kwargs: dict[str, Union[str, int]]) -> Optional[Player]:
        attr, val = self._parse_kwargs(kwargs)

        for p in self:
            if getattr(p, attr) == val:
                return p

    async def get(self, **kwargs: dict[str, Union[str, int]]) -> Optional[Player]:
        if player := self._get(**kwargs):
            return player

        if kwargs.get("sql", False):
            return await self.get_from_db(kwargs)

    async def get_from_db(
        self, **kwargs: dict[str, Union[str, int]]
    ) -> Optional[Player]:
        attr, val = self._parse_kwargs(kwargs)

        ...

    def get_from_login(self, name: str, md5: str) -> Optional[Player]:
        if not (player := self._get(name=name)):
            return

        if player.password_md5 == md5:
            return player

    def append(self, player: Player) -> None:
        if player in self:
            return

        super().append(player)

    def remove(self, player: Player) -> None:
        if player not in self:
            return

        super().remove(player)


class ClanList(list[Clan]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __iter__(self) -> Iterator[Clan]:
        return super().__iter__()

    def __contains__(self, clan: Union[Clan, str, int]) -> bool:
        if isinstance(clan, str):
            return clan in [name for name in self.names]
        elif isinstance(clan, int):
            return clan in [id for id in self.ids]
        else:
            return super().__contains__(clan)

    def __repr__(self) -> str:
        return f"[{', '.join(map(repr, self))}]"

    @property
    def ids(self) -> list[int]:
        return [c.id for c in self]

    @property
    def names(self) -> list[str]:
        return [c.name for c in self]

    def get(self, id: int) -> Optional[Clan]:  # XX: allow sql/kwargs?
        for clan in self:
            if clan.id == id:
                return clan

    def append(self, clan: Clan) -> None:
        if clan in self:
            return

        super().append(clan)

    def remove(self, clan: Clan) -> None:
        if clan not in self:
            return

        super().remove(clan)


class ChannelList(list[Channel]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __iter__(self) -> Iterator[Channel]:
        return super().__iter__()

    def __contains__(self, channel: Union[Channel, str, int]) -> bool:
        if isinstance(channel, str):
            return channel in [name for name in self.names]
        elif isinstance(channel, int):
            return channel in [id for id in self.ids]
        else:
            return super().__contains__(channel)

    def __repr__(self) -> str:
        return f"[{', '.join(map(repr, self))}]"

    @property
    def ids(self) -> list[int]:
        return [c.id for c in self]

    @property
    def names(self) -> list[str]:
        return [c.name for c in self]

    def get(self, name: int) -> Optional[Channel]:  # XX: allow sql/kwargs?
        for channel in self:
            if channel.name == name:
                return channel

    def append(self, channel: Channel) -> None:
        if channel in self:
            return

        super().append(channel)

    def remove(self, channel: Channel) -> None:
        if channel not in self:
            return

        super().remove(channel)


async def populate_lists() -> None:
    # XX: using multiple cursors as the plan in the future is for these to
    #     become background tasks

    bot_user = await app.state.services.database.fetch_one(
        "SELECT * FROM users WHERE id = 1",
    )
    app.state.sessions.bot = Player(**bot_user)
    app.state.sessions.bot.geoloc = Geolocation(
        country=Country.from_iso(bot_user["country"]),
    )
    app.state.sessions.players.append(app.state.sessions.bot)

    async with app.state.services.database.connection() as clan_cursor:
        clans = await clan_cursor.fetch_all("SELECT * FROM clans")

        for clan in clans:
            clan_obj = Clan(**clan)
            app.state.sessions.clans.append(clan_obj)

    async with app.state.services.database.connection() as channel_cursor:
        channels = await channel_cursor.fetch_all("SELECT * FROM channels")

        for channel in channels:
            channel_obj = Channel(**channel)
            app.state.sessions.channels.append(channel_obj)
