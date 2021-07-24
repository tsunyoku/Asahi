from functools import cached_property

class Achievement:
    def __init__(self, **ainfo):
        self.id: int = ainfo.get('id')
        self.image: str = ainfo.get('image')
        self.name: str = ainfo.get('name')
        self.desc: str = ainfo.get('desc')
        self.cond: eval = ainfo.get('cond')
        self.custom: bool = ainfo.get('custom')

    @cached_property
    def format(self):
        return f'{self.image}+{self.name}+{self.desc}'
