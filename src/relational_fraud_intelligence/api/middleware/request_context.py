from __future__ import annotations

import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, request_id_header: str) -> None:
        super().__init__(app)
        self._request_id_header = request_id_header

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint,
    ) -> Response:
        request_id = request.headers.get(self._request_id_header) or str(uuid.uuid4())
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[self._request_id_header] = request_id

        # Propagate rate-limit headers set by the auth dependency
        rl_limit = getattr(request.state, "rate_limit_limit", None)
        if rl_limit is not None:
            response.headers["X-RateLimit-Limit"] = str(rl_limit)
            response.headers["X-RateLimit-Remaining"] = str(
                getattr(request.state, "rate_limit_remaining", 0)
            )
            response.headers["X-RateLimit-Reset"] = str(
                getattr(request.state, "rate_limit_reset", 0)
            )

        return response
