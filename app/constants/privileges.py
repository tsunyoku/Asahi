from __future__ import annotations

from enum import IntFlag


class Privileges(IntFlag):
    NORMAL = 1 << 0
    VERIFIED = 1 << 1
    SUPPORTER = 1 << 2

    NOMINATOR = 1 << 3
    ADMIN = 1 << 4
    DEVELOPER = 1 << 5
    OWNER = 1 << 6

    RESTRICTED = 1 << 7
    BANNED = 1 << 8

    BYPASS_ANTICHEAT = 1 << 9  # can bypass anticheat checks
    FROZEN = 1 << 10
    WHITELISTED = 1 << 11  # can bypass pp cap

    STAFF = NOMINATOR | ADMIN | DEVELOPER | OWNER
    MANAGER = ADMIN | DEVELOPER | OWNER
    MASTER = (
        NORMAL
        | VERIFIED
        | SUPPORTER
        | NOMINATOR
        | ADMIN
        | DEVELOPER
        | OWNER
        | BYPASS_ANTICHEAT
        | WHITELISTED
    )
    DISALLOWED = RESTRICTED | BANNED


class BanchoPrivileges(IntFlag):
    PLAYER = 1 << 0
    MODERATOR = 1 << 1
    SUPPORTER = 1 << 2
    OWNER = 1 << 3
    DEVELOPER = 1 << 4
