# external imports (some may require to be installed, install using ext/requirements.txt)
from quart import Blueprint, Response, request, make_response # web server :blobcowboi:
from cmyui import Ansi, log # import console logger (cleaner than print | ansi is for log colours), version handler and database handler
from geoip2 import database # for geoloc
from re import compile

# pw stuff xd
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

import pyfiglet
import uuid
import time

# internal imports
from objects import glob # glob = global, server-wide objects will be stored here e.g database handler
from objects.player import Player # Player - player object to store stats, info etc.
from objects.beatmap import Beatmap # Beatmap - object to score map info etc.
from objects.channel import Channel
from objects.match import slotStatus, Teams
from constants.countries import country_codes
from constants.types import osuTypes, teamTypes
from constants.privs import Privileges, ClientPrivileges
from constants.mods import Mods, convert
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
        user.friends.append(tar)
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
            regex_domain = glob.config.domain.replace('.', r'\.')
            npr = compile( # yikes
                r'^\x01ACTION is (?:playing|editing|watching|listening to) '
                rf'\[https://osu\.(?:{regex_domain})/beatmapsets/(?P<sid>\d{{1,10}})#/?(?P<bid>\d{{1,10}})/? .+\]'
                r'(?: <(?P<mode>Taiko|CatchTheBeat|osu!mania)>)?'
                r'(?P<mods>(?: (?:-|\+|~|\|)\w+(?:~|\|)?)+)?\x01$'
            )

            if msg.startswith('!'):
                cmd = await commands.process(user, target, msg)
                if cmd is not None:
                    user.enqueue(packets.sendMessage(fromname = target.name, msg = cmd, tarname = user.name, fromid = target.id))
            elif m := npr.match(msg):
                user.np = await Beatmap.bid_fetch(int(m['bid']))
                np = await user.np.np_msg
                user.enqueue(packets.sendMessage(fromname = target.name, msg = np, tarname = user.name, fromid = target.id))
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
        elif chan == '#multiplayer':
            if not user.match:
                return

            m = user.match.id
            c = glob.channels.get(f'#multi_{m}')
        elif chan == '#clan':
            if not user.clan:
                return

            c = user.clan.chan
        elif chan not in ['#highlight', '#userlog']:
            c = glob.channels.get(chan)

        if not c:
            return

        c.send(user, msg, False)

@packet
class joinChannel(BanchoPacket, type=Packets.OSU_CHANNEL_JOIN):
    name: osuTypes.string

    async def handle(self, user: Player):
        if self.name == '#spectator':
            if user.spectating is not None:
                uid = user.spectating.id
            elif user.spectators:
                uid = user.id
            else:
                return # not spectating

            chan = glob.channels.get(f'#spec_{uid}')
        elif self.name == '#multiplayer':
            if not user.match:
                return

            m = user.match.id
            chan = glob.channels.get(f'#multi_{m}')
        elif self.name == '#clan':
            if not user.clan:
                return

            chan = user.clan.chan
        else:
            chan = glob.channels.get(self.name)

        if not chan:
            return

        user.join_chan(chan)

@packet
class leaveChannel(BanchoPacket, type=Packets.OSU_CHANNEL_PART):
    name: osuTypes.string

    async def handle(self, user: Player):
        if self.name in ['#highlight', '#userlog'] or not self.name.startswith('#'): # osu why!!!
            return

        if self.name == '#spectator':
            if user.spectating is not None:
                uid = user.spectating.id
            elif user.spectators:
                uid = user.id
            else:
                return # not spectating

            chan = glob.channels.get(f'#spec_{uid}')
        elif self.name == '#multiplayer':
            if not user.match:
                return

            m = user.match.id
            chan = glob.channels.get(f'#multi_{m}')
        elif self.name == '#clan':
            if not user.clan:
                return

            chan = user.clan.chan
        else:
            chan = glob.channels.get(self.name)

        if not chan:
            return

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

        if self.actionid == 2:
            user.info += f' +{convert(self.mods)}'

        for o in glob.players.values():
            o.enqueue(packets.userStats(user))

