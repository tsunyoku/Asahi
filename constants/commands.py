from objects import glob
from objects.match import Match, slotStatus
from objects.channel import Channel
from objects.beatmap import Beatmap
from objects.player import Player
from objects.menu import Menu
from objects.score import Score
from cmyui import log, Ansi
from cmyui.discord import Webhook, Embed
from packets import writer
from .privs import Privileges
from .types import teamTypes
from .modes import osuModes
from .mods import Mods
from .statuses import strStatuses, mapStatuses

import time
import asyncio

cmds = []
mp_cmds = []

def command(priv: Privileges = Privileges.Normal, name: str = None, elapsed: bool = True, allow_public: bool = False):
    def wrapper(cmd_cb):
        if name is not None:
            if not isinstance(name, list):
                cmds.append({
                    'name': name, 
                    'priv': priv, 
                    'elapsed': elapsed, 
                    'cb': cmd_cb,
                    'allow_public': allow_public,
                    'desc': cmd_cb.__doc__
                })
            else:
                for n in name:
                    cmds.append({
                        'name': n,
                        'priv': priv,
                        'elapsed': elapsed,
                        'cb': cmd_cb,
                        'allow_public': allow_public,
                        'desc': cmd_cb.__doc__
                    }) 
        else:
            log(f'Tried to add command with no name!', Ansi.LRED)
        
        return cmd_cb
    return wrapper

@command(name='help', elapsed=False)
async def help(user, args):
    """Displays all available commands to the user"""
    allowed_cmds = []
    for cmd in cmds:
        if user.priv & cmd['priv']:
            s = f'{glob.config.prefix}{cmd["name"]} - {cmd["desc"]}'
            allowed_cmds.append(s)

    cmd_list = '\n'.join(allowed_cmds)
    return f'List of available commands:\n\n{cmd_list}'

@command(name=['last', 'l', 'recent', 'r', 'rs'], elapsed=False, allow_public=True)
async def last_score(user, args):
    if (score := user.last_score):
        return await score.format()
    
    return 'No recent score found!'

@command(name=['verify', 'link']):
async def link_discord(user, args):
    if len(args) < 1:
        return 'Please provide a verification code!'

    if user.discord:
        return 'You already have your account linked to a Discord account.'

    if not (code := glob.codes.get(user)):
        return 'We were unable to find your link attempt. Please run the link command in Discord another time and try again.'

    if args[0] != code['code']:
        return 'Incorrect verification code!'
    
    user.discord = code['discord']
    await glob.db.execute('UPDATE users SET discord = %s WHERE id = %s', [user.discord, user.id])
    return 'Discord account linked!'

@command(priv=Privileges.Owner, name='addpriv')
async def add_priv(user, args):
    """Adds (a list of) privileges to a user"""
    if len(args) < 2:
        return "You haven't provided a username and privileges!"
    
    name = args[0]

    if not (user := await glob.players.get(name=name, sql=True)):
        return 'Couldn\'t find this user!'

    new_privs = Privileges(0)
    for npriv in args[1:]:
        if not (new_priv := Privileges.get(npriv)):
            return f'Privilege {npriv} not found.'

        new_privs |= new_priv
        
    for priv in new_privs:
        await user.add_priv(priv)

    return f"Added privilege(s) {new_privs} to {name}."

@command(priv=Privileges.Owner, name='rmpriv')
async def rm_priv(user, args):
    """Removes (a list of) privileges from a user"""
    if len(args) < 2:
        return "You haven't provided a username and privileges!"

    name = args[0]

    if not (user := await glob.players.get(name=name, sql=True)):
        return 'Couldn\'t find this user!'

    new_privs = Privileges(0)
    for npriv in args[1:]:
        if not (new_priv := Privileges.get(npriv)):
            return f'Privilege {npriv} not found.'

        new_privs |= new_priv

    for priv in new_privs:
        await user.remove_priv(priv)

    return f"Removed privilege(s) {new_privs} from {name}."

