"""
Logins: JWT for people, an API key for machine clients, and roles.

People
    POST /v1/auth/token with a user name and password returns a signed JWT
    (a "digital visitor badge") that says who you are, your role and when it
    expires. Send it on every call as  ``Authorization: Bearer <token>``.
    Nobody can change the role inside a token without breaking its signature.

Machine clients (scripts, later the v3.0 AI service)
    Send the shared key from .env as  ``X-API-Key: <key>``. They get the
    role ``service``.

Roles
    dispatcher  read readings, check readings, get decisions
    supervisor  everything a dispatcher can do, plus bulk scans
    admin       everything, plus reloading the rules file
    service     like a supervisor (for machine clients)

Demo users (dispatcher, supervisor, admin) have their passwords in .env.
In production the users would come from the company's identity provider
(for example Microsoft Entra ID) and no password would live in a file.
"""
from __future__ import annotations

import hmac
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, Request
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer

from .config import Settings
from .errors import AppError

log = logging.getLogger("rule_service.security")

PEOPLE_ROLES = ("dispatcher", "supervisor", "admin")
ALL_ROLES = PEOPLE_ROLES + ("service",)
JWT_ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/v1/auth/token",
    auto_error=False,
    scheme_name="Login (JWT)",
    description="People: log in with user name and password (dispatcher, supervisor or admin).",
)
api_key_scheme = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    scheme_name="API key",
    description="Machine clients: the RULE_API_KEY value from .env.",
)


@dataclass(frozen=True)
class Caller:
    name: str
    role: str
    auth_method: str  # "jwt" or "api_key"
    expires_at: datetime | None = None


def unauthorized(detail: str) -> AppError:
    return AppError(401, "unauthorized", "Not logged in", detail, {"WWW-Authenticate": "Bearer"})


def get_settings_from_app(request: Request) -> Settings:
    return request.app.state.settings


def check_password(settings: Settings, username: str, password: str) -> str | None:
    """Return the user's role if the password is right, else None (constant-time compare)."""
    entry = settings.user_passwords().get(username)
    expected = entry[1].get_secret_value() if entry else "x" * 32  # compare anyway: same time for unknown users
    ok = hmac.compare_digest(password.encode("utf-8"), expected.encode("utf-8"))
    return entry[0] if (entry and ok) else None


def create_token(settings: Settings, username: str, role: str) -> tuple[str, int]:
    now = datetime.now(timezone.utc)
    lifetime = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    payload = {
        "sub": username,
        "role": role,
        "iss": settings.JWT_ISSUER,
        "iat": now,
        "exp": now + lifetime,
    }
    token = jwt.encode(payload, settings.JWT_SECRET.get_secret_value(), algorithm=JWT_ALGORITHM)
    return token, int(lifetime.total_seconds())


def decode_token(settings: Settings, token: str) -> Caller:
    try:
        claims = jwt.decode(
            token,
            settings.JWT_SECRET.get_secret_value(),
            algorithms=[JWT_ALGORITHM],          # never accept "none" or another algorithm
            issuer=settings.JWT_ISSUER,
            options={"require": ["exp", "iat", "iss", "sub", "role"]},
        )
    except jwt.ExpiredSignatureError:
        raise unauthorized("Your token has expired. Log in again at POST /v1/auth/token.") from None
    except jwt.InvalidTokenError:
        raise unauthorized("The token is not valid (changed, signed with another key, or malformed).") from None
    role = claims.get("role")
    if role not in PEOPLE_ROLES:
        raise unauthorized("The token has an unknown role.")
    return Caller(
        name=str(claims["sub"]),
        role=role,
        auth_method="jwt",
        expires_at=datetime.fromtimestamp(int(claims["exp"]), tz=timezone.utc),
    )


async def get_caller(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    api_key: str | None = Depends(api_key_scheme),
    settings: Settings = Depends(get_settings_from_app),
) -> Caller:
    """Who is calling? Accepts a JWT (people) or the API key (machine clients)."""
    if token:
        caller = decode_token(settings, token)
    elif api_key:
        expected = settings.RULE_API_KEY.get_secret_value()
        if not hmac.compare_digest(api_key.encode("utf-8"), expected.encode("utf-8")):
            raise unauthorized("The API key is not valid.")
        caller = Caller(name="api-client", role="service", auth_method="api_key")
    else:
        raise unauthorized(
            "Log in first: send 'Authorization: Bearer <token>' (get one at POST /v1/auth/token) "
            "or 'X-API-Key: <key>'."
        )
    request.state.caller = f"{caller.name}({caller.role})"
    return caller


def require_roles(*roles: str):
    """Dependency: the caller must have one of these roles (else 403)."""

    async def _check(caller: Caller = Depends(get_caller)) -> Caller:
        if caller.role not in roles:
            raise AppError(
                403,
                "forbidden",
                "Not allowed",
                f"Your role '{caller.role}' may not do this. Allowed roles: {', '.join(roles)}.",
            )
        return caller

    return _check
