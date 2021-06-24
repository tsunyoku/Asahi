from typing import TYPE_CHECKING

import inspect

if TYPE_CHECKING:
    from constants.privs import Privileges

class Menu:
    def __init__(self, **args):
        self.id: int = args.get('id', 0)
        self.name: str = args.get('name', '')
        self.priv: Privileges = args.get('priv', 0)

        self.callback = args.get('callback', None) # ??
        self.args = args.get('args', None)

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
        if inspect.iscoroutinefunction(c):
            if not self.args:
                if not call:
                    return await c
                else:
                    if isL:
                        return await c(player)
                    else:
                        return await c()
            else:
                if not call:
                    return await c # has args but not a function???
                else:
                    if isL:
                        return await c(player)(*self.args)
                    else:
                        return await c(*self.args)
        
        if not self.args:
            if not call:
                return c
            else:
                if isL:
                    return c(player)
                else:
                    return c()
        else:
            if not call:
                return c # has args but not a function???
            else:
                if isL:
                    return c(player)(*self.args)
                else:
                    return c(*self.args)