"""Check any reading you send (it does not have to be in the database)."""
from __future__ import annotations

from fastapi import APIRouter, Body, Depends, Request

from ..audit import record
from ..deps import endpoint_name, get_repository, get_rules
from ..errors import problem_responses
from ..request_context import current_request_id
from ..rules.engine import RuleSet
from ..schemas import DecisionResponse, ReadingIn
from ..security import Caller, get_caller

router = APIRouter(prefix="/v1", tags=["Readings and decisions"])


@router.post(
    "/evaluate",
    response_model=DecisionResponse,
    summary="Check a reading you send",
    description=(
        "Applies the SOP rules to the reading in the request body, for example a reading the driver reads out "
        "on the phone, or a 'what if' test. The body is checked first: values out of range, an unknown risk "
        "class or extra fields are refused with 422. The decision is written to the audit trail."
    ),
    responses=problem_responses("/v1/evaluate", {401: "Not logged in", 422: "Invalid reading"}),
)
async def evaluate(
    request: Request,
    reading: ReadingIn = Body(...),
    caller: Caller = Depends(get_caller),
    repo=Depends(get_repository),
    rules: RuleSet = Depends(get_rules),
) -> DecisionResponse:
    data = reading.model_dump()
    decision = rules.evaluate(data)
    logged = await record(
        repo, caller, endpoint_name(request), decision.outcome,
        rules_version=decision.rules_version,
        fired_rules=[f.rule_id for f in decision.fired],
        detail={"input": data, "decision": decision.model_dump(mode="json")},
    )
    return DecisionResponse(request_id=current_request_id(), reading=None, decision=decision, audit_logged=logged)
