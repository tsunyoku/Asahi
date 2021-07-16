from xevel import Router
from cmyui import log, Ansi
from cmyui.osu.oppai_ng import OppaiWrapper
from pathlib import Path
from datetime import datetime

from objects import glob

from objects.beatmap import Beatmap
from objects.player import Player
from constants.mods import convert, Mods
from constants.modes import osuModes, lbModes
from constants.privs import Privileges
from packets import writer

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

    if pp == 0: return 0

    return 1

async def get_country_rank(mode, uid, pp, country):
    rank = await glob.redis.zrevrank(f'asahi:leaderboard:{mode}:{country}', uid)
    if rank is not None:
        return rank + 1

    if pp == 0: return 0
        
    return 1

@api.route('/player_count')
async def onlinePlayers(request):
    return {'online': len(glob.players) - 1}

@api.route('/player')
async def user(request):
    args = request.args

    id = int(args.get('id', 0))
    username = args.get('username', None)

    if not username and not id:
        return (400, {'message': 'you must specify either a username or id!'})

    if username:
        id = await glob.db.fetchval('SELECT id FROM users WHERE name = %s', [username])

    if not id:
        return (400, {'message': 'user could not be found! please check the username/id you specified and try again'})

    info = await glob.db.fetchrow('SELECT id, name, country, priv FROM users WHERE id = %s', [id])

    if not info:
        return (400, {'message': 'user could not be found! please check the username/id you specified and try again'})

    stats_db = await glob.db.fetchrow('SELECT * FROM stats WHERE id = %s', [id])
    
    if info['priv'] & Privileges.Disallowed:
        return (400, {'message': 'user is restricted/banned!'})

    stats = {}
    
    # cleaner way soonTM

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

    return {'info': info, 'stats': stats}

@api.route("/player_status")
async def playerStatus(request):
    args = request.args

    id = int(args.get('id', 0))
    username = args.get('username', None)

    if not id and not username:
        return (400, {'message': 'you must specify either a username or id!'})

    if username:
        id = await glob.db.fetchval('SELECT id FROM users WHERE name = %s', [username])

    if not id:
        return (400, {'message': 'user could not be found! please check the username/id you specified and try again'})

    if not (player := glob.players_id.get(id)):
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
        'mods': convert(player.mods),
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
async def getLb(request):
    args = request.args
    
    mode = int(args.get('mode', 0))
    rx = int(args.get('rx', 0))
    
    search = args.get('u', None)
    
    limit = int(args.get('limit', 50))
    page = int(args.get('p', 0))
    
    if rx == 0: rx = Mods.NOMOD
    elif rx == 1: rx = Mods.RELAX
    elif rx == 2: rx = Mods.AUTOPILOT
    
    lb_mode = lbModes(mode, rx)
    lb = [int(u) for u in await glob.redis.zrangebyscore(f'asahi:leaderboard:{lb_mode.name}')]
    lb.reverse() # redis returns backwards??
    
    # limit amount of users to return
    lb = lb[:limit]
    
    if page:
        offset = limit * page # ?
        lb = lb[offset:]
    
    ret = []
    
    if not search:
        for rank, uid in enumerate(lb):
            info = await glob.db.fetchrow('SELECT users.name, users.country, stats.pp_{0} pp, stats.acc_{0} acc FROM users LEFT OUTER JOIN stats ON stats.id = users.id WHERE users.id = %s'.format(lb_mode.name), [uid])
            
            ret.append({
                'rank': rank + 1,
                'userid': uid,
                'name': info['name'],
                'country': info['country'],
                'pp': info['pp'],
                'acc': info['acc']
            })
        
        return ret

    cursed_lb = (str(lb)).strip('[]')
    users = await glob.db.fetch(f'SELECT users.name, users.id, users.country, stats.pp_{lb_mode.name} pp, stats.acc_{lb_mode.name} acc FROM users LEFT OUTER JOIN stats ON stats.id = users.id WHERE users.id IN ({cursed_lb}) AND users.name LIKE %s', [f'{search}%'])
        
    for info in users:
        ret.append({
            'rank': lb[info['id']] + 1,
            'userid': info['id'],
            'name': info['name'],
            'country': info['country'],
            'pp': info['pp'],
            'acc': info['acc']
        })
        
    return ret

@api.route("/get_replay")
async def getReplay(request):
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

    raw = file.read_bytes()

    # get score from sql
    score = await glob.db.fetchrow(
        f'SELECT t.*, t.mode m, users.name, maps.* FROM {table} t '
        'LEFT OUTER JOIN users ON users.id = t.uid LEFT OUTER JOIN maps ON maps.md5 = t.md5 WHERE t.id = %s', 
        [sid]
    )

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

    rp += struct.pack('<Bi', score["m"], score["osuver"] or 20210520) # not all scores will have osuver so lets just send latest (as of this code) version
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

@api.route('/player_scores')
async def playerScores(req):
    args = req.args
    
    _type = args.get('type')
    mode = int(args.get('mode', 0))
    rx = int(args.get('rx', 0))
    
    uid = int(args.get('id', 0))
    username = args.get('username')
    
    limit = int(args.get('limit', 5))

    if not uid and not username:
        return (400, {'message': 'you must specify either a username or id!'})
    
    if not (user := await Player.from_sql(uid or username)):
        return (400, {'message': "user couldn't be found!"})

    if not _type:
        return (400, {'message': 'please provide a return type (recent/top)'})

    if rx == 0: rx = Mods.NOMOD
    elif rx == 1: rx = Mods.RELAX
    elif rx == 2: rx = Mods.AUTOPILOT
    
    mode = lbModes(mode, rx)
    
    query = ('SELECT id, md5, score, pp, acc, combo, mods, '
            'n300, n100, n50, miss, geki, katu, '
            'grade, status, mode, time, fc '
            f'FROM {mode.table} WHERE uid = %s AND mode = %s')
    
    if _type == 'best':
        query += ' AND status = 2'
        sort = 'pp'
    else:
        sort = 'time'
        
    query += f' ORDER BY {sort} DESC LIMIT %s'

    scores = await glob.db.fetch(query, [uid, mode.as_vn, limit])
    
    for idx, score in enumerate(scores):
        score = dict(score) # stupid psql records
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
        
        scores[idx] = score # stupid psql pt 2
        
    uinfo = {
        'id': user.id,
        'name': user.name,
        'country': user.country_iso,
        'clan': {
            'id': user.clan.id,
            'name': user.clan.name,
            'tag': user.clan.tag
        } if user.clan else None
    }
    
    return {'player': uinfo, 'scores': scores}

    