@command(name='battle')
async def clan_battle(user, args):
    """Battle other clans in a scrim-like multi lobby"""
    if args[0] in ('accept', 'deny'):
        if len(args) < 2:
            return 'Please accept/deny a battle and specify the clan!'

        clan_name = args[1]
        clan = glob.clans.get(await glob.db.fetchval('SELECT id FROM clans WHERE name = %s', [clan_name]))
        
        if not clan:
            return 'We could not find a clan by this name!'

        if not (owner := await glob.players.get(id=clan.owner)):
            return 'Clan owner offline, battle request cancelled!'
        
        if args[1] == 'deny':
            owner.enqueue(writer.sendMessage(fromname=glob.bot.name, msg=f'{user.name} denied your request to battle their clan {clan.name}!', tarname=owner.name, fromid=glob.bot.id))
            return 'Battle request denied!'

        # battle was accepted, create the battle match

        user.enqueue(writer.sendMessage(fromname=glob.bot.name, msg=f'Request accepted! Creating match...', tarname=user.name, fromid=glob.bot.id))
        owner.enqueue(writer.sendMessage(fromname=glob.bot.name, msg=f'{user.name} accepted your request to battle their clan {user.clan.name}! Creating match...', tarname=owner.name, fromid=glob.bot.id))

        match = Match()

        match.name = f'Clan Battle: ({clan.name}) vs ({user.clan.name})'
        match.clan_battle = True

        match.clan_1 = clan
        match.clan_2 = user.clan

        match.host = owner
        match.type = teamTypes.team

        glob.matches[match.id] = match

        mp_chan = Channel(name=f'#multiplayer', desc=f'Multiplayer channel for match ID {match.id}', auto=False, perm=False)
        glob.channels[f'#multi_{match.id}'] = mp_chan
        match.chat = mp_chan

        # get list of potential clan members we should expect
        online1 = []
        for m in clan.members:
            if (e := await glob.players.get(id=m)):
                online1.append(e)

        online2 = []
        for m in user.clan.members:
            if (e := await glob.players.get(id=m)):
                online2.append(e)

        b_info = {'clan1': clan, 'clan2': user.clan, 'online1': online1, 'online2': online2, 'total': (online1 + online2), 'match': match}

        glob.clan_battles[match.clan_1] = b_info
        glob.clan_battles[match.clan_2] = b_info

        for u in online1:
            u.enqueue(writer.sendMessage(fromname=glob.bot.name, msg=f'Your clan has initiated in a clan battle against the clan {user.clan.name}! Please join the battle here: {match.embed}', tarname=u.name, fromid=glob.bot.id)) 

        for u in online2:
            u.enqueue(writer.sendMessage(fromname=glob.bot.name, msg=f'Your clan has initiated in a clan battle against the clan {clan.name}! Please join the battle here: {match.embed}', tarname=u.name, fromid=glob.bot.id))

        return

    if user.clan.owner != user.id:
        return 'You must be the owner of your clan to request a battle!'

    if len(args) < 1:
        return "Please provide a clan to request a battle!"

    clan_name = args[0]
    clan = glob.clans.get(await glob.db.fetchval('SELECT id FROM clans WHERE name = %s', [clan_name]))

    if not clan:
        return 'We could not find a clan by this name!'

    if not (owner := await glob.players.get(id=clan.owner)):
        return 'The clan owner must be online for you to request a battle!'

    owner.enqueue(writer.sendMessage(fromname=glob.bot.name, msg=f'{user.name} has invited you to a clan battle! If you wish to accept then type !battle accept {user.clan.name}, or !battle deny {user.clan.name} to deny. If you accept, a multiplayer match will be created for you and all your online clanmates to battle to the death!', tarname=owner.name, fromid=glob.bot.id))

    return f'Clan battle request sent to {clan.name} clan!'

@command(priv=Privileges.Nominator, name='map')
async def _map(user, args):
    """Update map statuses on the server"""
    if len(args) != 2:
        return 'Please provide the new status & whether we should update the map/set! (!map <rank/love/unrank> <map/set>)'

    status = args[0]
    _type = args[1]

    if status not in ('love', 'rank', 'unrank') or _type not in ('set', 'map'):
        return 'Invalid syntax! Command: !map <rank/love/unrank> <set/map>'

    bmap = user.np
    ns = strStatuses(status)

    if _type == 'map':
        bmap.status = ns
        bmap.frozen = True

        # reset lb cache in case of major status change
        bmap.lb = None
        bmap.lb_rx = None
        bmap.lb_ap = None
        
        await bmap.save()
        glob.cache['maps'][bmap.md5] = bmap
    else:
        _set = await glob.db.fetch('SELECT md5 FROM maps WHERE sid = %s', [bmap.sid])

        for m in _set:
            md5 = m['md5']
            bm = await Beatmap.from_md5(md5)
            bm.status = ns
            bm.frozen = True

            # reset lb cache in case of major status change
            bm.lb = None
            bm.lb_rx = None
            bm.lb_ap = None
            
            await bm.save()
            glob.cache['maps'][bm.md5] = bm
    
    if (wh_url := glob.config.webhooks['maps']):
        wh = Webhook(url=wh_url)
        embed = Embed(title='')
        
        embed.set_author(url=f'https://{glob.config.domain}/u/{user.id}', name=user.name, icon_url=f'https://a.{glob.config.domain}/{user.id}')
        embed.set_image(url=f'https://assets.ppy.sh/beatmaps/{bmap.sid}/covers/card.jpg')
        embed.add_field(name=f'New {ns.name.lower()} map', value=f'[{bmap.name}]({bmap.url}) is now {ns.name.lower()}!', inline=True)
        
        wh.add_embed(embed)
        await wh.post()

    return 'Status updated!'

