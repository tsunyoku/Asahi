from xevel import Router
from cmyui import log, Ansi
from pathlib import Path
from datetime import datetime

from objects import glob

from objects.beatmap import Beatmap
from constants.mods import convert
from constants.modes import osuModes
from constants.privs import Privileges
from packets import writer

import time
import hashlib
import struct

api = Router(f'api.{glob.config.domain}')

if glob.config.debug:
    @api.after_request()
    async def logRequest(resp):
        if resp.code >= 400:
            colourret = Ansi.LRED
        else:
            colourret = Ansi.LCYAN

        log(f'[{resp.type}] {resp.code} {resp.url} | Time Elapsed: {resp.elapsed}', colourret)
        return resp

async def get_rank(mode, uid, pp):
    rank = await glob.redis.zrevrank(f'asahi:leaderboard:{mode}', uid)
    if rank is not None:
        return rank + 1
    else:
        if pp > 0:
            return 1
        else:
            return 0

async def get_country_rank(mode, uid, pp, country):
    rank = await glob.redis.zrevrank(f'asahi:leaderboard:{mode}:{country}', uid)
    if rank is not None:
        return rank + 1
    else:
        if pp > 0:
            return 1
        else:
            return 0

@api.route('/player_count')
async def onlinePlayers(request):
    return {'code': 200, 'online': len(glob.players) - 1}

@api.route('/player')
async def user(request):
    args = request.args

    id = int(args.get('id', 0))
    username = args.get('username', None)

    if not username and not id:
        return {'code': 400, 'message': 'you must specify either a username or id!'}

    if username:
        id = await glob.db.fetchval('SELECT id FROM users WHERE name = $1', username)

    if not id:
        return {'code': 400, 'message': 'user could not be found! please check the username/id you specified and try again'}

    info = await glob.db.fetchrow('SELECT id, name, country FROM users WHERE id = $1', id)

    if not info:
        return {'code': 400, 'message': 'user could not be found! please check the username/id you specified and try again'}

    stats_db = await glob.db.fetchrow('SELECT * FROM stats WHERE id = $1', id)
    
    if stats_db['priv'] & Privileges.Disallowed:
        return {'code': 400, 'message': 'user is restricted/banned!'}

    info = dict(info)
    stats_db = dict(stats_db)

    stats = {}

    for mode in ('std', 'taiko', 'catch', 'mania'):
        stats[mode] = {}

        stats[mode]['vn'] = {
            'acc': stats_db[f'acc_{mode}'],
            'playcount': stats_db[f'pc_{mode}'],
            'pp': stats_db[f'pp_{mode}'],
            'ranked_score': stats_db[f'rscore_{mode}'],
            'total_score': stats_db[f'tscore_{mode}'],
            'max_combo': stats_db[f'mc_{mode}'],
            'global_rank': await get_rank(f'{mode}', id, stats_db[f'pp_{mode}']),
            'country_rank': await get_country_rank(f'{mode}', id, stats_db[f'pp_{mode}'], info['country'].upper())
        }

        for s in ('rx', 'ap'):
            if (mode == 'mania' and s in ('rx', 'ap')) or (mode in ('taiko', 'catch') and s == 'ap'):
                continue

            stats[mode][s] = {
                'acc': stats_db[f'acc_{mode}_{s}'],
                'playcount': stats_db[f'pc_{mode}_{s}'],
                'pp': stats_db[f'pp_{mode}_{s}'],
                'ranked_score': stats_db[f'rscore_{mode}_{s}'],
                'total_score': stats_db[f'tscore_{mode}_{s}'],
                'max_combo': stats_db[f'mc_{mode}_{s}'],
                'global_rank': await get_rank(f'{mode}_{s}', id, stats_db[f'pp_{mode}_{s}']),
                'country_rank': await get_country_rank(f'{mode}_{s}', id, stats_db[f'pp_{mode}_{s}'], info['country'].upper())
            }

    return {'code': 200, 'info': info, 'stats': stats}

