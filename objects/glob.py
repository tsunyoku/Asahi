import config # indirect use of config

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from cmyui import Version
    from objects.player import Player

    from fatFuckSQL import fatFawkSQL
    import aioredis

db: 'fatFawkSQL.connect' # type hinting
version: 'Version' # once again, type hinting
web: 'ClientSession'
redis: 'aioredis.create_redis_pool'

packets = {}
packets_restricted = {} # packet dict for packets that restricted players *can* use

# cache some things like pws for speeeeeeeeeeeeeeeeeed hours
cache = {
    'pw': {}, # store encrypted pws for speed hours
    'maps': {}, # map cache cus xd
    'unsub': [], # unsubmitted maps xd
    'vers': {},
    'latest_ver': {}
}

# TODO: player list collection
players = {} # player dict | player[token] = player
players_name = {} # playername dict | player[name] = player
players_id = {} # playerid dict | player[id] = player

geoloc = {} # geoloc dict | geoloc[ip] = geoloc
channels = {} # channels dict | channel[name] = channel
matches = {} # matches dict | matches[id] = match
clans = {} # clans dict | clan[id] = clan
clan_battles = {} # clan battles dict | clan_battle[clan1/clan2] = dict of info
menus = {} # ingame menus dict | menu[id] = menu
achievements = []

bot: 'Player'
