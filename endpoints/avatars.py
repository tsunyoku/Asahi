from pathlib import Path
from quart import Blueprint, send_file, Response

ava_path = Path.cwd() / 'resources/avatars'
avatars = Blueprint('avatars', __name__)

@avatars.route("/")
async def default_avatar():
    return await send_file(ava_path / 'default.png')

@avatars.route("/<int:uid>")
async def avatar(uid):
    user = ava_path / f'{uid}.png'
    if user.exists():
        return await send_file(user)
    else:
        default = ava_path / 'default.png'
        return await send_file(default)