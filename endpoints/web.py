from xevel import Router
from cmyui import log, Ansi
from collections import defaultdict
from urllib.parse import unquote
from pathlib import Path
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand

import string
import random
import hashlib
import time
import orjson
import copy
import threading

from objects import glob
from objects.beatmap import Beatmap
from objects.score import Score
from constants.modes import lbModes
from constants.statuses import mapStatuses, scoreStatuses
from constants.mods import Mods
from constants.flags import osuFlags
from objects.leaderboard import Leaderboard
from constants import regexes
from packets import writer

ss_path = Path.cwd() / 'resources/screenshots'
vn_path = Path.cwd() / 'resources/replays'
rx_path = Path.cwd() / 'resources/replays_rx'
ap_path = Path.cwd() / 'resources/replays_ap'

web = Router(f'osu.{glob.config.domain}')

def auth(name, md5, req):
    player = glob.players_name.get(name)
    if not player:
        log(f'{name} failed authentication', Ansi.LRED)
        return False

    if player.pw != md5:
        log(f'{name} failed authentication', Ansi.LRED)
        return False
    
    req.extras['player'] = player
    return True

if glob.config.debug:
    @web.after_request()
    async def logRequest(resp):
        if resp.extras.get('player'):
            ret = f' | Request by {resp.extras.pop("player").name}'
        else:
            ret = ''

        if resp.code >= 400:
            colourret = Ansi.LRED
        else:
            colourret = Ansi.LCYAN

        log(f'[{resp.type}] {resp.code} {resp.url}{ret} | Time Elapsed: {resp.elapsed}', colourret)
        return resp

@web.route("/web/osu-screenshot.php", ['POST'])
async def uploadScreenshot(request):
    mpargs = request.args
    if not auth(mpargs['u'], mpargs['p'], request):
        return b''

    files = request.files
    screenshot = files['ss']
    if not screenshot:
        return b'missing screenshot'

    if screenshot[:4] == b'\xff\xd8\xff\xe0' and screenshot[6:11] == b'JFIF\x00':
        extension = 'jpg'
    else:
        extension = 'png'

    name = f"{''.join(random.choices(string.ascii_uppercase + string.digits, k=8))}.{extension}"
    ss = ss_path / name
    ss.write_bytes(screenshot)
    return name.encode()

@web.route("/ss/<scr>")
async def getScreenshot(request, scr):
    ss = ss_path / scr
    _type = scr.split('.')[1]

    if ss.exists():
        ssb = ss.read_bytes()
        request.resp_headers['Content-Type'] = f'image/{_type}'
        request.resp_headers['Content-Length'] = len(ssb)
        return ssb
    else:
        return b'could not find screenshot'

@web.route("/web/osu-getseasonal.php")
async def seasonalBG(request):
    return orjson.dumps(glob.config.menu_bgs)

@web.route("/web/bancho_connect.php")
async def banchoConnect(request):
    return b'asahi is gamer owo'

@web.route("/web/osu-getfriends.php")
async def getFriends(request):
    args = request.args
    if not auth(args['u'], args['h'], request):
        return b''

    p = glob.players_name.get(args['u'], request)
    return '\n'.join(map(str, p.friends)).encode()

@web.route("/d/<mid>")
async def mapDownload(request, mid):
    request.resp_headers['Location'] = f'https://osu.gatari.pw/d/{mid}' # reliable downloads
    return (301, b'') # redirect

@web.route("/web/osu-search.php")
async def osuSearch(request):
    args = request.args
    if not auth(args['u'], args['h'], request):
        return b''
    
    args['u'] = glob.config.bancho_username
    args['h'] = glob.config.bancho_hashed_password

    # james it was good try however someone can leak their u and h arg, sadly you need to opt to use clientsession here. 
    #request.resp_headers['Location'] = f'https://osu.ppy.sh/web/osu-search.php{argstr}'
    async with glob.web.get("https://osu.ppy.sh/web/osu-search-set.php", params=args) as resp:
        if resp.status != 200:
            return b'0'

        ret = await resp.read()

    return (200, ret.encode())

