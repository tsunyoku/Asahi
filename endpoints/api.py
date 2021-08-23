from xevel import Router, Request
from cmyui.logging import log, Ansi
from cmyui.osu.oppai_ng import OppaiWrapper
from pathlib import Path
from datetime import datetime
from typing import Union

from objects import glob

from objects.beatmap import Beatmap
from constants.mods import Mods
from constants.modes import osuModes, lbModes
from constants.privs import Privileges
from packets import writer

import hashlib
import struct
import orjson

api = Router(f'api.{glob.config.domain}')

if glob.config.debug:
    @api.after_request()
    async def logRequest(resp: Request) -> Request:
        if resp.code >= 400:
            colourret = Ansi.LRED
        else:
            colourret = Ansi.LCYAN

        log(f'[{resp.type}] {resp.code} {resp.url} | Time Elapsed: {resp.elapsed}', colourret)
        return resp

async def get_rank(mode: str, uid: int, pp: int) -> int:
    rank = await glob.redis.zrevrank(f'asahi:leaderboard:{mode}', uid)
    if rank is not None:
        return rank + 1

    if pp == 0: return 0

    return 1

async def get_country_rank(mode: str, uid: int, pp: int, country: str) -> int:
    rank = await glob.redis.zrevrank(f'asahi:leaderboard:{mode}:{country}', uid)
    if rank is not None:
        return rank + 1

    if pp == 0: return 0

    return 1

@api.route('/player_count')
async def onlinePlayers(request: Request) -> dict:
    return {'online': len(glob.players) - 1}

@api.route('/player')
async def user(request: Request) -> Union[tuple, dict]:
    args = request.args

    id = int(args.get('id', 0))
    username = args.get('username', None)

    m = int(args.get('mode', 0))
    rx = int(args.get('rx', 0))

    if not username and not id:
        return (400, {'message': 'you must specify either a username or id!'})

    if not id:
        id = await glob.db.fetchval('SELECT id FROM users WHERE name = %s', [username])

    if not (user := await glob.players.get(id=id, sql=True)):
        return (400, {'message': "user couldn't be found!"})

    if user.priv & Privileges.Disallowed:
        return (400, {'message': 'user is restricted/banned!'})

    if rx == 0: rx = Mods.NOMOD
    elif rx == 1: rx = Mods.RELAX
    elif rx == 2: rx = Mods.AUTOPILOT

    mode = lbModes(m, rx)

    info = {
        'id': user.id,
        'name': user.name,
        'country': user.country_iso,
        'priv': user.priv,
        'clan': {
            'id': user.clan.id,
            'name': user.clan.name,
            'tag': user.clan.tag
        } if user.clan else None
    }

    return {'info': info, 'stats': user.stats[mode.value]}

@api.route("/player_status")
async def playerStatus(request: Request) -> Union[tuple, dict]:
    args = request.args

    id = int(args.get('id', 0))
    username = args.get('username', None)

    if not id and not username:
        return (400, {'message': 'you must specify either a username or id!'})

    if username:
        id = await glob.db.fetchval('SELECT id FROM users WHERE name = %s', [username])

    if not id:
        return (400, {'message': 'user could not be found! please check the username/id you specified and try again'})

    if not (player := await glob.players.get(id=id)):
        return {'status': {'online': False}}

    if player.priv & Privileges.Disallowed:
        return (400, {'message': 'user is restricted/banned!'})

    if player.map_md5:
        bmap = await Beatmap.from_md5(player.map_md5)
    else:
        bmap = None

    status = {
        'online': True,
        'action': player.action,
        'info': player.info,
        'mode': osuModes(player.mode).name,
        'mods': repr(player.mods),
        'map': {
            'md5': bmap.md5,
            'id': bmap.id,
            'set_id': bmap.sid,
            'artist': bmap.artist,
            'title': bmap.title,
            'difficulty': bmap.diff,
            'mapper': bmap.mapper,
            'star_rating': bmap.sr
        } if bmap else None
    }

    return {'status': status}

