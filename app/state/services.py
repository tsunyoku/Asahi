from __future__ import annotations

import aioredis
import databases
from geoip2 import database as geoloc_db

import app.config

database = databases.Database(str(app.config.MYSQL_DSN))
redis: aioredis.Redis = aioredis.from_url(str(app.config.REDIS_DSN))
geoloc = geoloc_db.Reader("ext/geoloc.mmdb")
