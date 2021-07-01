from objects import glob
from objects.match import Match
from objects.channel import Channel
from objects.beatmap import Beatmap
from objects.player import Player
from constants.privs import Privileges
from constants.types import teamTypes
from constants.statuses import strStatuses

import time
import packets

cmds = []

def command(priv: Privileges = Privileges.Normal, name: str = None, elapsed: bool = True):
    def wrapper(cmd_cb):
        if name is not None:
            cmds.append({
                'name': name, 
                'priv': priv, 
                'elapsed': elapsed, 
                'cb': cmd_cb, 
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

@command(priv=Privileges.Owner, name='add_priv')
async def add_priv(user, args):
    """Adds (a list of) privileges to a user"""
    if len(args) < 2:
        return f"You haven't provided a username and privileges!"
    
    name = args[0]

    priv = Privileges(await glob.db.fetchval("SELECT priv FROM users WHERE name = $1", name))
    new_privs = Privileges(0)
    for npriv in args[1:]:
        if not (new_priv := privs.get(npriv.lower())):
            return f'Privilege {npriv} not found.'

        priv |= new_priv
        new_privs |= new_priv

    await glob.db.execute("UPDATE users SET priv = $1 WHERE name = $2", int(priv), name)
    return f"Added privilege(s) {new_privs} to {name}."

@command(priv=Privileges.Owner, name='rm_priv')
async def rm_priv(user, args):
    """Removes (a list of) privileges from a user"""
    if len(args) < 2:
        return f"You haven't provided a username and privileges!"

    name = args[0]

    priv = Privileges(await glob.db.fetchval("SELECT priv FROM users WHERE name = $1", name))
    new_privs = Privileges(0)
    for npriv in args[1:]:
        if not (new_priv := privs.get(npriv.lower())):
            return f'Privilege {npriv} not found.'

        priv &= ~new_priv
        new_privs |= new_priv

    await glob.db.execute("UPDATE users SET priv = $1 WHERE name = $2", int(priv), name)
    return f"Removed privilege(s) {new_privs} from {name}."

@command(name='battle')
async def clan_battle(user, args):
    """Battle other clans in a scrim-like multi lobby"""
    if args[0] in ('accept', 'deny'):
        if len(args) < 2:
            return f'Please accept/deny a battle and specify the clan!'

        clan_name = args[1]
        clan = glob.clans.get(await glob.db.fetchval('SELECT id FROM clans WHERE name = $1', clan_name))
        
        if not clan:
            return f'We could not find a clan by this name!'

        if not (owner := glob.players_id.get(clan.owner)):
            return f'Clan owner offline, battle request cancelled!'
        
        if args[1] == 'deny':
            owner.enqueue(packets.sendMessage(fromname=glob.bot.name, args=f'{user.name} denied your request to battle their clan {clan.name}!', tarname=owner.name, fromid=glob.bot.id))
            return f'Battle request denied!'

        # battle was accepted, create the battle match

        user.enqueue(packets.sendMessage(fromname=glob.bot.name, args=f'Request accepted! Creating match...', tarname=user.name, fromid=glob.bot.id))
        owner.enqueue(packets.sendMessage(fromname=glob.bot.name, args=f'{user.name} accepted your request to battle their clan {user.clan.name}! Creating match...', tarname=owner.name, fromid=glob.bot.id))

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

        # get list of potential clan members we should expect (TODO: if a clan member logs in after this point, add to list)
        online1 = []
        for m in clan.members:
            if (e := glob.players_id.get(m)):
                online1.append(e)

        online2 = []
        for m in user.clan.members:
            if (e := glob.players_id.get(m)):
                online2.append(e)

        b_info = {'clan1': clan, 'clan2': user.clan, 'online1': online1, 'online2': online2, 'total': (online1 + online2), 'match': match}

        glob.clan_battles[match.clan_1] = b_info
        glob.clan_battles[match.clan_2] = b_info

        for u in online1:
            u.enqueue(packets.sendMessage(fromname=glob.bot.name, args=f'Your clan has initiated in a clan battle against the clan {user.clan.name}! Please join the battle here: {match.embed}', tarname=u.name, fromid=glob.bot.id)) 

        for u in online2:
            u.enqueue(packets.sendMessage(fromname=glob.bot.name, args=f'Your clan has initiated in a clan battle against the clan {clan.name}! Please join the battle here: {match.embed}', tarname=u.name, fromid=glob.bot.id))

        return

    if user.clan.owner != user.id:
        return f'You must be the owner of your clan to request a battle!'

    if len(args) < 1:
        return f"Please provide a clan to request a battle!"

    clan_name = args[0]
    clan = glob.clans.get(await glob.db.fetchval('SELECT id FROM clans WHERE name = $1', clan_name))

    if not clan:
        return f'We could not find a clan by this name!'

    if not (owner := glob.players_id.get(clan.owner)):
        return f'The clan owner must be online for you to request a battle!'

    owner.enqueue(packets.sendMessage(fromname=glob.bot.name, args=f'{user.name} has invited you to a clan battle! If you wish to accept then type !battle accept {user.clan.name}, or !battle deny {user.clan.name} to deny. If you accept, a multiplayer match will be created for you and all your online clanmates to battle to the death!', tarname=owner.name, fromid=glob.bot.id))

    return f'Clan battle request sent to {clan.name} clan!'

@command(priv=Privileges.Nominator, name='map')
async def _map(user, args):
    """Update map statuses on the server"""
    if len(args) != 2:
        return 'Please provide the new status & whether we should update the map/set! (!map <rank/love/unrank> <map/set>)'

    status = args[0]
    type = args[1]

    if status not in ('love', 'rank', 'unrank') or type not in ('set', 'map'):
        return 'Invalid syntax! Command: !map <rank/love/unrank> <set/map>'

    map = user.np
    ns = strStatuses(status)

    if type == 'map':
        map.status = ns
        map.frozen = True
        map.lb = None # reset lb cache in case of major status change
        await map.save()
        glob.cache['maps'][map.md5] = map
    else:
        sid = await glob.db.fetchval('SELECT sid FROM maps WHERE md5 = $1', map.md5)
        set = await glob.db.fetch('SELECT md5 FROM maps WHERE sid = $1', sid)

        for m in set:
            md5 = m['md5']
            bm = await Beatmap.from_md5(md5)
            bm.status = ns
            bm.frozen = True
            bm.lb = None # reset lb cache in case of major status change
            await bm.save()
            glob.cache['maps'][bm.md5] = bm

    return 'Status updated!'

@command(priv=Privileges.Admin, name='ban')
async def ban(user, args):
    """Ban a specified user for a specified reason"""
    if len(args) < 2:
        return f'You must provide a user and a reason to ban!'
    
    username = args[0].lower()
    reason = args[1]
    
    if not (target := glob.players_name.get(username)):
        target = await Player.from_sql(username)
        
    await target.ban(reason=reason, fr=user)
    
    return f'User banned!'

@command(priv=Privileges.Admin, name='unban')
async def unban(user, args):
    """Unban a specified user for a specified reason"""
    if len(args) < 2:
        return f'You must provide a user and a reason to unban!'

    username = args[0].lower()
    reason = args[1]

    if not (target := glob.players_name.get(username)):
        target = await Player.from_sql(username)

    await target.unban(reason=reason, fr=user)

    return f'User unbanned!'

@command(priv=Privileges.Admin, name='restrict')
async def restrict(user, args):
    """Restrict a specified user for a specified reason"""
    if len(args) < 2:
        return f'You must provide a user and a reason to restrict!'

    username = args[0].lower()
    reason = args[1]

    if not (target := glob.players_name.get(username)):
        target = await Player.from_sql(username)

    await target.restrict(reason=reason, fr=user)

    return f'User restricted!'

@command(priv=Privileges.Admin, name='unrestrict')
async def unrestrict(user, args):
    """Unrestrict a specified user for a specified reason"""
    if len(args) < 2:
        return f'You must provide a user and a reason to unrestrict!'

    username = args[0].lower()
    reason = args[1]

    if not (target := glob.players_name.get(username)):
        target = await Player.from_sql(username)

    await target.unrestrict(reason=reason, fr=user)

    return f'User unrestricted!'

@command(priv=Privileges.Admin, name='freeze')
async def freeze(user, args):
    """Freeze a specified user for a specified reason"""
    if len(args) < 2:
        return f'You must provide a user and a reason to freeze!'

    username = args[0].lower()
    reason = args[1]

    if not (target := glob.players_name.get(username)):
        target = await Player.from_sql(username)
        
    if not target:
        return f'User {username} not found!'

    await target.freeze(reason=reason, fr=user)

    return f'User frozen!'

@command(priv=Privileges.Admin, name='unfreeze')
async def unfreeze(user, args):
    """Unfreeze a specified user for a specified reason"""
    if len(args) < 2:
        return f'You must provide a user and a reason to unfreeze!'

    username = args[0].lower()
    reason = args[1]

    if not (target := glob.players_name.get(username)):
        target = await Player.from_sql(username)

    await target.unfreeze(reason=reason, fr=user)

    return f'User unfrozen!'

async def process(user, msg):
    start = time.time()
    args = msg.split()
    ct = args[0].split(glob.config.prefix)[1]
    for c in cmds:
        cmd = c['name']
        
        if cmd == ct:
            if not user.priv & c['priv']:
                return 'You have insufficient permissions to perform this command!'

            cb = c['cb']
            o = await cb(user, args[1:])

            if c['elapsed']:
                elapsed = f'| Time Elapsed: {(time.time() - start) * 1000:.2f}ms'
            else:
                elapsed = ''

            if o:
                return f'{o} {elapsed}'
            
            return # we still wanna end the loop even if theres no text to return
    else:
        return f'Unknown command! Use {glob.config.prefix}help for a list of available commands.'