@packet
class startSpec(BanchoPacket, type=Packets.OSU_START_SPECTATING):
    tid: osuTypes.i32

    async def handle(self, user: Player):
        if self.tid == 1: # spectating bot is just gonna cause unnecessary errors
            return

        if not (target := glob.players_id.get(self.tid)):
            return

        target.add_spectator(user)

@packet
class stopSpec(BanchoPacket, type=Packets.OSU_STOP_SPECTATING):
    async def handle(self, user: Player):
        if not (host := user.spectating):
            return

        host.remove_spectator(user)

@packet
class specFrames(BanchoPacket, type=Packets.OSU_SPECTATE_FRAMES):
    frames: osuTypes.raw

    async def handle(self, user: Player):
        for u in user.spectators:
            u.enqueue(packets.spectateFrames(self.frames))

@packet
class osuPing(BanchoPacket, type=Packets.OSU_PING):
    async def handle(self, user: Player):
        pass # useless packet thank you osu

@packet
class joinLobby(BanchoPacket, type=Packets.OSU_JOIN_LOBBY):
    async def handle(self, user: Player):
        for m in glob.matches:
            user.enqueue(packets.newMatch(m))

@packet
class leaveLobby(BanchoPacket, type=Packets.OSU_JOIN_LOBBY):
    async def handle(self, user: Player):
        pass # ? xd

@packet
class createMatch(BanchoPacket, type=Packets.OSU_CREATE_MATCH):
    match: osuTypes.match

    async def handle(self, user: Player):
        glob.matches[self.match.id] = self.match
        if not glob.matches.get(self.match.id):
            user.enqueue(packets.matchJoinFail())
            return

        mp_chan = Channel(name=f'#multiplayer', desc=f'Multiplayer channel for match ID {self.match.id}', auto=False, perm=False)
        glob.channels[f'#multi_{self.match.id}'] = mp_chan
        self.match.chat = mp_chan

        user.join_match(self.match, self.match.pw)
        log(f'{user.name} created new multiplayer lobby.', Ansi.LBLUE)

@packet
class joinMatch(BanchoPacket, type=Packets.OSU_JOIN_MATCH):
    id: osuTypes.i32
    pw: osuTypes.string

    async def handle(self, user):
        if not (match := glob.matches.get(self.id)):
            user.enqueue(packets.matchJoinFail())
            return

        if match.clan_battle:
            if user.clan not in (match.clan_1, match.clan_2) or match.battle_ready:
                user.enqueue(packets.matchJoinFail())
                return
        
        user.join_match(match, self.pw)

        # enqueue after final user has joined
        if match.clan_battle:
            total = []
            for slot in match.slots:
                if slot.status & slotStatus.has_player:
                    total.append(slot.player)

            battle = glob.clan_battles[user.clan]
            if set(total) == set(battle['total']): # force set so its unordered
                await match.start_battle()

@packet
class leaveMatch(BanchoPacket, type=Packets.OSU_PART_MATCH):
    async def handle(self, user: Player):
        user.leave_match()

@packet
class changeMatchSlot(BanchoPacket, type=Packets.OSU_MATCH_CHANGE_SLOT):
    id: osuTypes.i32

    async def handle(self, user: Player):
        if not (match := user.match):
            return
        
        if match.slots[id].status != slotStatus.open:
            return

        old = match.get_slot(user)

        new = match.slots[self.id]
        new.copy(old)

        old.reset()

        match.enqueue_state()

@packet
class playerReady(BanchoPacket, type=Packets.OSU_MATCH_READY):
    async def handle(self, user):
        if not (match := user.match):
            return
        
        slot = match.get_slot(user)
        slot.status = slotStatus.ready

        match.enqueue_state(lobby=False)

