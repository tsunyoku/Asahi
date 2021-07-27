from objects import glob
from packets import writer

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .player import Player

class Channel:
    __slots__ = ('name', 'desc', 'auto', 'perm', 'players')
    def __init__(self, **kwargs):
        self.name: str = kwargs.get('name')
        self.desc: str = kwargs.get('desc')
        self.auto: bool = kwargs.get('auto', False)
        self.perm: bool = kwargs.get('perm', False) # whether the channel should stay
                                                    # in the global channels list even
                                                    # when all players have left
        self.players: list = []

    def send(self, f: 'Player', msg: str, send_self: bool) -> None:
        if not send_self:
            self.enqueue(writer.sendMessage(f.name, msg, self.name, f.id), ignore=f.id)
        else:
            self.enqueue(writer.sendMessage(f.name, msg, self.name, f.id))

    def add_player(self, user: 'Player') -> None:
        self.players.append(user)

    def remove_player(self, user: 'Player') -> None:
        self.players.remove(user)

        if len(self.players) == 0 and not self.perm:
            glob.channels.remove(self)

    @property
    def count(self) -> int:
        return len(self.players)

    @staticmethod
    def enqueue(b: bytes, ignore: int = 0, ignore_list: list[Player] = []) -> None:
        ignore_list.append(ignore)

        glob.players.enqueue(b, ignored=ignore_list)
