from enum import IntFlag

class Privileges(IntFlag):
    Normal = 1 << 0 # unbanned, even if they have verified but lack normal they are a banned user
    Verified = 1 << 1
    Supporter = 1 << 2
    Nominator = 1 << 3
    Admin = 1 << 4
    Developer = 1 << 5
    Owner = 1 << 6

    Staff = Nominator | Admin | Developer | Owner
    Manager = Admin | Developer | Owner
    Master =  Normal | Verified | Supporter | Nominator | Admin | Developer | Owner

class ClientPrivileges(IntFlag):
    Player = 1 << 0
    Moderator = 1 << 1
    Supporter = 1 << 2
    Owner = 1 << 3
    Developer = 1 << 4