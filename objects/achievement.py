from functools import cached_property

class Achievement:
    def __init__(self, **ainfo):
        self.id = ainfo.get('id')
        self.image = ainfo.get('image')
        self.name = ainfo.get('name')
        self.desc = ainfo.get('desc')
        self.cond = ainfo.get('cond')
        self.custom = ainfo.get('custom')
    
    @cached_property
    def format(self):
        return f'{self.image}+{self.name}+{self.desc}'