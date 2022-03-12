from __future__ import annotations

from functools import cache
from typing import TYPE_CHECKING

from app.constants.privileges import Privileges

if TYPE_CHECKING:
    from app.objects.player import Player


class Channel:
    def __init__(
        self,
        name: str,
        topic: str,
        priv: Privileges = Privileges.NORMAL,
        auto_join: bool = True,
        instance: bool = False,
    ) -> None:
        self.name = name
        self.topic = topic
        self.priv = priv
        self.auto_join = auto_join
        self.instance = instance

        self.players: list[Player] = []

    def __repr__(self) -> str:
        return f"<{self.name}>"

    @property
    def player_count(self) -> int:
        return len(self.players)

    def __contains__(self, player: Player) -> bool:
        return player in self.players

    def has_permission(self, priv: Privileges) -> bool:
        if not self.priv:
            return True

        return priv & self.priv != 0

    def add_player(self, player: Player) -> None:
        if player in self:
            return  # ?

        self.players.append(player)

    def remove_player(self, player: Player) -> None:
        if player not in self:
            return  # ?

        self.players.remove(player)

    def send(self, msg: str, sender: Player, to_self: bool = False) -> None:
        if not self.has_permission(sender.priv):
            return

        ...

    def selective_send(
        self,
        msg: str,
        sender: Player,
        recipients: list[Player],
    ) -> None:
        if not self.has_permission(sender.priv):
            return

        ...

    def enqueue(self, data: bytes, immune: list[int] = []) -> None:
        ...
