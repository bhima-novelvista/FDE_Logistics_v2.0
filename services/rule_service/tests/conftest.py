"""
Shared test set-up.

Unit and API tests use a FakeRepository (readings in memory, audit rows in
a list), so they run in a second without MySQL. The integration tests in
test_integration_mysql.py use the real database (run them with -m integration).
"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))

from app.config import DEFAULT_RULES_FILE, Settings  # noqa: E402
from app.main import create_app  # noqa: E402
from app.rules.engine import RuleSet, load_rules  # noqa: E402

PASSWORDS = {"dispatcher": "Disp_pw_123", "supervisor": "Super_pw_123", "admin": "Admin_pw_123"}
API_KEY = "k" * 48
JWT_SECRET = "t" * 64

# Three real readings from the data (exact values), plus two made-up ones.
SAMPLE_READINGS: dict[int, dict[str, Any]] = {
    32065: dict(reading_id=32065, timestamp=datetime(2024, 8, 29, 0, 0), latitude=38.57648248950679,
                longitude=-94.57954243970406, temperature_c=18.79651453879272, eta_variation_hours=4.068439877608897,
                port_congestion_level=7.693642636880453, delay_probability=0.9992302873270055,
                risk_classification="High Risk", cargo_condition_code=0.8765292360980542,
                route_risk_index=2.1126554320955155),
    32064: dict(reading_id=32064, timestamp=datetime(2024, 8, 28, 23, 0), latitude=32.08241012776637,
                longitude=-70.07015390298147, temperature_c=-6.951137131277026, eta_variation_hours=4.759411000702818,
                port_congestion_level=9.697466737351231, delay_probability=0.5573400961448669,
                risk_classification="High Risk", cargo_condition_code=0.4073768989192114,
                route_risk_index=9.185549476886113),
    31759: dict(reading_id=31759, timestamp=datetime(2024, 8, 16, 6, 0), latitude=33.49930951941184,
                longitude=-117.66700060363502, temperature_c=-9.97988482187644, eta_variation_hours=-1.9993087670158607,
                port_congestion_level=7.109516319931892, delay_probability=0.29363484379262006,
                risk_classification="High Risk", cargo_condition_code=0.0004955232961646748,
                route_risk_index=9.888170966569882),
    # made up: inside every SOP limit
    101: dict(reading_id=101, timestamp=datetime(2023, 1, 1, 12, 0), latitude=40.0, longitude=-100.0,
              temperature_c=2.5, eta_variation_hours=0.5, port_congestion_level=3.0, delay_probability=0.2,
              risk_classification="Low Risk", cargo_condition_code=0.5, route_risk_index=1.0),
    # made up: below 0 °C only (an SOP gap, nothing else)
    102: dict(reading_id=102, timestamp=datetime(2023, 1, 1, 13, 0), latitude=34.0, longitude=-118.0,
              temperature_c=-3.0, eta_variation_hours=0.0, port_congestion_level=2.0, delay_probability=0.9,
              risk_classification="Moderate Risk", cargo_condition_code=0.5, route_risk_index=1.0),
}


class FakeRepository:
    """Same methods as ReadingRepository, but in memory."""

    def __init__(self, readings: dict[int, dict[str, Any]] | None = None):
        self.readings = {k: dict(v) for k, v in (readings or SAMPLE_READINGS).items()}
        self.audit: list[dict[str, Any]] = []
        self.db_down = False
        self.audit_down = False

    def _check(self) -> None:
        if self.db_down:
            raise OperationalError("SELECT 1", {}, ConnectionError("database is down (test)"))

    async def close(self) -> None:
        pass

    async def count_readings(self) -> int:
        self._check()
        return len(self.readings)

    async def get_reading(self, reading_id: int):
        self._check()
        row = self.readings.get(reading_id)
        return dict(row) if row else None

    def _filtered(self, from_time=None, to_time=None, area=None):
        rows = list(self.readings.values())
        if from_time:
            rows = [r for r in rows if r["timestamp"] >= from_time.replace(tzinfo=None)]
        if to_time:
            rows = [r for r in rows if r["timestamp"] <= to_time.replace(tzinfo=None)]
        if area:
            rows = [r for r in rows if area.lat_min <= r["latitude"] <= area.lat_max
                    and area.lon_min <= r["longitude"] <= area.lon_max]
        return sorted(rows, key=lambda r: (r["timestamp"], r["reading_id"]), reverse=True)

    async def latest(self, limit: int, area=None):
        self._check()
        return [dict(r) for r in self._filtered(area=area)[:limit]]

    async def scan(self, ruleset: RuleSet, from_time, to_time, area, examples: int):
        self._check()
        rows = self._filtered(from_time, to_time, area)
        counts = {r.id: 0 for _, r in ruleset.all_defs()}
        outcomes = {"ACTION_REQUIRED": 0, "REVIEW": 0, "NO_ACTION": 0}
        need_action = []
        for row in rows:
            d = ruleset.evaluate(row)
            for f in d.fired:
                counts[f.rule_id] += 1
            outcomes[d.outcome] += 1
            if d.outcome == "ACTION_REQUIRED":
                need_action.append(dict(row))
        return len(rows), counts, outcomes, need_action[:examples]

    async def write_audit(self, row: dict[str, Any]) -> None:
        if self.audit_down or self.db_down:
            raise OperationalError("INSERT", {}, ConnectionError("audit table unreachable (test)"))
        self.audit.append(dict(row))


def make_settings(**overrides: Any) -> Settings:
    values: dict[str, Any] = dict(
        _env_file=None,
        RULE_SVC_PASSWORD="not-used-in-unit-tests",
        JWT_SECRET=JWT_SECRET,
        RULE_API_KEY=API_KEY,
        API_USER_DISPATCHER_PASSWORD=PASSWORDS["dispatcher"],
        API_USER_SUPERVISOR_PASSWORD=PASSWORDS["supervisor"],
        API_USER_ADMIN_PASSWORD=PASSWORDS["admin"],
        LOG_LEVEL="WARNING",
    )
    values.update(overrides)
    return Settings(**values)


@pytest.fixture
def rules() -> RuleSet:
    return load_rules(DEFAULT_RULES_FILE)


@pytest.fixture
def repo() -> FakeRepository:
    return FakeRepository()


@pytest.fixture
def settings() -> Settings:
    return make_settings()


@pytest.fixture
def client(settings: Settings, repo: FakeRepository):
    app = create_app(settings, repository=repo)
    with TestClient(app) as c:
        yield c


def login(client: TestClient, user: str) -> dict[str, str]:
    r = client.post("/v1/auth/token", data={"username": user, "password": PASSWORDS[user]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}