@command(priv=Privileges.Nominator, name=['requests', 'reqs'], elapsed=False)
async def reqs(user, args):
    """View all map status requests on the server"""
    if (requests := await glob.db.fetch(f'SELECT * FROM requests')):
        ret = []
        for idx, req in enumerate(requests):
            _map = await Beatmap.bid_fetch(req['map'])
            
            if not _map:
                continue # broken map we'll just skip to next one
                
            mode = repr(osuModes(req['mode']))
            status = mapStatuses(req['status'])
            
            # despite them being saved in cache, these are context based so we cant reuse them, hence destroy arg also
            rank = Menu(id=_map.id + 1, name='Rank', callback=a_req, args=(user, (req['id'], 'rank')), destroy=True) # CURSED CALLBACK
            glob.menus[_map.id + 1] = rank
                
            love = Menu(id=_map.id + 2, name='Love', callback=a_req, args=(user, (req['id'], 'love')), destroy=True) # CURSED CALLBACK
            glob.menus[_map.id + 2] = love

            deny = Menu(id=_map.id + 3, name='Deny', callback=d_req, args=(user, (req['id'],)), destroy=True) # CURSED CALLBACK
            glob.menus[_map.id + 3] = deny
                
            ret.append(f'Request #{idx + 1}: {req["requester"]} requested {_map.embed} to be {status.name.lower()} (Mode: {mode}) | {rank.embed}  {love.embed}  {deny.embed}')
            
        return '\n'.join(ret)
    
    return 'No requests to read!'

@command(name=['request', 'req'])
async def req(user, args):
    """Request a map status change"""
    if len(args) < 1:
        return 'You must provide what status you want the map to be!'
    
    if not (_map := user.np):
        return 'Please /np the map you want to request first!'
    
    if _map.status == mapStatuses.Ranked:
        return 'This map is already ranked!'
    
    ns = strStatuses(args[0])
    
    try:
        await glob.db.execute('INSERT INTO requests (requester, map, status, mode) VALUES (%s, %s, %s, %s)', [user.name, user.np.id, int(ns), user.mode_vn])
    except Exception:
        return "Someone has already requested this map's status to be changed! Your request has not been sent."

    if (wh_url := glob.config.webhooks['requests']):
        wh = Webhook(url=wh_url)
        embed = Embed(title='')

        embed.set_author(url=f'https://{glob.config.domain}/u/{user.id}', name=user.name, icon_url=f'https://a.{glob.config.domain}/{user.id}')
        embed.set_image(url=f'https://assets.ppy.sh/beatmaps/{_map.sid}/covers/card.jpg')
        embed.add_field(name=f'New request', value=f'{user.name} requested [{_map.name}]({_map.url}) to be {ns.name.lower()}', inline=True)

        wh.add_embed(embed)
        await wh.post()

    return 'Request sent!'

@command(priv=Privileges.Admin, name='ban')
async def ban(user, args):
    """Ban a specified user for a specified reason"""
    if len(args) < 2:
        return 'You must provide a user and a reason to ban!'
    
    username = args[0].lower()
    reason = args[1]
    
    if not (target := await glob.players.get(name=username, sql=True)):
        return 'Couldn\'t find this user!'
        
    await target.ban(reason=reason, fr=user)
    
    return 'User banned!'

@command(priv=Privileges.Admin, name='unban')
async def unban(user, args):
    """Unban a specified user for a specified reason"""
    if len(args) < 2:
        return 'You must provide a user and a reason to unban!'

    username = args[0].lower()
    reason = args[1]

    if not (target := await glob.players.get(name=username, sql=True)):
        return 'Couldn\'t find this user!'

    await target.unban(reason=reason, fr=user)

    return 'User unbanned!'

