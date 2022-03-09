from __future__ import annotations

from typing import Iterator
from typing import Optional
from typing import Union

import app.utils
from app.constants.privileges import Privileges
from app.objects.player import Player


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
        if player := self._get(kwargs):
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
