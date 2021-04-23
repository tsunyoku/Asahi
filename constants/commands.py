from cmyui import log

async def test(user):
    return {
        'text': f'Your username is {user.name}!'
    }

cmds = {
    '!test': test
}

async def process(user, target, msg):
    if msg in cmds.keys():
        cmd = cmds[msg]
        return await cmd(user)