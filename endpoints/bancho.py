# external imports (some may require to be installed, install using ext/requirements.txt)
import time
import uuid

import pyfiglet
from cryptography.hazmat.backends import default_backend as backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDFExpand
from geoip2 import database
from xevel import Request
from xevel import Router

from constants import commands
from constants import regexes
from constants.countries import country_codes
from constants.modes import lbModes
from constants.mods import Mods
from constants.privs import ClientPrivileges
from constants.privs import Privileges
from constants.types import osuTypes
from constants.types import teamTypes
from objects import glob  # global objects
from objects.anticheat import Anticheat
from objects.beatmap import Beatmap
from objects.channel import Channel
from objects.match import slotStatus
from objects.match import Teams
from objects.player import Player
from packets import reader
from packets import writer
from packets.writer import Packets

from utils.logging import warning, info, debug

if glob.config.server_migration:
    import bcrypt

bancho = Router(
    {  # handler for webserver :D
        f"c.{glob.config.domain}",
        f"c4.{glob.config.domain}",
        f"ce.{glob.config.domain}",
    },
)

rdr = database.Reader("ext/geoloc.mmdb")


def packet(pck: Packets, allow_res: bool = False):
    def wrapper(_cb):
        glob.packets |= {pck: _cb}

        if allow_res:
            glob.packets_restricted |= {pck: _cb}

    return wrapper


@packet(Packets.OSU_REQUEST_STATUS_UPDATE, allow_res=True)
async def update_stats(user: Player, _) -> None:
    user.enqueue(writer.userStats(user))


@packet(Packets.OSU_USER_STATS_REQUEST, allow_res=True)
async def request_stats(user: Player, p: bytes) -> None:
    uids = (reader.handle_packet(p, (("uids", osuTypes.i32_list),)))["uids"]

    for o in glob.players.unrestricted_users:
        if o.id != user.id and o.id in uids:
            user.enqueue(writer.userStats(o))


@packet(Packets.OSU_USER_PRESENCE_REQUEST)
async def presence_request(user: Player, p: bytes) -> None:
    uids = (reader.handle_packet(p, (("uids", osuTypes.i32_list),)))["uids"]

    for u in uids:
        if o := await glob.players.get(id=u):
            user.enqueue(writer.userPresence(o))


@packet(Packets.OSU_USER_PRESENCE_REQUEST_ALL)
async def presence_request_all(user: Player, _) -> None:
    for o in glob.players:
        if o.id != user.id:
            user.enqueue(writer.userPresence(o))


@packet(Packets.OSU_FRIEND_ADD)
async def friend_add(user: Player, p: bytes) -> None:
    tar = (reader.handle_packet(p, (("uid", osuTypes.i32),)))["uid"]

    if tar in user.friends:
        return

    user.friends.append(tar)
    await glob.db.execute(
        "INSERT INTO friends (user1, user2) VALUES (%s, %s)",
        [user.id, tar],
    )

    base_info(f"{user.name} added UID {tar} into their friends list.")


@packet(Packets.OSU_FRIEND_REMOVE)
async def friend_remove(user: Player, p: bytes) -> None:
    tar = (reader.handle_packet(p, (("uid", osuTypes.i32),)))["uid"]

    if tar not in user.friends:
        return

    user.friends.remove(tar)
    await glob.db.execute(
        "DELETE FROM friends WHERE user1 = %s AND user2 = %s",
        [user.id, tar],
    )

    base_info(f"{user.name} removed UID {tar} from their friends list.")


@packet(Packets.OSU_LOGOUT, allow_res=True)
async def logout(user: Player, _) -> None:
    if (time.time() - user.login_time) < 1:
        return

    user.logout()
    base_info(f"{user.name} logged out.")


