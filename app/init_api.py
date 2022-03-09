from __future__ import annotations

import pprint

from fastapi import FastAPI
from fastapi import status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.requests import Request
from fastapi.responses import ORJSONResponse
from fastapi.responses import Response
from starlette.middleware.base import RequestResponseEndpoint

import app.api
import app.config
import app.state
import log


def init_routes(asgi_app: FastAPI) -> None:
    for domain in ("ppy.sh", app.config.SERVER_DOMAIN):
        asgi_app.host(f"osu.{domain}", app.api.osu.router)
        asgi_app.host(f"a.{domain}", app.api.avatars.router)

        for subdomain in ("c", "ce", "c4"):
            asgi_app.host(f"{subdomain}.{domain}", app.api.bancho.router)

        asgi_app.host(f"api.{domain}", app.api.api.router)


def init_events(asgi_app: FastAPI) -> None:
    @asgi_app.on_event("startup")
    async def on_startup() -> None:
        await app.state.services.database.connect()
        await app.state.services.redis.initialize()

        log.debug("Asahi started!")

    @asgi_app.on_event("shutdown")
    async def on_shutdown() -> None:
        await app.state.services.database.disconnect()
        await app.state.services.redis.close()

        log.debug("Asahi stopped!")

    asgi_app.add_middleware(app.api.middlewares.MetricsMiddleware)

    @asgi_app.middleware("http")
    async def http_middleware(
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        try:
            return await call_next(request)
        except RuntimeError as e:
            if e.args[0] == "No response returned.":
                return Response("lol")

            raise e

    @asgi_app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        e: RequestValidationError,
    ) -> Response:
        log.warning(f"Validation error on {request.url}:\n{pprint.pformat(e.errors())}")

        return ORJSONResponse(
            content=jsonable_encoder(e.errors()),
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )


def init_asahi() -> FastAPI:
    asgi_app = FastAPI()

    init_routes(asgi_app)
    init_events(asgi_app)

    return asgi_app


asgi_app = init_asahi()