@web.route("/web/osu-search-set.php")
async def osuSearchSet(request):
    args = request.args
    if not auth(args['u'], args['h'], request):
        return b''

    args['u'] = glob.config.bancho_username
    args['h'] = glob.config.bancho_hashed_password

    # james it was good try however someone can leak their u and h arg, sadly you need to opt to use clientsession here.
    #request.resp_headers['Location'] = f'https://osu.ppy.sh/web/osu-search-set.php?{"&".join(_args)}'
    async with glob.web.get("https://osu.ppy.sh/web/osu-search-set.php", params=args) as resp:
        if resp.status != 200:
            return b'0'

        ret = await resp.read()

    return (200, ret.encode())

@web.route("/users", ['POST'])
async def ingameRegistration(request):
    start = time.time()
    mpargs = request.args

    name = mpargs['user[username]'].strip() # what is this setup osu lol
    email = mpargs['user[user_email]'].strip()
    pw = mpargs['user[password]'].strip()

    if not mpargs.get('check') or not all((name, email, pw)):
        return b'missing required paramaters'

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
        request.resp_headers['Content-Type'] = 'application/json'
        return orjson.dumps(ret)

    if int(mpargs['check']) == 0:
        md5 = hashlib.md5(pw.encode()).hexdigest().encode()
        k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'')
        bc = k.derive(md5).decode('unicode-escape')

        await glob.db.execute("INSERT INTO users (name, email, pw, safe_name) VALUES ($1, $2, $3, $4)", name, email, bc, name.lower().replace(' ', '_'))
        uid = await glob.db.fetchval("SELECT id FROM users WHERE name = $1", name)
        await glob.db.execute('INSERT INTO stats (id) VALUES ($1)', uid)
        log(f'{name} successfully registered. | Time Elapsed: {(time.time() - start) * 1000:.2f}ms', Ansi.LBLUE)

    return b'ok'

@web.route("/web/check-updates.php")
async def osuUpdates(request):
    args = request.args

    async with glob.web.get("https://old.ppy.sh/web/check-updates.php", params=args) as resp:
        if resp.status != 200:
            return b'error checking for updates'

        ret = await resp.read()

    return ret

@web.route("/web/osu-getbeatmapinfo.php")
async def osuMapInfo(request): # TODO
    args = request.args
    if not auth(args['u'], args['h'], request):
        return b''

    data = request.body
    ...

@web.route("/web/osu-osz2-getscores.php")
async def getMapScores(request):
    args = request.args
    if not auth(args['us'], args['ha'], request):
        return b''

    if (md5 := args['c']) in glob.cache['unsub']:
        return b'-1|false' # tell client map is unsub xd

    mods = int(args['mods'])
    mode = lbModes(int(args['m']), mods)
    sid = int(args['i'])
    lbm = int(args['v'])

    player = request.extras.get('player')

    if mode.value != player.mode or mods != player.mods:
        player.mode = mode.value
        player.mode_vn = mode.as_vn
        player.mods = mods
        
        if not player.restricted:
            for o in glob.players.values():
                o.enqueue(writer.userStats(player))

    bmap = await Beatmap.from_md5(md5)

    if not bmap:
        file = args['f'].replace('+', '')
        if not (info := regexes.map_file.match(unquote(file))): # once again osu why
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

    if not (lb := bmap.lb):
        lb = Leaderboard(bmap, mode)
        bmap.lb = lb
        
    return await lb.return_leaderboard(player, lbm, mods)

