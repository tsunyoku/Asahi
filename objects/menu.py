from typing import TYPE_CHECKING, Union, Coroutine, Optional
from . import glob

import inspect

if TYPE_CHECKING:
    from constants.privs import Privileges

class Menu:
    def __init__(self, **args):
        self.id: int = args.get('id', 0)
        self.name: str = args.get('name', '')
        self.priv: Privileges = args.get('priv', 0)

        self.callback: Union[Coroutine, eval] = args.get('callback') # ??
        self.args: Optional[list] = args.get('args')
        
        self.destroy: bool = args.get('destroy', False) # one-time usage

    @property
    def embed(self) -> str:
        return f'[osump://{self.id}/ {self.name}]'

    async def handle(self, player): # ok i definitely need to fix this one day
        # user has clicked on menu, we now return the callback
        
        if self.destroy:
            del glob.menus[self.id] # remove object from known list if its a one-time use 

        if not (c := self.callback):
            return

        call = callable(c)
        isL = c.__name__ == '<lambda>'

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
