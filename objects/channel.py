from objects import glob
import packets

class Channel:
    def __init__(self, **cinfo):
        self.name = cinfo.get('name')
        self.desc = cinfo.get('desc')
        self.auto = cinfo.get('auto')
        self.players: list = []

    def send(self, f, msg):
        self.enqueue(packets.sendMessage(f.name, msg, self.name, f.id))

    def add_player(self, user):
        self.players.append(user)

    @property
    def count(self):
        return len(self.players)

    def enqueue(self, b: bytes):
        for o in glob.players.values():
            o.enqueue(b)