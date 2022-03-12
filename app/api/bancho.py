from __future__ import annotations

import time
from typing import Any
from typing import Literal
from typing import Optional

import databases.core
from fastapi import APIRouter
from fastapi import Header
from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.responses import Response

import app.packets
import app.state
import app.utils
import log
from app.constants.privileges import BanchoPrivileges
from app.constants.privileges import Privileges
from app.models import LoginData
from app.objects.player import Player
from app.packets import Packet
from app.packets import PacketArray
from app.state.services import Geolocation
from app.typing import Message
from app.typing import PacketHandler

router = APIRouter(tags=["osu! Bancho API"])


@router.get("/")
async def bancho_index() -> HTMLResponse:
    return HTMLResponse("asahi bancho w")


@router.post("/")
async def bancho_handler(
    request: Request,
    osu_token: Optional[str] = Header(None),
    user_agent: Literal["osu!"] = Header(...),
) -> Response:
    geoloc = Geolocation.from_ip(request.headers)
    body = await request.body()

    if not osu_token:
        async with app.state.services.database.connection() as db_conn:
            login_data = await login(body, db_conn, geoloc)

        return Response(
            content=bytes(login_data["body"]),
            headers={"cho-token": login_data["token"]},
        )

    player = await app.state.sessions.players.get(token=osu_token)
    if not player:
        return Response(
            content=app.packets.notification("Server restarted!")
            + app.packets.restart_server(0),
        )

    packet_map = app.state.PACKETS
    if player.restricted:
        packet_map = app.state.RESTRICTED_PACKETS

    with bytearray(body) as body_view:
        for packet, handler in PacketArray(body_view, packet_map):
            await handler(packet, player)

    player.last_ping = time.time()
    return Response(content=player.dequeue())


async def login(
    body: bytes,
    db_conn: databases.core.Connection,
    geoloc: Geolocation,
) -> LoginData:
    if len(split := body.decode().split("\n")[:-1]) != 3:
        log.warning(f"Invalid login request from {geoloc.ip}")

        return {
            "token": "no",
            "body": b"",
        }

    username = split[0]
    password_md5 = split[1].encode()

    if len(client_info := split[2].split("|")) != 5:
        log.warning(f"Invalid login request from {geoloc.ip}")

        return {
            "token": "no",
            "body": b"",
        }

    osu_ver = client_info[0]

    if not client_info[1].replace("-", "").isdecimal():
        log.warning(f"Invalid login request from {geoloc.ip}")

        return {
            "token": "no",
            "body": b"",
        }

    utc_offset = int(client_info[1])

    client_hashes = client_info[3][:-1].split(":")
    if len(client_hashes) != 5:
        return {
            "token": "no",
            "body": b"",
        }

    (
        osu_path_md5,
        adapters_str,
        adapters_md5,
        uninstall_md5,
        disk_sig_md5,
    ) = client_hashes  # TODO: multi checks
    is_wine = adapters_str == "runningunderwine"
    adapters = [a for a in adapters_str[:-1].split(".") if a]

    if not any((is_wine, adapters)):
        return {
            "token": "no",
            "body": b"",
        }

    friend_only_dms = client_info[4] == "1"

    login_time = time.time()

    # TODO: tourney client checks

    if player := await app.state.sessions.players.get(name=username):
        if (login_time - player.last_ping) > 10:
            # player.logout()
            ...
        else:
            return {
                "token": "no",
                "body": app.packets.notification(
                    "You are already logged in at another location!",
                ),
            }

    user_info = await db_conn.fetch_one(
        "SELECT id, name, priv, pw, country, "
        "silence_end, clan FROM users "
        "WHERE safe_name = :name",
        {"name": app.utils.make_safe(username)},
    )

    if not user_info:
        return {
            "token": "no",
            "body": app.packets.notification("Unknown username!")
            + app.packets.user_id(-1),
        }

    user_info = dict(user_info)

    if not app.state.cache.password.verify_password(password_md5, user_info["pw"]):
        return {
            "token": "no",
            "body": app.packets.notification("Incorrect password!")
            + app.packets.user_id(-1),
        }

    user_info["geoloc"] = geoloc
    if user_info["country"] == "xx":
        await db_conn.execute(
            f"UPDATE users SET country = :country WHERE id = :user_id",
            {"country": geoloc.country.acronym, "user_id": user_info["id"]},
        )

    player = Player(
        **user_info,
        utc_offset=utc_offset,
        osu_ver=osu_ver,
        login_time=login_time,
        friend_only_dms=friend_only_dms,
    )

    data = bytearray(app.packets.protocol_version(19))

    data += app.packets.user_id(player.id)
    data += app.packets.bancho_privileges(
        player.bancho_priv | BanchoPrivileges.SUPPORTER,
    )

    # TODO: channel list

    data += app.packets.channel_info_end()

    # TODO: fetch achievements, stats, friends from sql

    data += app.packets.menu_icon()
    data += app.packets.friends_list(player.friends)
    data += app.packets.silence_end(player.remaining_silence)

    user_data = app.packets.user_presence(player) + app.packets.user_stats(player)
    data += user_data

    for target in app.state.sessions.players:
        if not player.restricted:
            target.enqueue(user_data)

        if not target.restricted:
            data += app.packets.user_presence(target) + app.packets.user_stats(target)

    if not player.priv & Privileges.VERIFIED:
        # add verified

        if player.id == 3:  # first user
            # add master
            ...

        data += app.packets.send_message(
            Message(
                "Asahi",  # TODO: bot user
                "Welcome to Asahi!",
                player.name,
                1,  # TODO: bot user
            ),
        )

    app.state.sessions.players.append(player)
    log.info(f"{player.name} logged in using {osu_ver}!")

    return {"token": player.token, "body": data}


def register_packet(packet_id: int, allow_restricted: bool = False):
    def decorator(handler: PacketHandler):
        async def wrapper(
            packet: Packet,
            player: Player,
            packet_data: Any = None,
        ):  # TODO: type-hint
            structure = handler.__annotations__.get("packet_data")

            if structure:
                data = structure()

                for field, _type in structure.__annotations__.items():
                    data.__dict__[field] = _type.read(packet)

                return await handler(
                    player,
                    data,
                )  # def handler(player: Player, packet_data: StructureClass) -> None

            # no data, just pass player
            await handler(player)  # def handler(player: Player) -> None

        app.state.PACKETS[packet_id] = wrapper
        if allow_restricted:
            app.state.RESTRICTED_PACKETS[packet_id] = wrapper

        return wrapper

    return decorator
