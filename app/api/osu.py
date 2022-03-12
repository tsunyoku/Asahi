from __future__ import annotations

import time
from collections import defaultdict
from typing import Mapping

import databases.core
from fastapi import APIRouter
from fastapi import Request
from fastapi import Response
from fastapi import status
from fastapi.param_functions import Depends
from fastapi.param_functions import Form
from fastapi.responses import ORJSONResponse

import app.state
import app.utils
from app.state.services import acquire_db_conn

router = APIRouter(tags=["osu! /web/ API"])


@router.post("/users")
async def register_user(
    request: Request,
    username: str = Form(..., alias="user[username]"),
    email: str = Form(..., alias="user[user_email]"),
    plain_password: str = Form(..., alias="user[password]"),
    check: int = Form(...),
    db_conn: databases.core.Connection = Depends(acquire_db_conn),
):
    if not all((username, email, plain_password)):
        return Response(
            content=b"Missing required params",
            status_code=status.HTTP_400_BAD_REQUEST,
        )

    errors: Mapping[str, list[str]] = defaultdict(list)
    safe_name = app.utils.make_safe(username)

    if " " in username and "_" in username:
        errors["username"] += "Username cannot contain space and underscore!"

    if await db_conn.fetch_val(
        "SELECT 1 FROM users WHERE safe_name = :name",
        {"name": safe_name},
    ):
        errors["username"] += "Username already taken!"

    if await db_conn.fetch_val(
        "SELECT 1 FROM users WHERE email = :email",
        {"email": email},
    ):
        errors["email"] += "Email already in use!"

    if errors:
        return ORJSONResponse(
            content={"form_error": {"user": errors}},
            status=status.HTTP_400_BAD_REQUEST,
        )

    if check == 0:
        encrypted_password = app.state.cache.generate_password(
            app.utils.generate_md5(plain_password),
        )

        user_id = await db_conn.execute(
            "INSERT INTO users (name, safe_name, pw, email, registered_at) VALUES "
            "(:name, :safe_name, :pw, :email, :register)",
            {
                "name": username,
                "safe_name": safe_name,
                "pw": encrypted_password,
                "email": email,
                "register": int(time.time()),
            },
        )

        await db_conn.execute("INSERT INTO stats (id) VALUES (:id)", {"id": user_id})

    return b"ok"
