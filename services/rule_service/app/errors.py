"""
One error format for every failure: "problem details" (RFC 9457).

Every error response has the media type ``application/problem+json`` and
looks like this:

    {
      "type": "https://fde-pb-sol.local/problems/not-found",
      "title": "Reading not found",
      "status": 404,
      "detail": "There is no reading with ID 99999999.",
      "instance": "/v1/readings/99999999",
      "request_id": "3f0c9d4e..."
    }

A caller can always tell what went wrong (status + title), read a
plain-language explanation (detail), and quote the request_id to find the
matching log line and audit row.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .request_context import current_request_id

log = logging.getLogger("rule_service")

PROBLEM_BASE = "https://fde-pb-sol.local/problems/"
PROBLEM_MEDIA_TYPE = "application/problem+json"


class Problem(BaseModel):
    """The body of every error response (RFC 9457 problem details)."""

    type: str = Field(examples=[PROBLEM_BASE + "not-found"])
    title: str = Field(examples=["Reading not found"])
    status: int = Field(examples=[404])
    detail: str = Field(examples=["There is no reading with ID 99999999."])
    instance: str = Field(examples=["/v1/readings/99999999"])
    request_id: str = Field(examples=["3f0c9d4e8b6a4c1e9a7d2b5c6e8f0a1b"])
    errors: list[dict[str, Any]] | None = Field(
        default=None, description="Only for 422: one entry per invalid input"
    )


_EXAMPLE_REQUEST_ID = "3f0c9d4e8b6a4c1e9a7d2b5c6e8f0a1b"
_DOC_DEFAULTS: dict[int, tuple[str, str, str]] = {
    401: ("unauthorized", "Not logged in",
          "Log in first: send 'Authorization: Bearer <token>' (get one at POST /v1/auth/token) or 'X-API-Key: <key>'."),
    403: ("forbidden", "Not allowed",
          "Your role 'dispatcher' may not do this. Allowed roles: supervisor, admin, service."),
    404: ("not-found", "Not found", "There is no reading with ID 99999999."),
    422: ("validation-error", "Invalid input", "1 input value(s) are missing or invalid. See 'errors'."),
    503: ("database-unavailable", "Database unavailable",
          "The legacy database could not be reached or did not answer in time. Try again shortly."),
}


_EXAMPLE_422_ERRORS: dict[str, dict[str, str]] = {
    "/v1/auth/token": {"where": "body.password", "problem": "Field required"},
    "/v1/readings/99999999": {"where": "path.reading_id", "problem": "Input should be greater than or equal to 1"},
    "/v1/readings/99999999/decision": {"where": "path.reading_id", "problem": "Input should be a valid integer"},
    "/v1/scan": {"where": "body", "problem": "Value error, from_time must be before to_time"},
    "default": {"where": "body.delay_probability", "problem": "Input should be less than or equal to 1"},
}


def problem_responses(instance: str, spec: dict[int, str | tuple[str, ...]]) -> dict[int | str, dict[str, Any]]:
    """OpenAPI documentation of a route's error answers, each with a realistic example.

    ``spec`` maps a status to its description, or to (description, detail) or
    (description, detail, slug, title) when the example needs its own words.
    """
    out: dict[int | str, dict[str, Any]] = {}
    for status, value in spec.items():
        parts = (value,) if isinstance(value, str) else value
        slug, title, detail = _DOC_DEFAULTS[status]
        if len(parts) >= 2:
            detail = parts[1]
        if len(parts) >= 4:
            slug, title = parts[2], parts[3]
        example: dict[str, Any] = {
            "type": PROBLEM_BASE + slug, "title": title, "status": status, "detail": detail,
            "instance": instance, "request_id": _EXAMPLE_REQUEST_ID,
        }
        if status == 422 and detail.endswith("See 'errors'."):
            example["errors"] = [_EXAMPLE_422_ERRORS.get(instance, _EXAMPLE_422_ERRORS["default"])]
        out[status] = {
            "description": parts[0],
            "content": {PROBLEM_MEDIA_TYPE: {"schema": {"$ref": "#/components/schemas/Problem"}, "example": example}},
        }
    return out


class AppError(Exception):
    """An expected error with a clear message for the caller."""

    def __init__(self, status: int, slug: str, title: str, detail: str, headers: dict[str, str] | None = None):
        self.status = status
        self.slug = slug
        self.title = title
        self.detail = detail
        self.headers = headers or {}
        super().__init__(detail)


class NotFoundError(AppError):
    def __init__(self, detail: str):
        super().__init__(404, "not-found", "Not found", detail)


class ServiceUnavailableError(AppError):
    def __init__(self, detail: str):
        super().__init__(503, "service-unavailable", "Service unavailable", detail, {"Retry-After": "10"})


def problem_response(
    request: Request,
    status: int,
    slug: str,
    title: str,
    detail: str,
    headers: dict[str, str] | None = None,
    errors: list[dict[str, Any]] | None = None,
) -> JSONResponse:
    body = Problem(
        type=PROBLEM_BASE + slug,
        title=title,
        status=status,
        detail=detail,
        instance=request.url.path,
        request_id=current_request_id(),
        errors=errors,
    ).model_dump(exclude_none=True)
    return JSONResponse(body, status_code=status, headers=headers, media_type=PROBLEM_MEDIA_TYPE)


_STATUS_SLUGS = {
    400: ("bad-request", "Bad request"),
    401: ("unauthorized", "Not logged in"),
    403: ("forbidden", "Not allowed"),
    404: ("not-found", "Not found"),
    405: ("method-not-allowed", "Method not allowed"),
    415: ("unsupported-media-type", "Unsupported media type"),
    429: ("too-many-requests", "Too many requests"),
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(request: Request, exc: AppError) -> JSONResponse:
        return problem_response(request, exc.status, exc.slug, exc.title, exc.detail, exc.headers)

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        slug, title = _STATUS_SLUGS.get(exc.status_code, ("error", "Error"))
        detail = exc.detail if isinstance(exc.detail, str) else title
        if exc.status_code == 404 and detail == "Not Found":
            detail = f"There is no endpoint {request.method} {request.url.path}. See /docs for the list."
        return problem_response(request, exc.status_code, slug, title, detail, dict(exc.headers or {}))

    @app.exception_handler(RequestValidationError)
    async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        # Keep only where and why; never echo the submitted values back
        # (a login form would otherwise return the password it was given).
        errors = [
            {"where": ".".join(str(x) for x in err.get("loc", ())), "problem": err.get("msg", "invalid")}
            for err in exc.errors()
        ]
        return problem_response(
            request,
            422,
            "validation-error",
            "Invalid input",
            f"{len(errors)} input value(s) are missing or invalid. See 'errors'.",
            errors=errors,
        )

    @app.exception_handler(SQLAlchemyError)
    async def _database_error(request: Request, exc: SQLAlchemyError) -> JSONResponse:
        log.error("database error request_id=%s: %s", current_request_id(), exc.__class__.__name__,
                  exc_info=log.isEnabledFor(logging.DEBUG))
        return problem_response(
            request,
            503,
            "database-unavailable",
            "Database unavailable",
            "The legacy database could not be reached or did not answer in time. Try again shortly.",
            {"Retry-After": "10"},
        )

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        log.exception("unexpected error request_id=%s", current_request_id())
        return problem_response(
            request,
            500,
            "internal-error",
            "Internal error",
            "Something went wrong inside the rule service. Quote the request_id when you report it.",
        )