@api.route("/player_status")
async def playerStatus(request):
    args = request.args

    id = int(args.get('id', 0))
    username = args.get('username', None)

    if not id and not username:
        return {'code': 400, 'message': 'you must specify either a username or id!'}

    if username:
        id = await glob.db.fetchval('SELECT id FROM users WHERE name = $1', username)

    if not id:
        return {'code': 400, 'message': 'user could not be found! please check the username/id you specified and try again'}

    if not (player := glob.players_id.get(id)):
        return {'code': 200, 'status': {'online': False}}
    
    if player.priv & Privileges.Disallowed:
        return {'code': 400, 'message': 'user is restricted/banned!'}

    if player.map_md5:
        if not (map := Beatmap.md5_cache(player.map_md5)):
            map = Beatmap.md5_sql(player.map_md5)
    else:
        map = None

    status = {
        'online': True,
        'action': player.action,
        'info': player.info,
        'mode': osuModes(player.mode).name,
        'mods': convert(player.mods),
        'map': {
            'md5': map.md5,
            'id': map.id,
            'set_id': map.sid,
            'artist': map.artist,
            'title': map.title,
            'difficulty': map.diff,
            'mapper': map.mapper,
            'star_rating': map.sr
        } if map else None
    }

    return {'code': 200, 'status': status}

@api.route("/get_replay")
async def getReplay(request):
    args = request.args

    sid = int(args.get('id', 0))
    rx = int(args.get('rx', 0))

    if not sid:
        return {'code': 400, 'message': 'please specify a score id!'}

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
        return {'code': 400, 'message': "replay couldn't be found. please check the score id and try again!"}

    raw = file.read_bytes()

    # get score from sql
    score = await glob.db.fetchrow(f'SELECT t.*, t.mode m, users.name, maps.* FROM {table} t LEFT OUTER JOIN users ON users.id = t.uid LEFT OUTER JOIN maps ON maps.md5 = t.md5 WHERE t.id = $1', sid)

    hash = hashlib.md5(
        (f'{score["n100"] + score["n300"]}p{score["n50"]}o'
        f'{score["geki"]}o{score["katu"]}t'
        f'{score["miss"]}a{score["md5"]}r'
        f'{score["combo"]}e{score["fc"] == 1}y'
        f'{score["name"]}o{score["score"]}u'
        f'0{score["mods"]}True'
        '').encode() # when im not lazy ill use Score.sql to get score object so we can implement rank and shit
    ).hexdigest()

    rp = bytearray() # headers timeee

    rp += struct.pack('<Bi', score["m"], 20210523) # osuver once im not lazy (score sub provides it so easy solution lol)
    rp += writer.write_string(score["md5"])

    rp += writer.write_string(score["name"])
    rp += writer.write_string(hash)

    rp += struct.pack('<hhhhhhihBi',
        score["n300"], score["n100"],
        score["n50"], score["geki"],
        score["katu"], score["miss"],
        score["score"], score["combo"],
        score["fc"], score["mods"]
    )

    rp += b'\x00' # graph probably NEVER

    t = int(score["time"] * 1e7)
    rp += struct.pack('<q', t + 0x89F7FF5F7B58000) # interesting choice osu

    rp += struct.pack('<i', len(raw))
    rp += raw
    rp += struct.pack('<q', sid)

    name = f'{score["name"]} ~ {score["artist"]} - {score["title"]} [{score["diff"]}] +{score["readable_mods"]} ({datetime.fromtimestamp(score["time"]).strftime("%Y/%m/%d")})'

    request.resp_headers['Content-Type'] = 'application/octet-stream'
    request.resp_headers['Content-Description'] = 'File Transfer'
    request.resp_headers['Content-Disposition'] = f'attachment; filename={name}.osr'

    return bytes(rp)
