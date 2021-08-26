#!/usr/bin/env python3.9

from xevel import Xevel
from cmyui.logging import Ansi, log
from cmyui.version import Version
from pathlib import Path
from aiohttp import ClientSession
from discord.ext import commands
from fatFuckSQL import fatFawkSQL
import aioredis
import asyncio
import plazy

# internal imports
from objects import glob # global objects
from objects.player import Player
from objects.channel import Channel
from objects.clan import Clan
from objects.achievement import Achievement
from constants.countries import country_codes
from lists.players import PlayerList

from endpoints.assets import assets, init_customs

from objects.tasks import expired_donor, freeze_timers, prepare_tasks

glob.version = Version(0, 4, 2) # TODO: autoupdater using this

app = Xevel(glob.config.socket, loop=asyncio.get_event_loop(), gzip=4) # webserver
dc = commands.Bot(command_prefix=glob.config.bot_prefix)

AVA_PATH = Path.cwd() / 'resources/avatars'
SS_PATH = Path.cwd() / 'resources/screenshots'
R_PATH = Path.cwd() / 'resources/replays'
RRX_PATH = Path.cwd() / 'resources/replays_rx'
RAP_PATH = Path.cwd() / 'resources/replays_ap'
MAPS_PATH = Path.cwd() / 'resources/maps'
ACHIEVEMENTS_PATH = Path.cwd() / 'resources/achievements'

''' TODO: currently breaks due to subprocess, may be re-enabled in the future.
import uvloop
asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
'''

@app.before_serving()
async def connect() -> None: # ran before server startup, used to do things like connecting to mysql :D
    log(f'==== Asahi v{glob.version} starting ====', Ansi.GREEN)

    glob.web = ClientSession() # aiohttp session for external web requests
    glob.players = PlayerList() # init player list

    try:
        glob.db = await fatFawkSQL.connect(**glob.config.sql) # connect to db using config :p
        if glob.config.debug:
            log('==== Asahi connected to MySQL ====', Ansi.GREEN)
    except Exception as error:
        log(f'==== Asahi failed to connect to MySQL ====\n\n{error}', Ansi.LRED)

    try:
        glob.redis = await aioredis.create_redis_pool(
            f"redis://{glob.config.redis['host']}",
            db=glob.config.redis['db'],
            password=glob.config.redis['password'] or None
        )
        if glob.config.debug:
            log('==== Asahi connected to Redis ====', Ansi.GREEN)
    except Exception as error:
        log(f'==== Asahi failed to connect to Redis ====\n\n{error}', Ansi.LRED)

    if not AVA_PATH.exists():
        AVA_PATH.mkdir(parents=True)
        log('Avatars folder has been created, please set a default avatar by placing a file named "default.png" into resources/avatars!', Ansi.LRED)

    for directory in (SS_PATH, R_PATH, RRX_PATH, RAP_PATH,
                      MAPS_PATH, ACHIEVEMENTS_PATH):
        if not directory.exists(): directory.mkdir(parents=True)

    botinfo = await glob.db.fetchrow('SELECT name, pw, country, name FROM users WHERE id = 1')
    glob.bot = Player(
        id=1,
        name=botinfo['name'],
        offset=1,
        country_iso=botinfo['country'],
        country=country_codes[botinfo['country'].upper()]
    )
    await glob.bot.set_stats()
    glob.players.append(glob.bot)

    if glob.config.debug:
        log(f"==== Added bot {glob.bot.name} to player list ====", Ansi.GREEN)

    async for clan_row in glob.db.iter('SELECT * FROM achievements'):
        clan_row['cond'] = eval(f'lambda s: {clan_row["cond"]}')
        clan_row['desc'] = clan_row.pop('descr') # TODO: fix in sql
        glob.achievements.append(Achievement(**clan_row))

    init_customs() # set custom achievements list for assets proxy

    # add all channels to cache
    async for clan_row in glob.db.iter('SELECT * FROM channels'):
        clan_row['desc'] = clan_row.pop('descr') # TODO: fix in sql
        channel = Channel(**clan_row)

        glob.channels[channel.name] = channel
        if glob.config.debug:
            log(f'==== Added channel {channel.name} to channel list ====', Ansi.GREEN)

    # add announce channel to cache
    announce = Channel(
        name='#announce',
        desc='#1 scores and public announcements will be posted here',
        auto=True,
        perm=True
    )
    glob.channels[announce.name] = announce

    if glob.config.debug:
        log('==== Added channel #announce to channel list ====', Ansi.GREEN)

    # add lobby channel to cache
    lobby = Channel(
        name='#lobby',
        desc='Multiplayer lobby',
        auto=False,
        perm=True
    )
    glob.channels[lobby.name] = lobby

    if glob.config.debug:
        log('==== Added channel #lobby to channel list ====', Ansi.GREEN)

    # add all clans to cache
    async for clan_row in glob.db.iter('SELECT * FROM clans'):
        clan = Clan(**clan_row)
        clan_chan = Channel(
            name='#clan',
            desc=f'Clan chat for clan {clan.name}',
            auto=False,
            perm=True
        )
        clan.chan = clan_chan # uwu
        glob.clans[clan.id] = clan
        clan.country = await glob.db.fetchval('SELECT country FROM users WHERE id = %s', [clan.owner])

        async for member_row in glob.db.iter('SELECT id FROM users WHERE clan = %s', [clan.id]):
            clan.members.append(member_row['id'])

        await glob.redis.zadd(f'asahi:clan_leaderboard', clan.score, clan.id)
        await glob.redis.zadd(f'asahi:clan_leaderboard:{clan.country}', clan.score, clan.id)

        r = await glob.redis.zrevrank(f'asahi:clan_leaderboard', clan.id)
        cr = await glob.redis.zrevrank(f'asahi:clan_leaderboard:{clan.country}', clan.id)

        if r is None:
            if clan.score > 0: clan.rank = 1
        else: clan.rank = r + 1
    
        if cr is None:
            if clan.score > 0: clan.country_rank = 1
        else:
            clan.country_rank = cr + 1

        if glob.config.debug:
            log(f'==== Added clan {clan.name} to clan list ====', Ansi.GREEN)

    await prepare_tasks() # make new db conn for donor/freeze tasks

    log(f'==== Asahi v{glob.version} started ====', Ansi.GREEN)