@packet(Packets.OSU_SEND_PRIVATE_MESSAGE)
async def send_pm(user: Player, p: bytes) -> None:
    d = reader.handle_packet(p, (("msg", osuTypes.message),))

    msg = d["msg"].msg
    tarname = d["msg"].tarname

    if not (target := await glob.players.get(name=tarname)):
        warning(f"{user.name} tried to send message to offline user {tarname}")
        return

    if target is glob.bot:
        if msg.startswith(glob.config.prefix) and (
            cmd := await commands.process(user, msg)
        ):
            user.enqueue(
                writer.sendMessage(
                    fromname=target.name,
                    msg=cmd,
                    tarname=user.name,
                    fromid=target.id,
                ),
            )

        elif m := regexes.np_regex.match(msg):
            user.np = await Beatmap.bid_fetch(int(m["bid"]))
            np = await user.np.np_msg(user)

            user.enqueue(
                writer.sendMessage(
                    fromname=target.name,
                    msg=np,
                    tarname=user.name,
                    fromid=target.id,
                ),
            )

    else:
        target.enqueue(
            writer.sendMessage(
                fromname=user.name,
                msg=msg,
                tarname=target.name,
                fromid=user.id,
            ),
        )

        base_info(f'{user.name} sent message "{msg}" to {tarname}')


@packet(Packets.OSU_SEND_PUBLIC_MESSAGE)
async def send_msg(user: Player, p: bytes) -> None:
    d = reader.handle_packet(p, (("msg", osuTypes.message),))

    msg = d["msg"].msg
    chan = d["msg"].tarname

    if chan == "#spectator":
        if user.spectating:
            sid = user.spectating.id
        elif user.spectators:
            sid = user.id
        else:
            return

        c = glob.channels.get(f"#spec_{sid}")

    elif chan == "#multiplayer":
        if not user.match:
            return

        m = user.match.id
        c = glob.channels.get(f"#multi_{m}")

        if msg.startswith(glob.config.prefix) and (
            cmd := await commands.process_multiplayer(user, msg)
        ):
            msg = cmd
            user = glob.bot

    elif chan == "#clan":
        if not user.clan:
            return

        c = user.clan.chan

    elif chan not in ["#highlight", "#userlog"]:
        c = glob.channels.get(chan)

    if not c:
        return

    if (
        not chan == "#multiplayer"
        and msg.startswith(glob.config.prefix)
        and (cmd := await commands.process(user, msg, True))
    ):
        msg = cmd
        user = glob.bot  # bot returns the message

    c.send(user, msg, send_self=False)


@packet(Packets.OSU_CHANNEL_JOIN, allow_res=True)
async def join_chan(user: Player, p: bytes) -> None:
    name = (reader.handle_packet(p, (("chan", osuTypes.string),)))["chan"]

    if name == "#spectator":
        if user.spectating is not None:
            uid = user.spectating.id
        elif user.spectators:
            uid = user.id
        else:
            return  # not spectating

        chan = glob.channels.get(f"#spec_{uid}")

    elif name == "#multiplayer":
        if not user.match:
            return

        m = user.match.id
        chan = glob.channels.get(f"#multi_{m}")

    elif name == "#clan":
        if not user.clan:
            return

        chan = user.clan.chan

    else:
        chan = glob.channels.get(name)

    if not chan:
        return

    user.join_chan(chan)


@packet(Packets.OSU_CHANNEL_PART, allow_res=True)
async def leave_chan(user: Player, p: bytes) -> None:
    name = (reader.handle_packet(p, (("chan", osuTypes.string),)))["chan"]

    if name in ["#highlight", "#userlog"] or not name.startswith("#"):  # osu why!!!
        return

    if name == "#spectator":
        if user.spectating is not None:
            uid = user.spectating.id
        elif user.spectators:
            uid = user.id
        else:
            return  # not spectating

        chan = glob.channels.get(f"#spec_{uid}")

    elif name == "#multiplayer":
        if not user.match:
            return

        m = user.match.id
        chan = glob.channels.get(f"#multi_{m}")

    elif name == "#clan":
        if not user.clan:
            return

        chan = user.clan.chan

    else:
        chan = glob.channels.get(name)

    if not chan:
        return

    if user not in chan.players:
        return

    user.leave_chan(chan)
    chan_leave = writer.channelInfo(chan)

    for (
        o
    ) in (
        chan.players
    ):  # TODO: playerlist instances for channels/multiplayer rooms etc..?
        o.enqueue(chan_leave)


