import asyncio
import time

from utils.logging import info

from . import glob
from constants.privs import Privileges

donors = None
frozen = None


async def prepare_tasks() -> None:
    global donors, frozen
    donors = await glob.db.fetch(
        f"SELECT * FROM users WHERE priv & {int(Privileges.Supporter)}",
    )
    frozen = await glob.db.fetch(
        f"SELECT * FROM users WHERE priv & {int(Privileges.Frozen)}",
    )


async def expired_donor() -> None:
    from packets import writer

    while True:  # this sux
        for user in list(donors):
            if user["donor_end"] < time.time():  # donor expired
                info(f"Removing {user['name']}'s expired donor.")
                donors.remove(user)

                if p := await glob.players.get(id=user["id"]):
                    p.enqueue(
                        writer.serverRestart(0),
                    )  # login will handle the removal, we just need to force a relog
                    continue  # go to next player

                # user isn't online, we'll remove it ourselves
                user_priv = Privileges(user["priv"])
                user_priv &= ~Privileges.Supporter
                await glob.db.execute(
                    "UPDATE users SET priv = %s WHERE id = %s",
                    [int(user_priv), user["id"]],
                )

        await asyncio.sleep(600)  # run every 10 mins


async def freeze_timers() -> None:
    from objects.player import Player

    while True:  # this sux v2
        for user in list(frozen):
            if user["freeze_timer"] < time.time():  # freeze timer passed
                info(f'Restricting {user["name"]} as their freeze timer expired.')
                frozen.remove(user)

                if p := await glob.players.get(id=user["id"]):
                    p.enqueue(
                        writer.serverRestart(0),
                    )  # login will handle restriction for us
                    continue  # next player

                # restrict is a bit more complicated, we'll use player object from sql
                p = await Player.from_sql(user["id"])
                await p.remove_priv(Privileges.Frozen)
                await p.restrict(reason="Expired freeze timer", fr=glob.bot)

        await asyncio.sleep(600)  # run every 10 mins