@app.after_serving()
async def disconnect() -> None:
    log(f'==== Asahi v{glob.version} stopping ====', Ansi.GREEN)

    await glob.web.close()

    await glob.db.close()
    if glob.config.debug:
        log('==== Closed MySQL connection ====', Ansi.GREEN)

    glob.redis.close()
    await glob.redis.wait_closed()
    if glob.config.debug:
        log('==== Closed Redis connection ====', Ansi.GREEN)

    bot = dc.cogs['asahiBot']
    await bot.end_tasks()

    await dc.close()
    if glob.config.debug:
        log('==== Asahi Discord bot stopped ====', Ansi.GREEN)

    log(f'==== Asahi v{glob.version} stopped ====', Ansi.GREEN)

def load_discord_cogs() -> None:
    files = plazy.list_files(
        root='disc',
        filter_func=lambda x: x.endswith('.py'),
        is_include_root=True
    )

    for file in files:
        cog_name = file.replace('/', '.')
        dc.load_extension(cog_name[:-3])

if __name__ == '__main__':
    load_discord_cogs()

    # add domains (with their respective endpoints)
    from endpoints.bancho import bancho
    from endpoints.avatars import avatars
    from endpoints.web import web
    from endpoints.api import api
    app.add_router(bancho)
    app.add_router(avatars)
    app.add_router(web)
    app.add_router(api)
    app.add_router(assets)

    # add tasks to run @ startup
    app.add_task((dc.start, glob.config.token))
    app.add_task(expired_donor)
    app.add_task(freeze_timers)

    app.start()
