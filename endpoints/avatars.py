from pathlib import Path
from xevel import Router

from objects import glob

ava_path = Path.cwd() / 'resources/avatars'
avatars = Router(f'a.{glob.config.domain}')

@avatars.route("/")
async def default_avatar(req):
    file = ava_path / 'default.png'
    
    req.resp_headers['Content-Type'] = 'image/png'
    return file.read_bytes()

@avatars.route("/<uid>")
async def avatar(req, uid):
    user = ava_path / f'{uid}'
    if user.exists():
        req.resp_headers['Content-Type'] = 'image/png'
        return user.read_bytes()
    else:
        default = ava_path / 'default.png'
        req.resp_headers['Content-Type'] = 'image/png'
        return default.read_bytes()
