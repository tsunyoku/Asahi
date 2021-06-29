# external imports (some may require to be installed, install using ext/requirements.txt)
from xevel import Router # web server :blobcowboi:
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
from constants import regexes
from packets import writer, reader
from packets.writer import Packets

bancho = Router({f'c.{glob.config.domain}', f'c4.{glob.config.domain}', f'ce.{glob.config.domain}'}) # handler for webserver :D
rdr = database.Reader('ext/geoloc.mmdb')

def packet(pck: Packets, allow_res: bool = False):
    def wrapper(_cb):
        glob.packets |= {pck: _cb}
        
        if allow_res:
            glob.packets_restricted |= {pck: _cb}

    return wrapper

@packet(Packets.OSU_REQUEST_STATUS_UPDATE, allow_res=True)
async def update_stats(user: Player, p):
    user.enqueue(writer.userStats(user))
        
@packet(Packets.OSU_USER_STATS_REQUEST, allow_res=True)
async def request_stats(user: Player, p):
    uids = (reader.handle_packet(p, (('uids', osuTypes.i32_list),)))['uids']
    
    for o in glob.players.values():
        if o.id != user.id and o.id in uids and not o.restricted:
            user.enqueue(writer.userStats(o))
            
@packet(Packets.OSU_USER_PRESENCE_REQUEST)
async def presence_request(user: Player, p):
    uids = (reader.handle_packet(p, (('uids', osuTypes.i32_list),)))['uids']
    
    for u in uid:
        if o := glob.players_id.get(u):
            user.enqueue(writer.userPresence(o))
        
@packet(Packets.OSU_USER_PRESENCE_REQUEST)
async def presence_request_all(user: Player, p):
    for o in glob.players.values():
        if o.id != user.id:
            user.enqueue(writer.userPresence(o))
            
@packet(Packets.OSU_FRIEND_ADD)
async def friend_add(user: Player, p):
    tar = (reader.handle_packet(p, (('uid', osuTypes.i32),)))['uid']
    req = user.id
    
    if tar in user.friends:
        return

    user.friends.append(tar)
    await glob.db.execute('INSERT INTO friends (user1, user2) VALUES ($1, $2)', req, tar)
    
    log(f"{user.name} added UID {tar} into their friends list.", Ansi.LCYAN)

@packet(Packets.OSU_FRIEND_REMOVE)
async def friend_remove(user: Player, p):
    tar = (reader.handle_packet(p, (('uid', osuTypes.i32),)))['uid']
    req = user.id

    if tar not in user.friends:
        return

    user.friends.remove(tar)
    await glob.db.execute('DELETE FROM friends WHERE user1 = $1 AND user2 = $2', req, tar)

    log(f"{user.name} removed UID {tar} from their friends list.", Ansi.LCYAN)
    
@packet(Packets.OSU_LOGOUT, allow_res=True)
async def logout(user: Player, p):
    if (time.time() - user.login_time) < 1:
        return
    
    user.logout()
    log(f'{user.name} logged out.', Ansi.LBLUE)
    
@packet(Packets.OSU_SEND_PRIVATE_MESSAGE)
async def send_pm(user: Player, p):
    d = reader.handle_packet(p, (('msg', osuTypes.message),))
    
    msg = d['msg'].msg
    tarname = d['msg'].tarname

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
                user.enqueue(writer.sendMessage(fromname = target.name, msg = cmd, tarname = user.name, fromid = target.id))
        elif m := npr.match(msg):
            user.np = await Beatmap.bid_fetch(int(m['bid']))
            np = await user.np.np_msg()
            user.enqueue(writer.sendMessage(fromname = target.name, msg = np, tarname = user.name, fromid = target.id))
    else:
        target.enqueue(writer.sendMessage(fromname = user.name, msg = msg, tarname = target.name, fromid = user.id))
        log(f'{user.name} sent message "{msg}" to {tarname}', Ansi.LCYAN)
        
@packet(Packets.OSU_SEND_PUBLIC_MESSAGE)
async def send_msg(user: Player, p):
    d = reader.handle_packet(p, (('msg', osuTypes.message),))

    msg = d['msg'].msg
    chan = d['msg'].tarname
    
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

