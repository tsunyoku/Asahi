# external imports (some may require to be installed, install using ext/requirements.txt)
from quart import Blueprint, Response, request, make_response # web server :blobcowboi:
from cmyui import Ansi, log # import console logger (cleaner than print | ansi is for log colours), version handler and database handler
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
from constants.privs import Privileges, ClientPrivileges
from constants.mods import Mods
from constants import commands
import packets
from packets import BanchoPacketReader, BanchoPacket, Packets

bancho = Blueprint('bancho', __name__) # handler for webserver :D
glob.packets = {}
reader = database.Reader('ext/geoloc.mmdb')

def packet(cls: BanchoPacket):
    glob.packets |= {cls.type: cls}
    return cls

@packet
class updateStats(BanchoPacket, type=Packets.OSU_REQUEST_STATUS_UPDATE):
    async def handle(self, user: Player):
        user.enqueue(packets.userStats(user))

@packet
class statsRequest(BanchoPacket, type=Packets.OSU_USER_STATS_REQUEST):
    uids: osuTypes.i32_list

    async def handle(self, user: Player):
        for o in glob.players.values():
            if o.id != user.id and o.id in self.uids:
                user.enqueue(packets.userStats(o))

@packet
class presenceRequest(BanchoPacket, type=Packets.OSU_USER_PRESENCE_REQUEST):
    uids: osuTypes.i32_list

    async def handle(self, user: Player):
        for o in glob.players.values():
            user.enqueue(packets.userPresence(o))

@packet
class presenceRequestAll(BanchoPacket, type=Packets.OSU_USER_PRESENCE_REQUEST_ALL):
    async def handle(self, user: Player):
        for o in glob.players.values():
            if o.id != user.id:
                user.enqueue(packets.userPresence(o))

@packet
class addFriend(BanchoPacket, type=Packets.OSU_FRIEND_ADD):
    uid: osuTypes.i32

    async def handle(self, user: Player):
        req = user.id
        tar = self.uid
        user.friends.add(tar)
        await glob.db.execute('INSERT INTO friends (user1, user2) VALUES ($1, $2)', req, tar)
        log(f"{user.name} added UID {tar} into their friends list.", Ansi.LCYAN)

@packet
class removeFriend(BanchoPacket, type=Packets.OSU_FRIEND_REMOVE):
    uid: osuTypes.i32

    async def handle(self, user: Player):
        req = user.id
        tar = self.uid
        user.friends.remove(tar)
        await glob.db.execute('DELETE FROM friends WHERE user1 = $1 AND user2 = $2', req, tar)
        log(f"{user.name} removed UID {tar} from their friends list.", Ansi.LCYAN)

@packet
class Logout(BanchoPacket, type=Packets.OSU_LOGOUT):
    async def handle(self, user: Player):
        if (time.time() - user.login_time) < 1:
            return # osu sends random logout packet token on login ?

        user.logout()
        log(f"{user.name} logged out.", Ansi.LBLUE)

@packet
class sendPrivateMessage(BanchoPacket, type=Packets.OSU_SEND_PRIVATE_MESSAGE):
    msg: osuTypes.message # i am so confused man wtf

    async def handle(self, user: Player):
        msg = self.msg.msg
        tarname = self.msg.tarname

        if not (target := glob.players_name.get(tarname)):
            log(f'{user.name} tried to send message to offline user {tarname}', Ansi.LRED)
            return

        if target is glob.bot:
            if msg.startswith('!'):
                cmd = await commands.process(user, target, msg)
                user.enqueue(packets.sendMessage(fromname = target.name, msg = cmd, tarname = user.name, fromid = target.id))
        else:
            target.enqueue(packets.sendMessage(fromname = user.name, msg = msg, tarname = target.name, fromid = user.id))
            log(f'{user.name} sent message "{msg}" to {tarname}', Ansi.LCYAN)

@packet
class sendPublicMessage(BanchoPacket, type=Packets.OSU_SEND_PUBLIC_MESSAGE):
    msg: osuTypes.message

    async def handle(self, user: Player):
        msg = self.msg.msg
        chan = self.msg.tarname

        if chan == '#spectator':
            if user.spectating:
                sid = user.spectating.id
            elif user.spectators:
                sid = user.id
            else:
                return
            c = glob.channels.get(f'#spec_{sid}')
        elif chan != '#multiplayer': # no mp stuff yet
            c = glob.channels.get(chan)

        if not c:
            log(f'{user.name} tried to send a message in non-existent channel {chan}', Ansi.LRED)
            return

        c.send(user, msg)