@packet
class lockSlot(BanchoPacket, type=Packets.OSU_MATCH_LOCK):
    id: osuTypes.i32

    async def handle(self, user):
        if not (match := user.match):
            return

        if match.clan_battle:
            return
        
        if user is not match.host:
            return
        
        slot = match.slots[self.id]

        if slot.status == slotStatus.locked:
            slot.status = slotStatus.open
        else:
            if slot.player is match.host:
                return

            slot.status = slotStatus.locked

        match.enqueue_state()

@packet
class changeMatchSettings(BanchoPacket, type=Packets.OSU_MATCH_CHANGE_SETTINGS):
    m: osuTypes.match

    async def handle(self, user):
        if not (match := user.match):
            return
        
        if user is not match.host:
            return

        if self.m.fm != match.fm:
            match.fm = self.m.fm

        if self.m.fm:
            for s in match.slots:
                if s.status & slotStatus.has_player:
                    s.mods = match.mods & ~Mods.SPEED_MODS
                    if match.clan_battle:
                        s.mods = (match.mods &~ Mods.SPEED_MODS) & ~Mods.GAME_CHANGING

            match.mods &= Mods.SPEED_MODS
            if match.clan_battle:
                match.mods &= Mods.GAME_CHANGING
        else:
            host = match.get_host()
            match.mods &= Mods.SPEED_MODS
            if match.clan_battle:
                match.mods &= Mods.GAME_CHANGING
            match.mods |= host.mods

            for s in match.slots:
                if s.status & slotStatus.has_player:
                    s.mods = Mods.NOMOD

        if self.m.bname == '':
            match.unready_players(slotStatus.ready)

        if self.m.bmd5 != match.bmd5:
            m = await Beatmap.from_md5(self.m.bmd5)

            if m:
                match.bid = m.id
                match.bmd5 = m.md5
                match.bname = m.name
                match.mode = m.mode
            else:
                match.bid = self.m.bid
                match.bmd5 = self.m.bmd5
                match.bname = self.m.bname
                match.mode = self.m.mode

        if match.type != self.m.type and not match.clan_battle:
            if self.m.type in (teamTypes.head, teamTypes.tag):
                team = Teams.neutral
            else:
                team = Teams.red

            for s in match.slots:
                if s.status & slotStatus.has_player:
                    s.team = team

            match.type = self.m.type

        if match.win_cond != self.m.win_cond and not match.clan_battle:
            match.win_cond = self.m.win_cond

        if not match.clan_battle:
            match.name = self.m.name

        match.enqueue_state()

@packet
class startMatch(BanchoPacket, type=Packets.OSU_MATCH_START):
    async def handle(self, user: Player):
        if not (match := user.match):
            return

        if user is not match.host:
            return
        
        match.start()

@packet
class updateMatchScore(BanchoPacket, type=Packets.OSU_MATCH_SCORE_UPDATE):
    data: osuTypes.raw

    async def handle(self, user: Player):
        if not (match := user.match):
            return
        
        r = bytearray(b'0\x00\x00')
        r += len(self.data).to_bytes(4, 'little')
        r += self.data
        r[11] = match.get_slot_id(user)

        match.enqueue(bytes(r), lobby=False)

@packet
class finishMatch(BanchoPacket, type=Packets.OSU_MATCH_COMPLETE):
    async def handle(self, user: Player):
        if not (match := user.match):
            return

        slot = match.get_slot(user)
        slot.status = slotStatus.complete

        if any((s.status is slotStatus.playing for s in match.slots)):
            return

        no_play = []

        for slot in match.slots:
            if slot.status & slotStatus.has_player and slot.status != slotStatus.complete:
                no_play.append(slot.player.id)

        match.unready_players(slotStatus.complete)
        match.in_prog = False

        match.enqueue(packets.matchComplete(), lobby=False, ignore=no_play)
        match.enqueue_state()

        if match.clan_battle:
            await match.clan_scores(no_play)

