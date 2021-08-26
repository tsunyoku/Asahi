from functools import cached_property
from typing import Callable

class Achievement:
    __slots__ = (
        '__dict__',
        'id', 'image', 'name',
        'desc', 'cond', 'custom'
    )
    def __init__(self, **kwargs) -> None:
        self.id: int = kwargs.get('id')
        self.image: str = kwargs.get('image')
        self.name: str = kwargs.get('name')
        self.desc: str = kwargs.get('desc')
        self.cond: Callable = kwargs.get('cond')
        self.custom: bool = kwargs.get('custom')

    @cached_property
    def format(self) -> str:
        return f'{self.image}+{self.name}+{self.desc}'
