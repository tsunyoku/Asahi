#!/usr/bin/env python3.9
# above is so we can use ./main.py instead

# external imports (some may require to be installed, install using ext/requirements.txt)
from quart import Quart, request # web server :blobcowboi:
from cmyui import Ansi, Version, log # import console logger (cleaner than print | ansi is for log colours), version handler and database handler
from pathlib import Path
from aiohttp import ClientSession
from discord.ext import commands
from hypercorn.asyncio import serve
from hypercorn.config import Config
import asyncpg
import aioredis

# internal imports
from objects import glob # glob = global, server-wide objects will be stored here e.g database handler
from objects.player import Player # Player - player object to store stats, info etc.
from objects.channel import Channel # Channel - channel object to store name, desc etc.
from objects.clan import Clan
from constants.countries import country_codes

app = Quart(__name__) # handler for webserver :D
app.config['SERVER_NAME'] = glob.config.domain

config = Config()
config.bind = [f"unix:{glob.config.socket}"]
config.loglevel = 'error'

dc = commands.Bot(command_prefix=glob.config.bot_prefix)

glob.version = Version(0, 2, 5) # set Asahi version, mainly for future updater but also for tracking

AVA_PATH = Path.cwd() / 'resources/avatars'
SS_PATH = Path.cwd() / 'resources/screenshots'

R_PATH = Path.cwd() / 'resources/replays'
RRX_PATH = Path.cwd() / 'resources/replays_rx'
RAP_PATH = Path.cwd() / 'resources/replays_ap'

MAPS_PATH = Path.cwd() / 'resources/maps'

@app.before_serving
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
        if glob.config.redis['password'] != '':
            glob.redis = await aioredis.create_redis_pool(f"redis://{glob.config.redis['host']}", db=glob.config.redis['db'], password=glob.config.redis['password'])
        else:
            glob.redis = await aioredis.create_redis_pool(f"redis://{glob.config.redis['host']}", db=glob.config.redis['db'])

        if glob.config.debug:
            log('==== Asahi connected to Redis ====', Ansi.GREEN)
    except Exception as error:
        log(f'==== Asahi failed to connect to Redis ====\n\n{error}', Ansi.LRED)

    if not AVA_PATH.exists():
        AVA_PATH.mkdir(parents=True)
        log('Avatars folder has been created, please set a default avatar by placing a file named "default.png" into resources/avatars!', Ansi.LRED)

    if not SS_PATH.exists():
        SS_PATH.mkdir(parents=True)

    if not R_PATH.exists():
        R_PATH.mkdir(parents=True)

    if not RRX_PATH.exists():
        RRX_PATH.mkdir(parents=True)
    
    if not RAP_PATH.exists():
        RAP_PATH.mkdir(parents=True)

    if not MAPS_PATH.exists():
        MAPS_PATH.mkdir(parents=True)

    # add bot to user cache lmao CURSED | needs to be cleaned DESPERATELY
    botinfo = await glob.db.fetchrow('SELECT name, pw, country, name FROM users WHERE id = 1')
    bot = Player(id=1, name=botinfo['name'], offset=1, country_iso=botinfo['country'], country=country_codes[botinfo['country'].upper()])
    glob.players[''] = bot
    glob.players_name[bot.name] = bot
    glob.players_id[1] = bot
    glob.bot = bot # might be useful in the future?
    if glob.config.debug:
        log(f"==== Added bot {bot.name} to player list ====", Ansi.GREEN)

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

@app.after_serving
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
app.register_blueprint(bancho, subdomain='c')
app.register_blueprint(bancho, subdomain='ce')
app.register_blueprint(bancho, subdomain='c4')
app.register_blueprint(avatars, subdomain='a')
app.register_blueprint(web, subdomain='osu')
app.register_blueprint(api, subdomain='api')

if __name__ == '__main__':
    dc.loop.create_task(serve(app, config))
    dc.load_extension('disc.bot')
    dc.run(glob.config.token)