@packet(Packets.OSU_CHANGE_ACTION, allow_res=True)
async def update_action(user: Player, p: bytes) -> None:
    d = reader.handle_packet(
        p,
        (
            ("actionid", osuTypes.u8),
            ("base_info", osuTypes.string),
            ("md5", osuTypes.string),
            ("mods", osuTypes.u32),
            ("mode", osuTypes.u8),
            ("mid", osuTypes.i32),
        ),
    )

    if d["actionid"] == 0 and d["mods"] & Mods.RELAX:
        d["base_info"] = "on Relax"
    elif d["actionid"] == 0 and d["mods"] & Mods.AUTOPILOT:
        d["base_info"] = "on Autopilot"

    user.action = d["actionid"]
    user.base_info = d["base_info"]
    user.map_md5 = d["md5"]
    user.mods = d["mods"]

    m = lbModes(d["mode"], d["mods"])
    user.mode = m.value
    user.mode_vn = m.as_vn

    user.map_id = d["mid"]

    if d["actionid"] == 2:
        user.base_info += f" +{(Mods(user.mods))!r}"  # ugly and i dont care!

    if not user.restricted:
        glob.players.enqueue(writer.userStats(user))


@packet(Packets.OSU_START_SPECTATING)
async def start_spec(user: Player, p: bytes) -> None:
    tid = (reader.handle_packet(p, (("tid", osuTypes.i32),)))["tid"]

    if tid == 1:
        return

    if not (target := await glob.players.get(id=tid)):
        return

    target.add_spectator(user)


@packet(Packets.OSU_STOP_SPECTATING)
async def stop_spec(user: Player, _) -> None:
    if not (host := user.spectating):
        return

    host.remove_spectator(user)


@packet(Packets.OSU_SPECTATE_FRAMES)
async def spec_frames(user: Player, p: bytes) -> None:
    frames = (reader.handle_packet(p, (("frames", osuTypes.raw),)))["frames"]

    frames_packet = writer.spectateFrames(frames)
    for u in user.spectators:  # playerlist instances for spectators?
        u.enqueue(frames_packet)


@packet(Packets.OSU_JOIN_LOBBY)
async def join_lobby(user: Player, _) -> None:
    for m in glob.matches:
        user.enqueue(writer.newMatch(m))


@packet(Packets.OSU_PART_LOBBY)
async def leave_lobby(_, __) -> None:
    pass  # lol


@packet(Packets.OSU_CREATE_MATCH)
async def create_match(user: Player, p: bytes) -> None:
    match = (reader.handle_packet(p, (("match", osuTypes.match),)))["match"]

    glob.matches[match.id] = match
    if not glob.matches.get(match.id):
        return user.enqueue(writer.matchJoinFail())

    mp_chan = Channel(
        name="#multiplayer",
        desc=f"Multiplayer channel for match ID {match.id}",
        auto=False,
        perm=False,
    )
    glob.channels[f"#multi_{match.id}"] = mp_chan
    match.chat = mp_chan

    user.join_match(match, match.pw)
    base_info(f"{user.name} created a new multiplayer lobby.")


@packet(Packets.OSU_JOIN_MATCH)
async def join_match(user: Player, p: bytes) -> None:
    d = reader.handle_packet(
        p,
        (
            ("id", osuTypes.i32),
            ("pw", osuTypes.string),
        ),
    )
    _id = d["id"]
    pw = d["pw"]

    if _id >= 1000:
        if not (menu := glob.menus.get(_id)):  # TODO: use pw instead of id
            return user.enqueue(writer.matchJoinFail())

        ret = await menu.handle(user)

        # if we don't return a join failure also, its gonna think we are still in lobby
        if isinstance(ret, str):  # return string message?
            user.enqueue(
                writer.sendMessage(
                    fromname=glob.bot.name,
                    msg=ret,
                    tarname=user.name,
                    fromid=glob.bot.id,
                ),
            )

            return user.enqueue(writer.matchJoinFail())

        user.enqueue(writer.matchJoinFail())
        return ret

    if not (match := glob.matches.get(_id)):
        return user.enqueue(writer.matchJoinFail())

    if (
        match.clan_battle
        and user.clan not in (match.clan_1, match.clan_2)
        or match.battle_ready
    ):
        return user.enqueue(writer.matchJoinFail())

    user.join_match(match, pw)

    if match.clan_battle:
        total = []
        for slot in match.slots:
            if slot.status & slotStatus.has_player:
                total.append(slot.player)

        battle = glob.clan_battles[user.clan]
        if set(total) == set(battle["total"]):
            await match.strat_battle()


