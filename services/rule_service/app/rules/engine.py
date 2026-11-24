"""
The rule engine.

1. ``load_rules(path)`` reads the SOP rules YAML file and checks it. A file
   with any mistake is refused with a readable list of problems, so a typo can
   never reach the dispatcher.
2. ``RuleSet.evaluate(reading)`` checks one reading against every rule and
   returns a ``Decision``: which rules fired, why (the evidence), what to do,
   how serious it is, and where the SOP says so.
3. ``RuleSet.sql_condition(rule_id)`` turns the same rule into a
   parameterised SQL condition, so bulk checks (POST /v1/scan) can be counted
   inside MySQL. Values are always passed as parameters, never pasted into
   the SQL text, and only known fields and comparisons are allowed.

The YAML file is data, not code: nothing in it is ever executed.
"""
from __future__ import annotations

import math
import operator
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

# ---------------------------------------------------------------------------
# What a rule may refer to. The key is the field name used in the YAML file
# and in the API; the value is the column of fde_views.vw_fleet_readings.
# ---------------------------------------------------------------------------
NUMERIC_FIELDS: dict[str, str] = {
    "temperature_c": "Current_Temperature_C",
    "eta_variation_hours": "ETA_Variation_Hours",
    "port_congestion_level": "Port_Congestion_Level",
    "delay_probability": "Delay_Probability",
    "cargo_condition_code": "Cargo_Condition_Code",
    "route_risk_index": "Route_Risk_Index",
    "latitude": "Latitude",
    "longitude": "Longitude",
}
TEXT_FIELDS: dict[str, str] = {
    "risk_classification": "Risk_Classification",
}
FIELD_TO_COLUMN: dict[str, str] = {**NUMERIC_FIELDS, **TEXT_FIELDS}

Op = Literal[">", ">=", "<", "<=", "==", "!="]
PY_OPERATORS: dict[str, Callable[[Any, Any], bool]] = {
    ">": operator.gt,
    ">=": operator.ge,
    "<": operator.lt,
    "<=": operator.le,
    "==": operator.eq,
    "!=": operator.ne,
}
SQL_OPERATORS: dict[str, str] = {">": ">", ">=": ">=", "<": "<", "<=": "<=", "==": "=", "!=": "<>"}

Severity = Literal["critical", "high", "medium", "review"]
SEVERITY_RANK: dict[str, int] = {"none": 0, "review": 1, "medium": 2, "high": 3, "critical": 4}

Outcome = Literal["ACTION_REQUIRED", "REVIEW", "NO_ACTION"]


class RuleFileError(ValueError):
    """The rules file is missing, unreadable or breaks the rules-file layout."""

    def __init__(self, path: Path | str, problems: list[str]):
        self.path = str(path)
        self.problems = problems
        super().__init__(f"Rules file {path} was refused: " + "; ".join(problems))


# ---------------------------------------------------------------------------
# The layout of the rules file (checked with Pydantic; unknown keys refused)
# ---------------------------------------------------------------------------
class Condition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str
    op: Op
    value: float | str

    @field_validator("field")
    @classmethod
    def known_field(cls, v: str) -> str:
        if v not in FIELD_TO_COLUMN:
            raise ValueError(f"unknown field '{v}'; allowed: {', '.join(sorted(FIELD_TO_COLUMN))}")
        return v

    @model_validator(mode="after")
    def value_matches_field(self) -> "Condition":
        if self.field in NUMERIC_FIELDS:
            if isinstance(self.value, str):
                raise ValueError(f"field '{self.field}' needs a number, not text ('{self.value}')")
            if isinstance(self.value, bool) or not math.isfinite(self.value):
                raise ValueError(f"field '{self.field}' needs a finite number")
        else:
            if not isinstance(self.value, str):
                raise ValueError(f"field '{self.field}' needs text, not a number")
            if self.op not in ("==", "!="):
                raise ValueError(f"text field '{self.field}' can only use == or !=")
        return self


