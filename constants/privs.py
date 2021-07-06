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
    
    Whitelisted = 1 << 9 # can bypass anticheat checks
    Frozen = 1 << 10

    Staff = Nominator | Admin | Developer | Owner
    Manager = Admin | Developer | Owner
    Master = Normal | Verified | Supporter | Nominator | Admin | Developer | Owner
    Disallowed = Restricted | Banned
    
def strPrivs(priv: str):
    return {
        'normal': Privileges.Normal,
        'verified': Privileges.Verified,
        'supporter': Privileges.Supporter,
        'nominator': Privileges.Nominator,
        'admin': Privileges.Admin,
        'developer': Privileges.Developer,
        'owner': Privileges.Owner,
        'restricted': Privileges.Restricted,
        'banned': Privileges.Banned,
        'whitelisted': Privileges.Whitelisted,
        'frozen': Privileges.Frozen,
        'manager': Privileges.Manager,
        'master': Privileges.Master
    }.get(priv.lower())

class ClientPrivileges(IntFlag):
    Player = 1 << 0
    Moderator = 1 << 1
    Supporter = 1 << 2
    Owner = 1 << 3
    Developer = 1 << 4