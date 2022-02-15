from functools import cached_property
from typing import Callable
from typing import Optional


class Achievement:
    __slots__ = ("__dict__", "id", "image", "name", "desc", "cond", "custom")

    def __init__(self, **kwargs) -> None:
        self.id: Optional[int] = kwargs.get("id")
        self.image: Optional[str] = kwargs.get("image")
        self.name: Optional[str] = kwargs.get("name")
        self.desc: Optional[str] = kwargs.get("desc")
        self.cond: Callable = kwargs.get("cond", None)
        self.custom: bool = kwargs.get("custom", False)

    @cached_property
    def format(self) -> str:
        return f"{self.image}+{self.name}+{self.desc}"
