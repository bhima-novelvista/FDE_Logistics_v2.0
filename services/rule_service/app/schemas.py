"""
The JSON contracts of the API (request and response bodies).

Pydantic checks every request body against these models before any code
runs: wrong types, values out of range, unknown risk classes and extra
fields are refused with 422 and a list of what is wrong. The same models
produce the OpenAPI schema and the examples shown in Swagger at /docs.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .rules.engine import Decision, FiredRule  # noqa: F401  (re-exported for the API)

RiskClass = Literal["High Risk", "Moderate Risk", "Low Risk"]


# --------------------------------------------------------------------------
# Readings
# --------------------------------------------------------------------------
class ReadingIn(BaseModel):
    """A reading to check. Only the five fields the SOP rules use are required."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "temperature_c": 18.8,
                    "eta_variation_hours": 4.07,
                    "port_congestion_level": 7.69,
                    "delay_probability": 0.999,
                    "risk_classification": "High Risk",
                },
                {
                    "temperature_c": -9.98,
                    "eta_variation_hours": -2.0,
                    "port_congestion_level": 7.11,
                    "delay_probability": 0.29,
                    "risk_classification": "High Risk",
                },
            ]
        },
    )

    temperature_c: float = Field(ge=-50, le=80, description="Cargo temperature in °C")
    eta_variation_hours: float = Field(ge=-48, le=240, description="Hours late (+) or early (-)")
    port_congestion_level: float = Field(ge=0, le=10, description="Port congestion, 0 to 10")
    delay_probability: float = Field(ge=0, le=1, description="Probability of delay, 0 to 1")
    risk_classification: RiskClass
    cargo_condition_code: float | None = Field(default=None, ge=0, le=1)
    route_risk_index: float | None = Field(default=None, ge=0, le=10)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)


class Reading(BaseModel):
    """One reading from the legacy data, with readable names."""

    reading_id: int = Field(examples=[32065], description="Row number in the legacy table (not a truck or shipment ID)")
    timestamp: datetime = Field(examples=["2024-08-29T00:00:00"], description="Reading time (UTC)")
    latitude: float | None
    longitude: float | None
    temperature_c: float | None
    eta_variation_hours: float | None
    port_congestion_level: float | None
    delay_probability: float | None
    risk_classification: str | None
    cargo_condition_code: float | None
    route_risk_index: float | None


class ReadingList(BaseModel):
    count: int
    readings: list[Reading]


# --------------------------------------------------------------------------
# Decisions
# --------------------------------------------------------------------------
class DecisionResponse(BaseModel):
    """The rule engine's decision, with the reading it is about."""

    request_id: str = Field(description="Quote this to find the log line and audit row")
    reading: Reading | None = Field(default=None, description="The reading from the database (decision endpoint only)")
    decision: Decision
    audit_logged: bool = Field(description="True when the decision was written to the audit table")


# --------------------------------------------------------------------------
# Scan
# --------------------------------------------------------------------------
class Area(BaseModel):
    model_config = ConfigDict(extra="forbid")

    lat_min: float = Field(ge=-90, le=90)
    lat_max: float = Field(ge=-90, le=90)
    lon_min: float = Field(ge=-180, le=180)
    lon_max: float = Field(ge=-180, le=180)

    @model_validator(mode="after")
    def ordered(self) -> "Area":
        if self.lat_min > self.lat_max or self.lon_min > self.lon_max:
            raise ValueError("lat_min must be <= lat_max and lon_min <= lon_max")
        return self


class ScanRequest(BaseModel):
    """Which readings to check. Leave everything out to check all readings."""

    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {},
                {"from_time": "2024-08-01T00:00:00", "to_time": "2024-08-29T23:59:59", "examples": 3},
                {"area": {"lat_min": 33.3, "lat_max": 34.3, "lon_min": -118.6, "lon_max": -117.6}},
            ]
        },
    )

    from_time: datetime | None = Field(default=None, description="From this time (UTC), inclusive")
    to_time: datetime | None = Field(default=None, description="Up to this time (UTC), inclusive")
    area: Area | None = Field(default=None, description="Latitude/longitude box")
    examples: int = Field(default=5, ge=0, le=50, description="How many of the newest readings that need action to return in full")

    @model_validator(mode="after")
    def ordered(self) -> "ScanRequest":
        if self.from_time and self.to_time and self.from_time > self.to_time:
            raise ValueError("from_time must be before to_time")
        return self


class ScanExample(BaseModel):
    reading: Reading
    decision: Decision


class ScanResponse(BaseModel):
    request_id: str
    rules_version: str
    readings_checked: int
    rule_counts: dict[str, int] = Field(
        description="How many readings each rule or gap applies to (counted inside MySQL)",
        examples=[{"R1": 8674, "R2": 6621, "R3": 19566, "R4": 15440, "G1": 21817}],
    )
    outcome_counts: dict[str, int] = Field(
        examples=[{"ACTION_REQUIRED": 27245, "REVIEW": 4524, "NO_ACTION": 296}]
    )
    examples: list[ScanExample] = Field(description="The newest readings that need action, evaluated in full")
    audit_logged: bool


# --------------------------------------------------------------------------
# Rules
# --------------------------------------------------------------------------
class ConditionOut(BaseModel):
    field: str
    op: str
    value: float | str


class RuleOut(BaseModel):
    rule_id: str
    kind: Literal["rule", "gap"]
    name: str
    match: Literal["all", "any"]
    conditions: list[ConditionOut]
    severity: str
    action: str
    sop_section: str
    note: str | None = None


class RulesResponse(BaseModel):
    sop_name: str
    rules_version: str
    effective: str | None
    source: str | None
    assumptions: list[str]
    loaded_at_utc: datetime
    rules: list[RuleOut]


class ReloadResponse(BaseModel):
    request_id: str
    message: str
    previous_version: str
    rules_version: str
    rule_count: int
    gap_count: int
    audit_logged: bool


# --------------------------------------------------------------------------
# Auth and health
# --------------------------------------------------------------------------
class TokenResponse(BaseModel):
    access_token: str = Field(description="Send it as:  Authorization: Bearer <access_token>")
    token_type: Literal["bearer"] = "bearer"
    expires_in: int = Field(description="Seconds until the token expires", examples=[1800])
    role: str = Field(examples=["dispatcher"])


class Me(BaseModel):
    caller: str = Field(examples=["dispatcher"])
    role: str = Field(examples=["dispatcher"])
    auth_method: Literal["jwt", "api_key"]
    token_expires_at_utc: datetime | None = None


class Health(BaseModel):
    status: Literal["ok"] = "ok"
    service: str = "rule-service"
    version: str


class Ready(BaseModel):
    status: Literal["ready"] = "ready"
    database: Literal["ok"] = "ok"
    rules_version: str
    readings_in_view: int
