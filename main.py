#!/usr/bin/env python3.9
import uvicorn
import logging
import log
import os

import app.config
import app.utils


def main() -> int:
    for safety_check in (
        app.utils.ensure_platform,
        app.utils.ensure_directories,
        app.utils.ensure_dependencies,
    ):
        if (exit_code := safety_check()) != 0:
            return exit_code

    if os.geteuid() == 0:
        log.warning("Running as root is not recommended, especially in production...")

    args = {}
    if app.config.SERVER_PORT:
        args["host"] = app.config.SERVER_HOST
        args["port"] = app.config.SERVER_PORT
    elif app.config.SERVER_SOCKET:
        if os.path.exists(app.config.SERVER_SOCKET):
            if app.utils.socket_in_use(app.config.SERVER_SOCKET):
                log.error(
                    "This socket is already in use by another process (likely Asahi).\n"
                    "Please stop this process and run Asahi again!"
                )

                return 1
            else:
                os.remove(app.config.SERVER_SOCKET)

        args["uds"] = app.config.SERVER_SOCKET
    else:
        log.error("You must specify either a socket or port for Asahi to run.")

        return 1

    uvicorn.run(
        "app.init_api:asgi_app",
        reload=app.config.DEBUG,
        log_level=logging.WARNING,
        server_header=False,
        date_header=False,
        **args,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