@packet
class joinChannel(BanchoPacket, type=Packets.OSU_CHANNEL_JOIN):
    name: osuTypes.string

    async def handle(self, user: Player):
        chan = glob.channels.get(self.name)

        if not chan:
            log(f'{user.name} failed to join channel {self.name}', Ansi.LRED)
            return

        user.join_chan(chan)
        user.enqueue(packets.channelJoin(chan.name))
        for o in chan.players:
            o.enqueue(packets.channelInfo(chan))

@packet
class leaveChannel(BanchoPacket, type=Packets.OSU_CHANNEL_PART):
    name: osuTypes.string

    async def handle(self, user: Player):
        if self.name == '#highlight' or not self.name.startswith('#'): # osu why!!!
            return

        chan = glob.channels.get(self.name)

        if not chan:
            log(f'{user.name} failed to leave channel {self.name}', Ansi.LRED)

        if user not in chan.players:
            return

        user.leave_chan(chan)
        for o in chan.players:
            o.enqueue(packets.channelInfo(chan))

@packet
class updateAction(BanchoPacket, type=Packets.OSU_CHANGE_ACTION):
    actionid: osuTypes.u8
    info: osuTypes.string
    md5: osuTypes.string
    mods: osuTypes.u32
    mode: osuTypes.u8
    mid: osuTypes.i32

    async def handle(self, user: Player):
        if self.actionid == 0 and self.mods & Mods.RELAX:
            self.info = 'on Relax'
        elif self.actionid == 0 and self.mods & Mods.AUTOPILOT:
            self.info = 'on Autopilot'

        user.action = self.actionid
        user.info = self.info
        user.map_md5 = self.md5
        user.mods = self.mods

        if user.mods & Mods.RELAX:
            user.mode_vn = self.mode
            self.mode += 4
        elif user.mods & Mods.AUTOPILOT:
            user.mode_vn = 0
            self.mode = 7

        user.mode = self.mode
        user.map_id = self.mid

        for o in glob.players.values():
            o.enqueue(packets.userStats(user))

@packet
class startSpec(BanchoPacket, type=Packets.OSU_START_SPECTATING):
    tid: osuTypes.i32

    async def handle(self, user: Player):
        if self.tid == 1: # spectating bot is just gonna cause unnecessary errors
            return

        if not (target := glob.players_id.get(self.tid)):
            log(f'{user.name} tried to spectate offline UID {self.tid}', Ansi.LRED)
            return

        target.add_spectator(user)

@packet
class stopSpec(BanchoPacket, type=Packets.OSU_STOP_SPECTATING):
    async def handle(self, user: Player):
        if not (host := user.spectating):
            log(f'{user.name} tried to stop spectating someone while not spectating anyone.', Ansi.LRED)
            return

        host.remove_spectator(user)

@packet
class specFrames(BanchoPacket, type=Packets.OSU_SPECTATE_FRAMES):
    frames: osuTypes.raw

    async def handle(self, user: Player):
        for u in user.spectators:
            u.enqueue(packets.spectateFrames(self.frames))

@bancho.route("/", methods=['GET']) # only accept GET requests as POST is for login method, see login method below
async def root_http():
    message = f"{pyfiglet.figlet_format(f'Asahi v{glob.version}')}\n\ntsunyoku attempts bancho v2, gone right :sunglasses:"
    return Response(message, mimetype='text/plain')

