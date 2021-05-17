from quart import Blueprint, request, Response, send_file, g, redirect
from cmyui import log, Ansi
from collections import defaultdict
from urllib.parse import unquote
from pathlib import Path

import string
import random
import os
import hashlib
import bcrypt
import time
import orjson
import re
import copy

from objects import glob
from objects.beatmap import Beatmap
from objects.score import Score
from constants.modes import lbModes
from constants.statuses import mapStatuses, scoreStatuses
from constants.mods import Mods

import packets

ss_path = os.path.join(os.getcwd(), 'resources/screenshots')
vn_path = Path.cwd() / 'resources/replays'
rx_path = Path.cwd() / 'resources/replays_rx'
ap_path = Path.cwd() / 'resources/replays_ap'

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
    if glob.config.debug:
        g.req_url = request.base_url
        g.req_method = request.method
        g.start = time.time()

@web.after_request
async def logRequest(resp):
    if not glob.config.debug:
        return resp

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
        log(f'{name} successfully registered. | Time Elapsed: {(time.time() - start) * 1000:.2f}ms', Ansi.LBLUE)

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
    lb = int(args['v'])

    player = g.pop("player")

    if mode.value != player.mode or mods != player.mods:
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

    if not bmap.frozen and bmap.nc < time.time():
        await bmap.check_status()

    if bmap.status < mapStatuses.Ranked:
        return f'{bmap.status}|false'.encode() # map is unranked, unsubmitted etc. then we return status with no scores or anything

    resp = []

    if lb == 2: # mod-specific lb
        if base := bmap.mod_cache.get(mode):
            if mods in base:
                resp = base[mods].copy() # no better conditional way to do this with a list(?)
        else:
            bmap.mod_cache[mode] = {}
        
        if not base or not mods in base:
            scores = await glob.db.fetch(f'SELECT t.*, users.name FROM {mode.table} t LEFT OUTER JOIN users ON users.id = t.uid WHERE t.md5 = $1 AND t.status = 2 AND mode = $2 AND users.priv & 1 > 0 AND t.mods = $3 ORDER BY t.{mode.sort} DESC LIMIT 100', md5, int(args['m']), mods)
            resp.append(f'{bmap.status}|false|{bmap.id}|{bmap.sid}|{len(scores)}')
            resp.append(f'0\n{bmap.name}\n10.0') # why osu using \n :( | force 10.0 rating cus no ratings rn, 0 is map offset (probably wont ever be used)
            if not scores:
                bmap.mod_cache[mode][mods] = resp.copy()
                return '\n'.join(resp).encode()

        best = await glob.db.fetchrow(f'SELECT t.* FROM {mode.table} t WHERE md5 = $1 AND mode = $2 AND uid = $3 AND status = 2 AND mods = $4 ORDER BY t.{mode.sort} DESC LIMIT 1', md5, int(args['m']), player.id, mods)
        if best:
            b_rank = await glob.db.fetchrow(f'SELECT COUNT(*) AS rank FROM {mode.table} t LEFT OUTER JOIN users ON users.id = t.uid WHERE md5 = $1 AND mode = $2 AND status = 2 AND users.priv & 1 > 0 AND t.{mode.sort} > $3', md5, int(args['m']), best[mode.sort])
            rank = b_rank['rank'] + 1

            resp.insert(2, f'{best["id"]}|{player.name}|{int(best[mode.sort])}|{best["combo"]}|{best["n50"]}|{best["n100"]}|{best["n300"]}|{best["miss"]}|{best["katu"]}|{best["geki"]}|{best["fc"]}|{best["mods"]}|{player.id}|{rank}|{best["time"]}|"1"')
        else:
            resp.insert(2, '')

        if not base or not mods in base:
            for rank, s in enumerate(scores):
                resp.append(f'{s["id"]}|{s["name"]}|{int(s[mode.sort])}|{s["combo"]}|{s["n50"]}|{s["n100"]}|{s["n300"]}|{s["miss"]}|{s["katu"]}|{s["geki"]}|{s["fc"]}|{s["mods"]}|{s["uid"]}|{rank + 1}|{s["time"]}|"1"')

        if not base or not mods in base:
            bmap.mod_cache[mode][mods] = resp.copy() # set cache to current lb
            bmap.mod_cache[mode][mods].remove(bmap.mod_cache[mode][mods][2]) # remove personal best since it will differ per user

        return '\n'.join(resp).encode()
    else:
        if bmap.lb_cache.get(mode):
            resp = bmap.lb_cache[mode].copy()

        if not bmap.lb_cache.get(mode):
            scores = await glob.db.fetch(f'SELECT t.*, users.name FROM {mode.table} t LEFT OUTER JOIN users ON users.id = t.uid WHERE t.md5 = $1 AND t.status = 2 AND mode = $2 AND users.priv & 1 > 0 ORDER BY t.{mode.sort} DESC LIMIT 100', md5, int(args['m']))
            resp.append(f'{bmap.status}|false|{bmap.id}|{bmap.sid}|{len(scores)}')
            resp.append(f'0\n{bmap.name}\n10.0') # why osu using \n :( | force 10.0 rating cus no ratings rn, 0 is map offset (probably wont ever be used)
            if not scores:
                bmap.lb_cache[mode] = resp.copy()
                return '\n'.join(resp).encode()

        best = await glob.db.fetchrow(f'SELECT t.* FROM {mode.table} t WHERE md5 = $1 AND mode = $2 AND uid = $3 AND status = 2 ORDER BY t.{mode.sort} DESC LIMIT 1', md5, int(args['m']), player.id)
        if best:
            b_rank = await glob.db.fetchrow(f'SELECT COUNT(*) AS rank FROM {mode.table} t LEFT OUTER JOIN users ON users.id = t.uid WHERE md5 = $1 AND mode = $2 AND status = 2 AND users.priv & 1 > 0 AND t.{mode.sort} > $3', md5, int(args['m']), best[mode.sort])
            rank = b_rank['rank'] + 1

            resp.insert(2, f'{best["id"]}|{player.name}|{int(best[mode.sort])}|{best["combo"]}|{best["n50"]}|{best["n100"]}|{best["n300"]}|{best["miss"]}|{best["katu"]}|{best["geki"]}|{best["fc"]}|{best["mods"]}|{player.id}|{rank}|{best["time"]}|"1"')
        else:
            resp.insert(2, '')

        if not bmap.lb_cache.get(mode):
            for rank, s in enumerate(scores):
                resp.append(f'{s["id"]}|{s["name"]}|{int(s[mode.sort])}|{s["combo"]}|{s["n50"]}|{s["n100"]}|{s["n300"]}|{s["miss"]}|{s["katu"]}|{s["geki"]}|{s["fc"]}|{s["mods"]}|{s["uid"]}|{rank + 1}|{s["time"]}|"1"')
        
        if not bmap.lb_cache.get(mode):
            bmap.lb_cache[mode] = resp.copy() # set cache to current lb
            bmap.lb_cache[mode].remove(bmap.lb_cache[mode][2]) # remove personal best since it will differ per user

        return '\n'.join(resp).encode()

