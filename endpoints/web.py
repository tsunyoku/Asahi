from xevel import Router, Request
from cmyui.logging import log, Ansi
from collections import defaultdict
from urllib.parse import unquote
from pathlib import Path
from typing import Union, Optional

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand
from cryptography.hazmat.backends import default_backend as backend

import string
import random
import hashlib
import time
import copy
import threading
import asyncio
import orjson

from objects import glob
from objects.beatmap import Beatmap
from objects.score import Score
from constants.modes import lbModes, osuModes
from constants.statuses import mapStatuses, scoreStatuses
from constants.mods import Mods
from constants.privs import Privileges
from constants.flags import osuFlags
from objects.leaderboard import Leaderboard
from constants import regexes
from packets import writer

ss_path = Path.cwd() / 'resources/screenshots'
vn_path = Path.cwd() / 'resources/replays'
rx_path = Path.cwd() / 'resources/replays_rx'
ap_path = Path.cwd() / 'resources/replays_ap'

web = Router(f'osu.{glob.config.domain}')

async def auth(name: str, md5: str, req: Request) -> bool:
    name = name.replace('%20', ' ')

    if not (player := await glob.players.find_login(name, md5)):
        log(f'{name} failed authentication', Ansi.LRED)
        return False

    req.extras['player'] = player
    return True

if glob.config.debug:
    @web.after_request()
    async def logRequest(resp: Request) -> Request:
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
async def uploadScreenshot(request: Request) -> bytes:
    mpargs = request.args
    if not await auth(mpargs['u'], mpargs['p'], request):
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
async def getScreenshot(request: Request, scr: str) -> bytes:
    ss = ss_path / scr
    _type = scr.split('.')[1]

    if ss.exists():
        ssb = ss.read_bytes()
        request.resp_headers['Content-Type'] = f'image/{_type}'
        return ssb
    else:
        return b'could not find screenshot'

@web.route("/web/osu-getseasonal.php")
async def seasonalBG(_) -> list:
    return glob.config.menu_bgs

@web.route("/web/bancho_connect.php")
async def banchoConnect(_) -> bytes:
    return b'asahi is gamer owo'

@web.route("/web/osu-getfriends.php")
async def getFriends(request: Request) -> bytes:
    args = request.args
    if not await auth(args['u'], args['h'], request):
        return b''

    p = await glob.players.get(name=args['u'])
    return '\n'.join(map(str, p.friends)).encode()

@web.route("/d/<mid>")
async def mapDownload(request: Request, mid: str) -> tuple[int, bytes]:
    request.resp_headers['Location'] = f'{glob.config.map_api}/d/{mid}'
    return (301, b'') # redirect

def directMapFormat(diff: dict) -> str:
    return f'{diff["DiffName"]} ({diff["DifficultyRating"]:.2f}⭐)@{diff["Mode"]}'

def directSetFormat(bmap: dict, diffs: list) -> str:
    return (f'{bmap["SetID"]}.osz|{bmap["Artist"]}|{bmap["Title"]}|{bmap["Creator"]}'
            f'|{bmap["RankedStatus"]}|10.0|{bmap["LastUpdate"]}|{bmap["SetID"]}|0|0'
            f'|0|0|0|{diffs}'
            )

@web.route("/web/osu-search.php")
async def osuSearch(request: Request) -> Union[tuple, bytes]:
    args = request.args
    if not await auth(args['u'], args['h'], request):
        return b''

    request_args = {'amount': 100, 'offset': 100 * int(args['p'])}

    if (query := args['q']) not in ('Newest', 'Top+Rated', 'Most+Played'):
        request_args['query'] = query

    if (mode := int(args['m'])) != -1:
        request_args['mode'] = mode

    if (d_status := int(args['r'])) != 4:
        request_args['status'] = mapStatuses.from_direct(d_status)

    async with glob.web.get(f"{glob.config.map_api}/api/search", params=request_args) as resp:
        if resp.status != 200:
            return (resp.status, b'0')

        result = await resp.json()

    map_amount = len(result)
    ret = [f'{"101" if map_amount == 100 else map_amount}']

    for _map in result:
        sorted_diffs = sorted(_map['ChildrenBeatmaps'], key=lambda sr: sr['DifficultyRating'])

        diffs = ', '.join([directMapFormat(s) for s in sorted_diffs])
        ret.append(directSetFormat(_map, diffs))

    return '\n'.join(ret).encode()

