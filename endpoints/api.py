from quart import Blueprint, request, g
from cmyui import log, Ansi
from objects import glob

from objects.beatmap import Beatmap
from constants.mods import convert
from constants.modes import osuModes

import time

api = Blueprint('api', __name__)

if glob.config.debug:
    @api.before_request
    async def bRequest():
        g.req_url = request.base_url
        g.req_method = request.method
        g.start = time.time()

    @api.after_request
    async def logRequest(resp):
        if resp.status_code != 200:
            colourret = Ansi.LRED
        else:
            colourret = Ansi.LCYAN

        log(f'[{g.pop("req_method")}] {resp.status_code} {g.pop("req_url")} | Time Elapsed: {(time.time() - g.pop("start")) * 1000:.2f}ms', colourret)
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
async def onlinePlayers():
    return {'code': 200, 'online': len(glob.players) - 1}

@api.route('/player')
async def user():
    args = request.args

    id = int(args.get('id', 0))
    username = args.get('username', None)

    if not username and not id:
        return {'code': 400, 'message': 'you must specify either a username or id!'}

    if username:
        id = await glob.db.fetchval('SELECT id FROM users WHERE name = $1', username)

    if not id:
        return {'code': 400, 'message': 'user could not be found! please check the username/id you specified and try again'}

    info = dict(await glob.db.fetchrow('SELECT id, name, country FROM users WHERE id = $1', id))
    stats_db = dict(await glob.db.fetchrow('SELECT * FROM stats WHERE id = $1', id))

    stats = {}

    for mode in ('std', 'taiko', 'catch', 'mania'):
        stats[mode] = {}

        stats[mode]['vn'] = {
            'acc': stats_db[f'acc_{mode}'],
            'playcount': stats_db[f'pc_{mode}'],
            'pp': stats_db[f'pp_{mode}'],
            'ranked_score': stats_db[f'rscore_{mode}'],
            'total_score': stats_db[f'tscore_{mode}'],
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
                'global_rank': await get_rank(f'{mode}_{s}', id, stats_db[f'pp_{mode}_{s}']),
                'country_rank': await get_country_rank(f'{mode}_{s}', id, stats_db[f'pp_{mode}_{s}'], info['country'].upper())
            }

    return {'code': 200, 'info': info, 'stats': stats}

@api.route("/player_status")
async def playerStatus():
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