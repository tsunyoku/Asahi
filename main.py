#!/usr/bin/env python3.9
# above is so we can use ./main.py instead

# external imports (some may require to be installed, install using ext/requirements.txt)
from xevel import Xevel # web server :blobcowboi:
from cmyui import Ansi, Version, log # import console logger (cleaner than print | ansi is for log colours), version handler and database handler
from pathlib import Path
from aiohttp import ClientSession
from discord.ext import commands
import asyncpg
import aioredis
import uvloop
import asyncio

# internal imports
from objects import glob # glob = global, server-wide objects will be stored here e.g database handler
from objects.player import Player # Player - player object to store stats, info etc.
from objects.channel import Channel # Channel - channel object to store name, desc etc.
from objects.clan import Clan
from objects.achievement import Achievement
from constants.countries import country_codes

from endpoints.assets import assets, init_customs

from objects.tasks import expired_donor, freeze_timers

app = Xevel(glob.config.socket) # handler for webserver :D
dc = commands.Bot(command_prefix=glob.config.bot_prefix)
glob.version = Version(0, 3, 2) # set Asahi version, mainly for future updater but also for tracking

AVA_PATH = Path.cwd() / 'resources/avatars'
SS_PATH = Path.cwd() / 'resources/screenshots'
R_PATH = Path.cwd() / 'resources/replays'
RRX_PATH = Path.cwd() / 'resources/replays_rx'
RAP_PATH = Path.cwd() / 'resources/replays_ap'
MAPS_PATH = Path.cwd() / 'resources/maps'
ACHIEVEMENTS_PATH = Path.cwd() / 'resources/achievements'

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

@app.before_serving()
async def connect(): # ran before server startup, used to do things like connecting to mysql :D
    log(f'==== Asahi v{glob.version} starting ====', Ansi.GREEN)

    glob.web = ClientSession() # aiohttp session for external web requests

    try:
        glob.db = await asyncpg.connect(user=glob.config.postgres['user'], password=glob.config.postgres['password'], database=glob.config.postgres['db'], host=glob.config.postgres['host']) # connect to db using config :p
        if glob.config.debug:
            log('==== Asahi connected to PostgreSQL ====', Ansi.GREEN)
    except Exception as error:
        log(f'==== Asahi failed to connect to PostgreSQL ====\n\n{error}', Ansi.LRED)

    try:
        glob.redis = await aioredis.create_redis_pool(f"redis://{glob.config.redis['host']}", db=glob.config.redis['db'], password=glob.config.redis['password'] or None)
        if glob.config.debug:
            log('==== Asahi connected to Redis ====', Ansi.GREEN)
    except Exception as error:
        log(f'==== Asahi failed to connect to Redis ====\n\n{error}', Ansi.LRED)

    if not AVA_PATH.exists():
        AVA_PATH.mkdir(parents=True)
        log('Avatars folder has been created, please set a default avatar by placing a file named "default.png" into resources/avatars!', Ansi.LRED)

    for directory in (SS_PATH, R_PATH, RRX_PATH, RAP_PATH, MAPS_PATH, ACHIEVEMENTS_PATH):
        if not directory.exists(): directory.mkdir(parents=True)

    # add bot to user cache lmao CURSED | needs to be cleaned DESPERATELY
    botinfo = await glob.db.fetchrow('SELECT name, pw, country, name FROM users WHERE id = 1')
    bot = Player(id=1, name=botinfo['name'], offset=1, country_iso=botinfo['country'], country=country_codes[botinfo['country'].upper()])
    glob.players[''] = bot
    glob.players_name[bot.name] = bot
    glob.players_id[1] = bot
    glob.bot = bot # might be useful in the future?
    if glob.config.debug:
        log(f"==== Added bot {bot.name} to player list ====", Ansi.GREEN)
        
    async with glob.db.transaction():
        async for ach in glob.db.cursor('SELECT * FROM achievements'):
            achievement = Achievement(id=ach['id'], image=ach['image'], name=ach['name'], desc=ach['descr'], cond=eval(f'lambda s: {ach["cond"]}'), custom=ach['custom'])
            glob.achievements.append(achievement)
            
    init_customs() # set custom achievements list for assets proxy

    # add all channels to cache
    async with glob.db.transaction():
        async for chan in glob.db.cursor('SELECT * FROM channels'):
            # "perm" may be confusing to some, i dont even really know how to explain it:
            # if it's true, the channel won't delete after all it's users has left
            # if it's false, the channel is deleted after all active users in the channel have left the channel
            channel = Channel(name=chan['name'], desc=chan['descr'], auto=chan['auto'], perm=chan['perm'])
            glob.channels[channel.name] = channel
            if glob.config.debug:
                log(f'==== Added channel {channel.name} to channel list ====', Ansi.GREEN)
    
    # add announce channel to cache
    announce = Channel(name='#announce', desc='#1 scores and public announcements will be posted here', auto=True, perm=True)
    glob.channels[announce.name] = announce
    if glob.config.debug:
        log(f'==== Added channel #announce to channel list ====', Ansi.GREEN)

    # add lobby channel to cache
    lobby = Channel(name='#lobby', desc='Multiplayer lobby', auto=False, perm=True)
    glob.channels[lobby.name] = lobby
    if glob.config.debug:
        log(f'==== Added channel #lobby to channel list ====', Ansi.GREEN)

    # add all clans to cache
    async with glob.db.transaction():
        async for c in glob.db.cursor('SELECT * FROM clans'):
            clan = Clan(id=c['id'], name=c['name'], tag=c['tag'], owner=c['owner'])
            clan_chan = Channel(name='#clan', desc=f'Clan chat for clan {clan.name}', auto=0, perm=1)
            clan.chan = clan_chan
            glob.clans[clan.id] = clan

            async for id in glob.db.cursor('SELECT id FROM users WHERE clan = $1', clan.id):
                clan.members.append(id['id'])

            if glob.config.debug:
                log(f'==== Added clan {clan.name} to clan list ====', Ansi.GREEN)

    log(f'==== Asahi v{glob.version} started ====', Ansi.GREEN)

@app.after_serving()
async def disconnect():
    log(f'==== Asahi v{glob.version} stopping ====', Ansi.GREEN)

    await glob.web.close()
    if glob.config.debug:
        log('==== Closed webserver ====', Ansi.GREEN)

    await glob.db.close()
    if glob.config.debug:
        log('==== Closed PostgreSQL connection ====', Ansi.GREEN)

    glob.redis.close()
    await glob.redis.wait_closed()
    if glob.config.debug:
        log('==== Closed Redis connection ====', Ansi.GREEN)

    await dc.close()
    if glob.config.debug:
        log('==== Asahi Discord bot stopped ====', Ansi.GREEN)

    log(f'==== Asahi v{glob.version} stopped ====', Ansi.GREEN)

from endpoints.bancho import bancho
from endpoints.avatars import avatars
from endpoints.web import web
from endpoints.api import api
app.add_router(bancho)
app.add_router(avatars)
app.add_router(web)
app.add_router(api)
app.add_router(assets)

if __name__ == '__main__':
    dc.load_extension('disc.bot')
    app.add_task((dc.start, glob.config.token))
    app.add_task(expired_donor)
    app.add_task(freeze_timers)
    app.start()
