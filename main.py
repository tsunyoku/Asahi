#!/usr/bin/env python3.9
import traceback

import aioredis
import plazy
from aiohttp import ClientSession
from cmyui.version import Version
from discord.ext import commands
from fatFuckSQL import fatFawkSQL
from xevel import Xevel

from constants.countries import country_codes
from endpoints.assets import assets
from endpoints.assets import init_customs
from objects import glob  # global objects
from objects.achievement import Achievement
from objects.clan import Clan
from objects.tasks import expired_donor
from objects.tasks import freeze_timers
from objects.tasks import prepare_tasks
from utils import housekeeping
from utils.logging import debug
from utils.logging import error
from utils.logging import info

glob.version = Version(0, 4, 2)  # TODO: autoupdater using this

app = Xevel(glob.config.socket, gzip=4)  # webserver
dc = commands.Bot(command_prefix=glob.config.bot_prefix)


@app.before_serving()
async def connect() -> None:  # ran before server startup, used to do things like connecting to mysql :D
    info(f"Asahi v{glob.version} starting")

    glob.web = ClientSession()  # aiohttp session for external web requests

    from lists.players import PlayerList

    glob.players = PlayerList()  # init player list

    try:
        glob.db = await fatFawkSQL.connect(
            **glob.config.sql
        )  # connect to db using config :p
        debug("Asahi connected to MySQL")
    except Exception:
        error(f"Asahi failed to connect to MySQL\n\n{traceback.format_exc()}")
        raise SystemExit(1)

    try:
        glob.redis = await aioredis.create_redis_pool(
            f"redis://{glob.config.redis['host']}",
            db=glob.config.redis["db"],
            password=glob.config.redis["password"] or None,
        )
        debug("Asahi connected to Redis")
    except Exception:
        error(f"Asahi failed to connect to Redis\n\n{traceback.format_exc()}")
        raise SystemExit(1)

    from objects.player import Player

    botinfo = await glob.db.fetchrow(
        "SELECT name, pw, country, name FROM users WHERE id = 1",
    )

    if not botinfo:
        error(
            "Bot account not found. "
            "Please insert the bot account with user ID 1 and start Asahi again"
        )

        raise SystemExit(1)

    glob.bot = Player(
        id=1,
        name=botinfo["name"],
        offset=1,
        country_iso=botinfo["country"],
        country=country_codes[botinfo["country"].upper()],
    )
    await glob.bot.set_stats()
    glob.players.append(glob.bot)

    debug(f"Added bot {glob.bot.name} to player list")

    async for ach_row in glob.db.iter("SELECT * FROM achievements"):
        ach_row["cond"] = eval(f'lambda s: {ach_row["cond"]}')
        ach_row["desc"] = ach_row.pop("descr")
        glob.achievements.append(Achievement(**ach_row))

    init_customs()  # set custom achievements list for assets proxy

    # add all channels to cache
    from objects.channel import Channel

    async for chan_row in glob.db.iter("SELECT * FROM channels"):
        chan_row["desc"] = chan_row.pop("descr")
        channel = Channel(**chan_row)

        glob.channels[channel.name] = channel
        debug(f"Added channel {channel.name} to channel list")

    # add announce channel to cache
    announce = Channel(
        name="#announce",
        desc="#1 scores and public announcements will be posted here",
        auto=True,
        perm=True,
    )
    glob.channels[announce.name] = announce

    debug("Added channel #announce to channel list")

    # add lobby channel to cache
    lobby = Channel(name="#lobby", desc="Multiplayer lobby", auto=False, perm=True)
    glob.channels[lobby.name] = lobby

    debug("Added channel #lobby to channel list")

    # add all clans to cache
    async for clan_row in glob.db.iter("SELECT * FROM clans"):
        clan = Clan(**clan_row)
        clan_chan = Channel(
            name="#clan",
            desc=f"Clan chat for clan {clan.name}",
            auto=False,
            perm=True,
        )
        clan.chan = clan_chan  # uwu
        glob.clans[clan.id] = clan
        clan.country = await glob.db.fetchval(
            "SELECT country FROM users WHERE id = %s",
            [clan.owner],
        )

        async for member_row in glob.db.iter(
            "SELECT id FROM users WHERE clan = %s",
            [clan.id],
        ):
            clan.members.append(member_row["id"])

        await glob.redis.zadd(f"asahi:clan_leaderboard", clan.score, clan.id)
        await glob.redis.zadd(
            f"asahi:clan_leaderboard:{clan.country}",
            clan.score,
            clan.id,
        )

        r = await glob.redis.zrevrank(f"asahi:clan_leaderboard", clan.id)
        cr = await glob.redis.zrevrank(
            f"asahi:clan_leaderboard:{clan.country}",
            clan.id,
        )

        clan.rank = r + 1 if r else 0
        clan.country_rank = cr + 1 if cr else 0

        debug(f"Added clan {clan.name} to clan list")

    await prepare_tasks()  # make new db conn for donor/freeze tasks
    app.add_task(expired_donor)
    app.add_task(freeze_timers)

    info(f"Asahi v{glob.version} started")


@app.after_serving()
async def disconnect() -> None:
    info(f"Asahi v{glob.version} stopping")

    await glob.web.close()

    await glob.db.close()
    debug("Closed MySQL connection")

    glob.redis.close()
    await glob.redis.wait_closed()
    debug("Closed Redis connection")

    if glob.config.token:
        bot = dc.cogs["asahiBot"]
        await bot.end_tasks()
        await dc.close()

        debug("Asahi Discord bot stopped")

    info(f"Asahi v{glob.version} stopped")


def load_discord_cogs() -> None:
    files = plazy.list_files(
        root="disc",
        filter_func=lambda x: x.endswith(".py"),
        is_include_root=True,
    )

    for file in files:
        cog_name = file.replace("/", ".")
        dc.load_extension(cog_name[:-3])


if __name__ == "__main__":
    try:
        import uvloop

        uvloop.install()
    except ImportError:
        pass

    for safety_check in (
        housekeeping.ensure_posix,
        housekeeping.ensure_services,
        housekeeping.ensure_resources,
        housekeeping.ensure_dependencies,
    ):
        if (exit_code := safety_check()) != 0:
            raise SystemExit(exit_code)

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
    if glob.config.token:
        load_discord_cogs()
        app.add_task((dc.start, glob.config.token))

    raise SystemExit(app.start())
elif __name__ == "main":
    if housekeeping.running_via_asgi():
        raise RuntimeError(
            "Asahi uses it's own web framework (Xevel) and does not need to be run via an ASGI server "
            "such as hypercorn. Please run the file directly with `./main.py`",
        )
    else:
        raise RuntimeError("Asahi should be run directly with `./main.py`")
