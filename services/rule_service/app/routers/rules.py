"""See the active SOP rules; reload the rules file after editing it (admin)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, Request

from ..audit import record
from ..deps import endpoint_name, get_repository, get_rules
from ..errors import problem_response, problem_responses
from ..request_context import current_request_id
from ..rules.engine import RuleFileError, RuleSet, load_rules
from ..schemas import ConditionOut, ReloadResponse, RuleOut, RulesResponse
from ..security import Caller, get_caller, require_roles

log = logging.getLogger("rule_service.rules")
router = APIRouter(prefix="/v1/rules", tags=["Rules"])



def describe(rules: RuleSet) -> RulesResponse:
    items = [
        RuleOut(
            rule_id=r.id,
            kind=kind,  # type: ignore[arg-type]
            name=r.name,
            match=r.when.mode,  # type: ignore[arg-type]
            conditions=[ConditionOut(field=c.field, op=c.op, value=c.value) for c in r.when.conditions],
            severity=r.then.severity,
            action=r.then.action,
            sop_section=r.then.sop_section,
            note=r.then.note,
        )
        for kind, r in rules.all_defs()
    ]
    sop = rules.file.sop
    return RulesResponse(
        sop_name=sop.name,
        rules_version=sop.version,
        effective=sop.effective,
        source=sop.source,
        assumptions=sop.assumptions,
        loaded_at_utc=rules.loaded_at_utc,
        rules=items,
    )


@router.get(
    "",
    response_model=RulesResponse,
    summary="List the active SOP rules",
    description="The rules and gaps the engine uses right now, exactly as read from the rules file.",
    responses=problem_responses("/v1/rules", {401: "Not logged in"}),
)
async def list_rules(_: Caller = Depends(get_caller), rules: RuleSet = Depends(get_rules)) -> RulesResponse:
    return describe(rules)


@router.post(
    "/reload",
    response_model=ReloadResponse,
    summary="Reload the rules file (admin)",
    description=(
        "Reads the rules file again, for example after you changed a threshold. The new file is "
        "checked first: if anything is wrong it is refused with 422 and a list of problems, and the "
        "old rules stay active. Every reload attempt is written to the audit trail."
    ),
    responses=problem_responses("/v1/rules/reload", {
        401: "Not logged in",
        403: ("Only admin may reload", "Your role 'supervisor' may not do this. Allowed roles: admin."),
        422: ("The rules file has mistakes; the old rules stay active",
              "The rules file has 1 problem(s). The old rules (version 2.4) stay active.",
              "rules-file-invalid", "Rules file refused"),
    }),
)
async def reload_rules(
    request: Request,
    caller: Caller = Depends(require_roles("admin")),
    repo=Depends(get_repository),
):
    old: RuleSet = request.app.state.rules
    path = request.app.state.settings.RULES_FILE
    try:
        new = load_rules(path)
    except RuleFileError as exc:
        log.warning("rules reload refused: %s", exc)
        await record(repo, caller, endpoint_name(request), "RULES_REJECTED",
                     rules_version=old.version, detail={"problems": exc.problems})
        return problem_response(
            request, 422, "rules-file-invalid", "Rules file refused",
            f"The rules file has {len(exc.problems)} problem(s). The old rules (version {old.version}) stay active.",
            errors=[{"where": "rules file", "problem": p} for p in exc.problems],
        )
    request.app.state.rules = new          # one assignment: callers see either the old or the new set
    log.info("rules reloaded: %s -> %s", old.version, new.version)
    logged = await record(repo, caller, endpoint_name(request), "RULES_RELOADED", rules_version=new.version,
                          detail={"previous_version": old.version, "rules": [r.id for _, r in new.all_defs()]})
    return ReloadResponse(
        request_id=current_request_id(),
        message="Rules reloaded.",
        previous_version=old.version,
        rules_version=new.version,
        rule_count=len(new.rules),
        gap_count=len(new.gaps),
        audit_logged=logged,
    )
