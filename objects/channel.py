from objects import glob
import packets

class Channel:
    def __init__(self, **cinfo):
        self.name = cinfo.get('name')
        self.desc = cinfo.get('desc')
        self.auto = cinfo.get('auto', False)
        self.un = cinfo.get('un', False)
        self.players: list = []

    def send(self, f, msg):
        self.enqueue(packets.sendMessage(f.name, msg, self.name, f.id), f.id)

    def add_player(self, user):
        self.players.append(user)

    def remove_player(self, user):
        self.players.remove(user)

        if len(self.players) == 0 and self.un:
            glob.channels.remove(self)

    @property
    def count(self):
        return len(self.players)

    def enqueue(self, b: bytes, ignore: int):
        for o in glob.players.values():
            if o.id != ignore:
                o.enqueue(b)