@packet(Packets.OSU_CHANNEL_JOIN, allow_res=True)
async def join_chan(user: Player, p):
    name = (reader.handle_packet(p, (('chan', osuTypes.string),)))['chan']

    if name == '#spectator':
        if user.spectating is not None:
            uid = user.spectating.id
        elif user.spectators:
            uid = user.id
        else:
            return # not spectating

        chan = glob.channels.get(f'#spec_{uid}')
    elif name == '#multiplayer':
        if not user.match:
            return

        m = user.match.id
        chan = glob.channels.get(f'#multi_{m}')
    elif name == '#clan':
        if not user.clan:
            return

        chan = user.clan.chan
    else:
        chan = glob.channels.get(name)

    if not chan:
        return

    user.join_chan(chan)
    
@packet(Packets.OSU_CHANNEL_PART, allow_res=True)
async def leave_chan(user: Player, p):
    name = (reader.handle_packet(p, (('chan', osuTypes.string),)))['chan']

    if name in ['#highlight', '#userlog'] or not name.startswith('#'): # osu why!!!
        return

    if name == '#spectator':
        if user.spectating is not None:
            uid = user.spectating.id
        elif user.spectators:
            uid = user.id
        else:
            return # not spectating

        chan = glob.channels.get(f'#spec_{uid}')
    elif name == '#multiplayer':
        if not user.match:
            return

        m = user.match.id
        chan = glob.channels.get(f'#multi_{m}')
    elif name == '#clan':
        if not user.clan:
            return

        chan = user.clan.chan
    else:
        chan = glob.channels.get(name)

    if not chan:
        return

    if user not in chan.players:
        return

    user.leave_chan(chan)
    for o in chan.players:
        o.enqueue(writer.channelInfo(chan))
        
@packet(Packets.OSU_CHANGE_ACTION, allow_res=True)
async def update_action(user: Player, p):
    d = reader.handle_packet(p, (
        ('actionid', osuTypes.u8), 
        ('info', osuTypes.string),
        ('md5', osuTypes.string),
        ('mods', osuTypes.u32),
        ('mode', osuTypes.u8),
        ('mid', osuTypes.i32)
    ))
    
    if d['actionid'] == 0 and d['mods'] & Mods.RELAX:
        d['info'] = 'on Relax'
    elif d['actionid'] == 0 and d['mods'] & Mods.AUTOPILOT:
        d['info'] = 'on Autopilot'
        
    user.action = d['actionid']
    user.info = d['info']
    user.map_md5 = d['md5']
    user.mods = d['mods']
    
    if user.mods & Mods.RELAX:
        user.mode_vn = d['mode']
        d['mode'] += 4
    elif user.mods & Mods.AUTOPILOT:
        user.mode_vn = 0
        d['mode'] = 7
        
    user.mode = d['mode']
    user.map_id = d['mid']
    
    if d['actionid'] == 2:
        user.info += f' +{convert(d["mods"])}'
        
    if not user.restricted:
        for o in glob.players.values():
            o.enqueue(writer.userStats(user))
        
@packet(Packets.OSU_START_SPECTATING)
async def start_spec(user: Player, p):
    tid = (reader.handle_packet(p, (('tid', osuTypes.i32),)))['tid']
    
    if tid == 1:
        return
    
    if not (target := glob.player_id.get(tid)):
        return
    
    target.add_spectator(user)
    
@packet(Packets.OSU_STOP_SPECTATING)
async def stop_spec(user: Player, p):
    if not (host := user.spectating):
        return
    
    host.remove_spectator(user)
    
@packet(Packets.OSU_SPECTATE_FRAMES)
async def spec_frames(user: Player, p):
    frames = (reader.handle_packet(p, (('frames', osuTypes.raw),)))['frames']
    
    for u in user.spectators:
        u.enqueue(writer.spectateFrames(frames))

@packet(Packets.OSU_JOIN_LOBBY)
async def join_lobby(user: Player, p):
    for m in glob.matches:
        user.enqueue(writer.newMatch(m))
        