@command(priv=Privileges.Admin, name='restrict')
async def restrict(user, args):
    """Restrict a specified user for a specified reason"""
    if len(args) < 2:
        return 'You must provide a user and a reason to restrict!'

    username = args[0].lower()
    reason = args[1]

    if not (target := await glob.players.get(name=username, sql=True)):
        return 'Couldn\'t find this user!'

    await target.restrict(reason=reason, fr=user)

    return 'User restricted!'

@command(priv=Privileges.Admin, name='unrestrict')
async def unrestrict(user, args):
    """Unrestrict a specified user for a specified reason"""
    if len(args) < 2:
        return 'You must provide a user and a reason to unrestrict!'

    username = args[0].lower()
    reason = args[1]

    if not (target := await glob.players.get(name=username, sql=True)):
        return 'Couldn\'t find this user!'

    await target.unrestrict(reason=reason, fr=user)

    return 'User unrestricted!'

@command(priv=Privileges.Admin, name='freeze')
async def freeze(user, args):
    """Freeze a specified user for a specified reason"""
    if len(args) < 2:
        return 'You must provide a user and a reason to freeze!'

    username = args[0].lower()
    reason = args[1]

    if not (target := await glob.players.get(name=username, sql=True)):
        return 'Couldn\'t find this user!'
        
    if not target:
        return f'User {username} not found!'

    await target.freeze(reason=reason, fr=user)

    return 'User frozen!'

@command(priv=Privileges.Admin, name='unfreeze')
async def unfreeze(user, args):
    """Unfreeze a specified user for a specified reason"""
    if len(args) < 2:
        return 'You must provide a user and a reason to unfreeze!'

    username = args[0].lower()
    reason = args[1]

    if not (target := await glob.players.get(name=username, sql=True)):
        return 'Couldn\'t find this user!'

    await target.unfreeze(reason=reason, fr=user)

    return 'User unfrozen!'

@command(priv=Privileges.Developer, name='crash')
async def crash(user, args):
    """Crash a user's client"""
    if len(args) < 1:
        return 'You must provide a username to crash!'
    
    if not (t := await glob.players.get(id=args[0])):
        return 'User not online'
    
    t.enqueue(b'G\x00\x00\x04\x00\x00\x00\x80\x00\x00\x00\x08\x00\x00\x00\x00\x00\x00')
    
    return ':troll:'

@command(priv=Privileges.Admin, name=['recalc', 'calc', 'recalculate', 'calculate'])
async def recalc(user, args):
   """Recalculate scores globally or on a specific map"""
   if len(args) < 1:
       return 'You must specify what to recalc! (map/all)'
   
   if args[0] == 'map':
       if not (bmap := user.np):
           return 'You must /np the map you want to recalculate first!'
       
       for mode in osuModes:
           scores_db = await glob.db.fetch(f'SELECT id, {mode.sort} sort FROM {mode.table} WHERE md5 = %s AND mode = %s', [bmap.md5, mode.value])
           
           for sc in scores_db:
               score = await Score.sql(sc['id'], mode.table, mode.sort, sc['sort'])
               score.pp, score.sr = await score.calc_pp(mode.as_vn)
               
               await glob.db.execute(f'UPDATE {mode.table} SET pp = %s WHERE id = %s', [score.pp, score.id])

       bmap.lb = None
       bmap.lb_rx = None
       bmap.lb_ap = None

       return f'Recalculated all scores on {bmap.embed}'
   elif args[0] == 'all':
       maps = await glob.db.fetch(f'SELECT md5 FROM maps WHERE status >= {mapStatuses.Ranked}')
       
       for map_sql in maps:
           bmap = await Beatmap.from_md5(map_sql['md5'])

           for mode in osuModes:
               scores_db = await glob.db.fetch(f'SELECT id, {mode.sort} sort FROM {mode.table} WHERE md5 = %s AND mode = %s', [bmap.md5, mode.value])
        
               for sc in scores_db:
                   score = await Score.sql(sc['id'], mode.table, mode.sort, sc['sort'])
                   score.pp, score.sr = await score.calc_pp(mode.as_vn)
        
                   await glob.db.execute(f'UPDATE {mode.table} SET pp = %s WHERE id = %s', [score.pp, score.id])
                   
           bmap.lb = None
           bmap.lb_rx = None
           bmap.lb_ap = None
                   
           user.enqueue(writer.sendMessage(writer.sendMessage(fromname=glob.bot.name, msg=f'Recalculated all scores on {bmap.embed}', tarname=user.name, fromid=glob.bot.id)))
           
       return 'Recalculated all scores!'
   else:
       return 'Unknown recalc option. Valid options: map/all'
        
