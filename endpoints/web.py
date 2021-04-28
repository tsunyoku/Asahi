from quart import Blueprint, request, Response, send_file, g, redirect
from cmyui import log, Ansi
from collections import defaultdict
from urllib.parse import unquote

import string
import random
import os
import hashlib
import bcrypt
import time
import orjson
import re

from objects import glob
from objects.beatmap import Beatmap
from constants.modes import lbModes
from constants.statuses import mapStatuses
from constants.mods import Mods

import packets

ss_path = os.path.join(os.getcwd(), 'resources/screenshots')
web = Blueprint('web', __name__)

def auth(name, md5):
    player = glob.players_name.get(name)
    if not player:
        log(f'{name} failed authentication', Ansi.LRED)
        return False

    if player.pw != md5:
        log(f'{name} failed authentication', Ansi.LRED)
        return False

    g.player = player
    return True

@web.before_request
async def bRequest():
    g.req_url = request.base_url
    g.req_method = request.method
    g.start = time.time()

@web.after_request
async def logRequest(resp):
    if g.get('player'):
        ret = f' | Request by {g.pop("player").name}'
    else:
        ret = ''

    if resp.status_code != 200:
        colourret = Ansi.LRED
    else:
        colourret = Ansi.LCYAN

    log(f'[{g.pop("req_method")}] {resp.status_code} {g.pop("req_url")}{ret} | Time Elapsed: {(time.time() - g.pop("start")) * 1000:.2f}ms', colourret)
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

@web.route("/d/<int:mid>")
async def mapDownload(mid):
    return redirect(f'https://tsuki.host/d/{mid}', code=307)

@web.route("/web/osu-search.php")
async def osuSearch():
    args = request.args
    if not auth(args['u'], args['h']):
        return Response(b'', status=400)

    direct_args = {}
    for key, _ in args.items():
        direct_args[key] = args[key]

    async with glob.web.get("http://tsuki.host/web/osu-search.php", params=direct_args) as resp:
        if resp.status != 200:
            return Response(b'0', status=resp.status)

        ret = await resp.read()

    return ret

@web.route("/web/osu-search-set.php")
async def osuSearchSet():
    args = request.args
    if not auth(args['u'], args['h']):
        return Response(b'', status=400)

    direct_args = {}
    for key, _ in args.items():
        direct_args[key] = args[key]

    async with glob.web.get("http://tsuki.host/web/osu-search-set.php", params=direct_args) as resp:
        if resp.status != 200:
            return Response(b'0', status=resp.status)

        ret = await resp.read()

    return ret

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

    if await glob.db.fetchval("SELECT 1 FROM users WHERE name = $1", name):
        errors['username'].append('Username already taken!')

    if await glob.db.fetchval("SELECT 1 FROM users WHERE name = $1", email):
        errors['user_email'].append('Email already in use!')

    if not len(pw) >= 8:
        errors['password'].append('Password must be 8+ characters!')

    if errors:
        ret = {'form_error': {'user': errors}}
        return Response(orjson.dumps(ret), mimetype='application/json', status=400)

    if int(mpargs['check']) == 0:
        md5 = hashlib.md5(pw.encode()).hexdigest().encode()
        bc = bcrypt.hashpw(md5, bcrypt.gensalt()).decode() # bcrypt i am begging pls make this faster some day i am actually crying

        await glob.db.execute("INSERT INTO users (name, email, pw, safe_name) VALUES ($1, $2, $3, $4)", name, email, bc, name.lower().replace(' ', '_'))
        uid = await glob.db.fetchval("SELECT id FROM users WHERE name = $1", name)
        await glob.db.execute('INSERT INTO stats (id) VALUES ($1)', uid)
        log(f'{name} successfully registered. | Time Elapsed: {(time.time() - start) * 1000:.2f}.ms', Ansi.LBLUE)

    return b'ok'

@web.route("/web/check-updates.php")
async def osuUpdates():
    args = request.args

    update_args = {}
    for key, _ in args.items():
        update_args[key] = args[key]

    async with glob.web.get("https://old.ppy.sh/web/check-updates.php", params=update_args) as resp:
        if resp.status != 200:
            return Response(b'error checking for updates', status=resp.status)

        ret = await resp.read()

    return ret