@packet
class changeMatchMods(BanchoPacket, type=Packets.OSU_MATCH_CHANGE_MODS):
    mods: osuTypes.i32

    async def handle(self, user: Player):
        if not (match := user.match):
            return

        if match.fm:
            if user is match.host:
                match.mods = self.mods & Mods.SPEED_MODS
                if match.clan_battle:
                    match.mods = (self.mods & Mods.SPEED_MODS) & Mods.GAME_CHANGING

            slot = match.get_slot(user)
            slot.mods = self.mods & ~Mods.SPEED_MODS
            if match.clan_battle:
                slot.mods = (self.mods & ~Mods.SPEED_MODS) & ~Mods.GAME_CHANGING
        else:
            if user is not match.host:
                return

            match.mods = self.mods
        
        match.enqueue_state()

@packet
class matchLoaded(BanchoPacket, type=Packets.OSU_MATCH_LOAD_COMPLETE):
    async def handle(self, user: Player):
        if not (match := user.match):
            return
        
        slot = match.get_slot(user)
        slot.loaded = True

        slot_bools = [s.playing for s in match.slots]
        if not any(slot_bools):
            match.enqueue(packets.matchAllLoaded(), lobby=False)

@packet
class matchPlayerMissingMap(BanchoPacket, type=Packets.OSU_MATCH_NO_BEATMAP):
    async def handle(self, user: Player):
        if not (match := user.match):
            return

        slot = match.get_slot(user)
        slot.status = slotStatus.no_map

        match.enqueue_state(lobby=False)

@packet
class matchPlayerUnready(BanchoPacket, type=Packets.OSU_MATCH_NOT_READY):
    async def handle(self, user: Player):
        if not (match := user.match):
            return

        slot = match.get_slot(user)
        slot.status = slotStatus.not_ready

        match.enqueue_state(lobby=False)

@packet
class matchPlayerFailed(BanchoPacket, type=Packets.OSU_MATCH_FAILED):
    async def handle(self, user: Player):
        if not (match := user.match):
            return

        slot = match.get_slot_id(user)
        match.enqueue(packets.matchPlayerFailed(slot), lobby=False)

@packet
class matchPlayerHasMap(BanchoPacket, type=Packets.OSU_MATCH_HAS_BEATMAP):
    async def handle(self, user: Player):
        if not (match := user.match):
            return

        slot = match.get_slot(user)
        slot.status = slotStatus.not_ready

        match.enqueue_state(lobby=False)

@packet
class matchPlayerSkip(BanchoPacket, type=Packets.OSU_MATCH_SKIP_REQUEST):
    async def handle(self, user: Player):
        if not (match := user.match):
            return
    
        slot = match.get_slot(user)
        slot.skipped = True

        match.enqueue(packets.matchPlayerSkipped(user.id))

        for slot in match.slots:
            if slot.status is slotStatus.playing and not slot.skipped:
                return
        
        match.enqueue(packets.matchSkip(), lobby=False)

@packet
class matchChangeHost(BanchoPacket, type=Packets.OSU_MATCH_TRANSFER_HOST):
    slot: osuTypes.i32

    async def handle(self, user: Player):
        if not (match := user.match):
            return
        
        if user is not match.host:
            return

        if not (host := match.slots[self.slot].player):
            return

        if match.clan_battle:
            return

        match.host = host
        match.host.enqueue(packets.matchTransferHost())

        match.enqueue_state()

@packet
class matchPlayerChangeTeam(BanchoPacket, type=Packets.OSU_MATCH_CHANGE_TEAM):
    async def handle(self, user: Player):
        if not (match := user.match):
            return
        
        if match.clan_battle:
            return
        
        slot = match.get_slot(user)

        if slot.team is Teams.teamless:
            return # ???

        if slot.team is Teams.blue:
            slot.team = Teams.red
        else:
            slot.team = Teams.blue

        match.enqueue_state(lobby=False)