@web.route("/web/osu-search-set.php")
async def osuSearchSet(request: Request) -> bytes:
    args = request.args
    if not await auth(args['u'], args['h'], request):
        return b''

    if 'b' in args: # wants beatmap
        _type, value = ('id', args['b'])
    elif 's' in args: # wants beatmapset
        _type, value = ('sid', args['s'])
    else:
        return

    _set = await glob.db.fetchrow(f'SELECT DISTINCT * FROM maps WHERE {_type} = %s', [value])

    if not _set: # get it from api and then grab it again!
        if 's' in args:
            await Beatmap.cache_set(args['s'])
        elif 'b' in args:
            await Beatmap.cache_from_map(args['b'])

        _set = await glob.db.fetchrow(f'SELECT DISTINCT * FROM maps WHERE {_type} = %s', [value])

    return (
        f'{_set["sid"]}.osz|{_set["artist"]}|{_set["title"]}|'
        f'{_set["mapper"]}|{_set["status"]}|10.0|{_set["update"]}|'
        f'{_set["sid"]}|0|0|0|0|0'
    ).encode()

@web.route("/users", ['POST'])
async def ingameRegistration(request: Request) -> Union[dict, bytes]:
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

    if await glob.db.fetchval("SELECT 1 FROM users WHERE name = %s", [name]):
        errors['username'].append('Username already taken!')

    if await glob.db.fetchval("SELECT 1 FROM users WHERE name = %s", [email]):
        errors['user_email'].append('Email already in use!')

    if not len(pw) >= 8:
        errors['password'].append('Password must be 8+ characters!')

    if errors:
        return {'form_error': {'user': errors}}

    if int(mpargs['check']) == 0:
        md5 = hashlib.md5(pw.encode()).hexdigest().encode()
        k = HKDFExpand(algorithm=hashes.SHA256(), length=32, info=b'', backend=backend())
        bc = k.derive(md5).decode('unicode-escape')

        glob.cache['pw'][bc] = md5

        uid = await glob.db.execute("INSERT INTO users (name, email, pw, safe_name, registered_at) VALUES (%s, %s, %s, %s, %s)", [name, email, bc, name.lower().replace(' ', '_'), time.time()])
        await glob.db.execute('INSERT INTO stats (id) VALUES (%s)', [uid])
        log(f'{name} successfully registered. | Time Elapsed: {(time.time() - start) * 1000:.2f}ms', Ansi.LBLUE)

    return b'ok'

@web.route("/web/check-updates.php")
async def osuUpdates(request: Request) -> bytes:
    args = request.args

    async with glob.web.get("https://old.ppy.sh/web/check-updates.php", params=args) as resp:
        if resp.status != 200:
            return b'error checking for updates'

        ret = await resp.read()

    return ret

@web.route("/web/osu-getbeatmapinfo.php")
async def osuMapInfo(request: Request) -> bytes:
    args = request.args
    if not await auth(args['u'], args['h'], request):
        return b''

    data = orjson.loads(request.body)
    player = request.extras.get('player')

    ret = []

    for idx, file in enumerate(data['Filenames']):
        if not (info := regexes.map_file.match(unquote(file))): # once again osu why
            continue

        _map = await glob.db.fetchrow(
            'SELECT id, sid, md5, status FROM maps WHERE artist = %s AND title = %s AND diff = %s AND mapper = %s',
            [info['artist'], info['title'], info['diff'], info['mapper']]
        )

        if not _map:
            continue

        status = mapStatuses(_map['status'])
        _map['status'] = status.to_api()

        grades = ['N', 'N', 'N', 'N'] # 1 per mode, N = no score?

        mode_table = osuModes(player.mode).table # use grades for their current mode

        async for s in glob.db.iter(f'SELECT grade, mode FROM {mode_table} WHERE md5 = %s AND uid = %s AND status = 2', [_map['md5'], player.id]):
            grades[s['mode']] = s['grade']

        ret.append(
            f'{idx}|'
            f'{_map["id"]}|{_map["sid"]}|{_map["md5"]}|'
            f'{_map["status"]}|{"|".join(grades)}'
        )

    return '\n'.join(ret).encode()


