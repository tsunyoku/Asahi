from typing import TYPE_CHECKING
from typing import Optional

if TYPE_CHECKING:
    from .channel import Channel
    from .match import Match

class Clan:
    __slots__ = ('id', 'name', 'tag', 'owner', 'chan', 'members')
    def __init__(self, **kwargs) -> None:
        self.id: int = kwargs.get('id', 0)
        self.name: str = kwargs.get('name', 0)
        self.tag: str = kwargs.get('tag', 0)
        self.owner: int = kwargs.get('owner', 0)
        self.chan: Optional[Channel] = None
        self.members: list = []

        self.battle: Match = None
