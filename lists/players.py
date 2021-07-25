from objects.player import Player
from constants.privs import Privileges

from typing import Iterator, Optional

class PlayerList(list[Player]):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __iter__(self) -> Iterator[Player]:
        return super().__iter__()

    def __contains__(self, user: Player) -> bool:
        if isinstance(user, str):
            return user in [p.name for p in self]
        else:
            return super().__contains__(user)

    # not sure when i'll use these 2 but sure
    @property
    def user_ids(self) -> list[int]:
        return [u.id for u in self]

    @property
    def user_names(self) -> list[str]:
        return [u.name for u in self]

    @property
    def restricted_users(self) -> list[Player]:
        return [u for u in self if u.priv & Privileges.Restricted]

    @property
    def unrestricted_users(self) -> list[Player]:
        return [u for u in self if not u.priv & Privileges.Restricted]

    def enqueue(self, data: bytes, ignored: list[Player] = []) -> None:
        for u in self:
            if u not in ignored:
                u.enqueue(data)

    async def get(self, **kwargs) -> Optional[Player]: # lord this is spaghetti
        for _type in ('id', 'name', 'token', 'discord'):
            if (user := kwargs.pop(_type, None)):
                utype = _type
                break
        else:
            return

        for u in self:
            if getattr(u, utype) == user:
                return u
        else:
            if kwargs.get('sql') and utype != 'token':
                return await Player.from_sql(user, True)

    async def find_login(self, name: str, pw: str) -> Optional[Player]:
        user = await self.get(name=name)

        if user and user.pw == pw:
            return user

    def append(self, user: Player) -> None:
        if user not in self:
            super().append(user)

    def remove(self, user: Player) -> None:
        if user in self:
            super().remove(user)