@packet(Packets.OSU_PART_MATCH)
async def leave_match(user: Player, _) -> None:
    user.leave_match()


@packet(Packets.OSU_MATCH_CHANGE_SLOT)
async def change_slot(user: Player, p: bytes) -> None:
    _id = (reader.handle_packet(p, (("id", osuTypes.i32),)))["id"]

    if not (match := user.match):
        return

    if match.slots[_id] != slotStatus.open:
        return

    old = match.get_slot(user)
    new = match.slots[_id]

    new.copy(old)
    old.reset()

    match.enqueue_state()


@packet(Packets.OSU_MATCH_READY)
async def user_ready(user: Player, _) -> None:
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.status = slotStatus.ready

    match.enqueue_state(lobby=False)


@packet(Packets.OSU_MATCH_LOCK)
async def lock_slot(user: Player, p: bytes) -> None:
    _id = (reader.handle_packet(p, (("id", osuTypes.i32),)))["id"]

    if not (match := user.match) or match.clan_battle or user is not match.host:
        return

    slot = match.slots[_id]

    if slot.status == slotStatus.locked:
        slot.status = slotStatus.open
    else:
        if slot.player is match.host:
            return

        slot.status = slotStatus.locked

    match.enqueue_state()


@packet(Packets.OSU_MATCH_CHANGE_SETTINGS)
async def match_settings(user: Player, p: bytes) -> None:
    m = (reader.handle_packet(p, (("m", osuTypes.match),)))["m"]

    if not (match := user.match) or user is not match.host:
        return

    if m.fm != match.fm:
        match.fm = m.fm

    if m.fm:
        for s in match.slots:
            if s.status & slotStatus.has_player:
                s.mods = match.mods & ~Mods.SPEED_MODS
                if match.clan_battle:
                    s.mods = match.mods & ~Mods.SPEED_MODS

        match.mods &= Mods.SPEED_MODS
    else:
        host = match.host
        match.mods &= Mods.SPEED_MODS
        match.mods |= host.mods

        for s in match.slots:
            if s.status & slotStatus.has_player:
                s.mods = Mods.NOMOD

    if m.bname == "":
        match.unready_players(slotStatus.ready)

    if m.bmd5 != match.bmd5:
        _m = await Beatmap.from_md5(m.bmd5)

        if _m:
            match.bid = _m.id
            match.bmd5 = _m.md5
            match.bname = _m.name
            match.mode = _m.mode
        else:
            match.bid = m.bid
            match.bmd5 = m.bmd5
            match.bname = m.bname
            match.mode = m.mode

    if match.type != m.type and not match.clan_battle:
        if m.type in (teamTypes.head, teamTypes.tag):
            team = Teams.neutral
        else:
            team = Teams.red

        for s in match.slots:
            if s.status & slotStatus.has_player:
                s.team = team

        match.type = m.type

    if match.win_cond != m.win_cond and not match.clan_battle:
        match.win_cond = m.win_cond

    if not match.clan_battle:
        match.name = m.name

    match.enqueue_state()


@packet(Packets.OSU_MATCH_START)
async def start_match(user: Player, _) -> None:
    if not (match := user.match) or user is not match.host:
        return

    match.start()


@packet(Packets.OSU_MATCH_SCORE_UPDATE)
async def match_score(user: Player, p: bytes) -> None:
    data = (reader.handle_packet(p, (("data", osuTypes.raw),)))["data"]

    if not (match := user.match):
        return

    r = bytearray(b"0\x00\x00")
    r += len(data).to_bytes(4, "little")
    r += data
    r[11] = match.get_slot_id(user)

    match.enqueue(bytes(r), lobby=False)


