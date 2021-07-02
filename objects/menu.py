from typing import TYPE_CHECKING, Union, Coroutine, Optional

import inspect

if TYPE_CHECKING:
    from constants.privs import Privileges

class Menu:
    def __init__(self, **args):
        self.id: int = args.get('id', 0)
        self.name: str = args.get('name', '')
        self.priv: Privileges = args.get('priv', 0)

        self.callback: Union[Coroutine, eval] = args.get('callback', None) # ??
        self.args: Optional[list] = args.get('args', None)

    @property
    def embed(self):
        return f'[osump://{self.id}/ {self.name}]'

    async def handle(self, player):
        # user has clicked on menu, we now return the callback

        if not (c := self.callback):
            return

        call = callable(c)
        isL = isinstance(c, type(lambda:0))
        
        # FUCK ME I AM GOING TO HELL FOR EVERYTHING HERE
        # ^^^ Old code but it has been cleaned by len4ee xd
        if inspect.iscoroutinefunction(c):
            if not self.args:
                if not call: return await c
                if not isL: return await c()

                return await c(player)

            if not call: return await c # has args but not a function???
            if not isL: return await c(*self.args)

            return await c(player)(*self.args)

        if not self.args:
            if not call: return c
            if not isL: return c()

            return c(player)

        if not call: return c # has args but not a function???
        if not isL: return c(*self.args)

        return c(player)(*self.args)