@packet(Packets.OSU_PART_LOBBY)
async def leave_lobby(user: Player, p):
    pass # lol

@packet(Packets.OSU_CREATE_MATCH)
async def create_match(user: Player, p):
    match = (reader.handle_packet(p, (('match', osuTypes.match),)))['match']
    
    glob.matches[match.id] = match
    if not glob.matches.get(match.id):
        return user.enqueue(writer.matchJoinFail())
    
    mp_chan = Channel(name=f'#multiplayer', desc=f'Multiplayer channel for match ID {match.id}', auto=False, perm=False)
    glob.channels[f'#multi_{match.id}'] = mp_chan
    match.chat = mp_chan
    
    user.join_match(match, match.pw)
    log(f'{user.name} created a new multiplayer lobby.', Ansi.LBLUE)
    
@packet(Packets.OSU_JOIN_MATCH)
async def join_match(user: Player, p):
    d = reader.handle_packet(p, (('id', osuTypes.i32), ('pw', osuTypes.string),))
    id = d['id']
    pw = d['pw']
    
    if id >= 1000:
        if not (menu := glob.menus.get(id)):
            return user.enqueue(writer.matchJoinFail())
        
        return await menu.handle(user)
    
    if not (match := glob.matches.get(id)):
        return user.enqueue(writer.matchJoinFail())
    
    if match.clan_battle:
        if user.clan not in (match.clan_1, match.clan_2) or match.battle_ready:
            return user.enqueue(writer.matchJoinFail())
        
    user.join_match(match, pw)
    
    if match.clan_battle:
        total = []
        for slot in match.slots:
            if slot.status & slotStatus.has_player:
                total.append(slot.player)
                
        battle = glob.clan_battles[user.clan]
        if set(total) == set(battle['total']):
            await match.strat_battle()
            
@packet(Packets.OSU_PART_MATCH)
async def leave_match(user: Player, p):
    user.leave_match()
        
@packet(Packets.OSU_MATCH_CHANGE_SLOT)
async def change_slot(user: Player, p):
    id = (reader.handle_packet(p, (('id', osuTypes.i32),)))['id']
    
    if not (match := user.match):
        return
    
    if match.slots[id] != slotStatus.open:
        return
    
    old = match.get_slot(user)
    new = match.slots[id]
    
    new.copy(old)
    old.reset()
    
    match.enqueue_state()
    
@packet(Packets.OSU_MATCH_READY)
async def user_ready(user: Player, p):
    if not (match := user.match):
        return
    
    slot = match.get_slot(user)
    slot.status = slotStatus.ready
    
    match.enqueue_state(lobby=False)
    
@packet(Packets.OSU_MATCH_LOCK)
async def lock_slot(user: Player, p):
    id = (reader.handle_packet(p, (('id', osuTypes.i32),)))['id']
    
    if not (match := user.match) or match.clan_battle or user is not match.host:
        return
    
    slot = match.slots[id]
    
    if slot.status == slotStatus.locked:
        slot.status = slotStatus.open
    else:
        if slot.player is match.host:
            return
        
        slot.status = slotStatus.locked
        
    match.enqueue_state()
    
