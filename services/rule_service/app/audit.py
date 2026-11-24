"""
Writing the audit trail (story rule C3: record every step).

Every decision, scan and rules reload adds one row to
fde_audit.RuleDecisionLog: who asked, with which login, what was asked,
which rules version was used, and the full answer.

If the audit row cannot be written (for example the database dropped the
connection just then), the caller still gets the answer, with
``"audit_logged": false``, and the failure is logged as a warning. This
keeps a dispatcher from being blocked in the middle of an incident; the
false flag makes the missing row visible instead of silent.
"""
from __future__ import annotations

import logging
from typing import Any

from .request_context import current_request_id
from .security import Caller

log = logging.getLogger("rule_service.audit")


async def record(
    repository: Any,
    caller: Caller,
    endpoint: str,
    outcome: str,
    *,
    reading_id: int | None = None,
    rules_version: str | None = None,
    fired_rules: list[str] | None = None,
    detail: Any = None,
) -> bool:
    row = {
        "request_id": current_request_id(),
        "caller": caller.name[:64],
        "caller_role": caller.role[:32],
        "auth_method": caller.auth_method[:16],
        "endpoint": endpoint[:128],
        "reading_id": reading_id,
        "rules_version": rules_version,
        "outcome": outcome[:32],
        "fired_rules": (",".join(fired_rules))[:255] if fired_rules else None,
        "detail_json": detail,
    }
    try:
        await repository.write_audit(row)
        return True
    except Exception as exc:  # never block the caller because of the audit trail
        log.warning("audit row NOT written request_id=%s endpoint=%s: %s",
                    row["request_id"], endpoint, exc.__class__.__name__)
        return False
