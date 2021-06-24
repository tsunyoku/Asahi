from objects import glob
from objects.match import Match
from objects.channel import Channel
from objects.beatmap import Beatmap
from constants.privs import Privileges
from constants.types import teamTypes
from constants.statuses import strStatuses

import time
import packets

async def help(user, msg):
    allowed_cmds = []
    for cmd, req_priv in cmd_privs.items():
        if user.priv & req_priv:
            allowed_cmds.append(cmd)

    cmd_list = '\n'.join(allowed_cmds)
    return f'List of available commands:\n\n{cmd_list}'

async def add_priv(user, msg):
    if len(msg) < 3:
        return f"You haven't provided a username and privileges!"
    
    name = msg[1]

    priv = Privileges(await glob.db.fetchval("SELECT priv FROM users WHERE name = $1", name))
    new_privs = Privileges(0)
    for npriv in msg[2:]:
        if not (new_priv := privs.get(npriv.lower())):
            return f'Privilege {npriv} not found.'

        priv |= new_priv
        new_privs |= new_priv

    await glob.db.execute("UPDATE users SET priv = $1 WHERE name = $2", int(priv), name)
    return f"Added privilege(s) {new_privs} to {name}."

async def rm_priv(user, msg):
    if len(msg) < 3:
        return f"You haven't provided a username and privileges!"

    name = msg[1]

    priv = Privileges(await glob.db.fetchval("SELECT priv FROM users WHERE name = $1", name))
    new_privs = Privileges(0)
    for npriv in msg[2:]:
        if not (new_priv := privs.get(npriv.lower())):
            return f'Privilege {npriv} not found.'

        priv &= ~new_priv
        new_privs |= new_priv

    await glob.db.execute("UPDATE users SET priv = $1 WHERE name = $2", int(priv), name)
    return f"Removed privilege(s) {new_privs} from {name}."

async def clan_battle(user, msg):
    if msg[1] in ('accept', 'deny'):
        if len(msg) < 3:
            return f'Please accept/deny a battle and specify the clan!'

        clan_name = msg[2]
        clan = glob.clans.get(await glob.db.fetchval('SELECT id FROM clans WHERE name = $1', clan_name))
        
        if not clan:
            return f'We could not find a clan by this name!'

        if not (owner := glob.players_id.get(clan.owner)):
            return f'Clan owner offline, battle request cancelled!'
        
        if msg[1] == 'deny':
            owner.enqueue(packets.sendMessage(fromname=glob.bot.name, msg=f'{user.name} denied your request to battle their clan {clan.name}!', tarname=owner.name, fromid=glob.bot.id))
            return f'Battle request denied!'

        # battle was accepted, create the battle match

        user.enqueue(packets.sendMessage(fromname=glob.bot.name, msg=f'Request accepted! Creating match...', tarname=user.name, fromid=glob.bot.id))
        owner.enqueue(packets.sendMessage(fromname=glob.bot.name, msg=f'{user.name} accepted your request to battle their clan {user.clan.name}! Creating match...', tarname=owner.name, fromid=glob.bot.id))

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
            u.enqueue(packets.sendMessage(fromname=glob.bot.name, msg=f'Your clan has initiated in a clan battle against the clan {user.clan.name}! Please join the battle here: {match.embed}', tarname=u.name, fromid=glob.bot.id)) 

        for u in online2:
            u.enqueue(packets.sendMessage(fromname=glob.bot.name, msg=f'Your clan has initiated in a clan battle against the clan {clan.name}! Please join the battle here: {match.embed}', tarname=u.name, fromid=glob.bot.id))

        return

    if user.clan.owner != user.id:
        return f'You must be the owner of your clan to request a battle!'

    if len(msg) < 2:
        return f"Please provide a clan to request a battle!"

    clan_name = msg[1]
    clan = glob.clans.get(await glob.db.fetchval('SELECT id FROM clans WHERE name = $1', clan_name))

    if not clan:
        return f'We could not find a clan by this name!'

    if not (owner := glob.players_id.get(clan.owner)):
        return f'The clan owner must be online for you to request a battle!'

    owner.enqueue(packets.sendMessage(fromname=glob.bot.name, msg=f'{user.name} has invited you to a clan battle! If you wish to accept then type !battle accept {user.clan.name}, or !battle deny {user.clan.name} to deny. If you accept, a multiplayer match will be created for you and all your online clanmates to battle to the death!', tarname=owner.name, fromid=glob.bot.id))

    return f'Clan battle request sent to {clan.name} clan!'

async def _map(user, msg):
    if len(msg) != 3:
        return 'Please provide the new status & whether we should update the map/set! (!map <rank/love/unrank> <map/set>)'

    status = msg[1]
    type = msg[2]

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

privs = {
    'normal': Privileges.Normal,
    'verified': Privileges.Verified,
    'supporter': Privileges.Supporter,
    'nominator': Privileges.Nominator,
    'admin': Privileges.Admin,
    'developer': Privileges.Developer,
    'owner': Privileges.Owner,
    'master': Privileges.Master,
    'staff': Privileges.Staff,
    'manager': Privileges.Manager
}

cmds = {
    '!addpriv': add_priv,
    '!rmpriv': rm_priv,
    '!help': help,
    '!battle': clan_battle,
    '!map': _map
}

cmd_privs = {
    '!addpriv': Privileges.Owner,
    '!rmpriv': Privileges.Owner,
    '!help': Privileges.Normal,
    '!battle': Privileges.Normal,
    '!map': Privileges.Nominator
}

async def process(user, target, msg):
    start = time.time()
    args = msg.split()
    c = args[0]
    if c in cmds.keys():
        if user.priv & cmd_privs[c]:
            cmd = cmds[c]

            if c != '!help':
                elapsed = f'| Time Elapsed: {(time.time() - start) * 1000:.2f}ms'
            else:
                elapsed = ''

            c = await cmd(user, args)

            if c is not None:
                return f'{await cmd(user, args)} {elapsed}'

            return
        else:
            return f'You have insufficient permissions to perform this command!'
    else:
        return f'Unknown command! Use !help for a list of commands.'
