from typing import TYPE_CHECKING

import config  # indirect use of config

if TYPE_CHECKING:
    from aiohttp import ClientSession
    from cmyui.version import Version
    from objects.player import Player
    from lists.players import PlayerList

    from fatFuckSQL import fatFawkSQL
    from aioredis import Redis

db: "fatFawkSQL"  # type hinting
version: "Version"  # once again, type hinting
web: "ClientSession"
redis: "Redis"

packets = {}
packets_restricted = {}  # packet dict for packets that restricted players *can* use

# cache some things like pws for speeeeeeeeeeeeeeeeeed hours
cache = {
    "pw": {},  # store encrypted pws for speed hours
    "maps": {},  # map cache cus xd
    "unsub": [],  # unsubmitted maps xd
    "vers": {},
    "latest_ver": {},
}

players: "PlayerList"  # player list

geoloc = {}  # geoloc dict | geoloc[ip] = geoloc
channels = {}  # channels dict | channel[name] = channel
matches = {}  # matches dict | matches[id] = match
clans = {}  # clans dict | clan[id] = clan
clan_battles = {}  # clan battles dict | clan_battle[clan1/clan2] = dict of info
menus = {}  # ingame menus dict | menu[id] = menu
achievements = []

codes = {}  # memory-cache list of verification codes for discord linking

bot: "Player"
