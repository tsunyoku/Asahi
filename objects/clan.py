from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from objects.channel import Channel
    from objects.match import Match

class Clan:
    def __init__(self, **cinfo):
        self.id: int = cinfo.get('id', 0)
        self.name: str = cinfo.get('name', 0)
        self.tag: str = cinfo.get('tag', 0)
        self.owner: int = cinfo.get('owner', 0)
        self.chan: Channel = None
        self.members: list = []

        self.battle: Match = None