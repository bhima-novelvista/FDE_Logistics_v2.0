"""The rules file is checked before use: every kind of mistake is refused with a readable reason."""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import DEFAULT_RULES_FILE
from app.rules.engine import RuleFileError, load_rules

GOOD = DEFAULT_RULES_FILE.read_text(encoding="utf-8")


def write(tmp_path: Path, text: str) -> Path:
    p = tmp_path / "rules.yaml"
    p.write_text(text, encoding="utf-8")
    return p


def test_the_real_rules_file_loads() -> None:
    rs = load_rules(DEFAULT_RULES_FILE)
    assert rs.version == "2.4"
    assert [r.id for r in rs.rules] == ["R1", "R2", "R3", "R4"]
    assert [g.id for g in rs.gaps] == ["G1"]
    assert len(rs.file.sop.assumptions) == 3


@pytest.mark.parametrize(
    "old, new, reason",
    [
        ("field: temperature_c, op: \">\", value: 4.0 }\n    then:\n      severity: critical\n      action: Contact",
         "field: temp, op: \">\", value: 4.0 }\n    then:\n      severity: critical\n      action: Contact",
         "unknown field 'temp'"),
        ("{ field: port_congestion_level, op: \">\", value: 7.0 }",
         "{ field: port_congestion_level, op: \"=>\", value: 7.0 }",
         "op"),
        ("{ field: port_congestion_level, op: \">\", value: 7.0 }",
         "{ field: port_congestion_level, op: \">\", value: \"seven\" }",
         "needs a number"),
        ("{ field: risk_classification, op: \"==\", value: \"High Risk\" }",
         "{ field: risk_classification, op: \">\", value: \"High Risk\" }",
         "can only use == or !="),
        ("  - id: R4\n", "  - id: R3\n", "duplicate rule id(s): R3"),
        ("      severity: high\n      action: Escalate", "      severity: urgent\n      action: Escalate", "severity"),
        ("      action: Escalate the shipment to the Tier 2 Logistics Manager.\n", "", "action"),
        ("      severity: review\n", "      severity: high\n", "must have severity 'review'"),
        ("    when:\n      all:\n        - { field: risk_classification",
         "    when:\n      all: []\n      any:\n        - { field: risk_classification",
         "exactly one of 'all' or 'any'"),
        ("  version: \"2.4\"\n", "  version: \"2.4\"\n  owner: ops\n", "Extra inputs are not permitted"),
    ],
)
def test_mistakes_are_refused(tmp_path: Path, old: str, new: str, reason: str) -> None:
    assert old in GOOD, f"test pattern not found: {old!r}"
    path = write(tmp_path, GOOD.replace(old, new, 1))
    with pytest.raises(RuleFileError) as info:
        load_rules(path)
    assert reason in " | ".join(info.value.problems)


def test_not_yaml_and_missing_file(tmp_path: Path) -> None:
    with pytest.raises(RuleFileError, match="not valid YAML"):
        load_rules(write(tmp_path, "rules: [unclosed"))
    with pytest.raises(RuleFileError, match="cannot read the file"):
        load_rules(tmp_path / "missing.yaml")
    with pytest.raises(RuleFileError, match="must start with"):
        load_rules(write(tmp_path, "just text"))


def test_sql_injection_in_a_text_value_stays_a_parameter(tmp_path: Path) -> None:
    evil = GOOD.replace('value: "High Risk"', 'value: "High Risk\' OR 1=1 --"', 1)
    rs = load_rules(write(tmp_path, evil))
    r4 = next(r for r in rs.rules if r.id == "R4")
    sql, params = rs.sql_condition(r4)
    assert "OR 1=1" not in sql
    assert params["R4_0"] == "High Risk' OR 1=1 --"