#####################

async def a_req(user, args):
    """Accept a map status request"""
    if len(args) < 2:
        return 'You must provide the request ID and status to set!'

    request = await glob.db.fetchrow('SELECT * FROM requests WHERE id = %s', [int(args[0])])
    _map = await Beatmap.bid_fetch(request['map'])
    ns = strStatuses(args[1])

    # TODO: better management for ranking only certain difficulties
    _set = await glob.db.fetch('SELECT md5 FROM maps WHERE sid = $s', [_map.sid])

    for m in _set:
        bm = await Beatmap.from_md5(m['md5'])
        bm.status = ns
        bm.frozen = True

        # reset lb cache in case of major status change
        bm.lb = None 
        bm.lb_rx = None
        bm.lb_ap = None

        await bm.save()
        glob.cache['maps'][bm.md5] = bm

    if (wh_url := glob.config.webhooks['maps']):
        wh = Webhook(url=wh_url)
        embed = Embed(title='')

        embed.set_author(url=f'https://{glob.config.domain}/u/{user.id}', name=user.name, icon_url=f'https://a.{glob.config.domain}/{user.id}')
        embed.set_image(url=f'https://assets.ppy.sh/beatmaps/{_map.sid}/covers/card.jpg')
        embed.add_field(name=f'New {ns.name.lower()} map', value=f'[{_map.name}]({_map.url}) is now {ns.name.lower()}!', inline=True)

        wh.add_embed(embed)
        await wh.post()

    if (rq := await glob.players.get(name=request['requester'])):
        rq.enqueue(writer.sendMessage(fromname=glob.bot.name, msg=f'Your request to make {_map.embed} {mapStatuses(request["status"]).name.lower()} was accepted by {user.name}! It is now {ns.name.lower()}.', tarname=rq.name, fromid=glob.bot.id))

    await glob.db.execute('DELETE FROM requests WHERE id = %s', [int(args[0])])

    return 'Map status updated!'

async def d_req(user, args):
    """Deny a map status request"""
    if len(args) < 1:
        return 'You must provide the request ID to deny!'

    request = await glob.db.fetchrow('SELECT * FROM requests WHERE id = %s', [int(args[0])])
    _map = await Beatmap.bid_fetch(request['map'])
    ns = mapStatuses(request['status'])

    if (rq := await glob.players.get(name=request['requester'])):
        rq.enqueue(writer.sendMessage(fromname=glob.bot.name, msg=f'Your request to make {_map.embed} {ns.name.lower()} was denied by {user.name}!', tarname=rq.name, fromid=glob.bot.id))

    await glob.db.execute('DELETE FROM requests WHERE id = %s', [int(args[0])])

    return 'Request denied!'

#####################

async def process(user, msg, public = False):
    start = time.time()
    args = msg.split()
    ct = args[0].split(glob.config.prefix)[1]
    for c in cmds:
        cmd = c['name']
        
        if cmd == ct:
            if not user.priv & c['priv']:
                return 'You have insufficient permissions to perform this command!'
            
            if public and not c['allow_public']:
                return

            cb = c['cb']
            o = await cb(user, args[1:])
            
            elapsed = ''

            if c['elapsed']:
                elapsed = f' | Time Elapsed: {(time.time() - start) * 1000:.2f}ms'

            if o:
                return f'{o}{elapsed}'
            
            return # we still wanna end the loop even if theres no text to return
    else:
        return f'Unknown command! Use {glob.config.prefix}help for a list of available commands.'

def mp_command(name: str = None, host: bool = True):
    def wrapper(cmd_cb):
        if name is not None:
            if not isinstance(name, list):
                mp_cmds.append({
                    'name': name,
                    'cb': cmd_cb,
                    'host': host,
                    'desc': cmd_cb.__doc__
                })
            else:
                for n in name:
                    mp_cmds.append({
                        'name': n,
                        'cb': cmd_cb,
                        'host': host,
                        'desc': cmd_cb.__doc__
                    })
        else:
            log(f'Tried to add multiplayer command with no name!', Ansi.LRED)

        return cmd_cb
    return wrapper

@mp_command(name='help', host=False)
async def mp_help(user, args, match):
    """Displays all available multiplayer commands to the user"""
    allowed_cmds = []
    for cmd in cmds:
        if user.priv & cmd['priv']:
            s = f'{glob.config.prefix}mp {cmd["name"]} - {cmd["desc"]}'
            allowed_cmds.append(s)

    cmd_list = '\n'.join(allowed_cmds)
    return f'List of available multiplayer commands:\n\n{cmd_list}'

