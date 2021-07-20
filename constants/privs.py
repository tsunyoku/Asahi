from enum import IntFlag

class Privileges(IntFlag):
    Normal = 1 << 0
    Verified = 1 << 1
    Supporter = 1 << 2

    Nominator = 1 << 3
    Admin = 1 << 4
    Developer = 1 << 5
    Owner = 1 << 6
    
    # i'm making banned/restricted privileges separately because the system of removing normal really confuses me to this day
    Restricted = 1 << 7
    Banned = 1 << 8
    
    BypassAnticheat = 1 << 9 # can bypass anticheat checks
    Frozen = 1 << 10
    Whitelisted = 1 << 11 # can bypass pp cap

    Staff = Nominator | Admin | Developer | Owner
    Manager = Admin | Developer | Owner
    Master = Normal | Verified | Supporter | Nominator | Admin | Developer | Owner | BypassAnticheat | Whitelisted
    Disallowed = Restricted | Banned
    
    @classmethod
    def get(self, name):
        if name in self.__members__:
            return self[name]
        else:
            return None

class ClientPrivileges(IntFlag):
    Player = 1 << 0
    Moderator = 1 << 1
    Supporter = 1 << 2
    Owner = 1 << 3
    Developer = 1 << 4