# POGGG
@web.route("/web/osu-submit-modular-selector.php", ['POST'])
async def scoreSubmit(request):
    mpargs = request.args

    s = await Score.submission(mpargs['score'], mpargs['iv'], mpargs['pass'], mpargs['osuver'])

    if not s:
        return b'error: no'
    elif not s.user:
        return b'' # player not online, make client make resubmit attempts
    elif not s.map:
        return b'error: beatmap' # map unsubmitted
    elif s.mods & Mods.UNRANKED:
        return b'error: no'

    if s.mode != s.user.mode or s.mods != s.user.mods:
        s.user.mode = s.mode.value
        s.user.mods = s.mods
        for o in glob.players.values():
            o.enqueue(writer.userStats(s.user))

    # submit score and get id xd
    await glob.db.execute(f'INSERT INTO {s.mode.table} (md5, score, acc, pp, combo, mods, n300, geki, n100, katu, n50, miss, grade, status, mode, time, uid, readable_mods, fc) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18, $19)', s.map.md5, s.score, s.acc, s.pp, s.combo, s.mods, s.n300, s.geki, s.n100, s.katu, s.n50, s.miss, s.grade, s.status.value, s.mode.as_vn, s.time, s.user.id, s.readable_mods, s.fc)
    s.id = await glob.db.fetchval(f'SELECT id FROM {s.mode.table} WHERE md5 = $1 AND uid = $2 AND time = $3', s.map.md5, s.user.id, s.time)
    
    if s.status == scoreStatuses.Best:
        # set any other best scores to submitted ones as they've been overwritten
        await glob.db.execute(f'UPDATE {s.mode.table} SET status = 1 WHERE status = 2 AND uid = $1 AND md5 = $2 AND mode = $3 AND id != $4', s.user.id, s.map.md5, s.mode.as_vn, s.id)

    # save replay if not a failed score
    if s.status != scoreStatuses.Failed:
        files = request.files
        replay = files.get('score')

        # i will make this auto-parse the replays one day when im not lazy
        if s.mods & Mods.RELAX:
            f = rx_path / f'{s.id}.osr'
        elif s.mods & Mods.AUTOPILOT:
            f = ap_path / f'{s.id}.osr'
        else:
            f = vn_path / f'{s.id}.osr'

        f.write_bytes(replay)
        
        if glob.config.anticheat:
            threading.Thread(target=s.analyse).start()
    
    cap = glob.config.pp_caps[s.mode.value]

    if cap is not None and s.pp >= cap and s.map.status & mapStatuses.GIVE_PP and glob.config.anticheat and not s.user.restricted:
        await s.user.restrict(reason='Exceeding PP cap', fr=glob.bot)

    # update stats EEEEEEE
    stats = s.user.stats[s.mode.value]
    old = copy.copy(stats) # we need a copy of the old stats for submission chart

    stats.pc += 1

    if s.status == scoreStatuses.Best and s.map.status >= mapStatuses.Ranked:
        add = s.score

        if s.old_best:
            add -= s.old_best.score

        if s.combo > old.max_combo:
            stats.max_combo = s.combo
        
        if s.map.status & mapStatuses.GIVE_PP:
            stats.rscore += add

    stats.tscore += s.score

    await s.user.update_stats(s.mode, s.mode.table, s.mode.as_vn)

    # sub charts bruh
    if s.mods & Mods.GAME_CHANGING or s.status == scoreStatuses.Failed:
        log(f'[{s.mode!r}] {s.user.name} submitted a score on {s.map.name} ({s.status.name})', Ansi.LBLUE)
        return b'error: no' # not actually erroring, score is already submitted we just want client to stop request as we cannot provide chart
    
    achievements = ''
    if s.map.status & mapStatuses.GIVE_PP and not s.user.restricted:
        achs = []
        for ach in glob.achievements:
            if ach in s.user.achievements:
                continue
                
            if ach.cond(s):
                await s.user.unlock_ach(ach)
                achs.append(ach)
                
        achievements = '/'.join([a.format for a in achs])

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

    # score-specific ranking
    if s.map.status >= mapStatuses.Ranked:
        charts.append('|'.join((
            'chartId:beatmap',
            f'chartUrl:https://{glob.config.domain}/b/{s.map.id}',
            'chartName:Current Score',

            *(( # wtaf
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
            chart_format('maxCombo', old.max_combo, stats.max_combo),
            chart_format('accuracy', round(old.acc, 2), round(stats.acc, 2)),
            chart_format('pp', old.pp, stats.pp)
        ) if old else (
            chart_format('rank', None, stats.rank),
            chart_format('rankedScore', None, stats.rscore),
            chart_format('totalScore', None, stats.tscore),
            chart_format('maxCombo', None, stats.max_combo),
            chart_format('accuracy', None, round(stats.acc, 2)),
            chart_format('pp', None, stats.pp)
        )),
        
        f'achievements-new:{achievements}'
    )))

    if s.status == scoreStatuses.Best and s.rank == 1 and s.map.status >= mapStatuses.Ranked:
        # announce #1 to announce channel cus they achieved #1

        perf = ''
        prev = ''

        if s.map.status != mapStatuses.Loved:
            perf = f' worth {round(s.pp):,}pp'

        prev1 = await glob.db.fetchrow(f'SELECT users.name FROM users LEFT OUTER JOIN {s.mode.table} t ON t.uid = users.id WHERE t.md5 = $1 AND t.mode = $2 AND t.status = 2 AND users.priv & 1 > 0 AND t.uid != $3 AND t.id != $4 ORDER BY t.{s.mode.sort} DESC LIMIT 1', s.map.md5, s.mode.as_vn, s.user.id, s.id)

        if prev1:
            prev = f' (Previous #1: [https://{glob.config.domain}/u/{prev1["name"]} {prev1["name"]}])'

        msg = f'[{s.mode!r}] {s.user.embed} achieved #1 on {s.map.embed} +{s.readable_mods}{perf}{prev}'
        chan = glob.channels['#announce']
        chan.send(glob.bot, msg, True)
        
    if s.status == scoreStatuses.Best and s.map.status >= mapStatuses.Ranked:
        threading.Thread(target=s.map.lb.set_user_pb, args=(s.user, s,)).start()
        
    s.user.last_score = s

    log(f'[{s.mode!r}] {s.user.name} submitted a score on {s.map.name} ({s.status.name})', Ansi.LBLUE)
    return '\n'.join(charts).encode() # thank u osu