class When(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    all_of: list[Condition] | None = Field(default=None, alias="all")
    any_of: list[Condition] | None = Field(default=None, alias="any")

    @model_validator(mode="after")
    def exactly_one_list(self) -> "When":
        if (self.all_of is None) == (self.any_of is None):
            raise ValueError("'when' needs exactly one of 'all' or 'any'")
        conditions = self.all_of if self.all_of is not None else self.any_of
        if not conditions:
            raise ValueError("'when' needs at least one condition")
        return self

    @property
    def mode(self) -> str:
        return "all" if self.all_of is not None else "any"

    @property
    def conditions(self) -> list[Condition]:
        return self.all_of if self.all_of is not None else (self.any_of or [])


class Then(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Severity
    action: str = Field(min_length=5)
    sop_section: str = Field(min_length=1)
    note: str | None = None


class RuleDef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=r"^[A-Z][A-Z0-9_]{0,15}$")
    name: str = Field(min_length=3)
    when: When
    then: Then


class SopInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    version: str = Field(pattern=r"^[0-9A-Za-z.\-]{1,16}$")
    effective: str | None = None
    source: str | None = None
    assumptions: list[str] = []


class RuleFile(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sop: SopInfo
    rules: list[RuleDef] = Field(min_length=1)
    gaps: list[RuleDef] = []

    @model_validator(mode="after")
    def ids_unique_and_gaps_review(self) -> "RuleFile":
        ids = [r.id for r in self.rules + self.gaps]
        duplicates = sorted({i for i in ids if ids.count(i) > 1})
        if duplicates:
            raise ValueError(f"duplicate rule id(s): {', '.join(duplicates)}")
        for g in self.gaps:
            if g.then.severity != "review":
                raise ValueError(f"gap {g.id} must have severity 'review' (the SOP gives no action for it)")
        return self


# ---------------------------------------------------------------------------
# What the engine returns
# ---------------------------------------------------------------------------
class FiredRule(BaseModel):
    """One rule (or gap) that applies to the reading."""

    rule_id: str = Field(examples=["R1"])
    kind: Literal["rule", "gap"] = Field(description="'rule' = SOP rule; 'gap' = the SOP has no rule for this")
    name: str = Field(examples=["Critical temperature breach"])
    severity: Severity
    action: str = Field(examples=["Contact the driver to restart the auxiliary cooling unit."])
    sop_section: str = Field(examples=["1. Temperature Control & Spoilage Prevention"])
    evidence: list[str] = Field(description="The values that made the rule fire", examples=[["temperature_c = 18.8 > 4.0"]])
    note: str | None = None


class Decision(BaseModel):
    """The rule engine's answer for one reading."""

    outcome: Outcome = Field(
        description="ACTION_REQUIRED = at least one SOP rule applies; REVIEW = only an SOP gap applies; "
        "NO_ACTION = nothing applies"
    )
    highest_severity: Literal["critical", "high", "medium", "review", "none"]
    summary: str
    fired: list[FiredRule]
    rules_version: str = Field(examples=["2.4"])
    sop_name: str = Field(examples=["Cold-Chain Incident SOP"])
    evaluated_at_utc: datetime


def _fmt(v: Any) -> str:
    if isinstance(v, float):
        return f"{v:.1f}" if v.is_integer() else f"{v:.4g}"
    if isinstance(v, str):
        return f"'{v}'"
    return str(v)


def _condition_true(cond: Condition, reading: Mapping[str, Any]) -> bool:
    actual = reading.get(cond.field)
    if actual is None:
        return False  # a missing value never triggers a rule (same as SQL NULL)
    if cond.field in TEXT_FIELDS:
        if not isinstance(actual, str):
            return False
        # Text comparisons ignore upper/lower case, like MySQL's default collation.
        return PY_OPERATORS[cond.op](actual.casefold(), str(cond.value).casefold())
    try:
        number = float(actual)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(number):
        return False
    return PY_OPERATORS[cond.op](number, float(cond.value))


class RuleSet:
    """A checked rules file, ready to evaluate readings."""

    def __init__(self, rule_file: RuleFile, path: Path | str):
        self.file = rule_file
        self.path = str(path)
        self.loaded_at_utc = datetime.now(timezone.utc)

    # -- information ------------------------------------------------------
    @property
    def version(self) -> str:
        return self.file.sop.version

    @property
    def sop_name(self) -> str:
        return self.file.sop.name

    @property
    def rules(self) -> list[RuleDef]:
        return self.file.rules

    @property
    def gaps(self) -> list[RuleDef]:
        return self.file.gaps

    def all_defs(self) -> list[tuple[str, RuleDef]]:
        return [("rule", r) for r in self.rules] + [("gap", g) for g in self.gaps]

    # -- evaluation ---------------------------------------------------------
    def matches(self, rule: RuleDef, reading: Mapping[str, Any]) -> bool:
        results = (_condition_true(c, reading) for c in rule.when.conditions)
        return all(results) if rule.when.mode == "all" else any(results)

    def evaluate(self, reading: Mapping[str, Any]) -> Decision:
        fired: list[FiredRule] = []
        for kind, rule in self.all_defs():
            if not self.matches(rule, reading):
                continue
            evidence = [
                f"{c.field} = {_fmt(reading.get(c.field))} {c.op} {_fmt(c.value)}"
                for c in rule.when.conditions
                if _condition_true(c, reading)
            ]
            fired.append(
                FiredRule(
                    rule_id=rule.id,
                    kind=kind,  # type: ignore[arg-type]
                    name=rule.name,
                    severity=rule.then.severity,
                    action=rule.then.action,
                    sop_section=rule.then.sop_section,
                    evidence=evidence,
                    note=rule.then.note,
                )
            )

        rules_fired = [f for f in fired if f.kind == "rule"]
        gaps_fired = [f for f in fired if f.kind == "gap"]
        highest = max((f.severity for f in fired), key=lambda s: SEVERITY_RANK[s], default="none")

        if rules_fired:
            outcome: Outcome = "ACTION_REQUIRED"
            summary = (
                f"{len(rules_fired)} SOP rule(s) apply: {', '.join(f.rule_id for f in rules_fired)}."
            )
            if gaps_fired:
                summary += (
                    f" Also outside the SOP: {', '.join(f.rule_id for f in gaps_fired)}"
                    " (no SOP rule; refer to the shift supervisor)."
                )
        elif gaps_fired:
            outcome = "REVIEW"
            summary = (
                f"No SOP rule applies, but the reading is in a situation the SOP does not cover "
                f"({', '.join(f.rule_id for f in gaps_fired)}). Refer it to the shift supervisor."
            )
        else:
            outcome = "NO_ACTION"
            summary = "No SOP rule applies to this reading."

        return Decision(
            outcome=outcome,
            highest_severity=highest,  # type: ignore[arg-type]
            summary=summary,
            fired=fired,
            rules_version=self.version,
            sop_name=self.sop_name,
            evaluated_at_utc=datetime.now(timezone.utc),
        )

    # -- SQL ----------------------------------------------------------------
    def sql_condition(self, rule: RuleDef) -> tuple[str, dict[str, Any]]:
        """The rule as a SQL condition on the view, with its parameters.

        Example for R4:
        ``(Risk_Classification = :R4_0 AND Delay_Probability > :R4_1)``
        with ``{"R4_0": "High Risk", "R4_1": 0.65}``.
        """
        parts: list[str] = []
        params: dict[str, Any] = {}
        for i, c in enumerate(rule.when.conditions):
            name = f"{rule.id}_{i}"
            parts.append(f"{FIELD_TO_COLUMN[c.field]} {SQL_OPERATORS[c.op]} :{name}")
            params[name] = c.value
        joiner = " AND " if rule.when.mode == "all" else " OR "
        return "(" + joiner.join(parts) + ")", params


def load_rules(path: Path | str) -> RuleSet:
    """Read and check a rules file. Raises RuleFileError with readable problems."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuleFileError(p, [f"cannot read the file: {exc.strerror or exc}"]) from exc
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        raise RuleFileError(p, [f"not valid YAML: {exc}"]) from exc
    if not isinstance(data, dict):
        raise RuleFileError(p, ["the file must start with 'sop:', 'rules:' and 'gaps:' sections"])
    try:
        rule_file = RuleFile.model_validate(data)
    except ValidationError as exc:
        problems = []
        for err in exc.errors():
            where = ".".join(str(x) for x in err["loc"]) or "(file)"
            problems.append(f"{where}: {err['msg']}")
        raise RuleFileError(p, problems) from exc
    return RuleSet(rule_file, p)