@web.route("/web/osu-osz2-getscores.php")
async def getMapScores(request: Request) -> bytes:
    args = request.args
    if not await auth(args['us'], args['ha'], request):
        return b''

    if (md5 := args['c']) in glob.cache['unsub']:
        return b'-1|false' # tell client map is unsub xd

    mods = int(args['mods'])
    mode = lbModes(int(args['m']), mods)
    lbm = int(args['v'])

    player = request.extras.get('player')

    if mode.value != player.mode or mods != player.mods:
        player.mode = mode.value
        player.mode_vn = mode.as_vn
        player.mods = mods

        if not player.restricted:
            glob.players.enqueue(writer.userStats(player))

    bmap = await Beatmap.from_md5(md5)

    if not bmap:
        file = args['f'].replace('+', '')
        if not (info := regexes.map_file.match(unquote(file))): # once again osu why
            # invalid file? idfk
            glob.cache['unsub'].append(md5)
            return b'-1|false'

        exists = await glob.db.fetchval(
            'SELECT 1 FROM maps WHERE artist = %s AND title = %s AND diff = %s AND mapper = %s',
            [info['artist'], info['title'], info['diff'], info['mapper']]
        )

        if exists:
            return b'1|false' # bmap submitted but not up to date, send update available
        else:
            glob.cache['unsub'].append(md5)
            return b'-1|false' # bmap or other version of bmap cannot be found, must be unsubmitted

    if bmap.nc < time.time():
        await bmap.check_status()

    if not (lb := getattr(bmap, mode.leaderboard)):
        setattr(bmap, mode.leaderboard, lb := Leaderboard(bmap, mode)) # cursed 1 line lol

    return await lb.return_leaderboard(player, lbm, mods)