@packet(Packets.OSU_MATCH_COMPLETE)
async def finish_match(user: Player, _) -> None:
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.status = slotStatus.complete

    if any((s.status is slotStatus.playing for s in match.slots)):
        return

    no_play = []

    for slot in match.slots:
        if slot.status & slotStatus.has_player and slot.status != slotStatus.complete:
            no_play.append(slot.player.id)

    match.unready_players(slotStatus.complete)
    match.in_prog = False

    match.enqueue(writer.matchComplete(), lobby=False, ignore=no_play)
    match.enqueue_state()

    if match.clan_battle:
        await match.clan_scores(no_play)


@packet(Packets.OSU_MATCH_CHANGE_MODS)
async def match_mods(user: Player, p: bytes) -> None:
    mods = (reader.handle_packet(p, (("mods", osuTypes.i32),)))["mods"]

    if not (match := user.match):
        return

    if match.fm:
        if user is match.host:
            match.mods = mods & Mods.SPEED_MODS

        slot = match.get_slot(user)
        slot.mods = mods & ~Mods.SPEED_MODS
    else:
        if user is not match.host:
            return

        match.mods = mods

    match.enqueue_state()


@packet(Packets.OSU_MATCH_LOAD_COMPLETE)
async def match_loaded(user: Player, _) -> None:
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.loaded = True

    slot_bools = [s.playing for s in match.slots]
    if not any(slot_bools):
        match.enqueue(writer.matchAllLoaded(), lobby=False)


@packet(Packets.OSU_MATCH_NO_BEATMAP)
async def match_nomap(user: Player, _) -> None:
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.status = slotStatus.no_map

    match.enqueue_state(lobby=False)


@packet(Packets.OSU_MATCH_NOT_READY)
async def user_unready(user: Player, _) -> None:
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.status = slotStatus.not_ready

    match.enqueue_state(lobby=False)


@packet(Packets.OSU_MATCH_FAILED)
async def user_failed(user: Player, _) -> None:
    if not (match := user.match):
        return

    slot = match.get_slot_id(user)
    match.enqueue(writer.matchPlayerFailed(slot), lobby=False)


@packet(Packets.OSU_MATCH_HAS_BEATMAP)
async def user_map(user: Player, _) -> None:
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.status = slotStatus.not_ready

    match.enqueue_state(lobby=False)


@packet(Packets.OSU_MATCH_SKIP_REQUEST)
async def user_skip(user: Player, _) -> None:
    if not (match := user.match):
        return

    slot = match.get_slot(user)
    slot.skipped = True

    match.enqueue(writer.matchPlayerSkipped(user.id))

    for slot in match.slots:
        if slot.status is slotStatus.playing and not slot.skipped:
            return

    match.enqueue(writer.matchSkip(), lobby=False)


@packet(Packets.OSU_MATCH_TRANSFER_HOST)
async def match_host(user: Player, p: bytes) -> None:
    slot = (reader.handle_packet(p, (("slot", osuTypes.i32),)))["slot"]

    if (
        not (match := user.match)
        or user is not match.host
        or not (host := match.slots[slot].player)
        or match.clan_battle
    ):
        return

    match.host = host
    match.host.enqueue(writer.matchTransferHost())
    match.enqueue_state()


@packet(Packets.OSU_MATCH_CHANGE_TEAM)
async def match_team(user: Player, _) -> None:
    if not (match := user.match):
        return

    if match.clan_battle:
        return

    slot = match.get_slot(user)

    if slot.team is Teams.teamless:
        return  # ???

    if slot.team is Teams.blue:
        slot.team = Teams.red
    else:
        slot.team = Teams.blue

    match.enqueue_state(lobby=False)


@packet(Packets.OSU_MATCH_INVITE)
async def match_invite(user: Player, p: bytes) -> None:
    uid = (reader.handle_packet(p, (("uid", osuTypes.i32),)))["uid"]

    if (
        not user.match
        or not (target := await glob.players.get(id=uid))
        or target is glob.bot
    ):
        return

    target.enqueue(writer.matchInvite(user, target.name))


@packet(Packets.OSU_MATCH_CHANGE_PASSWORD)
async def match_pw(user: Player, p: bytes) -> None:
    m = (reader.handle_packet(p, (("m", osuTypes.match),)))["m"]

    if not (match := user.match) or user is not match.host:
        return

    match.pw = m.pw
    match.enqueue_state()


