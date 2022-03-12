from __future__ import annotations

from app.lists import ChannelList
from app.lists import ClanList
from app.lists import PlayerList
from app.objects.player import Player

players = PlayerList()
clans = ClanList()
channels = ChannelList()

bot: Player