@web.route("/web/osu-getreplay.php")
async def getReplay(request):
    args = request.args
    if not auth(args['u'], args['h'], request):
        return b''

    player = request.extras.get('player')
    sid = args['c']

    if player.mods & Mods.RELAX:
        f = rx_path / f'{sid}.osr'
    elif player.mods & Mods.AUTOPILOT:
        f = ap_path / f'{sid}.osr'
    else:
        f = vn_path / f'{sid}.osr'

    if f.exists():
        return f.read_bytes()

    return # osu wants empty response if there's no replay

@web.route("/web/lastfm.php")
async def lastFM(request):
    args = request.args
    if not auth(args['us'], args['ha'], request):
        return b''

    player = request.extras.get('player')

    b = args['b']

    if b[0] != 'a' or not glob.config.anticheat:
        return b'-3'

    flags = int(b[1:])

    # this is quite ugly but whatev
    if flags & osuFlags.SpeedHackDetected: # speed hack
        return await player.restrict(reason='osu!anticheat flags (speed hack)', fr=glob.bot)
    if flags & osuFlags.FL_CHEAT: # fl tampering
        return await player.restrict(reason='osu!anticheat flags (fl cheating)', fr=glob.bot)
    if flags & osuFlags.SpinnerHack: # spin hack
        return await player.restrict(reason='osu!anticheat flags (spin hack)', fr=glob.bot)
    if flags & osuFlags.FastPress: # mania fast presses:
        return await player.restrict(reason='osu!anticheat flags (mania fast presses)', fr=glob.bot)
    if flags & osuFlags.AUTO_BOT: # autobot
        return await player.restrict(reason='osu!anticheat (autobot)', fr=glob.bot)
    if flags & osuFlags.HQ_RELATED: # hqosu
        return await player.restrict(reason='osu!anticheat flags (hqosu)', fr=glob.bot)
    if flags & osuFlags.AQN_RELATED: # old aqn
        return await player.restrict(reason='osu!anticheat flags (aqn)', fr=glob.bot)

    return b'-3'
