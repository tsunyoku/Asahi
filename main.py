# external imports (some may require to be installed, install using ext/requirements.txt)
from quart import Quart, Response, request, make_response # web server :blobcowboi:
from cmyui import AsyncSQLPool, Ansi, Version, log # import console logger (cleaner than print | ansi is for log colours), version handler and database handler
import pyfiglet
import bcrypt
import uuid

# internal imports
from objects import glob # glob = global, server-wide objects will be stored here e.g database handler
import packets

app = Quart(__name__) # handler for webserver :D
glob.db = AsyncSQLPool() # define db globally
glob.version = Version(0, 0, 3) # set Asahi version, mainly for future updater but also for tracking

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
        info = data.decode().split('\n')[:-1] # format data so we can use it easier

        username = info[0]
        pw = info[1].encode() # password in md5 form, we will use this to compare against db's stored bcrypt later

        user = await glob.db.fetch('SELECT id, pw, country, name FROM users WHERE name = %s', [username])
        if not user: # ensure user actually exists before attempting to do anything else
            log(f'User {username} does not exist.', Ansi.LRED)
            resp = await make_response(packets.userID(-1))
            resp.headers['cho-token'] = 'no'
            return resp

        pw_bcrypt = user['pw'].encode()
        if not bcrypt.checkpw(pw, pw_bcrypt): # compare provided md5 with the stored bcrypt to ensure they have provided the correct password
            log(f"{username}'s login attempt failed: provided an incorrect password", Ansi.LRED)
            resp = await make_response(packets.userID(-1))
            resp.headers['cho-token'] = 'no'
            return resp

        token = uuid.uuid4() # generate token for client to use as auth
        data = bytearray(packets.userID(user['id'])) # initiate login by providing the user's id
        data += packets.protocolVersion(19) # no clue what this does
        data += packets.banchoPrivileges(1 << 4) # force priv to developer for now
        data += (packets.userPresence(user) + packets.userStats(user)) # provide user & other user's presence/stats (for f9 + user stats)
        data += packets.notification(f'Welcome to Asahi v{glob.version}') # send notification as indicator they've logged in iguess
        data += packets.channelInfoEnd() # no clue what this does either

        resp = await make_response(bytes(data))
        resp.headers['cho-token'] = token
        log(f'{username} successfully logged in.', Ansi.GREEN)
        return resp

    # if we have made it this far then it's a reconnect attempt with token already provided, i will handle this later