#!/usr/bin/env python3.9
from __future__ import annotations

import asyncio

import databases
from starlette.config import Config
from starlette.datastructures import Secret

cfg = Config("../.env")

MYSQL_DSN: Secret = cfg("MYSQL_DSN", cast=Secret)
TABLE_COLUMNS = ["rscore", "acc", "pc", "tscore", "pp"]


async def main():
    db = databases.Database(str(MYSQL_DSN))
    await db.connect()

    async with (
        db.connection() as read_cursor,
        db.connection() as write_cursor,
    ):
        await write_cursor.execute("RENAME TABLE stats TO old_stats")

        await write_cursor.execute(
            """
            CREATE TABLE `stats` (
                `id` bigint(20) NOT NULL,
                `mode` tinyint(1) NOT NULL,
                `rscore` bigint(20) NOT NULL DEFAULT '0',
                `acc` double NOT NULL DEFAULT '0',
                `pc` bigint(20) NOT NULL DEFAULT '0',
                `tscore` bigint(20) NOT NULL DEFAULT '0',
                `pp` bigint(20) NOT NULL DEFAULT '0',
                PRIMARY KEY (id, mode)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """,
        )

        stats = await read_cursor.fetch_all("SELECT * FROM old_stats")
        for row in stats:
            for mode, mode_val in enumerate(
                [
                    "std",
                    "taiko",
                    "catch",
                    "mania",
                    "std_rx",
                    "taiko_rx",
                    "catch_rx",
                    "std_ap",
                ],
            ):
                row_values = {
                    column: row[f"{column}_{mode_val}"] for column in TABLE_COLUMNS
                }

                await write_cursor.execute(
                    f"INSERT INTO stats (id, mode, rscore, acc, plays, tscore, pp) VALUES (:id, :mode, :rscore, :acc, :pc, :tscore, :pp)",
                    {
                        "id": row["id"],
                        "mode": mode,
                        **row_values,
                    },
                )

    print("Migrations completed, your old stats table has been left at old_stats!")
    await db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