@packet(Packets.OSU_MATCH_CHANGE_SETTINGS)
async def match_settings(user: Player, p):
    m = (reader.handle_packet(p, (('m', osuTypes.match),)))['m']

    if not (match := user.match) or user is not match.host:
        return

    if m.fm != match.fm:
        match.fm = m.fm

    if m.fm:
        for s in match.slots:
            if s.status & slotStatus.has_player:
                s.mods = match.mods & ~Mods.SPEED_MODS
                if match.clan_battle:
                    s.mods = match.mods &~ Mods.SPEED_MODS

        match.mods &= Mods.SPEED_MODS
    else:
        host = match.get_host()
        match.mods &= Mods.SPEED_MODS
        match.mods |= host.mods

        for s in match.slots:
            if s.status & slotStatus.has_player:
                s.mods = Mods.NOMOD

    if m.bname == '':
        match.unready_players(slotStatus.ready)

    if m.bmd5 != match.bmd5:
        m = await Beatmap.from_md5(m.bmd5)

        if m:
            match.bid = m.id
            match.bmd5 = m.md5
            match.bname = m.name
            match.mode = m.mode
        else:
            match.bid = m.bid
            match.bmd5 = m.bmd5
            match.bname = m.bname
            match.mode = m.mode

    if match.type != m.type and not match.clan_battle:
        if m.type in (teamTypes.head, teamTypes.tag):
            team = Teams.neutral
        else:
            team = Teams.red

        for s in match.slots:
            if s.status & slotStatus.has_player:
                s.team = team

        match.type = m.type

    if match.win_cond != m.win_cond and not match.clan_battle:
        match.win_cond = m.win_cond

    if not match.clan_battle:
        match.name = m.name

    match.enqueue_state()
    
@packet(Packets.OSU_MATCH_START)
async def start_match(user: Player, p):
    if not (match := user.match) or user is not match.host:
        return
    
    match.start()
    
@packet(Packets.OSU_MATCH_SCORE_UPDATE)
async def match_score(user: Player, p):
    data = (reader.handle_packet(p, (('data', osuTypes.raw),)))['data']
    
    if not (match := user.match):
        return
    
    r = bytearray(b'0\x00\x00')
    r += len(data).to_bytes(4, 'little')
    r += data
    r[11] = match.get_slot_id(user)
    
    match.enqueue(bytes(r), lobby=False)

@packet(Packets.OSU_MATCH_COMPLETE)
async def finish_match(user: Player, p):
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
    
    match.enqueue(writer.matchComplete(), lobby=False, ignore=no_play)
    match.enqueue_state()
    
    if match.clan_battle:
        await match.clan_scores(no_play)
        
@packet(Packets.OSU_MATCH_CHANGE_MODS)
async def match_mods(user: Player, p):
    mods = (reader.handle_packet(p, (('mods', osuTypes.i32),)))['mods']
    
    if not (match := user.match):
        return

    if match.fm:
        if user is match.host:
            match.mods = mods & Mods.SPEED_MODS

        slot = match.get_slot(user)
        slot.mods = mods & ~Mods.SPEED_MODS
    else:
        if user is not match.host:
            return

        match.mods = mods

    match.enqueue_state()
    
@packet(Packets.OSU_MATCH_LOAD_COMPLETE)
async def match_loaded(user: Player, p):
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.loaded = True

    slot_bools = [s.playing for s in match.slots]
    if not any(slot_bools):
        match.enqueue(writer.matchAllLoaded(), lobby=False)
        
@packet(Packets.OSU_MATCH_NO_BEATMAP)
async def match_nomap(user: Player, p):
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.status = slotStatus.no_map

    match.enqueue_state(lobby=False) 
    
@packet(Packets.OSU_MATCH_NOT_READY)
async def user_unready(user: Player, p):
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.status = slotStatus.not_ready

    match.enqueue_state(lobby=False)
    
@packet(Packets.OSU_MATCH_FAILED)
async def user_failed(user: Player, p):
    if not (match := user.match):
        return

    slot = match.get_slot_id(user)
    match.enqueue(writer.matchPlayerFailed(slot), lobby=False)
    
@packet(Packets.OSU_MATCH_HAS_BEATMAP)
async def user_map(user: Player, p):
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.status = slotStatus.not_ready

    match.enqueue_state(lobby=False)
    
@packet(Packets.OSU_MATCH_SKIP_REQUEST)
async def user_skip(user: Player, p):
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.skipped = True

    match.enqueue(writer.matchPlayerSkipped(user.id))

    for slot in match.slots:
        if slot.status is slotStatus.playing and not slot.skipped:
            return

    match.enqueue(writer.matchSkip(), lobby=False)
    
@packet(Packets.OSU_MATCH_TRANSFER_HOST)
async def match_host(user: Player, p):
    slot = (reader.handle_packet(p, (('slot', osuTypes.i32),)))['slot']
    
    if not (match := user.match) or user is not match.host or not (host := match.slots[slot].player) or match.clan_battle:
        return
    
    match.host = host
    match.host.enqueue(writer.matchTransferHost())
    match.enqueue_state()
    
