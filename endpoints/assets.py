from pathlib import Path
from typing import Union

from xevel import Request
from xevel import Router

from objects import glob

assets = Router(f"assets.{glob.config.domain}")
custom = []


def init_customs():
    for ach in glob.achievements:
        if ach.custom:
            custom.append(ach.image)

            # client likes @2x
            custom.append(f"{ach.image}@2x")


@assets.route("/medals/client/<medal>")
async def ingameAchievements(request: Request, medal: str) -> Union[tuple, bytes]:
    name = medal.split(".")[0]
    if name not in custom:
        request.resp_headers[
            "Location"
        ] = f"https://assets.ppy.sh/medals/client/{medal}"  # redirect regular achievements
        return (301, b"")
    else:
        request.resp_headers["Content-Type"] = "image/png"
        return (
            Path.cwd() / f'resources/achievements/{medal.replace("@2x", "")}'
        ).read_bytes()
