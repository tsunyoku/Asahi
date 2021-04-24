from cmyui import log
from objects import glob
from constants.privs import Privileges

async def help(user, msg):
    allowed_cmds = []
    for cmd, req_priv in cmd_privs.items():
        if user.priv & req_priv:
            allowed_cmds.append(cmd)

    cmd_list = '\n'.join(allowed_cmds)
    return f'List of available commands:\n\n{cmd_list}'

async def add_priv(user, msg):
    if len(msg) < 2:
        return f"You haven't provided a username and privileges!"

    user = await glob.db.fetch('SELECT priv FROM users WHERE name = %s', [msg[1]])
    priv = Privileges(user['priv'])
    new_privs = Privileges(0)
    for npriv in msg[2:]:
        if not (new_priv := privs.get(npriv.lower())):
            return f'Privilege {npriv} not found.'

        priv |= new_priv
        new_privs |= new_priv

    await glob.db.execute('UPDATE users SET priv = %s WHERE name = %s', [int(priv), msg[1]])
    return f"Added privilege(s) {new_privs} to {msg[1]}."

async def rm_priv(user, msg):
    if len(msg) < 2:
        return f"You haven't provided a username and privileges!"

    user = await glob.db.fetch('SELECT priv FROM users WHERE name = %s', [msg[1]])
    priv = Privileges(user['priv'])
    new_privs = Privileges(0)
    for npriv in msg[2:]:
        if not (new_priv := privs.get(npriv.lower())):
            return f'Privilege {npriv} not found.'

        priv &= ~new_priv
        new_privs |= new_priv

    await glob.db.execute('UPDATE users SET priv = %s WHERE name = %s', [int(priv), msg[1]])
    return f"Removed privilege(s) {new_privs} from {msg[1]}."

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
    '!help': help
}

cmd_privs = {
    '!addpriv': Privileges.Owner,
    '!rmpriv': Privileges.Owner,
    '!help': Privileges.Normal
}

async def process(user, target, msg):
    args = msg.split()
    c = args[0]
    if c in cmds.keys():
        if user.priv & cmd_privs[c]:
            cmd = cmds[c]
            return await cmd(user, args)
        else:
            return f'You have insufficient permissions to perform this command!'
    else:
        return f'Unknown command! Use !help for a list of commands.'