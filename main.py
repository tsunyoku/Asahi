# external imports (some may require to be installed, install using ext/requirements.txt)
from quart import Quart, Response, request, make_response # web server :blobcowboi:
from cmyui import AsyncSQLPool, Ansi, Version, log # import console logger (cleaner than print | ansi is for log colours), version handler and database handler
from pathlib import Path
from aiohttp import ClientSession
from aiofile import AIOFile
from os import makedirs
import pyfiglet
import pickle

# internal imports
from objects import glob # glob = global, server-wide objects will be stored here e.g database handler
from objects.player import Player # Player - player object to store stats, info etc.
from constants.countries import country_codes

app = Quart(__name__) # handler for webserver :D
app.config['SERVER_NAME'] = glob.config.domain
glob.version = Version(0, 1, 3) # set Asahi version, mainly for future updater but also for tracking

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

    ava_path = Path.cwd() / 'resources/avatars'
    if not ava_path.exists():
        makedirs(ava_path, exist_ok=True)
        log('Avatars folder has been created, please set a default avatar by placing a file named "default.png" into resources/avatars!', Ansi.LRED)
    
    ss_path = Path.cwd() / 'resources/screenshots'
    if not ss_path.exists():
        makedirs(ss_path, exist_ok=True)

    # this is my most cursed creation | speed gains but im going to hell for this
    cache_path = Path.cwd() / 'resources/cache'
    if not cache_path.exists():
        makedirs(cache_path, exist_ok=True)
        bcrypt_file = cache_path / 'bcrypt.json'
        geoloc_file = cache_path / 'geoloc.json'
        with open(bcrypt_file, 'wb') as f:
            f.write("")
            f.close()
        with open(geoloc_file, 'wb') as f:
            f.write("")
            f.close()
    else:
        try:
            with open(Path.cwd() / 'resources/cache/bcrypt.json', 'rb') as f:
                glob.cache['bcrypt'] = pickle.loads(f.read())
                f.close()
        except EOFError:
            pass

        try:
            with open(Path.cwd() / 'resources/cache/geoloc.json', 'rb') as f:
                glob.geoloc = pickle.loads(f.read())
                f.close()
        except EOFError:
            pass

    # add bot to user cache lmao CURSED | needs to be cleaned DESPERATELY
    botinfo = await glob.db.fetch('SELECT name, pw, country, name FROM users WHERE id = 1')
    bot = Player(id=1, name=botinfo['name'], offset=1, is_bot=True, country_iso=botinfo['country'], country=country_codes[botinfo['country'].upper()])
    glob.players[''] = bot
    glob.players_name[bot.name] = ''
    glob.bot = bot # might be useful in the future?
    if glob.config.debug:
        log(f"==== Added bot {bot.name} to player list ====", Ansi.GREEN)

    log(f'==== Asahi v{glob.version} started ====', Ansi.GREEN)

@app.after_serving
async def disconnect():
    log(f'==== Asahi v{glob.version} stopping ====', Ansi.GREEN)

    # this is my most cursed creation part 2 | speed gains but im going to hell for this part 2
    with open(Path.cwd() / 'resources/cache/bcrypt.json', 'wb') as f:
        pickle.dump(glob.cache['bcrypt'], f)
        f.close()

    with open(Path.cwd() / 'resources/cache/geoloc.json', 'wb') as f:
        pickle.dump(glob.geoloc, f)

    await glob.web.close()
    if glob.config.debug:
        log('==== Closed webserver ====', Ansi.GREEN)

    await glob.db.close()
    if glob.config.debug:
        log('==== Closed database connection ====', Ansi.GREEN)
    
    log(f'==== Asahi v{glob.version} stopped ====', Ansi.GREEN)

from endpoints.bancho import bancho
from endpoints.avatars import avatars
from endpoints.web import web
app.register_blueprint(bancho, subdomain='c')
app.register_blueprint(bancho, subdomain='ce')
app.register_blueprint(bancho, subdomain='c4')
app.register_blueprint(avatars, subdomain='a')
app.register_blueprint(web, subdomain='osu')

