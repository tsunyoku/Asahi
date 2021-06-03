from objects import glob
import packets

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.player import Player

class Channel:
    def __init__(self, **cinfo):
        self.name = cinfo.get('name')
        self.desc = cinfo.get('desc')
        self.auto = cinfo.get('auto', False)
        self.perm = cinfo.get('perm', False)
        self.players: list = []

    def send(self, f: 'Player', msg: str, send_self: bool):
        if not send_self:
            self.enqueue(packets.sendMessage(f.name, msg, self.name, f.id), ignore=f.id)
        else:
            self.enqueue(packets.sendMessage(f.name, msg, self.name, ignore=f.id))

    def add_player(self, user: 'Player'):
        self.players.append(user)

    def remove_player(self, user: 'Player'):
        self.players.remove(user)

        if len(self.players) == 0 and not self.perm:
            glob.channels.remove(self)

    @property
    def count(self):
        return len(self.players)

    def enqueue(self, b: bytes, ignore: int = 0, ignore_list: list = []):
        for o in glob.players.values():
            if o.id != ignore:
                if ignore_list:
                    if o.id not in ignore_list:
                        o.enqueue(b)
                else:
                    o.enqueue(b)
