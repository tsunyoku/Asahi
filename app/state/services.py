import databases
import aioredis

import app.config

database = databases.Database(str(app.config.MYSQL_DSN))
redis: aioredis.Redis = aioredis.from_url(str(app.config.REDIS_DSN))
