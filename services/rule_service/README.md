# Rule service (v2.0 Engineering Core, Step 4)

A small FastAPI service that applies the company's **Cold-Chain Incident SOP (v2.4)** to the
legacy fleet readings and answers over a JSON API. No AI: the rules are written in a YAML
file and checked by a small, tested Python engine.

The step-by-step guide (Windows first, then macOS) is
[`docs/04_Rule_Service_API_Guide.md`](../../docs/04_Rule_Service_API_Guide.md). The API contract is in
[`docs/api/`](../../docs/api/).

## How it fits together

```text
 people (Swagger, PowerShell, curl)          machine clients (examples/rule_client.py, later the v3.0 AI)
        |  JWT  (POST /v1/auth/token)                 |  X-API-Key
        +------------------------+--------------------+
                                 v
                  rule service  (FastAPI, 127.0.0.1:8101, Docker container fde-rule-service)
                  - checks the login and the role
                  - checks every request body (Pydantic)
                  - applies app/rules/sop_rules_v2.4.yaml  (rule engine)
                  - writes an audit row for every decision
                                 |  login rule_svc (Step 3): SELECT view + INSERT audit only
                                 v
        fde_views.vw_fleet_readings  ->  legacy_fleet.TBL_SC_FLEET_HIST_RAW (unchanged)
        fde_audit.RuleDecisionLog    (append-only)
```

## Folder

| Path | What it is |
|---|---|
| `app/main.py` | Builds the app (`create_app`), API description, OpenAPI |
| `app/config.py` | Settings from the environment / project `.env` (secrets never printed) |
| `app/rules/sop_rules_v2.4.yaml` | **The SOP rules, as data** |
| `app/rules/engine.py` | Loads and checks the rules file; evaluates readings; turns rules into SQL |
| `app/repository.py` | All database access (async, parameterised, with time limits) |
| `app/security.py` | JWT for people, API key for machines, roles |
| `app/errors.py` | One error format (RFC 9457 problem details) |
| `app/middleware.py`, `app/request_context.py` | Request ID, timing, security headers, one log line per request |
| `app/audit.py` | Writes audit rows (never blocks the caller) |
| `app/schemas.py` | JSON contracts (Pydantic models) |
| `app/routers/` | The endpoints: health, auth, rules, readings, evaluate, scan |
| `tests/` | 53 unit and API tests (no database needed) + 2 integration tests (`-m integration`) |
| `examples/rule_client.py` | A machine client: API key, timeouts, retries, request ID |
| `scripts/export_openapi.py` | Writes the OpenAPI file to `docs/api/openapi.json` |
| `Dockerfile`, `docker-compose.yml` | The container, joined to the legacy MySQL network |
| `requirements.txt`, `requirements-dev.txt` | Exact package versions |

## Endpoints

| Method and path | Who | What |
|---|---|---|
| `GET /health` | anyone | Is the service running? |
| `GET /ready` | anyone | Rules loaded and database reachable? (503 if not) |
| `POST /v1/auth/token` | anyone | Log in (form: username, password) and get a JWT |
| `GET /v1/auth/me` | logged in | Who am I? |
| `GET /v1/rules` | logged in | The active rules |
| `POST /v1/rules/reload` | admin | Reload the rules file (refused with 422 if it has mistakes) |
| `GET /v1/readings/latest` | logged in | Newest readings, optionally in a lat/long box |
| `GET /v1/readings/{id}` | logged in | One reading |
| `GET /v1/readings/{id}/decision` | dispatcher, supervisor, admin, service | SOP decision for one reading (audited) |
| `POST /v1/evaluate` | logged in | SOP decision for a reading in the body (audited) |
| `POST /v1/scan` | supervisor, admin, service | Rule counts over a window or area (audited) |

## Quick commands (from the project folder)

Windows (PowerShell):

```powershell
.\venv_services\Scripts\python.exe -m pytest services\rule_service
docker compose -f services/rule_service/docker-compose.yml --env-file .env up -d --build --wait
.\venv_services\Scripts\python.exe services\rule_service\examples\rule_client.py decision 32065
```

macOS (Terminal):

```bash
./venv_services/bin/python -m pytest services/rule_service
docker compose -f services/rule_service/docker-compose.yml --env-file .env up -d --build --wait
./venv_services/bin/python services/rule_service/examples/rule_client.py decision 32065
```

Swagger UI: <http://127.0.0.1:8101/docs> · ReDoc: <http://127.0.0.1:8101/redoc>
