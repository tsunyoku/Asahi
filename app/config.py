from __future__ import annotations

from starlette.config import Config
from starlette.datastructures import Secret

cfg = Config(".env")

MYSQL_DSN: Secret = cfg("MYSQL_DSN", cast=Secret)
REDIS_DSN: Secret = cfg("REDIS_DSN", cast=Secret)

SERVER_DOMAIN: str = cfg("SERVER_DOMAIN")
SERVER_SOCKET: str = cfg("SERVER_SOCKET", default=None)
SERVER_PORT: int = cfg("SERVER_PORT", cast=int, default=None)
SERVER_HOST: str = cfg("SERVER_HOST", default="0.0.0.0")

DEBUG: bool = cfg("DEBUG", cast=bool, default=False)

# pre-rewrite version = 0.4.3
VERSION = "0.5.0"  # DO NOT CHANGE
