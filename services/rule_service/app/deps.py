"""
Shared dependencies (FastAPI's dependency injection).

Routes ask for what they need with ``Depends(...)``. Tests swap the real
database for a fake one by passing their own repository to ``create_app``,
without touching any route.
"""
from __future__ import annotations

from fastapi import Request

from .errors import ServiceUnavailableError
from .rules.engine import RuleSet


def get_repository(request: Request):
    repo = getattr(request.app.state, "repository", None)
    if repo is None:
        raise ServiceUnavailableError("The service is still starting. Try again in a few seconds.")
    return repo


def get_rules(request: Request) -> RuleSet:
    return request.app.state.rules


def endpoint_name(request: Request) -> str:
    """For example 'GET /v1/readings/{reading_id}/decision' (the route, not the filled-in path)."""
    route = request.scope.get("route")
    path = getattr(route, "path", request.url.path)
    return f"{request.method} {path}"
