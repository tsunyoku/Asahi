from __future__ import annotations

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.base import RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

import log


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        start_time = time.perf_counter_ns()
        response = await call_next(request)
        end_time = time.perf_counter_ns()

        elapsed_time = end_time - start_time
        url = f"{request.headers['host']}{request['path']}"

        log.debug(
            f"Handled {request.method} request on {url} in {elapsed_time} ({response.status_code})",
        )

        return response
