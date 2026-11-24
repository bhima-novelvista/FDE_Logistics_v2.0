"""
Integration tests against the real legacy database (Step 1 + Step 3).

Run with:   python -m pytest -m integration
They read the settings from the project-root .env (host 127.0.0.1, the
rule_svc login and the API user passwords), so MySQL must be running.

The key test is the reconciliation: the rule engine (Python) and the same
rules turned into SQL (MySQL) must give exactly the counts that the Step 3
self-test checks, over all 32,065 readings.
"""
from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.repository import SELECT_COLUMNS, ReadingRepository
from app.rules.engine import load_rules

pytestmark = pytest.mark.integration

EXPECTED_RULE_COUNTS = {"R1": 8674, "R2": 6621, "R3": 19566, "R4": 15440, "G1": 21817}
EXPECTED_OUTCOMES = {"ACTION_REQUIRED": 27245, "REVIEW": 4524, "NO_ACTION": 296}
TOTAL = 32065


@pytest.fixture(scope="module")
def real_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]   (reads ../../.env)


def test_python_engine_and_sql_give_the_same_counts(real_settings: Settings) -> None:
    rules = load_rules(real_settings.RULES_FILE)

    async def run():
        repo = ReadingRepository(real_settings)
        try:
            rows = await repo._fetch_all(f"SELECT {SELECT_COLUMNS} FROM {repo.view}", {})
            sql_result = await repo.scan(rules, None, None, None, examples=0)
        finally:
            await repo.close()
        return rows, sql_result

    rows, (total, sql_counts, sql_outcomes, _) = asyncio.run(run())
    assert len(rows) == total == TOTAL

    py_counts = {rid: 0 for rid in EXPECTED_RULE_COUNTS}
    py_outcomes = {k: 0 for k in EXPECTED_OUTCOMES}
    for row in rows:
        decision = rules.evaluate(row)
        py_outcomes[decision.outcome] += 1
        for f in decision.fired:
            py_counts[f.rule_id] += 1

    assert py_counts == sql_counts == EXPECTED_RULE_COUNTS
    assert py_outcomes == sql_outcomes == EXPECTED_OUTCOMES


def test_api_end_to_end_on_the_real_database(real_settings: Settings) -> None:
    app = create_app(real_settings)
    with TestClient(app) as c:
        assert c.get("/ready").json()["readings_in_view"] == TOTAL

        token = c.post("/v1/auth/token", data={
            "username": "dispatcher",
            "password": real_settings.API_USER_DISPATCHER_PASSWORD.get_secret_value(),
        }).json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}

        body = c.get("/v1/readings/32065/decision", headers=h).json()
        assert [f["rule_id"] for f in body["decision"]["fired"]] == ["R1", "R2", "R3", "R4"]
        assert body["audit_logged"] is True

        body = c.get("/v1/readings/31759/decision", headers=h).json()
        assert [f["rule_id"] for f in body["decision"]["fired"]] == ["R3", "G1"]

        la = {"lat_min": 33.3, "lat_max": 34.3, "lon_min": -118.6, "lon_max": -117.6, "limit": 1}
        latest_la = c.get("/v1/readings/latest", params=la, headers=h).json()["readings"][0]
        assert (latest_la["reading_id"], latest_la["timestamp"]) == (31759, "2024-08-16T06:00:00")

        key = {"X-API-Key": real_settings.RULE_API_KEY.get_secret_value()}
        scan = c.post("/v1/scan", json={"examples": 3}, headers=key).json()
        assert scan["readings_checked"] == TOTAL
        assert scan["rule_counts"] == EXPECTED_RULE_COUNTS
        assert scan["outcome_counts"] == EXPECTED_OUTCOMES
        assert [e["reading"]["reading_id"] for e in scan["examples"]] == [32065, 32064, 32063]

        assert c.get("/v1/readings/99999999", headers=h).status_code == 404
