# external imports (some may require to be installed, install using ext/requirements.txt)
from quart import Quart, Response, request, make_response # web server :blobcowboi:
from cmyui import AsyncSQLPool, Ansi, Version, log # import console logger (cleaner than print | ansi is for log colours), version handler and database handler
from geoip2 import database # for geoloc
import pyfiglet
import bcrypt
import uuid
import time

# internal imports
from objects import glob # glob = global, server-wide objects will be stored here e.g database handler
from objects.player import Player # Player - player object to store stats, info etc.
from constants.countries import country_codes
from constants.types import osuTypes
import packets
from packets import BanchoPacketReader, BanchoPacket, Packets

app = Quart(__name__) # handler for webserver :D
glob.db = AsyncSQLPool() # define db globally
glob.version = Version(0, 0, 9) # set Asahi version, mainly for future updater but also for tracking
glob.packets = {}

def register(cls: BanchoPacket): # not a register handler, used for packets
    glob.packets |= {cls.type: cls}
    return cls

@register
class updateStats(BanchoPacket, type=Packets.OSU_REQUEST_STATUS_UPDATE):
    async def handle(self, user):
        user.enqueue(packets.userStats(user))

@register
class statsRequest(BanchoPacket, type=Packets.OSU_USER_STATS_REQUEST):
    uids: osuTypes.i32_list

    async def handle(self, user):
        for o in glob.players.values():
            if o.id != user.id and o.id in self.uids:
                user.enqueue(packets.userStats(o))

@register
class presenceRequest(BanchoPacket, type=Packets.OSU_USER_PRESENCE_REQUEST):
    uids: osuTypes.i32_list

    async def handle(self, user):
        for o in glob.players.values():
            user.enqueue(packets.userPresence(o))

@register
class presenceRequestAll(BanchoPacket, type=Packets.OSU_USER_PRESENCE_REQUEST_ALL):
    async def handle(self, user):
        for o in glob.players.values():
            if o.id != user.id:
                user.enqueue(packets.userPresence(o))

@register
class addFriend(BanchoPacket, type=Packets.OSU_FRIEND_ADD):
    uid: osuTypes.i32

    async def handle(self, user):
        req = user.id
        tar = self.uid
        await glob.db.execute('INSERT INTO friends (user1, user2) VALUES (%s, %s)', [req, tar])
        log(f"{user.name} added UID {tar} into their friends list.", Ansi.LBLUE)

@register
class removeFriend(BanchoPacket, type=Packets.OSU_FRIEND_REMOVE):
    uid: osuTypes.i32

    async def handle(self, user):
        req = user.id
        tar = self.uid
        await glob.db.execute('DELETE FROM friends WHERE user1 = %s AND user2 = %s', [req, tar])
        log(f"{user.name} removed UID {tar} from their friends list.", Ansi.LBLUE)

@register
class Logout(BanchoPacket, type=Packets.OSU_LOGOUT):
    async def handle(self, user):
        if (time.time() - user.login_time) < 1:
            return # osu sends random logout packet token on login ?

        user.logout()
        log(f"{user.name} logged out.", Ansi.LBLUE)

@register
class sendMessage(BanchoPacket, type=Packets.OSU_SEND_PRIVATE_MESSAGE):
    msg: osuTypes.message # i am so confused man wtf

    async def handle(self, user):
        msg = self.msg.msg
        tarname = self.msg.tarname

        tarto = glob.players_name[tarname]
        target = glob.players[tarto]

        target.enqueue(packets.sendMessage(fromname = user.name, msg = msg, tarname = target.name, fromid = user.id))
        log(f'{user.name} sent message "{msg}" to {tarname}')

@app.before_serving
async def connect(): # ran before server startup, used to do things like connecting to mysql :D
    log(f'==== Asahi v{glob.version} starting ====', Ansi.GREEN)
    try:
        await glob.db.connect(glob.config.mysql) # connect to db using config :p
        if glob.config.debug:
            log('==== Asahi connected to MySQL ====', Ansi.GREEN)
    except Exception as error:
        log(f'==== Asahi failed to connect to MySQL ====\n\n{error}', Ansi.LRED)

    # add bot to user cache lmao CURSED | needs to be cleaned DESPERATELY
    botinfo = await glob.db.fetch('SELECT name, pw, country, name FROM users WHERE id = 1')
    bot = Player(id=1, name=botinfo['name'], offset=1, is_bot=True, country_iso=botinfo['country'], country=country_codes[botinfo['country'].upper()])
    glob.players[''] = bot
    glob.players_name[bot.name] = ''
    if glob.config.debug:
        log(f"==== Added bot {botinfo['name']} to player list ====", Ansi.GREEN)

    log(f'==== Asahi v{glob.version} started ====', Ansi.GREEN)


@app.route("/", methods=['GET']) # only accept GET requests as POST is for login method, see login method below
async def root():
    message = f"{pyfiglet.figlet_format(f'Asahi v{glob.version}')}\n\ntsunyoku attempts bancho v2, gone right :sunglasses:"
    return Response(message, mimetype='text/plain')

