from quart import Blueprint, request, Response, send_file
from cmyui import log, Ansi

import string
import random
import os
import orjson

from objects import glob

ss_path = os.path.join(os.getcwd(), 'resources/screenshots')
web = Blueprint('web', __name__)

@web.route("/web/osu-screenshot.php", methods=['POST'])
async def uploadScreenshot():
    files = await request.files
    screenshot = files['ss']
    if not screenshot:
        return Response(b'missing screenshot')

    name = f"{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}.png"
    ss = os.path.join(ss_path, name)
    screenshot.save(ss)
    log(f'Screenshot {name} saved to disk')
    return name.encode()

@web.route("/ss/<string:scr>")
async def getScreenshot(scr):
    ss = os.path.join(ss_path, scr)
    if os.path.exists(ss):
        return await send_file(ss)
    else:
        return Response('could not find screenshot')

@web.route("/web/osu-getseasonal.php")
async def seasonalBG():
    return Response(f'{glob.config.menu_bgs}', mimetype='application/json')

@web.route("/web/bancho_connect.php")
async def banchoConnect():
    verif = request.args.get('v')
    if verif:
        return Response(b'asahi is gamer')

    return Response(b'')