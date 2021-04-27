import config # indirect use of config

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp import ClientSession

    from cmyui import AsyncSQLPool, Version

    from packets import Packets, BanchoPacket
    from objects.player import Player

db: 'AsyncSQLPool' # type hinting
version: 'Version' # once again, type hinting
web: 'ClientSession'

packets: dict['Packets', 'BanchoPacket']

# cache some things like bcrypt for speeeeeeeeeeeeeeeeeed hours
cache = {
    'bcrypt': {}, # store bcrypt pws for speed hours
    'maps': {}, # map cache cus xd
    'unsub': [] # unsubmitted maps xd
}

players = {} # player dict | player[token] = player
players_name = {} # playername dict | player[name] = player
players_id = {} # playerid dict | player[id] = player
geoloc = {} # geoloc dict | geoloc[ip] = geoloc
channels = {} # channels dict | channel[name] = channel

bot: 'Player'