BASE_MESSAGE = (
    f"{pyfiglet.figlet_format(f'Asahi v{glob.version}')}\n\n"
    "tsunyoku attempts bancho v2, gone right :sunglasses:"
    "\n\nOnline Players:\n"
)


def root_web() -> bytes:
    pl = "\n".join(p.name for p in glob.players)
    return (BASE_MESSAGE + pl).encode()


@bancho.route(
    "/",
    ["POST", "GET"],
)  # only accept POST requests, we can assume it is for a login request but we can deny access if not
async def root_client(request: Request) -> bytes:
    start = time.time()
    headers = (
        request.headers
    )  # request headers, used for things such as user ip and agent

    if (
        "User-Agent" not in headers
        or headers["User-Agent"] != "osu!"
        or request.type == "GET"
    ):
        # request isn't sent from osu client, return html
        return root_web()

    if (
        "osu-token" not in headers
    ):  # sometimes a login request will be a re-connect attempt, in which case they will already have a token, if not: login the user
        data = (
            request.body
        )  # request data, used to get base_info such as username to login the user
        if (
            len(base_info := data.decode().split("\n")[:-1]) != 3
        ):  # format data so we can use it easier & also ensure it is valid at the same time
            request.resp_headers[
                "cho-token"
            ] = "no"  # client knows there is something up if we set token to 'no'
            return writer.userID(-2)

        if (
            len(cinfo := base_info[2].split("|")) != 5
        ):  # format client data (hash, utc etc.) & ensure it is valid
            request.resp_headers[
                "cho-token"
            ] = "no"  # client knows there is something up if we set token to 'no'
            return writer.userID(-2)

        username = base_info[0]
        pw = base_info[
            1
        ].encode()  # password in md5 form, we will use this to compare against db's stored bcrypt later

        user = await glob.db.fetchrow("SELECT * FROM users WHERE name = %s", [username])
        if (
            not user
        ):  # ensure user actually exists before attempting to do anything else
            warning(f"User {username} does not exist.")

            request.resp_headers[
                "cho-token"
            ] = "no"  # client knows there is something up if we set token to 'no'
            return writer.userID(-1)

        # if server is migrated then passwords are previously stored as bcrypt
        # lets check if we need to convert and do so if needed
        if glob.config.server_migration and (
            "$" in user["pw"] and len(user["pw"]) == 60
        ):
            user_pw = user["pw"].encode()
            if not bcrypt.checkpw(pw, user_pw):
                warning(
                    f"{username}'s login attempt failed: provided an incorrect password",
                )

                request.resp_headers[
                    "cho-token"
                ] = "no"  # client knows there is something up if we set token to 'no'
                return writer.userID(-1)
            else:  # correct password, we allow the user to continue but lets convert the password to our new format first
                k = HKDFExpand(
                    algorithm=hashes.SHA256(),
                    length=32,
                    info=b"",
                    backend=backend(),
                )
                new_pw = k.derive(pw).decode("unicode-escape")
                await glob.db.execute(
                    "UPDATE users SET pw = %s WHERE id = %s",
                    [new_pw, user["id"]],
                )

                # add to cache for the future
                glob.cache["pw"][new_pw] = pw

        else:  # password is already converted or db already has correct formats
            bcache = glob.cache["pw"]  # get our cached pws to potentially enhance speed
            user_pw = (
                user["pw"]
                .encode("ISO-8859-1")
                .decode("unicode-escape")
                .encode("ISO-8859-1")
            )  # this is cursed SHUT UP

            if user_pw in bcache:
                if (
                    pw != bcache[user_pw]
                ):  # compare provided md5 with the stored (cached) pw to ensure they have provided the correct password
                    warning(
                        f"{username}'s login attempt failed: provided an incorrect password",
                    )

                    request.resp_headers[
                        "cho-token"
                    ] = "no"  # client knows there is something up if we set token to 'no'
                    return writer.userID(-1)
            else:
                k = HKDFExpand(
                    algorithm=hashes.SHA256(),
                    length=32,
                    info=b"",
                    backend=backend(),
                )

                try:
                    k.verify(pw, user_pw)
                except Exception:
                    warning(
                        f"{username}'s login attempt failed: provided an incorrect password",
                    )

                    request.resp_headers[
                        "cho-token"
                    ] = "no"  # client knows there is something up if we set token to 'no'
                    return writer.userID(-1)

                bcache[user_pw] = pw  # cache pw for future

        if user["priv"] & Privileges.Banned:
            request.resp_headers["cho-token"] = "no"
            return writer.userID(-3)

        if (p := await glob.players.get(id=user["id"])) and (
            start - p.last_ping
        ) > 10:  # game crashes n shit
            p.logout()

        token = uuid.uuid4()  # generate token for client to use as auth
        user["offset"] = int(cinfo[1])  # utc offset for time
        user["bot"] = False  # used to specialise bot functions, kinda gay setup ngl
        user["token"] = str(token)  # this may be useful in the future
        user["ltime"] = time.time()  # useful for handling random logouts
        user["md5"] = pw  # used for auth on /web/

        # i hate it here
        if "CF-Connecting-IP" in headers:
            ip = headers["CF-Connecting-IP"]
        else:
            ip = headers["X-Forwarded-For"].split(",")[0]

        # cache ip's geoloc | the speed gains too are ungodly
        if not glob.geoloc.get(ip):
            geoloc = rdr.city(ip)
            glob.geoloc[ip] = geoloc
        else:
            geoloc = glob.geoloc[ip]

        user["country_iso"], user["lat"], user["lon"] = (
            geoloc.country.iso_code,
            geoloc.location.latitude,
            geoloc.location.longitude,
        )
        user["country"] = country_codes[user["country_iso"]]

        # set player object
        p = await Player.login(user)
        await p.set_stats()

        if not p.priv & Privileges.Verified:
            if p.id == 3:
                # first user & not verified, give all permissions
                await p.set_priv(Privileges.Master)
            else:
                await p.add_priv(Privileges.Verified)  # verify user

            await glob.db.execute(
                "UPDATE users SET country = %s WHERE id = %s",
                [p.country_iso.lower(), p.id],
            )  # set country code in db
            info(f"{p.name} has been successfully verified.")

        if glob.config.anticheat and not p.priv & Privileges.BypassAnticheat:
            a = cinfo[3][:-1].split(":")  # client-provided adapters
            adapters = {
                "osu_md5": a[0],
                "mac_address": a[1],
                "uninstall_id": a[2],
                "disk_serial": a[3],
                "ip": ip,
            }  # prepare adapters for abtucgeat

            checks = Anticheat(
                osuver=cinfo[0],
                adapters=adapters,
                player=p,
                headers=headers,
            )

            # we want to check multi stuff before any cheats just in case
            await checks.multi_check()

            # this is probably confusing syntax.
            # client_check will restrict if a client is custom and if that's the case we want to ignore any update checks.
            # if an update check is made, this will send update required packet if thats what the function returns.
            # i should probably rename these funcs in the future
            if not await checks.client_check() and not await checks.version_check():
                request.resp_headers["cho-token"] = "no"
                return writer.versionUpdateForced() + writer.userID(-2)

        # start enqueueing login data to the client
        data = bytearray(
            writer.userID(p.id),
        )  # initiate login by providing the user's id
        data += writer.protocolVersion(19)  # no clue what this does
        data += writer.banchoPrivileges(p.client_priv | ClientPrivileges.Supporter)
        data += writer.userPresence(p) + writer.userStats(
            p,
        )  # provide user & other user's presence/stats (for f9 + user stats)
        data += writer.channelInfoEnd()  # no clue what this does either
        data += writer.menuIcon()  # set main menu icon
        data += writer.friends(p.friends)  # send user friend list
        data += writer.silenceEnd(p.silence_end)

        # get channels from cache and send to user
        for chan in glob.channels.values():
            if chan.auto:
                p.join_chan(chan)
                data += writer.channelJoin(
                    chan.name,
                )  # only join user to channel if the channel is meant for purpose

            data += writer.channelInfo(
                chan,
            )  # regardless of whether the channel should be auto-joined we should make the client aware of it

        # add user to cache?
        glob.players.append(p)

        if not p.restricted:
            glob.players.enqueue(writer.userPresence(p) + writer.userStats(p))

        for o in glob.players:
            data += writer.userPresence(o) + writer.userStats(
                o,
            )  # enqueue every other logged in user to this user

        if p.clan:
            p.join_chan(p.clan.chan)

            # doesnt join_chan func already handle this? lol i dont remember ill check tomorrow
            data += writer.channelJoin(p.clan.chan.name)
            data += writer.channelInfo(p.clan.chan)

            # check if clan is in battle, if so: send invite to them too
            if (m := p.clan.battle) and not m.battle_ready:
                # battle hasn't started/isn't ready yet, lets invite them too!
                if p.clan == m.clan_1:
                    against = m.clan_2
                    add = "online1"
                else:
                    against = m.clan_1
                    add = "online2"

                data += writer.sendMessage(
                    fromname=glob.bot.name,
                    msg=f"Your clan has initiated in a clan battle against the clan {against.name}! "
                    f"Please join the battle here: {m.embed}",
                    tarname=p.name,
                    fromid=glob.bot.id,
                )

                # update player lists for the battle
                battle = glob.clan_battles[m.clan_1]
                battle["total"].append(p)
                battle[add].append(p)

        if p.restricted:
            reason = await glob.db.fetchval(
                "SELECT reason FROM punishments WHERE type = 'restrict' AND target = %s "
                "ORDER BY time DESC LIMIT 1",
                [p.id],
            )

            data += writer.sendMessage(
                fromname=glob.bot.name,
                msg=f'Your account is currently restricted for reason "{reason}"!',
                tarname=p.name,
                fromid=glob.bot.id,
            )

        if p.frozen and not p.restricted:
            if p.freeze_timer.timestamp() < start:  # freeze timer has expired lol
                await p.remove_priv(Privileges.Frozen)
                await p.restrict(reason="Expired freeze timer")

                data += writer.sendMessage(
                    fromname=glob.bot.name,
                    msg="Your freeze timer has expired and you have not submitted any liveplay, you have been restricted as a result!",
                    tarname=p.name,
                    fromid=glob.bot.id,
                )

            else:
                reason = await glob.db.fetchval(
                    "SELECT reason FROM punishments WHERE type = 'freeze' AND target = %s ORDER BY time DESC LIMIT 1",
                    [p.id],
                )

                data += writer.sendMessage(
                    fromname=glob.bot.name,
                    msg=f'Your account is currently frozen for reason "{reason}"! '
                    f'If you do not provide a liveplay by {p.freeze_timer.strftime("%d/%m/%Y %H:%M:%S")}, you will be autorestricted.',
                    tarname=p.name,
                    fromid=glob.bot.id,
                )

        if p.priv & Privileges.Supporter and p.donor_end < start:
            info(f"Removing {p.name}'s expired donor.")
            await p.remove_priv(Privileges.Supporter)

            data += writer.sendMessage(
                fromname=glob.bot.name,
                msg="Your supporter has expired! Your support perks have been removed.",
                tarname=p.name,
                fromid=glob.bot.id,
            )

        elapsed = (time.time() - start) * 1000
        data += writer.notification(
            f"Welcome to Asahi v{glob.version}\n\nTime Elapsed: {elapsed:.2f}ms",
        )  # send notification as indicator they've logged in i guess
        info(f"{p.name} successfully logged in.")

        request.resp_headers["cho-token"] = token
        return bytes(data)

    # if we have made it this far then it's a reconnect attempt with token already provided
    user_token = headers["osu-token"]  # client-provided token
    if not (p := await glob.players.get(token=user_token)):
        # user is logged in but token is not found? most likely a restart so we force a reconnection
        return writer.restartServer(0)

    # handle any packets the client has sent
    body = request.body

    if p.restricted:
        pm = glob.packets_restricted
    else:
        pm = glob.packets

    if body[0] != 4:
        for pck, cb in pm.items():
            if body[0] == pck:
                await cb(p, bytes(body))

                debug(f"Packet {pck.name} handled for user {p.name}")

    p.last_ping = time.time()

    request.resp_headers["Content-Type"] = "text/html; charset=UTF-8"  # ?
    return p.dequeue() or b""