@packet(Packets.OSU_MATCH_CHANGE_TEAM)
async def match_team(user: Player, p):
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
    
@packet(Packets.OSU_MATCH_INVITE)
async def match_invite(user: Player, p):
    uid = (reader.handle_packet(p, (('uid', osuTypes.i32),)))['uid']
    
    if not user.match or not (target := glob.players_id.get(uid)) or target is glob.bot:
        return
    
    target.enqueue(writer.matchInvite(user, target.name))
    
@packet(Packets.OSU_MATCH_CHANGE_PASSWORD)
async def match_pw(user: Player, p):
    m = (reader.handle_packet(p, (('m', osuTypes.match),)))['m']
    
    if not (match := user.match) or user is not match.host:
        return
    
    match.pw = m.pw
    match.enqueue_state()

def root_web():
    pl = '\n'.join(p.name for p in glob.players.values())
    message = f"{pyfiglet.figlet_format(f'Asahi v{glob.version}')}\n\ntsunyoku attempts bancho v2, gone right :sunglasses:\n\nOnline Players:\n{pl}"
    return message.encode()

@bancho.route("/", ['POST', 'GET']) # only accept POST requests, we can assume it is for a login request but we can deny access if not
async def root_client(request):
    start = time.time()
    headers = request.headers # request headers, used for things such as user ip and agent

    if 'User-Agent' not in headers or headers['User-Agent'] != 'osu!' or request.type == 'GET':
        # request isn't sent from osu client, return html
        return root_web()

    if 'osu-token' not in headers: # sometimes a login request will be a re-connect attempt, in which case they will already have a token, if not: login the user
        data = request.body # request data, used to get info such as username to login the user
        if len(info := data.decode().split('\n')[:-1]) != 3: # format data so we can use it easier & also ensure it is valid at the same time
            request.resp_headers['cho-token'] = 'no' # client knows there is something up if we set token to 'no'
            return writer.userID(-2)

        if len(cinfo := info[2].split('|')) != 5: # format client data (hash, utc etc.) & ensure it is valid
            request.resp_headers['cho-token'] = 'no' # client knows there is something up if we set token to 'no'
            return writer.userID(-2)

        username = info[0]
        pw = info[1].encode() # password in md5 form, we will use this to compare against db's stored bcrypt later    
        osu_ver = regexes.osu_ver.match(cinfo[0])

        if glob.config.anticheat:
            if int(osu_ver['ver']) <= 20210125:
                request.resp_headers['cho-token'] = 'no'
                return writer.versionUpdateForced() + writer.userID(-2)
         
        user = await glob.db.fetchrow("SELECT id, pw, country, name, priv FROM users WHERE name = $1", username)
        if not user: # ensure user actually exists before attempting to do anything else
            if glob.config.debug:
                log(f'User {username} does not exist.', Ansi.LRED)

            request.resp_headers['cho-token'] = 'no' # client knows there is something up if we set token to 'no'
            return writer.userID(-1)

        bcache = glob.cache['pw'] # get our cached pws to potentially enhance speed
        user_pw = user['pw'].encode('ISO-8859-1').decode('unicode-escape').encode('ISO-8859-1') # this is cursed SHUT UP
        if user_pw in bcache:
            if pw != bcache[user_pw]: # compare provided md5 with the stored (cached) pw to ensure they have provided the correct password
                if glob.config.debug:
                    log(f"{username}'s login attempt failed: provided an incorrect password", Ansi.LRED)

                request.resp_headers['cho-token'] = 'no' # client knows there is something up if we set token to 'no'
                return writer.userID(-1)
        else:
            k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'')
            try:
                k.verify(pw, user_pw)
            except Exception as e:
                if glob.config.debug:
                    log(f"{username}'s login attempt failed: provided an incorrect password", Ansi.LRED)

                request.resp_headers['cho-token'] = 'no' # client knows there is something up if we set token to 'no'
                return writer.userID(-1)

            bcache[user_pw] = pw # cache pw for future

        if not user['priv'] & Privileges.Banned:
            request.resp_headers['cho-token'] = 'no'
            return writer.userID(-3)

        if (p := glob.players_id.get(user['id'])):
            if (start - p.last_ping) > 10: # game crashes n shit
                p.logout()

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
            geoloc = rdr.city(ip)
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


        data = bytearray(writer.userID(p.id)) # initiate login by providing the user's id
        data += writer.protocolVersion(19) # no clue what this does
        data += writer.banchoPrivileges(p.client_priv | ClientPrivileges.Supporter)
        data += (writer.userPresence(p) + writer.userStats(p)) # provide user & other user's presence/stats (for f9 + user stats)
        data += writer.channelInfoEnd() # no clue what this does either
        data += writer.menuIcon() # set main menu icon
        data += writer.friends(p.friends) # send user friend list
        data += writer.silenceEnd(0) # force to 0 for now since silences arent a thing

        # get channels from cache and send to user
        for chan in glob.channels.values():
            if chan.auto:
                p.join_chan(chan)
                data += writer.channelJoin(chan.name) # only join user to channel if the channel is meant for purpose

            data += writer.channelInfo(chan) # regardless of whether the channel should be auto-joined we should make the client aware of it

        if glob.config.anticheat and not osu_ver:
            await p.restrict(reason='Missing osu! version')
            data += writer.notification('Cheat advantages are not allowed! Your account has been restricted.')

        # add user to cache?
        glob.players[p.token] = p
        glob.players_name[p.name] = p
        glob.players_id[p.id] = p
        for o in glob.players.values(): # enqueue other users to client
            if not p.restricted:
                o.enqueue((writer.userPresence(p) + writer.userStats(p))) # enqueue this user to every other logged in user

            data += (writer.userPresence(o) + writer.userStats(o)) # enqueue every other logged in user to this user

        if p.clan:
            p.join_chan(p.clan.chan)
            data += writer.channelJoin(p.clan.chan.name)
            data += writer.channelInfo(p.clan.chan)

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
                    
                    data += writer.sendMessage(fromname=glob.bot.name, msg=f'Your clan has initiated in a clan battle against the clan {against.name}! Please join the battle here: {m.embed}', tarname=p.name, fromid=glob.bot.id)

                    # update player lists for the battle
                    b1 = glob.clan_battles[m.clan_1]
                    b2 = glob.clan_battles[m.clan_2]

                    b1['total'].append(p)
                    b2['total'].append(p)
                    b1[add].append(p)
                    b2[add].append(p)
                
        if p.restricted:
            data += writer.sendMessage(fromname=glob.bot.name, msg='Your account is currently restricted!', tarname=p.name, fromid=glob.bot.id)

        elapsed = (time.time() - start) * 1000
        data += writer.notification(f'Welcome to Asahi v{glob.version}\n\nTime Elapsed: {elapsed:.2f}ms') # send notification as indicator they've logged in i guess
        log(f'{p.name} successfully logged in.', Ansi.LBLUE)

        request.resp_headers['cho-token'] = token
        return bytes(data)

    # if we have made it this far then it's a reconnect attempt with token already provided
    user_token = headers['osu-token'] # client-provided token
    if not (p := glob.players.get(user_token)):
        # user is logged in but token is not found? most likely a restart so we force a reconnection
        return writer.restartServer(0)

    # handle any packets the client has sent
    body = request.body
    
    if p.restricted:
        pm = glob.packets_restricted
    else:
        pm = glob.packets

    for pck, cb in pm.items():
        if body[0] == 4:
            continue # fuck OSU_PING

        if body[0] == pck:
            await cb(p, body)

            if glob.config.debug:
                log(f'Packet {pck.name} handled for user {p.name}', Ansi.LMAGENTA)

    p.last_ping = time.time()

    request.resp_headers['Content-Type'] = 'text/html; charset=UTF-8' # ?

    if not (d := p.dequeue()):
        return b''

    return d
