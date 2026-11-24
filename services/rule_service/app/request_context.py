"""
The request ID of the request being handled.

Every request gets an ID: the caller's own ``X-Request-ID`` header if it is
safe to reuse, otherwise a new random one. It is returned in the
``X-Request-ID`` response header, in every error body, in the log line and
in the audit row, so one request can be followed end to end (also across
services, when a calling service passes its own ID on).
"""
from __future__ import annotations

import re
import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="-")
_SAFE_ID = re.compile(r"^[A-Za-z0-9._\-]{8,64}$")


def new_request_id(incoming: str | None) -> str:
    if incoming and _SAFE_ID.match(incoming):
        return incoming
    return uuid.uuid4().hex


def set_request_id(value: str) -> None:
    _request_id.set(value)


def current_request_id() -> str:
    return _request_id.get()