@mp_command(name='start')
async def mp_start(user, args, match):
    """Starts the current match, either forcefully or on a timer"""
    if len(args) < 1:
        return 'Please provide either a timer to start or cancel/force'
    
    if not args[0]: # start now
        if any([s.status == slotStatus.not_ready for s in match.slots]):
            return 'Not all players are ready. You can force start with `!mp start force`'

    elif args[0] == 'force':
        match.start()
        match.chat.send(glob.bot, 'Starting match. Have fun!', False)

    elif args[0].isdecimal():
        def start_timer():
            match.start()
            match.chat.send(glob.bot, 'Starting match. Have fun!', False)
            
        def alert_timer(remaining):
            match.chat.send(glob.bot, f'Starting match in {remaining} seconds!', False)
            
        loop = asyncio.get_event_loop()
        timer = int(args[0])
        match.start_task = loop.call_later(timer, start_timer)
        match.alert_tasks = [
            loop.call_later(
                timer - countdown, lambda countdown = countdown: alert_timer(countdown)
            ) for countdown in (30, 10, 5, 4, 3, 2, 1) if countdown < timer
        ]
        
        return f'Starting match in {timer} seconds'

    elif args[0] == 'cancel':
        if not match.start_task:
            return
        
        match.start_task.cancel()
        for alert in match.alert_tasks:
            alert.cancel()
            
        match.start_task = None
        match.alert_tasks = None
        
        return 'Cancelled timer.'
        
    else:
        return 'Unknown argument. Please use seconds/force/cancel'
    
@mp_command(name='abort')
async def mp_abort(user, args, match):
    """Abort current multiplayer session"""
    if not match.in_prog:
        return
    
    match.unready_players(wanted=slotStatus.playing)
    match.in_prog = False
    
    match.enqueue(writer.matchAbort())
    match.enqueue_state()
    
    return 'Match aborted.'

@mp_command(name='mods')
async def mp_mods(user, args, match):
    """Set the mods of the lobby"""
    if len(args) < 1:
        return 'You must provide the mods to set!'
    
    if args[0].isdecimal():
        mods = Mods(args[0])
    elif isinstance(args[0], str):
        mods = Mods.convert_str(args[0])
    else:
        return 'Invalid mods.'
    
    if match.fm:
        match.mods = mods & Mods.SPEED_MODS
        
        for slot in match.slots:
            if slot.status & slotStatus.has_player:
                slot.mods = mods & ~Mods.SPEED_MODS
    else:
        match.mods = match.mods = mods
        
    match.enqueue_state()
    return 'Updated mods.'

@mp_command(name=['freemod', 'fm'])
async def mp_fm(user, args, match):
    if len(args) < 1:
        return 'Please provide whether to turn freemod on or off!'
    
    if args[0] == 'on':
        match.fm = True
        
        for slot in match.slots:
            if slot.status & slotStatus.has_player:
                slot.mods = match.mods & ~Mods.SPEED_MODS
                
        match.mods &= Mods.SPEED_MODS
    else:
        match.fm = False
        
        match.mods &= Mods.SPEED_MODS
        match.mods |= (match.get_slot(user)).mods
        
        for slot in match.slots:
            if slot.status & slotStatus.has_player:
                slot.mods = Mods.NOMOD
                
    match.enqueue_state()
    return 'Freemod state toggled.'

@mp_command(name='host', host=False)
async def mp_host(user, args, match):
    if user not in (match.host, match.first_host):
        return
    
    if len(args) < 1:
        return 'Please provide the user to give host!'
    
    if not (u := await glob.players.get(name=args[0])):
        return 'Couldn\'t find this user!'
    
    if u is match.host:
        return
    
    if not u.match or u.match is not match:
        return
    
    match.host = u
    u.enqueue(writer.matchTransferHost())
    match.enqueue_state(lobby=False)
    
    return f'Match host given to {u.name}'

async def process_multiplayer(user, msg):
    args = msg.split()
    ct = args[1]
    for c in mp_cmds:
        cmd = c['name']

        if cmd == ct:
            if user is not user.match.host:
                return 'You must be the host to perform this command!'

            cb = c['cb']
            o = await cb(user, args[2:], user.match)

            if o:
                return f'{o}'

            return # we still wanna end the loop even if theres no text to return
    else:
        return f'Unknown command! Use {glob.config.prefix}mp help for a list of available multiplayer commands.'
