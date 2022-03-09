from __future__ import annotations

from enum import IntEnum

from app.utils import escape_enum
from app.utils import pymysql_encode


@pymysql_encode(escape_enum)
class Action(IntEnum):
    IDLE = 0
    AFK = 1
    PLAYING = 2
    EDITING = 3
    MODDING = 4
    MULTIPLAYER = 5
    WATCHING = 6
    UNKNOWN = 7
    TESTING = 8
    SUBMITTING = 9
    PAUSED = 10
    LOBBY = 11
    MULTIPLAYING = 12
    OSUDIRECT = 13