@bancho.route("/", methods=['POST']) # only accept POST requests, we can assume it is for a login request but we can deny access if not
async def root_client():
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

        user = await glob.db.fetchrow("SELECT id, pw, country, name, priv FROM users WHERE name = $1", username)
        if not user: # ensure user actually exists before attempting to do anything else
            if glob.config.debug:
                log(f'User {username} does not exist.', Ansi.LRED)
            resp = await make_response(packets.userID(-1)) # -1 userid informs client of an auth error
            resp.headers['cho-token'] = 'no' # client knows there is something up if we set token to 'no'
            return resp

        bcache = glob.cache['bcrypt'] # get our cached bcrypts to potentially enhance speed
        pw_bcrypt = user['pw'].encode()
        if pw_bcrypt in bcache:
            if pw != bcache[pw_bcrypt]: # compare provided md5 with the stored (cached) bcrypt to ensure they have provided the correct password
                if glob.config.debug:
                    log(f"{username}'s login attempt failed: provided an incorrect password", Ansi.LRED)
                resp = await make_response(packets.userID(-1))
                resp.headers['cho-token'] = 'no'
                return resp
        else:
            if not bcrypt.checkpw(pw, pw_bcrypt): # compare provided md5 with the stored bcrypt to ensure they have provided the correct password
                if glob.config.debug:
                    log(f"{username}'s login attempt failed: provided an incorrect password", Ansi.LRED)
                resp = await make_response(packets.userID(-1))
                resp.headers['cho-token'] = 'no'
                return resp

            bcache[pw_bcrypt] = pw # cache pw for future

        if not user['priv'] & Privileges.Normal:
            resp = await make_response(packets.userID(-3)) # banned packet
            resp.headers['cho-token'] = 'no'
            return resp

        token = uuid.uuid4() # generate token for client to use as auth
        user2 = dict(user)
        user2['offset'] = int(cinfo[1]) # utc offset for time
        user2['bot'] = False # used to specialise bot functions, kinda gay setup ngl
        user2['token'] = str(token) # this may be useful in the future
        user2['ltime'] = time.time() # useful for handling random logouts
        user2['md5'] = pw # used for auth on /web/
        ip = headers['X-Forwarded-For']

        # cache ip's geoloc | the speed gains too are ungodly
        if not glob.geoloc.get(ip):
            geoloc = reader.city(ip)
            glob.geoloc[ip] = geoloc
        else:
            geoloc = glob.geoloc[ip]

        user2['country_iso'], user2['lat'], user2['lon'] = (geoloc.country.iso_code, geoloc.location.latitude, geoloc.location.longitude)
        user2['country'] = country_codes[user2['country_iso']]

        # set player object
        p = await Player.login(user2)
        await p.set_stats()

        if not p.priv & Privileges.Verified:
            if p.id == 3:
                # first user & not verified, give all permissions
                await p.set_priv(Privileges.Master)

            await glob.db.execute("UPDATE users SET country = $1 WHERE id = $2", p.country_iso.lower(), p.id) # set country code in db
            await p.add_priv(Privileges.Verified) # verify user
            log(f'{p.name} has been successfully verified.', Ansi.LBLUE)

        data = bytearray(packets.userID(p.id)) # initiate login by providing the user's id
        data += packets.protocolVersion(19) # no clue what this does
        data += packets.banchoPrivileges(p.client_priv | ClientPrivileges.Supporter)
        data += (packets.userPresence(p) + packets.userStats(p)) # provide user & other user's presence/stats (for f9 + user stats)
        data += packets.channelInfoEnd() # no clue what this does either
        data += packets.menuIcon() # set main menu icon
        data += packets.friends(p.friends) # send user friend list
        data += packets.silenceEnd(0) # force to 0 for now since silences arent a thing

        # get channels from cache and send to user
        for chan in glob.channels.values():
            if chan.auto:
                p.join_chan(chan)
                data += packets.channelJoin(chan.name) # only join user to channel if the channel is meant for purpose

            data += packets.channelInfo(chan) # regardless of whether the channel should be auto-joined we should make the client aware of it

        # add user to cache?
        glob.players[p.token] = p
        glob.players_name[p.name] = p
        glob.players_id[p.id] = p
        for o in glob.players.values(): # enqueue other users to client
            o.enqueue((packets.userPresence(p) + packets.userStats(p))) # enqueue this user to every other logged in user
            data += (packets.userPresence(o) + packets.userStats(o)) # enqueue every other logged in user to this user

        elapsed = round((time.time() - start) * 1000, 2)
        data += packets.notification(f'Welcome to Asahi v{glob.version}\n\nTime Elapsed: {elapsed}ms') # send notification as indicator they've logged in i guess
        if glob.config.debug:
            log(f'{p.name} successfully logged in. | Time Elapsed: {elapsed}ms', Ansi.LBLUE)

        resp = await make_response(bytes(data))
        resp.headers['cho-token'] = token
        return resp

    # if we have made it this far then it's a reconnect attempt with token already provided
    user_token = headers['osu-token'] # client-provided token
    if not (p := glob.players.get(user_token)):
        # user is logged in but token is not found? most likely a restart so we force a reconnection
        return packets.restartServer(0)

    body = await request.body

    # handle any packets the client has sent
    for packet in BanchoPacketReader(body, glob.packets):
        await packet.handle(p)

    data = bytearray()
    while not p.queue_empty():
        data += p.dequeue()

    resp = await make_response(bytes(data))
    resp.headers['Content-Type'] = 'text/html; charset=UTF-8' # ?
    return resp