@api.route("/get_leaderboard")
async def getLb(request: Request) -> list:
    args = request.args

    mode = int(args.get('mode', 0))
    rx = int(args.get('rx', 0))

    search = args.get('u', None)

    limit = int(args.get('limit', 50))
    page = int(args.get('p', 0))

    country = args.get('country', None)

    if rx == 0: rx = Mods.NOMOD
    elif rx == 1: rx = Mods.RELAX
    elif rx == 2: rx = Mods.AUTOPILOT

    lb_mode = lbModes(mode, rx)
    lb_str = f'asahi:leaderboard:{lb_mode.name}'

    if country:
        lb_str += f':{country.upper()}'

    lb = [int(u) for u in await glob.redis.zrangebyscore(lb_str)]
    lb.reverse() # redis returns backwards??

    # limit amount of users to return
    lb = lb[:limit]

    if page:
        offset = limit * page # ?
        lb = lb[offset:]

    ret = []

    # TODO: clean this?

    if not search:
        for rank, uid in enumerate(lb):
            info = await glob.db.fetchrow(
                'SELECT users.name, users.country, stats.pp_{0} pp, stats.acc_{0} acc, stats.pc_{0} pc FROM users '
                'LEFT OUTER JOIN stats ON stats.id = users.id WHERE users.id = %s'.format(lb_mode.name),
                [uid]
            )

            db_grades = await glob.db.fetchrow(
                'SELECT SUM(grade IN ("X", "XH")) AS ss, '
                'SUM(grade IN ("S", "SH")) AS s, '
                'SUM(grade = "A") AS a FROM {0} WHERE uid = %s AND mode = %s'.format(lb_mode.table),
                [uid, mode]
            )


            ret.append({
                'rank': rank + 1,
                'userid': uid,
                'name': info['name'],
                'country': info['country'],
                'pp': info['pp'],
                'acc': info['acc'],
                'playcount': info['pc'],
                'grades': {key: int(val or 0) for key, val in db_grades.items()}
            })

        return ret

    users = await glob.db.fetch(
        f'SELECT users.name, users.id, users.country, stats.pp_{lb_mode.name} pp, stats.acc_{lb_mode.name} acc, stats.pc_{lb_mode.name} pc '
        f'FROM users LEFT OUTER JOIN stats ON stats.id = users.id WHERE users.name LIKE %s', [f'{search}%']
    )

    for info in users:
        if info['id'] not in lb:
            continue

        db_grades = await glob.db.fetchrow(
            'SELECT SUM(grade IN ("SS", "SSH")) AS ss, '
            'SUM(grade IN ("S", "SH")) AS s, '
            'SUM(grade = "A") AS a FROM {0} WHERE uid = %s AND mode = %s'.format(lb_mode.table),
            [info['id'], mode]
        )

        ret.append({
            'rank': lb.index(info['id']) + 1,
            'userid': info['id'],
            'name': info['name'],
            'country': info['country'],
            'pp': info['pp'],
            'acc': info['acc'],
            'playcount': info['pc'],
            'grades': {key: int(val) for key, val in db_grades.items()}
        })

    return ret

DATETIME_OFFSET = 0x89F7FF5F7B58000

