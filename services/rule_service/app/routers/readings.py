"""Readings from the legacy data, and the SOP decision for one reading."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Query, Request

from ..audit import record
from ..deps import endpoint_name, get_repository, get_rules
from ..errors import AppError, NotFoundError, problem_responses
from ..request_context import current_request_id
from ..rules.engine import RuleSet
from ..schemas import Area, DecisionResponse, Reading, ReadingList
from ..security import Caller, get_caller, require_roles

router = APIRouter(prefix="/v1/readings", tags=["Readings and decisions"])



@router.get(
    "/latest",
    response_model=ReadingList,
    summary="The newest readings",
    description=(
        "The newest readings first. Optionally only inside a latitude/longitude box: give all four of "
        "`lat_min`, `lat_max`, `lon_min`, `lon_max` (for example the Los Angeles area 33.3, 34.3, -118.6, -117.6)."
    ),
    responses=problem_responses("/v1/readings/latest", {
        401: "Not logged in",
        422: ("Invalid input", "Give all four of lat_min, lat_max, lon_min and lon_max, or none of them."),
        503: "Database unavailable",
    }),
)
async def latest(
    limit: int = Query(5, ge=1, le=50, description="How many readings (1 to 50)"),
    lat_min: float | None = Query(None, ge=-90, le=90),
    lat_max: float | None = Query(None, ge=-90, le=90),
    lon_min: float | None = Query(None, ge=-180, le=180),
    lon_max: float | None = Query(None, ge=-180, le=180),
    _: Caller = Depends(get_caller),
    repo=Depends(get_repository),
) -> ReadingList:
    box = [lat_min, lat_max, lon_min, lon_max]
    area = None
    if any(v is not None for v in box):
        if any(v is None for v in box):
            raise AppError(422, "validation-error", "Invalid input",
                           "Give all four of lat_min, lat_max, lon_min and lon_max, or none of them.")
        try:
            area = Area(lat_min=lat_min, lat_max=lat_max, lon_min=lon_min, lon_max=lon_max)
        except ValueError as exc:
            raise AppError(422, "validation-error", "Invalid input",
                           "lat_min must be <= lat_max and lon_min <= lon_max.") from exc
    rows = await repo.latest(limit, area)
    return ReadingList(count=len(rows), readings=[Reading(**r) for r in rows])


@router.get(
    "/{reading_id}",
    response_model=Reading,
    summary="One reading",
    responses=problem_responses("/v1/readings/99999999", {
        401: "Not logged in", 404: "No reading with this ID", 422: "Invalid reading ID", 503: "Database unavailable",
    }),
)
async def get_reading(
    reading_id: int = Path(ge=1, le=10**12, description="Reading ID, for example 32065"),
    _: Caller = Depends(get_caller),
    repo=Depends(get_repository),
) -> Reading:
    row = await repo.get_reading(reading_id)
    if row is None:
        raise NotFoundError(f"There is no reading with ID {reading_id}.")
    return Reading(**row)


@router.get(
    "/{reading_id}/decision",
    response_model=DecisionResponse,
    summary="What does the SOP say about this reading?",
    description=(
        "Reads the reading from the legacy data (through the read-only view), applies the SOP rules and "
        "returns the decision: which rules apply, why (the evidence), what to do and where the SOP says so. "
        "The decision is written to the audit trail with your name. Roles: dispatcher, supervisor, admin, service."
    ),
    responses=problem_responses("/v1/readings/99999999/decision", {
        401: "Not logged in",
        404: "No reading with this ID", 422: "Invalid reading ID", 503: "Database unavailable",
    }),
)
async def decision_for_reading(
    request: Request,
    reading_id: int = Path(ge=1, le=10**12, description="Reading ID, for example 32065"),
    caller: Caller = Depends(require_roles("dispatcher", "supervisor", "admin", "service")),
    repo=Depends(get_repository),
    rules: RuleSet = Depends(get_rules),
) -> DecisionResponse:
    row = await repo.get_reading(reading_id)
    if row is None:
        raise NotFoundError(f"There is no reading with ID {reading_id}.")
    reading = Reading(**row)
    decision = rules.evaluate(row)
    logged = await record(
        repo, caller, endpoint_name(request), decision.outcome,
        reading_id=reading_id, rules_version=decision.rules_version,
        fired_rules=[f.rule_id for f in decision.fired],
        detail={"reading": reading.model_dump(mode="json"), "decision": decision.model_dump(mode="json")},
    )
    return DecisionResponse(request_id=current_request_id(), reading=reading, decision=decision, audit_logged=logged)
