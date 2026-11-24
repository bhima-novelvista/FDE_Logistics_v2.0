"""The rule engine: every rule at its exact edge, real readings, and the SQL form of the rules."""
from __future__ import annotations

import pytest

from conftest import SAMPLE_READINGS
from app.rules.engine import RuleSet

BASE = dict(temperature_c=2.0, eta_variation_hours=0.0, port_congestion_level=3.0,
            delay_probability=0.2, risk_classification="Low Risk")


def fired(rules: RuleSet, **changes) -> list[str]:
    reading = dict(BASE, **changes)
    return [f.rule_id for f in rules.evaluate(reading).fired]


@pytest.mark.parametrize(
    "changes, expected",
    [
        # R1: strictly above 4.0 °C
        (dict(temperature_c=4.0), []),
        (dict(temperature_c=4.0000001), ["R1"]),
        # R2: above 4.0 °C AND more than 1 hour late
        (dict(temperature_c=5.0, eta_variation_hours=1.0), ["R1"]),
        (dict(temperature_c=5.0, eta_variation_hours=1.01), ["R1", "R2"]),
        (dict(temperature_c=3.9, eta_variation_hours=3.0), []),
        # R3: port congestion strictly above 7.0
        (dict(port_congestion_level=7.0), []),
        (dict(port_congestion_level=7.01), ["R3"]),
        # R4: High Risk AND delay probability strictly above 0.65
        (dict(risk_classification="High Risk", delay_probability=0.65), []),
        (dict(risk_classification="High Risk", delay_probability=0.6501), ["R4"]),
        (dict(risk_classification="Moderate Risk", delay_probability=0.99), []),
        (dict(risk_classification="high risk", delay_probability=0.99), ["R4"]),   # case is ignored
        # G1: below 0.0 °C (no SOP rule)
        (dict(temperature_c=0.0), []),
        (dict(temperature_c=-0.01), ["G1"]),
    ],
)
def test_rule_edges(rules: RuleSet, changes: dict, expected: list[str]) -> None:
    assert fired(rules, **changes) == expected


def test_latest_reading_fires_all_four_rules(rules: RuleSet) -> None:
    d = rules.evaluate(SAMPLE_READINGS[32065])
    assert d.outcome == "ACTION_REQUIRED"
    assert d.highest_severity == "critical"
    assert [f.rule_id for f in d.fired] == ["R1", "R2", "R3", "R4"]
    r2 = d.fired[1]
    assert r2.evidence == ["temperature_c = 18.8 > 4.0", "eta_variation_hours = 4.068 > 1.0"]
    assert d.rules_version == "2.4"


def test_los_angeles_reading_is_r3_plus_gap(rules: RuleSet) -> None:
    d = rules.evaluate(SAMPLE_READINGS[31759])
    assert [(f.rule_id, f.kind) for f in d.fired] == [("R3", "rule"), ("G1", "gap")]
    assert d.outcome == "ACTION_REQUIRED"
    assert "refer to the shift supervisor" in d.summary
    assert d.fired[0].note and "destination port" in d.fired[0].note


def test_gap_only_is_review(rules: RuleSet) -> None:
    d = rules.evaluate(SAMPLE_READINGS[102])
    assert d.outcome == "REVIEW"
    assert d.highest_severity == "review"
    assert [f.rule_id for f in d.fired] == ["G1"]


def test_inside_limits_is_no_action(rules: RuleSet) -> None:
    d = rules.evaluate(SAMPLE_READINGS[101])
    assert d.outcome == "NO_ACTION"
    assert d.fired == []
    assert d.highest_severity == "none"


def test_missing_or_odd_values_never_fire(rules: RuleSet) -> None:
    assert fired(rules, temperature_c=None) == []
    assert fired(rules, temperature_c=float("nan")) == []
    assert fired(rules, temperature_c="hot") == []
    assert fired(rules, risk_classification=None, delay_probability=0.99) == []


def test_sql_form_uses_parameters_only(rules: RuleSet) -> None:
    r4 = next(r for r in rules.rules if r.id == "R4")
    sql, params = rules.sql_condition(r4)
    assert sql == "(Risk_Classification = :R4_0 AND Delay_Probability > :R4_1)"
    assert params == {"R4_0": "High Risk", "R4_1": 0.65}
    # no value is ever pasted into the SQL text
    assert "High Risk" not in sql and "0.65" not in sql
