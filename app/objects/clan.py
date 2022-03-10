from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

import databases.core

if TYPE_CHECKING:
    from app.objects.player import Player


class Clan:
    def __init__(
        self,
        id: int,
        name: str,
        tag: str,
        created_at: int,
        owner: int,
        members: list[int] = [],
    ) -> None:
        self.id = id
        self.name = name
        self.tag = tag
        self.created_at = created_at
        self.owner = owner

        self.members = members

    @cache
    def __repr__(self) -> str:
        return f"[{self.tag}] {self.name}"

    async def add_member(self, player: "Player") -> None:
        ...

    async def remove_member(self, player: "Player") -> None:
        ...

    async def get_members(self, db_conn: databases.core.Connection) -> None:
        ...