@packet
class matchInvite(BanchoPacket, type=Packets.OSU_MATCH_INVITE):
    uid: osuTypes.i32

    async def handle(self, user: Player):
        if not user.match:
            return
        
        if not (target := glob.players_id.get(self.uid)):
            return
        
        if target is glob.bot:
            return
        
        target.enqueue(packets.matchInvite(user, target.name))

@packet
class matchChangePassword(BanchoPacket, type=Packets.OSU_MATCH_CHANGE_PASSWORD):
    m: osuTypes.match

    async def handle(self, user: Player):
        if not (match := user.match):
            return
        
        if user is not match.host:
            return

        match.pw = self.m.pw

        match.enqueue_state()

@bancho.route("/", methods=['GET']) # only accept GET requests as POST is for login method, see login method below
async def root_http():
    pl = '\n'.join(p.name for p in glob.players.values())
    message = f"{pyfiglet.figlet_format(f'Asahi v{glob.version}')}\n\ntsunyoku attempts bancho v2, gone right :sunglasses:\n\nOnline Players:\n{pl}"
    return Response(message, mimetype='text/plain')

@bancho.route("/", methods=['POST']) # only accept POST requests, we can assume it is for a login request but we can deny access if not
async def root_client():
    start = time.time()
    headers = request.headers # request headers, used for things such as user ip and agent

    if 'User-Agent' not in headers or headers['User-Agent'] != 'osu!':
        # request isn't sent from osu client, return html
        return b''

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

        bcache = glob.cache['pw'] # get our cached pws to potentially enhance speed
        user_pw = user['pw'].encode('ISO-8859-1').decode('unicode-escape').encode('ISO-8859-1') # this is cursed SHUT UP
        if user_pw in bcache:
            if pw != bcache[user_pw]: # compare provided md5 with the stored (cached) pw to ensure they have provided the correct password
                if glob.config.debug:
                    log(f"{username}'s login attempt failed: provided an incorrect password", Ansi.LRED)
                resp = await make_response(packets.userID(-1))
                resp.headers['cho-token'] = 'no'
                return resp
        else:
            k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'')
            try:
                k.verify(pw, user_pw)
            except Exception:
                if glob.config.debug:
                    log(f"{username}'s login attempt failed: provided an incorrect password", Ansi.LRED)
                resp = await make_response(packets.userID(-1))
                resp.headers['cho-token'] = 'no'
                return resp

            bcache[user_pw] = pw # cache pw for future

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

        if p.clan:
            p.join_chan(p.clan.chan)
            data += packets.channelJoin(p.clan.chan.name)
            data += packets.channelInfo(p.clan.chan)

            # check if clan is in battle, if so: send invite to them too
            if (m := p.clan.battle):
                if not m.battle_ready:
                    # battle hasn't started/isn't ready yet, lets invite them too!
                    if p.clan == m.clan_1:
                        against = m.clan_2
                        add = 'online1'
                    else:
                        against = m.clan_1
                        add = 'online2'
                    
                    data += packets.sendMessage(fromname=glob.bot.name, msg=f'Your clan has initiated in a clan battle against the clan {against.name}! Please join the battle here: {m.embed}', tarname=p.name, fromid=glob.bot.id)

                    # update player lists for the battle
                    b1 = glob.clan_battles[m.clan_1]
                    b2 = glob.clan_battles[m.clan_2]

                    b1['total'].append(p)
                    b2['total'].append(p)
                    b1[add].append(p)
                    b2[add].append(p)

        elapsed = (time.time() - start) * 1000
        data += packets.notification(f'Welcome to Asahi v{glob.version}\n\nTime Elapsed: {elapsed:.2f}ms') # send notification as indicator they've logged in i guess
        log(f'{p.name} successfully logged in.', Ansi.LBLUE)

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

        if glob.config.debug:
            log(f'Packet {packet.type.name} handled for user {p.name}', Ansi.LMAGENTA)

    data = bytearray()
    while not p.queue_empty():
        data += p.dequeue()

    resp = await make_response(bytes(data))
    resp.headers['Content-Type'] = 'text/html; charset=UTF-8' # ?
    return resp