# POGGG
@web.route("/web/osu-submit-modular-selector.php", methods=['POST'])
async def scoreSubmit():
    mpargs = await request.form

    s = await Score.submission(mpargs['score'], mpargs['iv'], mpargs['pass'], mpargs['osuver'])

    if not s:
        return b'error: no'
    elif not s.user:
        return b'' # player not online, make client make resubmit attempts
    elif not s.map:
        return b'error: no' # map unsubmitted

    if s.mode != s.user.mode or s.mods != s.user.mods:
        s.user.mode = s.mode.value
        s.user.mods = s.mods
        for o in glob.players.values():
            o.enqueue(packets.userStats(s.user))

    # submit score and get id xd
    await glob.db.execute(f'INSERT INTO {s.mode.table} (md5, score, acc, pp, combo, mods, n300, geki, n100, katu, n50, miss, grade, status, mode, time, uid, readable_mods, fc) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)', s.map.md5, s.score, s.acc, s.pp, s.combo, s.mods, s.n300, s.geki, s.n100, s.katu, s.n50, s.miss, s.grade, s.status.value, s.mode_vn, s.time, s.user.id, s.readable_mods, s.fc)
    s.id = await glob.db.fetchval(f'SELECT id FROM {s.mode.table} WHERE md5 = $1 AND uid = $2 AND time = $3', s.map.md5, s.user.id, s.time)
    
    if s.status == scoreStatuses.Best:
        # set any other best scores to submitted ones as they've been overwritten
        await glob.db.execute(f'UPDATE {s.mode.table} SET status = 1 WHERE status = 2 AND uid = $1 AND md5 = $2 AND mode = $3 AND id != $4', s.user.id, s.map.md5, s.mode_vn, s.id)

    # save replay if not a failed score
    if s.status != scoreStatuses.Failed:
        files = await request.files
        replay = files.get('score')

        # i will make this auto-parse the replays one day when im not lazy
        if s.mods & Mods.RELAX:
            f = rx_path / f'{s.id}.osr'
        elif s.mods & Mods.AUTOPILOT:
            f = ap_path / f'{s.id}.osr'
        else:
            f = vn_path / f'{s.id}.osr'

        replay.save(str(f))

    # update stats EEEEEEE
    stats = s.user.stats[s.mode.value]
    old = copy.copy(stats) # we need a copy of the old stats for submission chart

    stats.pc += 1

    if s.status == scoreStatuses.Best and s.map.status >= mapStatuses.Ranked:
        add = s.score

        if s.old_best:
            add -= s.old_best.score
        
        stats.rscore += add

    stats.tscore += s.score

    await s.user.update_stats(s.mode, s.mode.table, s.mode_vn)

    # sub charts bruh
    if s.mods & Mods.RELAX or s.mods & Mods.AUTOPILOT or s.status == scoreStatuses.Failed:
        log(f'[{s.mode!r}] {s.user.name} submitted a score on {s.map.name} ({s.status.name})', Ansi.LBLUE)
        return b'error: no' # not actually erroring, score is already submitted we just want client to stop request as we cannot provide chart

    charts = []

    # could be done better
    def chart_format(name, b, a):
        return f'{name}Before:{b or ""}|{name}After:{a}' # osu makes this so ugly man.

    # map info
    charts.append(
        f'beatmapId:{s.map.id}|'
        f'beatmapSetId:{s.map.sid}|'
        # temp hardcode these values below because yea xd
        'beatmapPlaycount:0|'
        'beatmapPasscount:0|'
        'approvedDate:0'
    )

    # map-specific ranking
    if s.map.status >= mapStatuses.Ranked:
        charts.append('|'.join((
            'chartId:beatmap',
            f'chartUrl:https://osu.ppy.sh/b/{s.map.id}',
            'chartName:Current Score', # not sure if this is allowed to be customised ??

            *(( # wtaf | no previous stats for now
                chart_format('rank', s.old_best.rank, s.rank),
                chart_format('rankedScore', s.old_best.score, s.score),
                chart_format('totalScore', s.old_best.score, s.score),
                chart_format('maxCombo', s.old_best.combo, s.combo),
                chart_format('accuracy', round(s.old_best.acc, 2), round(s.acc, 2)),
                chart_format('pp', s.old_best.pp, s.pp)
            ) if s.old_best else (
                chart_format('rank', None, s.rank),
                chart_format('rankedScore', None, s.score),
                chart_format('totalScore', None, s.score),
                chart_format('maxCombo', None, s.combo),
                chart_format('accuracy', None, round(s.acc, 2)),
                chart_format('pp', None, s.pp)
            )),

            f'onlineScoreId:{s.id}'
        )))

    # overall user stats
    charts.append('|'.join((
        'chartId:overall',
        f'chartUrl:https://{glob.config.domain}/u/{s.user.id}',
        'chartName:Global Stats',

        *((
            chart_format('rank', old.rank, stats.rank),
            chart_format('rankedScore', old.rscore, stats.rscore),
            chart_format('totalScore', old.tscore, stats.tscore),
            chart_format('maxCombo', None, None), # no max combo shit yet
            chart_format('accuracy', round(old.acc, 2), round(stats.acc, 2)),
            chart_format('pp', old.pp, stats.pp)
        ) if old else (
            chart_format('rank', None, stats.rank),
            chart_format('rankedScore', None, stats.rscore),
            chart_format('totalScore', None, stats.tscore),
            chart_format('maxCombo', None, None), # no max combo shit yet
            chart_format('accuracy', None, round(stats.acc, 2)),
            chart_format('pp', None, stats.pp)
        ))
    )))

    if s.status == scoreStatuses.Best and s.rank == 1 and s.map.status >= mapStatuses.Ranked:
        # announce #1 to announce channel cus they achieved #1
        if s.map.status == mapStatuses.Loved:
            perf = ''
        else:
            perf = f' worth {round(s.pp):,}pp'

        prev1 = await glob.db.fetchrow(f'SELECT users.name FROM users LEFT OUTER JOIN {s.mode.table} t ON t.uid = users.id WHERE t.md5 = $1 AND t.mode = $2 AND t.status = 2 AND users.priv & 1 > 0 AND t.uid != $3 AND t.id != $4 ORDER BY t.{s.mode.sort} DESC LIMIT 1', s.map.md5, s.mode_vn, s.user.id, s.id)

        if prev1:
            prev = f' (Previous #1: [https://{glob.config.domain}/u/{prev1["name"]} {prev1["name"]}])'
        else:
            prev = ''

        msg = f'[{s.mode!r}] {s.user.embed} achieved #1 on {s.map.embed} +{s.readable_mods}{perf}{prev}'
        chan = glob.channels['#announce']
        chan.send(glob.bot, msg, True)
        
    if s.status == scoreStatuses.Best and s.map.status >= mapStatuses.Ranked:
        # add score to lb cache xd
        if s.mode.sort == 'pp':
            st = s.pp
        else:
            st = s.score

        # ?
        fmt = f'|{s.user.name}|'
        for val in s.map.lb_cache[s.mode.value]:
            if fmt in val:
                s.map.lb_cache[s.mode.value].remove(val)

        s.map.lb_cache[s.mode.value].append(f'{s.id}|{s.user.name}|{st}|{s.combo}|{s.n50}|{s.n100}|{s.n300}|{s.miss}|{s.katu}|{s.geki}|{s.fc}|{s.mods}|{s.user.id}|{s.rank}|{s.time}|"1"')

    log(f'[{s.mode.name}] {s.user.name} submitted a score on {s.map.name} ({s.status.name})', Ansi.LBLUE)
    return '\n'.join(charts).encode() # thank u osu


        