# oo map info this is starting to get good
@web.route("/web/osu-getbeatmapinfo.php")
async def osuMapInfo():
    args = request.args
    if not auth(args['u'], args['h']):
        return Response(b'', status=400)

    data = await request.data
    log(data)

@web.route("/web/osu-osz2-getscores.php")
async def getMapScores():
    args = request.args
    if not auth(args['us'], args['ha']):
        return Response(b'', status=400)

    if (md5 := args['c']) in glob.cache['unsub']:
        return b'-1|false' # tell client map is unsub xd

    mods = int(args['mods'])
    mode = lbModes(int(args['m']), mods)
    sid = int(args['i'])

    player = g.pop("player")

    if mode != player.mode or mods != player.mods:
        player.mode = mode.value
        player.mods = mods
        for o in glob.players.values():
            o.enqueue(packets.userStats(player))

    if not (bmap := Beatmap.md5_cache(md5)):
        if not (bmap := await Beatmap.md5_sql(md5)):
            if sid != -1:
                await Beatmap.cache(sid)
                bmap = Beatmap.md5_cache(md5)
            else:
                bmap = await Beatmap.md5_api(md5)

        if not bmap:
            file = args['f'].replace('+', '')
            reg = re.compile(r'^(?P<artist>.+) - (?P<title>.+) \((?P<mapper>.+)\) \[(?P<diff>.+)\]\.osu$') # fuck sake osu why do this to me
            if not (info := reg.match(unquote(file))): # once again osu why
                # invalid file? idfk
                glob.cache['unsub'].append(md5)
                return b'-1|false'

            exists = await glob.db.fetchval('SELECT 1 FROM maps WHERE artist = $1 AND title = $2 AND diff = $3 AND mapper = $4', info['artist'], info['title'], info['diff'], info['mapper'])

            if exists:
                return b'1|false' # bmap submitted but not up to date, send update available
            else:
                glob.cache['unsub'].append(md5)
                return b'-1|false' # bmap or other version of bmap cannot be found, must be unsubmitted

    if bmap.status < mapStatuses.Ranked:
        return f'{bmap.status}|false'.encode() # map is unranked, unsubmitted etc. then we return status with no scores or anything

    if mods & Mods.RELAX:
        table = 'scores_rx'
        sort = 'pp'
    elif mods & Mods.AUTOPILOT:
        table = 'scores_ap'
        sort = 'pp'
    else:
        table = 'scores'
        sort = 'score'

    scores = await glob.db.fetch(f'SELECT {table}.*, users.name FROM {table} LEFT OUTER JOIN users ON users.id = {table}.uid WHERE {table}.md5 = $1 AND {table}.status = 2 AND mode = $2 ORDER BY {table}.{sort} DESC LIMIT 100', md5, int(args['m']))

    resp = []

    resp.append(f'{bmap.status}|false|{bmap.id}|{bmap.sid}|{len(scores)}')
    resp.append(f'0\n{bmap.name}\n10.0') # why osu using \n :( | force 10.0 rating cus no ratings rn, 0 is map offset (probably wont ever be used)
    if not scores:
        return '\n'.join(resp).encode()

    best = await glob.db.fetchrow(f'SELECT {table}.* FROM {table} WHERE md5 = $1 AND mode = $2 AND uid = $3 AND status = 2 ORDER BY {table}.{sort} DESC LIMIT 1', md5, int(args['m']), player.id)
    if best:
        b_rank = await glob.db.fetchrow(f'SELECT COUNT(*) AS rank FROM {table} WHERE md5 = $1 AND mode = $2 AND status = 2 AND {table}.{sort} > $3', md5, int(args['m']), best[sort])
        rank = b_rank['rank'] + 1

        resp.append(f'{best["id"]}|{player.name}|{best[sort]}|{best["combo"]}|{best["50"]}|{best["100"]}|{best["300"]}|{best["miss"]}|{best["katu"]}|{best["geki"]}|{best["fc"]}|{best["mods"]}|{player.id}|{rank}|{best["time"]}|"1"')

    resp.extend([(f'{s["id"]}|{s["name"]}|{s[sort]}|{s["combo"]}|{s["50"]}|{s["100"]}|{s["300"]}|{s["miss"]}|{s["katu"]}|{s["geki"]}|{s["fc"]}|{s["mods"]}|{s["uid"]}|{rank + 1}|{s["time"]}|"1"') for rank, s in enumerate(scores)])
    
    return '\n'.join(resp).encode()