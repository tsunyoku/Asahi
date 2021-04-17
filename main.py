# external imports (some may require to be installed, install using ext/requirements.txt)
from quart import Quart, Response, request # web server :blobcowboi:
from cmyui import AsyncSQLPool, Ansi, Version, log # import console logger (cleaner than print | ansi is for log colours), version handler and database handler
import pyfiglet

# internal imports
from objects import glob # glob = global, server-wide objects will be stored here e.g database handler

app = Quart(__name__) # handler for webserver :D
glob.db = AsyncSQLPool() # define db globally
glob.version = Version(0, 0, 1) # set Asahi version, mainly for future updater but also for tracking

@app.before_serving
async def connect(): # ran before server startup, used to do things like connecting to mysql :D
    log(f'==== Asahi v{glob.version} starting ====', Ansi.GREEN)
    try:
        await glob.db.connect(glob.config.mysql) # connect to db using config :p
        if glob.config.debug:
            log('==== Asahi connected to MySQL ====', Ansi.GREEN)
    except Exception as error:
        log(f'==== Asahi failed to connect to MySQL ====\n\n{error}', Ansi.LRED)
    

@app.route("/", methods=['GET']) # only accept GET requests as POST is for login method, see login method below
async def root():
    message = f"{pyfiglet.figlet_format('Asahi')}\n\ntsunyoku attempts bancho v2, gone right :sunglasses:"
    return Response(message, mimetype='text/plain')

@app.route("/", methods=['POST']) # only accept POST requests, we can assume it is for a login request but we can deny access if not
async def login():
    headers = request.headers # request headers, used for things such as user ip and agent

    if 'User-Agent' not in headers or headers['User-Agent'] != 'osu!':
        # request isn't sent from osu client, return nothing
        return

    if 'osu-token' not in headers: # sometimes a login request will be a re-connect attempt, in which case they will already have a token, if not: login the user
        data = await request.data # request data, used to get info such as username to login the user