from quart import Blueprint, request, Response, send_file, g
from cmyui import log, Ansi
from collections import defaultdict

import string
import random
import os
import hashlib
import bcrypt
import time
import orjson

from objects import glob

ss_path = os.path.join(os.getcwd(), 'resources/screenshots')
web = Blueprint('web', __name__)

def auth(name, md5):
    player = glob.players_name.get(name)
    if not player:
        return False

    if player.pw != md5:
        return False

    g.player = player.name
    return True

@web.before_request
async def bRequest():
    g.req_url = request.base_url
    g.req_method = request.method
    g.start = time.time()

@web.after_request
async def logRequest(resp):
    if g.get('player'):
        ret = f' | Request by {g.pop("player")}'
    else:
        ret = ''

    log(f'[{g.pop("req_method")}] {resp.status_code} {g.pop("req_url")}{ret} | Time Elapsed: {(time.time() - g.pop("start")) * 1000:.2f}ms', Ansi.LCYAN)
    return resp

@web.route("/web/osu-screenshot.php", methods=['POST'])
async def uploadScreenshot():
    mpargs = await request.form
    if not auth(mpargs['u'], mpargs['p']):
        return Response(b'', status=400)

    files = await request.files
    screenshot = files['ss']
    if not screenshot:
        return Response(b'missing screenshot', status=400)

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
        return Response('could not find screenshot', status=400)

@web.route("/web/osu-getseasonal.php")
async def seasonalBG():
    return Response(f'{glob.config.menu_bgs}', mimetype='application/json')

@web.route("/web/bancho_connect.php")
async def banchoConnect():
    return Response(b'asahi is gamer')

@web.route("/web/osu-getfriends.php")
async def getFriends():
    args = request.args
    if not auth(args['u'], args['h']):
        return Response(b'', status=400)
    
    p = glob.players_name.get(args['u'])
    return '\n'.join(map(str, p.friends)).encode()

@web.route("/users", methods=['POST'])
async def ingameRegistration():
    start = time.time()
    mpargs = await request.form

    name = mpargs['user[username]'] # what is this setup osu lol
    email = mpargs['user[user_email]']
    pw = mpargs['user[password]']

    if not mpargs.get('check') or not all((name, email, pw)):
        return Response(b'missing required paramaters', status=400)

    errors = defaultdict(list)
    if ' ' in name and '_' in name:
        errors['username'].append('Username cannot contain both "_" and " "')

    if await glob.db.fetch('SELECT 1 FROM users WHERE name = %s', [name]):
        errors['username'].append('Username already taken!')

    if await glob.db.fetch('SELECT 1 FROM users WHERE email = %s', [email]):
        errors['user_email'].append('Email already in use!')
    
    if not len(pw) > 8:
        errors['password'].append('Password must be 8+ characters!')
    
    if errors:
        ret = {'form_error': {'user': errors}}
        return Response(orjson.dumps(ret), mimetype='application/json', status=400)

    if int(mpargs['check']) == 0:
        md5 = hashlib.md5(pw.encode()).hexdigest().encode()
        bc = bcrypt.hashpw(md5, bcrypt.gensalt()) # bcrypt i am begging pls make this faster some day i am actually crying

        await glob.db.execute('INSERT INTO users (name, email, pw) VALUES (%s, %s, %s)', [name, email, bc])
        log(f'{name} successfully registered. | Time Elapsed: {time.time() - start}', Ansi.LBLUE)
    
    return b'ok'