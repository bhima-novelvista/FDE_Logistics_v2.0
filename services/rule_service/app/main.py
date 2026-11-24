"""
The rule service: FastAPI application.

Start it with the factory (it reads the settings and the rules file first,
and refuses to start if the rules file has mistakes):

    uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8101

Swagger UI: http://127.0.0.1:8101/docs   ReDoc: http://127.0.0.1:8101/redoc
"""
from __future__ import annotations

import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from . import __version__
from .config import Settings, get_settings
from .errors import Problem, install_error_handlers
from .middleware import RequestContextMiddleware
from .repository import ReadingRepository
from .routers import auth, evaluate, health, readings, rules, scan
from .rules.engine import load_rules

DESCRIPTION = """
Applies Harborline's **Cold-Chain Incident SOP (v2.4)** to the legacy fleet readings and returns a
decision a dispatcher can act on: which rules apply, why, what to do, and where the SOP says so.

* Reads the legacy data **only** through the read-only view `fde_views.vw_fleet_readings`
  (database login `rule_svc`; it cannot change data).
* Writes **every decision** to the append-only audit table `fde_audit.RuleDecisionLog`.
* The rules live in a YAML file (`app/rules/sop_rules_v2.4.yaml`); `GET /v1/rules` shows them.

### How to log in here
Click **Authorize** (top right):
* **Login (JWT)**: user name `dispatcher`, `supervisor` or `admin` and the password from your `.env`
  (`API_USER_..._PASSWORD`). Leave *client_id* and *client_secret* empty.
* **API key**: for machine clients; the `RULE_API_KEY` value from `.env`.

| Role | Can do |
|---|---|
| dispatcher | read readings, check readings, get decisions |
| supervisor | the above, plus bulk scans |
| admin | the above, plus reloading the rules file |
| service (API key) | like a supervisor |

Every response carries an `X-Request-ID` header; errors use one format (RFC 9457 problem details).
Harborline and its people are fictional; the readings are a real public dataset.
"""

TAGS = [
    {"name": "Health", "description": "Is the service up and ready?"},
    {"name": "Login", "description": "Get a JWT; see who you are."},
    {"name": "Rules", "description": "The SOP rules the engine applies."},
    {"name": "Readings and decisions", "description": "Readings from the legacy data and SOP decisions."},
    {"name": "Bulk checks", "description": "Rule counts over many readings."},
]


def configure_logging(level: str) -> None:
    logging.Formatter.converter = time.gmtime
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)sZ %(levelname)-7s %(name)s: %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        force=True,
    )


def create_app(settings: Settings | None = None, repository: Any | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.LOG_LEVEL)
    log = logging.getLogger("rule_service")
    rule_set = load_rules(settings.RULES_FILE)   # a bad rules file stops the start here, with the reasons

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if getattr(app.state, "repository", None) is None:
            app.state.repository = ReadingRepository(settings)
        log.info(
            "rule service %s started: rules %s (%d rules, %d gaps) from %s; database %s:%s as %s",
            __version__, rule_set.version, len(rule_set.rules), len(rule_set.gaps), settings.RULES_FILE,
            settings.MYSQL_HOST, settings.MYSQL_PORT, settings.RULE_SVC_USER,
        )
        yield
        close = getattr(app.state.repository, "close", None)
        if close is not None:
            await close()
        log.info("rule service stopped")

    app = FastAPI(
        title="Harborline Cold-Chain Rule Service",
        version=__version__,
        summary="SOP rules as an API, over the legacy fleet data (FDE_PB_Sol v2.0).",
        description=DESCRIPTION,
        openapi_tags=TAGS,
        lifespan=lifespan,
        swagger_ui_parameters={"persistAuthorization": False, "displayRequestDuration": True},
    )
    app.state.settings = settings
    app.state.rules = rule_set
    app.state.repository = repository   # None -> created at start-up (real database)

    def openapi_with_problem_schema() -> dict[str, Any]:
        # Error answers are documented as application/problem+json with the Problem schema.
        if app.openapi_schema:
            return app.openapi_schema
        spec = get_openapi(title=app.title, version=app.version, summary=app.summary,
                           description=app.description, routes=app.routes, tags=app.openapi_tags)
        schemas = spec.setdefault("components", {}).setdefault("schemas", {})
        schemas["Problem"] = Problem.model_json_schema(ref_template="#/components/schemas/{model}")
        used = json.dumps(spec["paths"])
        for name in ("HTTPValidationError", "ValidationError"):   # FastAPI's defaults, replaced by Problem
            if f"#/components/schemas/{name}" not in used and name == "HTTPValidationError":
                schemas.pop(name, None)
                schemas.pop("ValidationError", None)
        app.openapi_schema = spec
        return spec

    app.openapi = openapi_with_problem_schema  # type: ignore[method-assign]
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)
    for module in (health, auth, rules, readings, evaluate, scan):
        app.include_router(module.router)
    return app