@api.route("/get_replay")
async def getReplay(request: Request) -> Union[tuple, bytes]:
    args = request.args

    sid = int(args.get('id', 0))
    rx = int(args.get('rx', 0))

    if not sid:
        return (400, {'message': 'please specify a score id!'})

    BASE_DIR = Path.cwd() / 'resources'

    if rx == 0:
        REPLAY_PATH = BASE_DIR / 'replays'
        table = 'scores'
    elif rx == 1:
        REPLAY_PATH = BASE_DIR / 'replays_rx'
        table = 'scores_rx'
    elif rx == 2:
        REPLAY_PATH = BASE_DIR / 'replays_ap'
        table = 'scores_ap'

    file = REPLAY_PATH / f'{sid}.osr'

    if not file.exists():
        return (400, {'message': "replay couldn't be found. please check the score id and try again!"})

    raw_replay = file.read_bytes()

    # get score from sql
    score = await glob.db.fetchrow(
        f'SELECT t.*, t.mode m, users.name, maps.* FROM {table} t '
        'LEFT OUTER JOIN users ON users.id = t.uid LEFT OUTER JOIN maps ON maps.md5 = t.md5 WHERE t.id = %s',
        [sid]
    )

    # when im not lazy ill use Score.sql to get score object so we can implement rank and shit
    replay_hash = hashlib.md5((
        f'{score["n100"] + score["n300"]}p{score["n50"]}o'
        f'{score["geki"]}o{score["katu"]}t'
        f'{score["miss"]}a{score["md5"]}r'
        f'{score["combo"]}e{score["fc"] == 1}y'
        f'{score["name"]}o{score["score"]}u'
        f'0{score["mods"]}True'
    ).encode()).hexdigest()

    buffer = bytearray() # headers timeee

    # not all scores will have osuver so lets just send latest (as of this code) version
    buffer += struct.pack('<Bi', score["m"], score["osuver"] or 2021_05_20)
    buffer += writer.write_string(score["md5"])

    buffer += writer.write_string(score["name"])
    buffer += writer.write_string(replay_hash)

    buffer += struct.pack('<hhhhhhihBi',
        score["n300"], score["n100"],
        score["n50"], score["geki"],
        score["katu"], score["miss"],
        score["score"], score["combo"],
        score["fc"], score["mods"]
    )

    buffer += b'\x00' # graph probably NEVER

    buffer += struct.pack('<q', score["time"] * 1_000_000 + DATETIME_OFFSET)

    buffer += struct.pack('<i', len(raw_replay))
    buffer += raw_replay
    buffer += struct.pack('<q', sid)

    name = (f'{score["name"]} ~ {score["artist"]} - {score["title"]} [{score["diff"]}] '
           f'+{score["readable_mods"]} ({datetime.fromtimestamp(score["time"]):%Y/%m/%d})')

    request.resp_headers['Content-Type'] = 'application/octet-stream'
    request.resp_headers['Content-Description'] = 'File Transfer'
    request.resp_headers['Content-Disposition'] = f'attachment; filename={name}.osr'

    return bytes(buffer)

@api.route('/player_scores')
async def playerScores(req: Request) -> Union[tuple, list]:
    args = req.args

    _type = args.get('type')
    mode = int(args.get('mode', 0))
    rx = int(args.get('rx', 0))

    uid = int(args.get('id', 0))
    username = args.get('username')

    limit = int(args.get('limit', 5))

    if not uid and not username:
        return (400, {'message': 'you must specify either a username or id!'})

    if not uid:
        uid = await glob.db.fetchval('SELECT id FROM users WHERE name = %s', [username])

    if not (user := await glob.players.get(id=uid, sql=True)):
        return (400, {'message': "user couldn't be found!"})

    if user.priv & Privileges.Disallowed:
        return (400, {'message': 'user is restricted/banned!'})

    if not _type:
        return (400, {'message': 'please provide a return type (recent/top)'})

    if rx == 0: rx = Mods.NOMOD
    elif rx == 1: rx = Mods.RELAX
    elif rx == 2: rx = Mods.AUTOPILOT

    mode = lbModes(mode, rx)

    query = ('SELECT t.id, t.md5, score, pp, acc, combo, mods, readable_mods, '
            'n300, n100, n50, miss, geki, katu, '
            'grade, t.status, t.mode, time, fc '
            f'FROM {mode.table} t INNER JOIN maps ON t.md5 = maps.md5 WHERE uid = %s AND t.mode = %s')

    if _type == 'best':
        query += ' AND t.status = 2'
        sort = 'pp'
        s_list = '2, 3'
    else:
        sort = 'time'
        s_list = '2, 3, 4, 5'

    query += f' AND maps.status IN ({s_list}) ORDER BY {sort} DESC LIMIT %s'

    scores = await glob.db.fetch(query, [uid, mode.as_vn, limit])

    for score in scores:
        bmap = await Beatmap.from_md5(score.pop('md5'))

        if mode.as_vn <= 1:
            with OppaiWrapper('oppai-ng/liboppai.so') as ezpp:
                ezpp.set_mode(mode.as_vn)
                ezpp.set_mods(score['mods'])

                ezpp.calculate(Path.cwd() / f'resources/maps/{bmap.id}.osu')

                modded_sr = ezpp.get_sr()
        else:
            modded_sr = bmap.sr # TODO

        score['map'] = {
            'md5': bmap.md5,
            'id': bmap.id,
            'set_id': bmap.sid,
            'artist': bmap.artist,
            'title': bmap.title,
            'difficulty': bmap.diff,
            'mapper': bmap.mapper,
            'nomod_sr': bmap.sr,
            'modded_sr': modded_sr
        } if bmap else None

    return {'scores': scores}

