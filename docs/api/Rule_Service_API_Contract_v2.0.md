# Rule Service API Contract, v2.0

**Service:** Harborline Cold-Chain Rule Service 2.0.0 (FDE_PB_Sol v2.0 Engineering Core)
**Machine-readable contract:** [`openapi.json`](openapi.json) (OpenAPI 3.1). Interactive copies are at `/docs` (Swagger UI) and `/redoc` while the service runs.
**Date:** 24 Nov 2026 · Harborline and its people are fictional; the readings are a real public dataset.

This document is the human-readable contract: what every endpoint expects and returns. All examples are **captured** from the service running against the real data, unless marked *illustrative*. Request IDs and times differ on every call.

---

## 1. Conventions (apply to every endpoint)

| Topic | Rule |
|---|---|
| Base URL | `http://127.0.0.1:8101` (port `RULE_API_PORT`). Local only. |
| Versioning | Business endpoints live under `/v1/`. A change that breaks callers gets `/v2/`; adding optional fields does not. |
| Format | Requests and responses are JSON (`application/json`, UTF-8). The only exception is the login, a form (`application/x-www-form-urlencoded`), as OAuth2 requires. |
| Names | JSON fields are `snake_case`. Times are ISO 8601 in UTC (`2024-08-29T00:00:00`); the readings have no time zone, and they are UTC. |
| Numbers | Readings keep full precision (for example `18.79651453879272`). Evidence strings round to 4 significant digits. |
| Unknown fields | Request bodies with fields that are not in the contract are refused (422). |
| Login | **People:** `Authorization: Bearer <JWT>` from `POST /v1/auth/token`. **Programs:** `X-API-Key: <RULE_API_KEY>`. If both are sent, the JWT is used. |
| Roles | `dispatcher`, `supervisor`, `admin` (people); `service` (API key). See each endpoint. |
| Request ID | Every response has `X-Request-ID`. Send your own (8–64 characters: letters, digits, `.`, `_`, `-`) to have it reused. It also appears in error bodies and audit rows. |
| Other headers | `X-Process-Time-Ms` (server time), `Cache-Control: no-store`, `X-Content-Type-Options: nosniff` |
| Errors | `application/problem+json` ([RFC 9457](https://www.rfc-editor.org/rfc/rfc9457)); see section 2 |
| Audit | Decisions, scans and rules reloads write one row to `fde_audit.RuleDecisionLog`. The answer says `"audit_logged": true/false`. |
| Idempotency | All `GET` endpoints are safe to repeat. `POST /v1/evaluate` and `POST /v1/scan` change no data, but each call writes one audit row. |

## 2. Errors

Every error body has the same shape:

```json
{
  "type": "https://fde-pb-sol.local/problems/not-found",
  "title": "Not found",
  "status": 404,
  "detail": "There is no reading with ID 99999999.",
  "instance": "/v1/readings/99999999",
  "request_id": "3dab0fa0587e486fb7ae060f4068f3fb"
}
```

`errors` is added for 422 only:

```json
"errors": [{"where": "body.delay_probability", "problem": "Input should be less than or equal to 1"}]
```

Submitted values are never echoed back.

| Status | `type` ends with | `title` | When |
|---|---|---|---|
| 401 | `unauthorized` | Not logged in | No, wrong, expired or forged JWT; wrong API key; wrong user name or password. Has `WWW-Authenticate: Bearer`. |
| 403 | `forbidden` | Not allowed | Logged in, but the role may not use this endpoint |
| 404 | `not-found` | Not found | No reading with this ID, or no such endpoint |
| 405 | `method-not-allowed` | Method not allowed | For example `DELETE /v1/rules` |
| 422 | `validation-error` | Invalid input | Missing, wrong-type, out-of-range or extra values |
| 422 | `rules-file-invalid` | Rules file refused | `POST /v1/rules/reload` with a broken rules file; the old rules stay active |
| 500 | `internal-error` | Internal error | An unexpected fault (quote the `request_id`) |
| 503 | `database-unavailable` | Database unavailable | MySQL unreachable or too slow. Has `Retry-After: 10`. |
| 503 | `service-unavailable` | Service unavailable | Still starting, or a time limit was reached. Has `Retry-After: 10`. |

## 3. Data models

**Reading** (response)

| Field | Type | Meaning |
|---|---|---|
| `reading_id` | integer | Row number in the legacy table (not a truck or shipment ID) |
| `timestamp` | date-time | Reading time, UTC |
| `latitude`, `longitude` | number | Position |
| `temperature_c` | number | Cargo temperature, °C |
| `eta_variation_hours` | number | Hours late (+) or early (−) |
| `port_congestion_level` | number | 0 to 10 |
| `delay_probability` | number | 0 to 1 |
| `risk_classification` | string | `High Risk`, `Moderate Risk` or `Low Risk` |
| `cargo_condition_code`, `route_risk_index` | number | Further indicators (not used by the rules) |

**ReadingIn** (request body of `/v1/evaluate`)

| Field | Required | Allowed |
|---|---|---|
| `temperature_c` | yes | −50 to 80 |
| `eta_variation_hours` | yes | −48 to 240 |
| `port_congestion_level` | yes | 0 to 10 |
| `delay_probability` | yes | 0 to 1 |
| `risk_classification` | yes | `High Risk`, `Moderate Risk`, `Low Risk` |
| `cargo_condition_code` | no | 0 to 1 |
| `route_risk_index` | no | 0 to 10 |
| `latitude` | no | −90 to 90 |
| `longitude` | no | −180 to 180 |

**Decision**

| Field | Meaning |
|---|---|
| `outcome` | `ACTION_REQUIRED` (at least one SOP rule applies), `REVIEW` (only an SOP gap applies), `NO_ACTION` (nothing applies) |
| `highest_severity` | `critical`, `high`, `medium`, `review` or `none` |
| `summary` | One sentence for a person |
| `fired[]` | One entry per rule or gap that applies, in rules-file order: `rule_id`, `kind` (`rule` / `gap`), `name`, `severity`, `action`, `sop_section`, `evidence[]` (the values that made it fire), `note` |
| `rules_version`, `sop_name` | Which rules were used, for example `2.4` and `Cold-Chain Incident SOP` |
| `evaluated_at_utc` | When the decision was made |

**The rules (version 2.4)**

| ID | Kind | Severity | Condition | Action |
|---|---|---|---|---|
| R1 | rule | critical | `temperature_c > 4.0` | Contact the driver to restart the auxiliary cooling unit |
| R2 | rule | critical | `temperature_c > 4.0` and `eta_variation_hours > 1.0` | Divert to the nearest emergency cold-storage facility |
| R3 | rule | high | `port_congestion_level > 7.0` (applied to all readings; assumption stated in the answer) | Divert to the Inland Empire Overflow Depot (San Bernardino) |
| R4 | rule | high | `risk_classification == "High Risk"` and `delay_probability > 0.65` | Escalate to the Tier 2 Logistics Manager |
| G1 | gap | review | `temperature_c < 0.0` | The SOP has no rule; refer to the shift supervisor |

Thresholds are strict: a value exactly at 4.0, 1.0, 7.0 or 0.65 does not fire a rule. Text comparisons ignore upper and lower case.

---

## 4. Endpoints

### 4.1 `GET /health`: is the service running?

- **Login:** none.
- **Response 200:** `{"status":"ok","service":"rule-service","version":"2.0.0"}`.
- Does not touch the database. Docker uses it as the container health check.

### 4.2 `GET /ready`: can the service do its work?

- **Login:** none.
- **Response 200:** `{"status":"ready","database":"ok","rules_version":"2.4","readings_in_view":32065}`.
- **Errors:** 503 `database-unavailable`.

### 4.3 `POST /v1/auth/token`: log in

- **Login:** none.
- **Body (form):** `username`, `password`. The users are `dispatcher`, `supervisor` and `admin`.
- **Response 200** (*illustrative* token):

  ```json
  {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", "token_type": "bearer", "expires_in": 1800, "role": "dispatcher"}
  ```

- **The token:** a JWT signed with HS256 (key `JWT_SECRET`). Its claims are `sub` (user), `role`, `iss` = `fde-rule-service`, `iat` and `exp`. Tokens signed with another key, with another algorithm, or with `alg: none` are refused.
- **Errors:**
  - 401 `Wrong user name or password.` (answered after a 0.5 s delay, to slow down guessing);
  - 422 when a field is missing.

### 4.4 `GET /v1/auth/me`: who am I?

- **Login:** JWT or API key.
- **Response 200:**
  - JWT: `{"caller":"dispatcher","role":"dispatcher","auth_method":"jwt","token_expires_at_utc":"2026-11-24T16:37:59Z"}`;
  - API key: `{"caller":"api-client","role":"service","auth_method":"api_key","token_expires_at_utc":null}`.
- **Errors:** 401.

### 4.5 `GET /v1/rules`: the active rules

- **Login:** any role.
- **Response 200:** `sop_name`, `rules_version`, `effective`, `source`, `assumptions[]`, `loaded_at_utc`, and `rules[]`. Each rule has `rule_id`, `kind`, `name`, `match` (`all`/`any`), `conditions[]` (`field`, `op`, `value`), `severity`, `action`, `sop_section` and `note`.
- **Errors:** 401.

### 4.6 `POST /v1/rules/reload`: reload the rules file

- **Login:** admin.
- **Body:** none.
- **Response 200:**

  ```json
  {"request_id":"b58f1dc4…","message":"Rules reloaded.","previous_version":"2.4","rules_version":"2.4-test","rule_count":4,"gap_count":1,"audit_logged":true}
  ```

- **Errors:**
  - 401;
  - 403 for other roles;
  - 422 `rules-file-invalid`, with one `errors` entry per problem, for example `rules.0.when.all.0.field: Value error, unknown field 'temprature_c'; …`. The old rules stay active.
- **Audit:** `RULES_RELOADED` or `RULES_REJECTED`.

### 4.7 `GET /v1/readings/latest`: the newest readings

- **Login:** any role.
- **Query:**
  - `limit`: 1–50, default 5;
  - optionally all four of `lat_min`, `lat_max`, `lon_min`, `lon_max`.
- **Response 200:** `{"count": 1, "readings": [Reading, …]}`, newest first.

  Example: `limit=1&lat_min=33.3&lat_max=34.3&lon_min=-118.6&lon_max=-117.6` returns reading **31759** (2024-08-16 06:00, −9.98 °C).
- **Errors:**
  - 401;
  - 422 (`limit` out of range; only some of the four box values; min greater than max);
  - 503.

### 4.8 `GET /v1/readings/{reading_id}`: one reading

- **Login:** any role.
- **Path:** `reading_id`, an integer of at least 1.
- **Response 200:** one Reading.
- **Errors:**
  - 401;
  - 404 `There is no reading with ID 99999999.`;
  - 422 (for example `0` or `abc`);
  - 503.

### 4.9 `GET /v1/readings/{reading_id}/decision`: the SOP decision for a stored reading

- **Login:** dispatcher, supervisor, admin or service.
- **Response 200:** `{"request_id", "reading": Reading, "decision": Decision, "audit_logged"}`. Captured for reading **31759**, shortened:

  ```json
  {
    "reading": {"reading_id": 31759, "timestamp": "2024-08-16T06:00:00", "temperature_c": -9.97988482187644,
                "eta_variation_hours": -1.9993087670158607, "port_congestion_level": 7.109516319931892,
                "delay_probability": 0.29363484379262006, "risk_classification": "High Risk", "...": "..."},
    "decision": {
      "outcome": "ACTION_REQUIRED", "highest_severity": "high",
      "summary": "1 SOP rule(s) apply: R3. Also outside the SOP: G1 (no SOP rule; refer to the shift supervisor).",
      "fired": [
        {"rule_id": "R3", "kind": "rule", "severity": "high",
         "action": "Suspend standard routing and divert to the Inland Empire Overflow Depot (San Bernardino).",
         "sop_section": "2. Port Congestion (section number inferred)",
         "evidence": ["port_congestion_level = 7.11 > 7.0"],
         "note": "Assumes the port congestion level is the destination port's level (see assumptions)."},
        {"rule_id": "G1", "kind": "gap", "severity": "review",
         "action": "The SOP has no rule for readings below 0.0 °C. Do not act on the rules alone; refer this reading to the shift supervisor.",
         "evidence": ["temperature_c = -9.98 < 0.0"]}
      ],
      "rules_version": "2.4", "sop_name": "Cold-Chain Incident SOP"
    },
    "audit_logged": true
  }
  ```

  Reading **32065** gives `ACTION_REQUIRED` and `critical`, with R1, R2, R3 and R4.
- **Errors:** 401, 404, 422, 503.
- **Audit:** the outcome, `Reading_ID` and fired rules.

### 4.10 `POST /v1/evaluate`: the SOP decision for a reading you send

- **Login:** any role.
- **Body:** ReadingIn, for example:

  ```json
  {"temperature_c": 6.5, "eta_variation_hours": 2.0, "port_congestion_level": 3.0, "delay_probability": 0.4, "risk_classification": "Moderate Risk"}
  ```

- **Response 200:** `{"request_id", "reading": null, "decision": Decision, "audit_logged"}`. The example above gives `ACTION_REQUIRED`, `critical`, with R1 and R2.
- **Errors:**
  - 401;
  - 422 (for example `delay_probability` 1.4, an unknown risk class, extra fields, an empty body: one entry per problem).
- **Audit:** the outcome, with `Reading_ID` NULL; the input is stored in `Detail_JSON`.

### 4.11 `POST /v1/scan`: rule counts over many readings

- **Login:** supervisor, admin or service.
- **Body (all optional):**
  - `from_time`, `to_time` (date-time, inclusive);
  - `area` with `lat_min`, `lat_max`, `lon_min`, `lon_max`;
  - `examples`: 0–50, default 5.

  An empty body, or no body, means all readings.
- **Response 200:** captured with `{"examples": 3}`, examples shortened:

  ```json
  {
    "request_id": "…", "rules_version": "2.4", "readings_checked": 32065,
    "rule_counts": {"R1": 8674, "R2": 6621, "R3": 19566, "R4": 15440, "G1": 21817},
    "outcome_counts": {"ACTION_REQUIRED": 27245, "REVIEW": 4524, "NO_ACTION": 296},
    "examples": [{"reading": {"reading_id": 32065, "...": "..."}, "decision": {"outcome": "ACTION_REQUIRED", "...": "..."}}, "…"],
    "audit_logged": true
  }
  ```

  - `rule_counts` is counted inside MySQL from the same YAML rules, turned into parameterised SQL.
  - `examples` are the newest readings that need action, evaluated in full by the engine.
  - Other captured scans:
    - 2024-08-28 to 2024-08-29: 25 readings; R1 5, R2 2, R3 16, R4 16, G1 19.
    - Los Angeles box (33.3–34.3, −118.6 to −117.6): 35 readings; R1 6, R2 6, R3 29, R4 18, G1 28.
- **Errors:**
  - 401;
  - 403 for dispatchers;
  - 422 (`from_time` after `to_time`; min greater than max in `area`; `examples` out of range);
  - 503.
- **Audit:** `SCAN`, with the request and the counts.

---

## 5. Limits and non-goals of v2.0

- Local use only, over plain HTTP on `127.0.0.1`. HTTPS, an identity provider, rate limits and several copies are pillar 04 (Deploy & Operate).
- The three API users and their passwords come from `.env` (demo set-up).
- The data has no truck or shipment ID, so a reading is addressed by its row number (`reading_id`).
- The rules are derived from HLD v1.2 §8.2. The original SOP file was not available, and the R3 section number is inferred.