@web.route("/web/osu-submit-modular-selector.php", ['POST'])
async def scoreSubmit(request: Request) -> bytes:
    mpargs = request.args

    s = await Score.from_submission(mpargs['score'], mpargs['iv'], mpargs['pass'], mpargs['osuver'])

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
        glob.players.enqueue(writer.userStats(s.user))

    # submit score and get id xd
    s.id = await glob.db.execute(
        f'INSERT INTO {s.mode.table} (md5, score, acc, pp, combo, mods, n300, '
        f'geki, n100, katu, n50, miss, grade, status, mode, time, uid, readable_mods, fc) VALUES '
        f'(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        [s.map.md5, s.score, s.acc, s.pp, s.combo, int(s.mods), s.n300,
         s.geki, s.n100, s.katu, s.n50, s.miss, s.grade, s.status.value, s.mode.as_vn, s.time, s.user.id, s.readable_mods, s.fc]
    )

    if s.status == scoreStatuses.Best:
        # set any other best scores to submitted ones as they've been overwritten
        await glob.db.execute(
            f'UPDATE {s.mode.table} SET status = 1 WHERE status = 2 AND uid = %s AND md5 = %s AND mode = %s AND id != %s',
            [s.user.id, s.map.md5, s.mode.as_vn, s.id]
        )

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

        if glob.config.anticheat and not s.user.priv & Privileges.BypassAnticheat:
            loop = asyncio.get_event_loop()
            loop.create_task(s.analyse())

    cap = glob.config.pp_caps[s.mode.value]

    if cap is not None and s.pp >= cap \
        and s.map.status & mapStatuses.GIVE_PP and glob.config.anticheat \
        and not s.user.restricted and not s.user.priv & Privileges.Whitelisted: # ugly

        await s.user.restrict(reason=f'Exceeding PP cap ({s.pp:,}pp) on {s.map.name}', fr=glob.bot)

    # update stats EEEEEEE
    stats = s.user.stats[s.mode.value]
    old = copy.copy(stats) # we need a copy of the old stats for submission chart

    elapsed = mpargs.get('st' if s.passed else 'ft') # timewarp check with this soon?

    if not elapsed and s.user.priv & Privileges.BypassAnticheat:
        await s.user.restrict('Modified client', fr=glob.bot) # its really only old version, but its supposed to be blocked on login. if it isnt present it must be modified to seem like a new version

    stats.playtime += int(elapsed) // 1000
    stats.tscore += s.score
    stats.pc += 1

    if s.status == scoreStatuses.Best and s.map.status >= mapStatuses.Ranked:
        add = s.score

        if s.old_best:
            add -= s.old_best.score

        if s.combo > old.max_combo:
            stats.max_combo = s.combo

        if s.map.status & mapStatuses.GIVE_PP:
            stats.rscore += add

    await s.user.update_stats(s.mode, s.mode.table, s.mode.as_vn)

    if not s.user.restricted:
        s.map.plays += 1
        if s.passed:
            s.map.passes += 1

        await glob.db.execute(
            'UPDATE maps SET plays = %s, passes = %s WHERE md5 = %s',
            [s.map.plays, s.map.passes, s.map.md5]
        )

    # sub charts bruh
    if s.status == scoreStatuses.Failed:
        log(f'[{s.mode!r}] {s.user.name} submitted a score on {s.map.name} ({s.status.name})', Ansi.LBLUE)
        return b'error: no' # not actually erroring, score is already submitted we just want client to stop request as we cannot provide chart

    achievements = ''
    if s.map.status & mapStatuses.GIVE_PP and not s.user.restricted: # TODO: hush-hush etc. achievements
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
        f'beatmapPlaycount:{s.map.plays}|'
        f'beatmapPasscount:{s.map.passes}|'
        f'approvedDate:{s.map.update}'
    )

    # score-specific ranking
    if s.map.status >= mapStatuses.Ranked:
        charts.append('|'.join((
            'chartId:beatmap',
            f'chartUrl:{s.map.set_url}',
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
        'chartName:Overall Stats',

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

    if s.status == scoreStatuses.Best and s.map.status >= mapStatuses.Ranked:
        if s.rank == 1: # announce #1 to announce channel cus they achieved #1
            await s.announce_n1()

        # update lb cache
        lb = getattr(s.map, s.mode.leaderboard)

        if lb:
            threading.Thread(target=lb.set_user_pb, args=(s.user, s,)).start()

    s.user.last_score = s

    log(f'[{s.mode!r}] {s.user.name} submitted a score on {s.map.name} ({s.status.name})', Ansi.LBLUE)
    return '\n'.join(charts).encode() # thank u osu

@web.route("/web/osu-getreplay.php")
async def getReplay(request: Request) -> bytes:
    args = request.args
    if not await auth(args['u'], args['h'], request):
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
async def lastFM(request: Request) -> Optional[bytes]:
    args = request.args
    if not await auth(args['us'], args['ha'], request):
        return b''

    player = request.extras.get('player')

    b = args['b']

    if b[0] != 'a' or not glob.config.anticheat or player.priv & Privileges.BypassAnticheat:
        return b'-3'

    flags = int(b[1:])

    # this is quite ugly but whatev
    if flags & osuFlags.SpeedHackDetected: # speed hack
        return await player.restrict(reason='osu!anticheat flags (speed hack)', fr=glob.bot)
    if flags & osuFlags.FL_CHEAT: # fl tampering
        return await player.restrict(reason='osu!anticheat flags (fl cheating)', fr=glob.bot)
    if flags & osuFlags.SpinnerHack: # spin hack
        return await player.restrict(reason='osu!anticheat flags (spin hack)', fr=glob.bot)
    if flags & osuFlags.FastPress: # mania fast presses
        return await player.restrict(reason='osu!anticheat flags (mania fast presses)', fr=glob.bot)
    if flags & osuFlags.AUTO_BOT: # autobot
        return await player.restrict(reason='osu!anticheat (autobot)', fr=glob.bot)
    if flags & osuFlags.HQ_RELATED: # hqosu
        return await player.restrict(reason='osu!anticheat flags (hqosu)', fr=glob.bot)
    if flags & osuFlags.AQN_RELATED: # old aqn
        return await player.restrict(reason='osu!anticheat flags (aqn)', fr=glob.bot)

    return b'-3'

@web.route("/web/osu-addfavourite.php")
async def osuAddSetFavourite(request: Request) -> bytes:
    args = request.args
    if not await auth(args['u'], args['h'], request):
        return b'Please login to add favourites!' # request-specific auth error? XD

    player = request.extras.get('player')

    sid = int(args['a'])

    if await glob.db.fetchval('SELECT 1 FROM favourites WHERE uid = %s AND sid = %s', [player.id, sid]):
        return b'You\'ve already favourited this beatmap!' # request-specific return? XD

    await glob.db.execute(
        'INSERT INTO favourites '
        'VALUES (%s, %s)',
        [player.id, sid]
    )

@web.route("/web/osu-getfavourites.php")
async def osuGetSetFavourites(request: Request) -> bytes:
    args = request.args
    if not await auth(args['u'], args['h'], request):
        return b''

    player = request.extras.get('player')
    favourites = await glob.db.fetchall('SELECT sid FROM favourites WHERE uid = %s', [player.id])

    return '\n'.join(favourites).encode()

@web.route("/web/osu-rate.php")
async def osuAddMapRating(request: Request) -> bytes:
    args = request.args
    if not await auth(args['u'], args['p'], request):
        return b'auth fail' # request-specific auth error? XD

    md5 = args['c']
    player = request.extras.get('player')

    if 'v' not in args: # verifying we can rate the map?
        if md5 in glob.cache['unsub']:
            return b'no exist'

        _map = await Beatmap.from_md5(md5)

        if _map.status < mapStatuses.Ranked:
            return b'not ranked'

        if not await glob.db.fetchval('SELECT 1 FROM ratings WHERE md5 = %s AND uid = %s', [md5, player.id]):
            return b'ok'
    else: # already verified, we just need to add the rating
        rating = int(args['v'])

        await glob.db.execute(
            'INSERT INTO ratings '
            'VALUES (%s, %s, %s)',
            [player.id, md5, rating]
        )

    # already voted/just voted, we'll return the average rating
    avg = await glob.db.fetchval('SELECT AVG(rating) AS average FROM ratings WHERE md5 = %s', [md5])
    return f'alreadyvoted\n{avg}'.encode()