@app.route("/", methods=['POST']) # only accept POST requests, we can assume it is for a login request but we can deny access if not
async def login():
    start = time.time()
    headers = request.headers # request headers, used for things such as user ip and agent

    if 'User-Agent' not in headers or headers['User-Agent'] != 'osu!':
        # request isn't sent from osu client, return html
        message = f"{pyfiglet.figlet_format(f'Asahi v{glob.version}')}\n\ntsunyoku attempts bancho v2, gone right :sunglasses:"
        return Response(message, mimetype='text/plain')

    if 'osu-token' not in headers: # sometimes a login request will be a re-connect attempt, in which case they will already have a token, if not: login the user
        data = await request.data # request data, used to get info such as username to login the user
        if len(info := data.decode().split('\n')[:-1]) != 3: # format data so we can use it easier & also ensure it is valid at the same time
            resp = await make_response(packets.userID(-2)) # -2 userid informs client it is too old | i assume that is the only valid reason for this to happen
            resp.headers['cho-token'] = 'no' # client knows there is something up if we set token to 'no'
            return resp

        if len(cinfo := info[2].split('|')) != 5: # format client data (hash, utc etc.) & ensure it is valid
            resp = await make_response(packets.userID(-2)) # -2 userid informs client it is too old
            resp.headers['cho-token'] = 'no' # client knows there is something up if we set token to 'no'
            return resp

        username = info[0]
        pw = info[1].encode() # password in md5 form, we will use this to compare against db's stored bcrypt later

        user = await glob.db.fetch('SELECT id, pw, country, name FROM users WHERE name = %s', [username])
        if not user: # ensure user actually exists before attempting to do anything else
            if glob.config.debug:
                log(f'User {username} does not exist. | Time Elapsed: {(time.time() - start) * 1000:.2f}ms', Ansi.LRED)
            resp = await make_response(packets.userID(-1)) # -1 userid informs client of an auth error
            resp.headers['cho-token'] = 'no' # client knows there is something up if we set token to 'no'
            return resp

        bcache = glob.cache['bcrypt'] # get our cached bcrypts to potentially enhance speed
        pw_bcrypt = user['pw'].encode()
        if pw_bcrypt in bcache:
            if pw != bcache[pw_bcrypt]: # compare provided md5 with the stored (cached) bcrypt to ensure they have provided the correct password
                if glob.config.debug:
                    log(f"{username}'s login attempt failed: provided an incorrect password | Time Elapsed (with cached bcrypt): {(time.time() - start) * 1000:.2f}ms", Ansi.LRED)
                resp = await make_response(packets.userID(-1))
                resp.headers['cho-token'] = 'no'
                return resp
            ub = True
        else:
            if not bcrypt.checkpw(pw, pw_bcrypt): # compare provided md5 with the stored bcrypt to ensure they have provided the correct password
                if glob.config.debug:
                    log(f"{username}'s login attempt failed: provided an incorrect password | Time Elapsed (bcrypt not cached): {(time.time() - start) * 1000:.2f}ms", Ansi.LRED)
                resp = await make_response(packets.userID(-1))
                resp.headers['cho-token'] = 'no'
                return resp
            ub = False
            
            bcache[pw_bcrypt] = pw # cache pw for future

        token = uuid.uuid4() # generate token for client to use as auth
        user['offset'] = int(cinfo[1]) # utc offset for time
        user['bot'] = False # used to specialise bot functions, kinda gay setup ngl
        user['token'] = str(token) # this may be useful in the future
        user['ltime'] = time.time() # useful for handling random logouts

        # sort out geoloc | SPEEEEEEEEEEEEEED gains
        ip = headers['X-Real-IP']
        reader = database.Reader('ext/geoloc.mmdb')
        geoloc = reader.city(ip)
        user['country_iso'], user['lat'], user['lon'] = (geoloc.country.iso_code, geoloc.location.latitude, geoloc.location.longitude)
        user['country'] = country_codes[user['country_iso']]
        await glob.db.execute('UPDATE users SET country = %s WHERE id = %s', [user['country_iso'].lower(), user['id']]) # update country code in db

        friends = {row['user2'] async for row in glob.db.iterall('SELECT user2 FROM friends WHERE user1 = %s', [user['id']])} # select all friends from db

        p = Player.login(user)
        data = bytearray(packets.userID(p.id)) # initiate login by providing the user's id
        data += packets.protocolVersion(19) # no clue what this does
        data += packets.banchoPrivileges(1 << 4) # force priv to developer for now
        data += (packets.userPresence(p) + packets.userStats(p)) # provide user & other user's presence/stats (for f9 + user stats)
        data += packets.notification(f'Welcome to Asahi v{glob.version}') # send notification as indicator they've logged in i guess
        data += packets.channelInfoEnd() # no clue what this does either
        data += packets.menuIcon() # set main menu icon
        data += packets.friends(*friends) # send user friend list
        data += packets.silenceEnd(0) # force to 0 for now since silences arent a thing
        #data += packets.sendMessage(user['name'], 'test message lol so cool', user['name'], user['id']) # test message

        # add user to cache?
        glob.players[p.token] = p
        glob.players_name[p.name] = p.token
        for o in glob.players.values(): # enqueue other users to client
            o.enqueue((packets.userPresence(p) + packets.userStats(p))) # enqueue this user to every other logged in user
            data += (packets.userPresence(o) + packets.userStats(o)) # enqueue every other logged in user to this user

        resp = await make_response(bytes(data))
        resp.headers['cho-token'] = token
        if glob.config.debug:
            log(f'{p.name} successfully logged in. | Time Elapsed (using bcrypt cache: {ub}): {(time.time() - start) * 1000:.2f}ms', Ansi.LBLUE)
        return resp
    
    # if we have made it this far then it's a reconnect attempt with token already provided
    user_token = headers['osu-token'] # client-provided token
    try:
        p = glob.players[user_token]
    except:
        # user is logged in but token is not found? most likely a restart so we force a reconnection
        return packets.restartServer(0)

    body = await request.body

    # handle any packets the client has sent
    for packet in BanchoPacketReader(body, glob.packets):
        await packet.handle(p)
        if glob.config.debug:
            log(f'Handled packet {packet.type!r}', Ansi.LBLUE)
 
    data = bytearray()
    while not p.queue_empty():
        data += p.dequeue()

    resp = await make_response(bytes(data))
    resp.headers['Content-Type'] = 'text/html; charset=UTF-8' # ?
    return resp

