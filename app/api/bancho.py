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

import app.state
import app.utils
import log
from app.models import Geolocation
from app.models import LoginData
from app.objects.player import Player
from app.packets import Packet
from app.packets import PacketArray
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
            content=login_data["body"],
            headers={"cho-token": login_data["token"]},
        )

    player = await app.state.sessions.players.get(token=osu_token)
    if not player:
        return Response(content=b"")  # notification + server restart packet goes here

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

    if player := app.state.sessions.players.get(name=username):
        if (login_time - player.last_ping) > 10:
            # player.logout()
            ...
        else:
            return {
                "token": "no",
                "body": b"",
            }  # TODO: notification (already logged in)

    user_info = await db_conn.fetch_one(
        "SELECT id, name, priv, pw, country, "
        "silence_end, clan FROM users "
        "WHERE safe_name = :name",
        {"name": app.utils.make_safe(username)},
    )

    if not user_info:
        return {
            "token": "no",
            "body": b"",
        }  # TODO: notification and userid packet

    user_info = dict(user_info)


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
                    data.__dict__[field] = _type.reada(packet)

            await handler(packet, player, data)
            return structure is not None  # should increment

        app.state.PACKETS[packet_id] = wrapper

        if allow_restricted:
            app.state.RESTRICTED_PACKETS[packet_id] = wrapper

        return wrapper

    return decorator