@api.route('/player_search')
async def searchPlayers(req: Request) -> tuple[dict[str, object]]:
    args = req.args

    query = args.get('search')

    if not query:
        return (400, {'message': 'please provide a search query!'})

    users = await glob.db.fetch('SELECT id, name FROM users WHERE name LIKE %s', [f'{query}%'])
    return users or ()

@api.route('/player_most_played')
async def mostPlayed(req: Request) -> Union[tuple, dict]:
    args = req.args

    uid = int(args.get('id', 0))
    username = args.get('username', None)

    m = int(args.get('mode', 0))
    r = int(args.get('rx', 0))

    limit = int(args.get('limit', 6))

    if r == 0: rx = Mods.NOMOD
    elif r == 1: rx = Mods.RELAX
    elif r == 2: rx = Mods.AUTOPILOT

    mode = lbModes(m, rx)

    if not uid and not username:
        return (400, {'message': 'please provide either a username or user id!'})

    if not uid:
        uid = await glob.db.fetchval('SELECT id FROM users WHERE name = %s', [username])

    if not (user := await glob.players.get(id=uid, sql=True)):
        return (400, {'message': "user couldn't be found!"})

    if user.priv & Privileges.Disallowed:
        return (400, {'message': 'user is restricted/banned!'})

    query = ('SELECT md5, COUNT(*) plays '
             f'FROM {mode.table} WHERE uid = %s AND mode = %s '
             f'GROUP BY md5 ORDER BY plays DESC LIMIT %s')

    maps = await glob.db.fetch(query, [user.id, mode.value, limit])

    for _map in maps:
        bmap = await Beatmap.from_md5(_map.pop('md5'))
        _map['map'] = {
            'md5': bmap.md5,
            'id': bmap.id,
            'set_id': bmap.sid,
            'artist': bmap.artist,
            'title': bmap.title,
            'difficulty': bmap.diff,
            'mapper': bmap.mapper,
            'nomod_sr': bmap.sr,
        } if bmap else None

    return {'maps': maps}

@api.route('/get_clan')
async def getClan(req: Request) -> Union[tuple, dict]:
    args = req.args

    clan_id = int(args.get('id', 0))
    m = int(args.get('mode', 0))
    r = int(args.get('rx', 0))

    if not (clan := glob.clans.get(clan_id)):
        return (400, {'message': "clan couldn't be found!"})

    if r == 0: rx = Mods.NOMOD
    elif r == 1: rx = Mods.RELAX
    elif r == 2: rx = Mods.AUTOPILOT
    mode = lbModes(m, rx)

    members = [await glob.players.get(id=uid, sql=True) for uid in clan.members]
    o = await glob.players.get(id=clan.owner, sql=True)

    resp = {
        'info': {
            'id': clan.id,
            'name': clan.name,
            'tag': clan.tag
        },
        'owner': {
            'id': o.id,
            'name': o.name,
            'country': o.country_iso,
            'priv': o.priv,
            'rank': o.stats[mode.value].rank
        },
        'members': [{
            'id': m.id,
            'name': m.name,
            'country': m.country_iso,
            'priv': m.priv,
            'rank': m.stats[mode.value].rank
        } for m in members if m.id != clan.owner],
        'stats': {
            'score': await glob.db.fetchval('SELECT score FROM clans WHERE id = %s', [clan.id]),
            'rank': clan.rank,
            'country_rank': clan.country_rank,
            'rscore': sum([u.stats[mode.value].rscore for u in members]),
            'tscore': sum([u.stats[mode.value].tscore for u in members]),
            'pc': sum([u.stats[mode.value].pc for u in members])
        }
    }

    return {'clan': resp}