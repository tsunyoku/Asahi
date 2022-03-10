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
        read_priv: Privileges = Privileges.NORMAL,
        write_priv: Privileges = Privileges.NORMAL,
        auto_join: bool = True,
        instance: bool = False,
    ) -> None:
        self.name = name
        self.topic = topic
        self.read_priv = read_priv
        self.write_priv = write_priv
        self.auto_join = auto_join
        self.instance = instance

        self.players: list[Player] = []

    @cache
    def __repr__(self) -> str:
        return f"<{self.name}>"

    @property
    def player_count(self) -> int:
        return len(self.players)

    def __contains__(self, player: Player) -> bool:
        return player in self.players

    def can_read(self, priv: Privileges) -> bool:
        if not self.read_priv:
            return True

        return priv & self.read_priv != 0

    def can_write(self, priv: Privileges) -> bool:
        if not self.write_priv:
            return True

        return priv & self.write_priv != 0

    def add_player(self, player: Player) -> None:
        if player in self:
            return  # ?

        self.players.append(player)

    def remove_player(self, player: Player) -> None:
        if player not in self:
            return  # ?

        self.players.remove(player)

    def send(self, msg: str, sender: Player, to_self: bool = False) -> None:
        if not self.can_write(sender.priv):
            return

        ...

    def selective_send(
        self,
        msg: str,
        sender: Player,
        recipients: list[Player],
    ) -> None:
        if not self.can_write(sender.priv):
            return

        ...

    def enqueue(self, data: bytes, immune: list[int] = []) -> None:
        ...
