"""
Request middleware (plain ASGI, so it adds almost no overhead).

For every HTTP request it:
- gives the request an ID (see request_context.py) and returns it in the
  ``X-Request-ID`` header;
- measures the time and returns it in ``X-Process-Time-Ms``;
- adds ``X-Content-Type-Options: nosniff`` and ``Cache-Control: no-store``
  (answers can contain operational data and tokens; they must not be cached);
- writes one log line: method, path, status, time, caller, request ID.
  Tokens, passwords and request bodies are never logged.
"""
from __future__ import annotations

import logging
import time

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .request_context import new_request_id, set_request_id

log = logging.getLogger("rule_service.access")


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        incoming = None
        for name, value in scope.get("headers", []):
            if name == b"x-request-id":
                incoming = value.decode("latin-1")
                break
        request_id = new_request_id(incoming)
        set_request_id(request_id)
        start = time.perf_counter()
        status = {"code": 500}

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                status["code"] = message["status"]
                headers = MutableHeaders(scope=message)
                headers["X-Request-ID"] = request_id
                headers["X-Process-Time-Ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"
                headers["X-Content-Type-Options"] = "nosniff"
                if "cache-control" not in headers:
                    headers["Cache-Control"] = "no-store"
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        finally:
            state = scope.get("state") or {}
            caller = state.get("caller", "-") if isinstance(state, dict) else "-"
            log.info(
                '%s %s -> %s in %.1f ms caller=%s request_id=%s',
                scope.get("method"),
                scope.get("path"),
                status["code"],
                (time.perf_counter() - start) * 1000,
                caller,
                request_id,
            )
