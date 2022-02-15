import os
import shutil
import subprocess
import sys
from pathlib import Path

import requests

from .logging import error
from .logging import info
from .logging import warning
from objects import glob

RESOURCES_PATH = Path.cwd() / "resources"
AVA_PATH = RESOURCES_PATH / "avatars"
SS_PATH = RESOURCES_PATH / "screenshots"
R_PATH = RESOURCES_PATH / "replays"
RRX_PATH = RESOURCES_PATH / "replays_rx"
RAP_PATH = RESOURCES_PATH / "replays_ap"
MAPS_PATH = RESOURCES_PATH / "maps"
ACHIEVEMENTS_PATH = RESOURCES_PATH / "achievements"

OPPAI_PATH = Path.cwd() / "oppai-ng"
OPPAI_LIB = OPPAI_PATH / "liboppai.so"

PACKETS_PATH = Path.cwd() / "packets"

CONFIG_FILE = Path.cwd() / "config.py"

DEFAULT_AVATAR = AVA_PATH / "default.png"
AVATAR_URL = "https://i.imgur.com/tWWmQbu.png"


def running_via_asgi() -> bool:
    return any(
        map(
            sys.argv[0].endswith,
            (
                "hypercorn",
                "uvicorn",
            ),
        ),
    )


def ensure_posix() -> int:
    if sys.platform not in (
        "linux",
        "darwin",
    ):
        error("Asahi only supports Posix (linux/darwin) systems currently.")

        if sys.platform == "win32":
            info(
                "You could also look into using WSL (Windows Subsystem for Linux) to run a test instance on a local machine",
            )

        return 1

    return 0


def ensure_services() -> int:
    if glob.config.sql["host"] in (
        "localhost",
        "127.0.0.1",
    ):
        for service in (
            "mysqld",
            "mariadb",
        ):
            if os.path.exists(f"/var/run/{service}/{service}.pid"):
                break
        else:
            pgrep_exit_code = subprocess.call(
                ["pgrep", "mysqld"],
                stdout=subprocess.DEVNULL,
            )

            if pgrep_exit_code != 0:
                error("Please start your mysql server")
                return 1

    if glob.config.redis["host"] in (
        "localhost",
        "127.0.0.1",
    ) and not os.path.exists("/var/run/redis/redis-server.pid"):
        error("Please start your redis server")
        return 1

    return 0


def ensure_resources() -> int:
    RESOURCES_PATH.mkdir(exist_ok=True)

    if not AVA_PATH.exists():
        AVA_PATH.mkdir(parents=True)
        warning(
            "Avatars folder has been created, "
            "if you would like to change the default avatar replace the `default.png` image available in `resources/avatars`",
        )

    if not DEFAULT_AVATAR.exists():
        with requests.get(AVATAR_URL) as req:
            if not req or req.status_code != 200:
                error("Error while downloading default avatar")
                return 1

            avatar_bytes = req.content
            DEFAULT_AVATAR.write_bytes(avatar_bytes)

            info("Downloaded default avatar")

    for directory in (
        SS_PATH,
        R_PATH,
        RRX_PATH,
        RAP_PATH,
        MAPS_PATH,
        ACHIEVEMENTS_PATH,
    ):
        if not directory.exists():
            directory.mkdir(parents=True)

    return 0


def ensure_dependencies() -> int:
    if not OPPAI_PATH.exists():
        proc = subprocess.Popen(
            args=["git", "submodule", "init"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if exit_code := proc.wait():
            error("Failed to initialise git submodules")
            return exit_code

        proc = subprocess.Popen(
            args=["git", "submodule", "update"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if exit_code := proc.wait():
            error("Failed to update git submodules")
            return exit_code

        info("Downloaded oppai-ng")

    if not OPPAI_LIB.exists():
        proc = subprocess.Popen(
            args=["./libbuild"],
            cwd="oppai-ng",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if exit_code := proc.wait():
            error("Failed to build oppai-ng")
            return exit_code

        info("Built oppai-ng")

    if not list(PACKETS_PATH.glob("*.so")):
        proc = subprocess.Popen(
            args=["python3.9", "setup.py", "build_ext", "--inplace"],
            cwd="packets",
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if exit_code := proc.wait():
            error("Failed to build packet reader/writer")
            return exit_code

        info("Built packet reader/writer")

    return 0


def ensure_config():
    if not CONFIG_FILE.exists():
        shutil.copy("ext/config.sample.py", "config.py")
        error("Created config file, please edit and start Asahi again")

        return 1

    return 0
