# external imports (some may require to be installed, install using ext/requirements.txt)
from quart import Quart, Response, request, make_response # web server :blobcowboi:
from cmyui import AsyncSQLPool, Ansi, Version, log # import console logger (cleaner than print | ansi is for log colours), version handler and database handler
from pathlib import Path
from aiohttp import ClientSession
import pyfiglet
import pickle

# internal imports
from objects import glob # glob = global, server-wide objects will be stored here e.g database handler
from objects.player import Player # Player - player object to store stats, info etc.
from objects.channel import Channel # Channel - channel object to store name, desc etc.
from constants.countries import country_codes

app = Quart(__name__) # handler for webserver :D
app.config['SERVER_NAME'] = glob.config.domain
glob.version = Version(0, 1, 5) # set Asahi version, mainly for future updater but also for tracking

CACHE_PATH = Path.cwd() / 'resources/cache'
BCRYPT_CACHE_FILE = CACHE_PATH / 'bcrypt.p'
GEOLOC_CACHE_FILE = CACHE_PATH / 'geoloc.p'

AVA_PATH = Path.cwd() / 'resources/avatars'
SS_PATH = Path.cwd() / 'resources/screenshots'

@app.before_serving
async def connect(): # ran before server startup, used to do things like connecting to mysql :D
    log(f'==== Asahi v{glob.version} starting ====', Ansi.GREEN)

    glob.db = AsyncSQLPool() # define db globally
    glob.web = ClientSession() # aiohttp session for external web requests

    try:
        await glob.db.connect(glob.config.mysql) # connect to db using config :p
        if glob.config.debug:
            log('==== Asahi connected to MySQL ====', Ansi.GREEN)
    except Exception as error:
        log(f'==== Asahi failed to connect to MySQL ====\n\n{error}', Ansi.LRED)

    if not AVA_PATH.exists():
        AVA_PATH.mkdir(parents=True)
        log('Avatars folder has been created, please set a default avatar by placing a file named "default.png" into resources/avatars!', Ansi.LRED)

    if not SS_PATH.exists():
        SS_PATH.mkdir(parents=True)

    # this is my most cursed creation | speed gains but im going to hell for this
    if not CACHE_PATH.exists():
        CACHE_PATH.mkdir(parents=True)
    else:
        if BCRYPT_CACHE_FILE.exists():
            with open(BCRYPT_CACHE_FILE, 'rb') as f:
                try:
                    glob.cache['bcrypt'] |= dict(pickle.load(f))
                except EOFError:
                    pass

        if GEOLOC_CACHE_FILE.exists():
            with open(GEOLOC_CACHE_FILE, 'rb') as f:
                try:
                    glob.geoloc |= dict(pickle.load(f))
                except EOFError:
                    pass

    # add bot to user cache lmao CURSED | needs to be cleaned DESPERATELY
    botinfo = await glob.db.fetch('SELECT name, pw, country, name FROM users WHERE id = 1')
    bot = Player(id=1, name=botinfo['name'], offset=1, is_bot=True, country_iso=botinfo['country'], country=country_codes[botinfo['country'].upper()])
    glob.players[''] = bot
    glob.players_name[bot.name] = bot
    glob.players_id[1] = bot
    glob.bot = bot # might be useful in the future?
    if glob.config.debug:
        log(f"==== Added bot {bot.name} to player list ====", Ansi.GREEN)

    # add all channels to cache
    async for chan in glob.db.iterall('SELECT * FROM channels'):
        channel = Channel(name=chan['name'], desc=chan['descr'], auto=chan['auto'], un=False)
        glob.channels[channel.name] = channel
        if glob.config.debug:
            log(f'==== Added channel {channel.name} to channel list ====', Ansi.GREEN)

    log(f'==== Asahi v{glob.version} started ====', Ansi.GREEN)

@app.after_serving
async def disconnect():
    log(f'==== Asahi v{glob.version} stopping ====', Ansi.GREEN)

    # this is my most cursed creation part 2 | speed gains but im going to hell for this part 2

    new_bcrypt = glob.cache['bcrypt']
    if BCRYPT_CACHE_FILE.exists():
        try:
            with open(BCRYPT_CACHE_FILE, 'rb') as file:
                new_bcrypt |= dict(pickle.load(file))
        except EOFError:
            pass

    with open(BCRYPT_CACHE_FILE, 'wb') as file:
        pickle.dump(new_bcrypt, file, protocol=pickle.HIGHEST_PROTOCOL)

    new_geoloc = glob.geoloc
    if GEOLOC_CACHE_FILE.exists():
        try:
            with open(GEOLOC_CACHE_FILE, 'rb') as file:
                new_geoloc |= dict(pickle.load(file))
        except EOFError:
            pass

    with open(GEOLOC_CACHE_FILE, 'wb') as file:
        pickle.dump(new_geoloc, file, protocol=pickle.HIGHEST_PROTOCOL)

    await glob.web.close()
    if glob.config.debug:
        log('==== Closed webserver ====', Ansi.GREEN)

    await glob.db.close()
    if glob.config.debug:
        log('==== Closed database connection ====', Ansi.GREEN)

    log(f'==== Asahi v{glob.version} stopped ====', Ansi.GREEN)

if __name__ == '__main__':
    from endpoints.bancho import bancho
    from endpoints.avatars import avatars
    from endpoints.web import web
    app.register_blueprint(bancho, subdomain='c')
    app.register_blueprint(bancho, subdomain='ce')
    app.register_blueprint(bancho, subdomain='c4')
    app.register_blueprint(avatars, subdomain='a')
    app.register_blueprint(web, subdomain='osu')
