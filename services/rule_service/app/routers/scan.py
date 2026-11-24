"""Bulk check: how many readings in a time window or area need action, and which."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request

from ..audit import record
from ..deps import endpoint_name, get_repository, get_rules
from ..errors import problem_responses
from ..request_context import current_request_id
from ..rules.engine import RuleSet
from ..schemas import Reading, ScanExample, ScanRequest, ScanResponse
from ..security import Caller, require_roles

router = APIRouter(prefix="/v1", tags=["Bulk checks"])


@router.post(
    "/scan",
    response_model=ScanResponse,
    summary="Check many readings at once (supervisor)",
    description=(
        "Counts, for every rule, how many readings in the window or area it applies to. The counting runs "
        "inside MySQL: the engine turns each YAML rule into a parameterised SQL condition, so only the totals "
        "travel over the network. The newest readings that need action are then fetched and evaluated in full "
        "by the same engine (`examples`). With an empty body all 32,065 readings are checked. "
        "Roles: supervisor, admin, service."
    ),
    responses=problem_responses("/v1/scan", {
        401: "Not logged in",
        403: ("Role not allowed (dispatchers cannot scan)",
              "Your role 'dispatcher' may not do this. Allowed roles: supervisor, admin, service."),
        422: ("Invalid window or area", "1 input value(s) are missing or invalid. See 'errors'."),
        503: "Database unavailable",
    }),
)
async def scan(
    request: Request,
    body: ScanRequest = Body(default_factory=ScanRequest),
    caller: Caller = Depends(require_roles("supervisor", "admin", "service")),
    repo=Depends(get_repository),
    rules: RuleSet = Depends(get_rules),
) -> ScanResponse:
    total, rule_counts, outcome_counts, rows = await repo.scan(
        rules, body.from_time, body.to_time, body.area, body.examples
    )
    examples = [ScanExample(reading=Reading(**r), decision=rules.evaluate(r)) for r in rows]
    logged = await record(
        repo, caller, endpoint_name(request), "SCAN",
        rules_version=rules.version,
        detail={"request": body.model_dump(mode="json"), "readings_checked": total,
                "rule_counts": rule_counts, "outcome_counts": outcome_counts},
    )
    return ScanResponse(
        request_id=current_request_id(),
        rules_version=rules.version,
        readings_checked=total,
        rule_counts=rule_counts,
        outcome_counts=outcome_counts,
        examples=examples,
        audit_logged=logged,
    )
