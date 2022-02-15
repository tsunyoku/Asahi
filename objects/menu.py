import asyncio
from typing import Callable
from typing import Optional
from typing import TYPE_CHECKING

from . import glob

if TYPE_CHECKING:
    from constants.privs import Privileges


class Menu:
    def __init__(self, **kwargs) -> None:
        self.id: int = kwargs.get("id", 0)
        self.name: Optional[str] = kwargs.get("name")
        self.priv: Privileges = kwargs.get("priv", 0)

        self.callback: Callable = kwargs.get("callback", None)

        self.destroy: bool = kwargs.get("destroy", False)  # one-time usage

    @property
    def embed(self) -> str:
        return f"[osump://{self.id}/ {self.name}]"

    async def handle(
        self,
        player,
    ) -> object:  # ok i definitely need to fix this one day
        # user has clicked on menu, we now return the callback

        if self.destroy:
            del glob.menus[
                self.id
            ]  # remove object from known list if its a one-time use

        if not (c := self.callback):
            return

        if asyncio.iscoroutinefunction(c):
            return await c(player)
        else:
            return c(player)
