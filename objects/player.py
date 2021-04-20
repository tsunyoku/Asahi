from objects import glob
import queue
import packets

class Player:
    def __init__(self, **uinfo):
        self.id: int = uinfo.get('id')
        self.name: str = uinfo.get('name')
        self.token: str = uinfo.get('token', '') # we will set default token in case of bot which won't have a token provided
        self.offset: int = uinfo.get('offset')
        self.login_time: int = uinfo.get('login_time')
        self.is_bot: bool = uinfo.get('is_bot', False)
        self.country_iso: str = uinfo.get('country_iso')
        self.country: int = uinfo.get('country')
        self.loc: list[float, float] = uinfo.get('loc', [0.0, 0.0]) # store as list cus y not (long, lat)
        self.queue = queue.SimpleQueue()
        self.action: int = 0
        self.info: str = ''
        self.map_md5: str = ''
        self.mods = int = 0
        self.mode: int = 0
        self.map_id: int = 0

    @classmethod
    def login(self, user):
        p = self(
            id=user['id'], 
            name=user['name'], 
            token=user['token'], 
            offset=user['offset'], 
            login_time=user['ltime'],
            country_iso=user['country_iso'],
            country=user['country'],
            loc=[user['lon'], user['lat']]
        )

        return p

    def logout(self):
        glob.players.pop(self.token)
        self.token = ''
        glob.players_name.pop(self.name)
        for o in glob.players.values():
            o.enqueue(packets.logout(self.id))

    def enqueue(self, b: bytes):
        self.queue.put_nowait(b)

    def dequeue(self):
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            pass

    def queue_empty(self):
        return self.queue.empty()
