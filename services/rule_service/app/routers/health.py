"""Health checks: is the service up (liveness), and can it do its work (readiness)?"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from .. import __version__
from ..deps import get_repository, get_rules
from ..errors import problem_responses
from ..rules.engine import RuleSet
from ..schemas import Health, Ready

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=Health,
    summary="Is the service running?",
    description="Liveness check. Needs no login and does not touch the database. "
    "Docker uses it to mark the container healthy.",
)
async def health() -> Health:
    return Health(version=__version__)


@router.get(
    "/ready",
    response_model=Ready,
    summary="Can the service do its work?",
    description="Readiness check: the rules are loaded and the legacy database answers through the view. "
    "Returns 503 if the database cannot be reached.",
    responses=problem_responses("/ready", {503: "Database unavailable"}),
)
async def ready(repo=Depends(get_repository), rules: RuleSet = Depends(get_rules)) -> Ready:
    count = await repo.count_readings()
    return Ready(rules_version=rules.version, readings_in_view=count)
