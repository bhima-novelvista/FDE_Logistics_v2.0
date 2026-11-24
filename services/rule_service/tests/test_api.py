"""The HTTP API: status codes, JSON contracts, logins and roles, errors, audit rows, request IDs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi.testclient import TestClient

from conftest import API_KEY, JWT_SECRET, PASSWORDS, FakeRepository, login, make_settings
from app.config import DEFAULT_RULES_FILE
from app.main import create_app

PROBLEM = "application/problem+json"


# ---------------------------------------------------------------- health
def test_health_and_standard_headers(client: TestClient) -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "service": "rule-service", "version": "2.0.0"}
    assert len(r.headers["X-Request-ID"]) == 32
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["Cache-Control"] == "no-store"
    assert float(r.headers["X-Process-Time-Ms"]) >= 0


def test_ready_ok_and_503_when_database_down(client: TestClient, repo: FakeRepository) -> None:
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.json() == {"status": "ready", "database": "ok", "rules_version": "2.4", "readings_in_view": 5}
    repo.db_down = True
    r = client.get("/ready")
    assert r.status_code == 503
    assert r.headers["content-type"] == PROBLEM
    assert r.headers["Retry-After"] == "10"
    body = r.json()
    assert body["title"] == "Database unavailable"
    assert body["request_id"] == r.headers["X-Request-ID"]


# ---------------------------------------------------------------- login (JWT)
def test_login_each_user_gets_a_signed_token_with_role(client: TestClient) -> None:
    for user in ("dispatcher", "supervisor", "admin"):
        r = client.post("/v1/auth/token", data={"username": user, "password": PASSWORDS[user]})
        assert r.status_code == 200
        body = r.json()
        assert body["token_type"] == "bearer" and body["role"] == user and body["expires_in"] == 1800
        claims = jwt.decode(body["access_token"], JWT_SECRET, algorithms=["HS256"], issuer="fde-rule-service")
        assert claims["sub"] == user and claims["role"] == user


def test_login_wrong_password_unknown_user_and_missing_fields(client: TestClient) -> None:
    for data in ({"username": "dispatcher", "password": "wrong"}, {"username": "nobody", "password": "x"}):
        r = client.post("/v1/auth/token", data=data)
        assert r.status_code == 401
        assert r.headers["WWW-Authenticate"] == "Bearer"
        assert r.json()["detail"] == "Wrong user name or password."
    r = client.post("/v1/auth/token", data={"username": "dispatcher"})
    assert r.status_code == 422
    assert r.json()["errors"] == [{"where": "body.password", "problem": "Field required"}]


def test_validation_errors_never_echo_the_submitted_values(client: TestClient) -> None:
    r = client.post("/v1/auth/token", data={"username": "", "password": "Secret_typed_123"})
    assert "Secret_typed_123" not in r.text


def test_me_shows_the_caller(client: TestClient) -> None:
    r = client.get("/v1/auth/me", headers=login(client, "supervisor"))
    assert r.status_code == 200
    body = r.json()
    assert body["caller"] == "supervisor" and body["role"] == "supervisor" and body["auth_method"] == "jwt"
    r = client.get("/v1/auth/me", headers={"X-API-Key": API_KEY})
    assert r.json()["role"] == "service" and r.json()["auth_method"] == "api_key"


def test_missing_bad_expired_and_forged_tokens_are_refused(client: TestClient) -> None:
    assert client.get("/v1/rules").status_code == 401
    assert client.get("/v1/rules", headers={"Authorization": "Bearer not.a.token"}).status_code == 401
    assert client.get("/v1/rules", headers={"X-API-Key": "wrong"}).status_code == 401

    now = datetime.now(timezone.utc)
    base = {"sub": "dispatcher", "role": "dispatcher", "iss": "fde-rule-service", "iat": now}
    expired = jwt.encode({**base, "exp": now - timedelta(minutes=1)}, JWT_SECRET, algorithm="HS256")
    r = client.get("/v1/rules", headers={"Authorization": f"Bearer {expired}"})
    assert r.status_code == 401 and "expired" in r.json()["detail"]

    # a token someone made with another key and promoted to admin
    forged = jwt.encode({**base, "role": "admin", "exp": now + timedelta(minutes=5)}, "x" * 64, algorithm="HS256")
    assert client.post("/v1/rules/reload", headers={"Authorization": f"Bearer {forged}"}).status_code == 401

    # the "none" algorithm (no signature) is never accepted
    unsigned = jwt.encode({**base, "exp": now + timedelta(minutes=5)}, None, algorithm="none")
    assert client.get("/v1/rules", headers={"Authorization": f"Bearer {unsigned}"}).status_code == 401


# ---------------------------------------------------------------- rules
def test_rules_list(client: TestClient) -> None:
    r = client.get("/v1/rules", headers=login(client, "dispatcher"))
    assert r.status_code == 200
    body = r.json()
    assert body["rules_version"] == "2.4"
    assert [x["rule_id"] for x in body["rules"]] == ["R1", "R2", "R3", "R4", "G1"]
    assert body["rules"][1]["conditions"] == [
        {"field": "temperature_c", "op": ">", "value": 4.0},
        {"field": "eta_variation_hours", "op": ">", "value": 1.0},
    ]


def test_reload_rules_admin_only_and_bad_file_keeps_old_rules(tmp_path: Path) -> None:
    rules_file = tmp_path / "rules.yaml"
    rules_file.write_text(DEFAULT_RULES_FILE.read_text(encoding="utf-8"), encoding="utf-8")
    repo = FakeRepository()
    app = create_app(make_settings(RULES_FILE=rules_file), repository=repo)
    with TestClient(app) as c:
        assert c.post("/v1/rules/reload", headers=login(c, "supervisor")).status_code == 403

        # change a threshold and reload: the new rule is used at once
        rules_file.write_text(rules_file.read_text().replace('version: "2.4"', 'version: "2.5"')
                              .replace("value: 7.0 }", "value: 8.0 }"), encoding="utf-8")
        admin = login(c, "admin")
        r = c.post("/v1/rules/reload", headers=admin)
        assert r.status_code == 200
        assert (r.json()["previous_version"], r.json()["rules_version"]) == ("2.4", "2.5")
        d = c.get("/v1/readings/31759/decision", headers=admin).json()["decision"]
        assert [f["rule_id"] for f in d["fired"]] == ["G1"]        # 7.11 is no longer above the new 8.0

        # a broken file is refused and version 2.5 stays active
        rules_file.write_text("sop: {name: x}\nrules: []\n", encoding="utf-8")
        r = c.post("/v1/rules/reload", headers=admin)
        assert r.status_code == 422 and r.headers["content-type"] == PROBLEM
        assert "version 2.5" in r.json()["detail"]
        assert c.get("/v1/rules", headers=admin).json()["rules_version"] == "2.5"
    outcomes = [row["outcome"] for row in repo.audit]
    assert outcomes == ["RULES_RELOADED", "REVIEW", "RULES_REJECTED"]


# ---------------------------------------------------------------- readings and decisions
def test_decision_for_latest_reading_and_audit_row(client: TestClient, repo: FakeRepository) -> None:
    r = client.get("/v1/readings/32065/decision", headers=login(client, "dispatcher"))
    assert r.status_code == 200
    body = r.json()
    assert body["reading"]["reading_id"] == 32065
    assert body["decision"]["outcome"] == "ACTION_REQUIRED"
    assert [f["rule_id"] for f in body["decision"]["fired"]] == ["R1", "R2", "R3", "R4"]
    assert body["audit_logged"] is True
    row = repo.audit[-1]
    assert row["caller"] == "dispatcher" and row["auth_method"] == "jwt"
    assert row["endpoint"] == "GET /v1/readings/{reading_id}/decision"
    assert row["reading_id"] == 32065 and row["fired_rules"] == "R1,R2,R3,R4"
    assert row["request_id"] == body["request_id"] == r.headers["X-Request-ID"]


def test_decision_outcomes_review_and_no_action(client: TestClient) -> None:
    h = {"X-API-Key": API_KEY}
    assert client.get("/v1/readings/102/decision", headers=h).json()["decision"]["outcome"] == "REVIEW"
    assert client.get("/v1/readings/101/decision", headers=h).json()["decision"]["outcome"] == "NO_ACTION"


def test_unknown_and_invalid_reading_ids(client: TestClient) -> None:
    h = login(client, "dispatcher")
    r = client.get("/v1/readings/99999999", headers=h)
    assert r.status_code == 404 and r.headers["content-type"] == PROBLEM
    assert r.json()["detail"] == "There is no reading with ID 99999999."
    assert client.get("/v1/readings/99999999/decision", headers=h).status_code == 404
    assert client.get("/v1/readings/0", headers=h).status_code == 422
    assert client.get("/v1/readings/abc", headers=h).status_code == 422


def test_answer_still_returned_when_audit_write_fails(client: TestClient, repo: FakeRepository) -> None:
    repo.audit_down = True
    r = client.get("/v1/readings/32065/decision", headers={"X-API-Key": API_KEY})
    assert r.status_code == 200 and r.json()["audit_logged"] is False


def test_database_down_gives_503_problem(client: TestClient, repo: FakeRepository) -> None:
    h = login(client, "dispatcher")
    repo.db_down = True
    r = client.get("/v1/readings/32065/decision", headers=h)
    assert r.status_code == 503 and r.json()["title"] == "Database unavailable"


def test_latest_with_and_without_area(client: TestClient) -> None:
    h = login(client, "dispatcher")
    r = client.get("/v1/readings/latest", params={"limit": 2}, headers=h)
    assert [x["reading_id"] for x in r.json()["readings"]] == [32065, 32064]
    la = {"lat_min": 33.3, "lat_max": 34.3, "lon_min": -118.6, "lon_max": -117.6, "limit": 5}
    r = client.get("/v1/readings/latest", params=la, headers=h)
    assert [x["reading_id"] for x in r.json()["readings"]] == [31759, 102]
    assert client.get("/v1/readings/latest", params={"limit": 0}, headers=h).status_code == 422
    assert client.get("/v1/readings/latest", params={"limit": 51}, headers=h).status_code == 422
    r = client.get("/v1/readings/latest", params={"lat_min": 33}, headers=h)
    assert r.status_code == 422 and "all four" in r.json()["detail"]


# ---------------------------------------------------------------- evaluate
def test_evaluate_a_reading_from_the_body(client: TestClient, repo: FakeRepository) -> None:
    reading = {"temperature_c": 5.2, "eta_variation_hours": 1.5, "port_congestion_level": 4.0,
               "delay_probability": 0.4, "risk_classification": "Moderate Risk"}
    r = client.post("/v1/evaluate", json=reading, headers=login(client, "dispatcher"))
    assert r.status_code == 200
    d = r.json()["decision"]
    assert [f["rule_id"] for f in d["fired"]] == ["R1", "R2"]
    assert r.json()["reading"] is None
    assert repo.audit[-1]["endpoint"] == "POST /v1/evaluate" and repo.audit[-1]["reading_id"] is None


def test_evaluate_refuses_invalid_bodies(client: TestClient) -> None:
    h = login(client, "dispatcher")
    bad = {"temperature_c": 5, "eta_variation_hours": 2, "port_congestion_level": 3,
           "delay_probability": 1.5, "risk_classification": "Very High", "colour": "red"}
    r = client.post("/v1/evaluate", json=bad, headers=h)
    assert r.status_code == 422 and r.headers["content-type"] == PROBLEM
    wheres = [e["where"] for e in r.json()["errors"]]
    assert wheres == ["body.delay_probability", "body.risk_classification", "body.colour"]
    r = client.post("/v1/evaluate", json={}, headers=h)
    assert r.status_code == 422 and len(r.json()["errors"]) == 5
    r = client.post("/v1/evaluate", content="not json", headers={**h, "Content-Type": "application/json"})
    assert r.status_code == 422


# ---------------------------------------------------------------- scan
def test_scan_roles_counts_and_validation(client: TestClient, repo: FakeRepository) -> None:
    assert client.post("/v1/scan", json={}, headers=login(client, "dispatcher")).status_code == 403
    r = client.post("/v1/scan", json={"examples": 1}, headers=login(client, "supervisor"))
    assert r.status_code == 200
    body = r.json()
    assert body["readings_checked"] == 5
    assert body["rule_counts"] == {"R1": 1, "R2": 1, "R3": 3, "R4": 1, "G1": 3}
    assert body["outcome_counts"] == {"ACTION_REQUIRED": 3, "REVIEW": 1, "NO_ACTION": 1}
    assert [e["reading"]["reading_id"] for e in body["examples"]] == [32065]
    assert repo.audit[-1]["outcome"] == "SCAN"
    r = client.post("/v1/scan", headers={"X-API-Key": API_KEY})            # no body at all = everything
    assert r.status_code == 200 and r.json()["readings_checked"] == 5
    bad = {"from_time": "2024-08-29T00:00:00", "to_time": "2024-08-01T00:00:00"}
    assert client.post("/v1/scan", json=bad, headers={"X-API-Key": API_KEY}).status_code == 422
    bad_area = {"area": {"lat_min": 34, "lat_max": 33, "lon_min": -118, "lon_max": -117}}
    assert client.post("/v1/scan", json=bad_area, headers={"X-API-Key": API_KEY}).status_code == 422


# ---------------------------------------------------------------- general
def test_request_id_is_reused_only_when_safe(client: TestClient) -> None:
    assert client.get("/health", headers={"X-Request-ID": "dispatch-0001"}).headers["X-Request-ID"] == "dispatch-0001"
    unsafe = client.get("/health", headers={"X-Request-ID": "bad id with spaces"}).headers["X-Request-ID"]
    assert unsafe != "bad id with spaces" and len(unsafe) == 32


def test_unknown_endpoint_and_wrong_method(client: TestClient) -> None:
    r = client.get("/v1/nothing")
    assert r.status_code == 404 and r.headers["content-type"] == PROBLEM
    r = client.delete("/v1/rules", headers={"X-API-Key": API_KEY})
    assert r.status_code == 405


def test_openapi_lists_every_endpoint_and_both_logins(client: TestClient) -> None:
    spec = client.get("/openapi.json").json()
    assert set(spec["components"]["securitySchemes"]) == {"Login (JWT)", "API key"}
    assert set(spec["paths"]) == {
        "/health", "/ready", "/v1/auth/token", "/v1/auth/me", "/v1/rules", "/v1/rules/reload",
        "/v1/readings/latest", "/v1/readings/{reading_id}", "/v1/readings/{reading_id}/decision",
        "/v1/evaluate", "/v1/scan",
    }
    assert client.get("/docs").status_code == 200 and client.get("/redoc").status_code == 200
