from objects.player import Player
from constants.privs import Privileges

class PlayerList(list[Player]):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
    def __iter__(self):
        return super().__iter__()
    
    def __contains__(self, user):
        if isinstance(user, str):
            return user in [p.name for p in self]
        else:
            return super().__contains__(user)
        
    @property
    def user_ids(self):
        return [u.id for u in self]
    
    @property
    def restricted_users(self):
        return [u for u in self if u.priv & Privileges.Restricted]
    
    def enqueue(self, packets, ignored = []):
        for u in self:
            if u not in ignored:
                u.enqueue(packets)
                
    async def get(self, **kwargs): # lord this is spaghetti
        for _type in ('id', 'name', 'token'):
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
                return await Player.from_sql(user)
            
    async def find_login(self, name, pw):
        if not (user := await self.get(name=name)):
            return
        
        if user.pw == pw:
            return user
        
    def append(self, user):
        if user in self:
            return
        
        super().append(user)
        
    def remove(self, user):
        if user not in self:
            return
        
        super().remove(user)