"""Login: get a JWT with a user name and password; see who you are logged in as."""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from ..config import Settings
from ..errors import problem_responses
from ..schemas import Me, TokenResponse
from ..security import Caller, check_password, create_token, get_caller, get_settings_from_app, unauthorized

log = logging.getLogger("rule_service.security")
router = APIRouter(prefix="/v1/auth", tags=["Login"])


@router.post(
    "/token",
    response_model=TokenResponse,
    summary="Log in and get a token (JWT)",
    description=(
        "Send the user name and password as a form (`application/x-www-form-urlencoded`), "
        "the standard OAuth2 'password' way. Users: `dispatcher`, `supervisor`, `admin`; "
        "their passwords are in your `.env`. The token is valid for `JWT_EXPIRE_MINUTES` "
        "(30 by default). In Swagger, use the **Authorize** button instead of calling this yourself."
    ),
    responses=problem_responses("/v1/auth/token", {
        401: ("Wrong user name or password", "Wrong user name or password."),
        422: "User name or password missing",
    }),
)
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    settings: Settings = Depends(get_settings_from_app),
) -> TokenResponse:
    role = check_password(settings, form.username, form.password)
    if role is None:
        log.warning("login failed for user name '%s'", form.username[:64])
        await asyncio.sleep(0.5)  # slows down password guessing
        raise unauthorized("Wrong user name or password.")
    token, expires_in = create_token(settings, form.username, role)
    request.state.caller = f"{form.username}({role})"
    log.info("login ok: %s (%s)", form.username, role)
    return TokenResponse(access_token=token, expires_in=expires_in, role=role)


@router.get(
    "/me",
    response_model=Me,
    summary="Who am I logged in as?",
    responses=problem_responses("/v1/auth/me", {401: "Not logged in"}),
)
async def me(caller: Caller = Depends(get_caller)) -> Me:
    return Me(
        caller=caller.name,
        role=caller.role,
        auth_method=caller.auth_method,  # type: ignore[arg-type]
        token_expires_at_utc=caller.expires_at,
    )
