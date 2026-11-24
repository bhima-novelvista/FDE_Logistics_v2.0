"""
All database access of the rule service, in one place.

- Logs in as ``rule_svc`` (Step 3): it can only read the view
  ``fde_views.vw_fleet_readings`` and add rows to ``fde_audit.RuleDecisionLog``.
  MySQL refuses anything else, whatever this code does.
- Async: queries run without blocking the web server (SQLAlchemy asyncio +
  aiomysql), so one slow query does not hold up other callers.
- Every value is a bound parameter (``:name``); no user input is ever pasted
  into SQL text.
- Every query has a time limit, both in MySQL (MAX_EXECUTION_TIME) and in
  Python, so a stuck database gives a clear 503 instead of a hanging call.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import Awaitable
from datetime import datetime
from typing import Any, TypeVar

from sqlalchemy import URL, text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .config import Settings
from .errors import ServiceUnavailableError
from .rules.engine import RuleSet

log = logging.getLogger("rule_service.db")
T = TypeVar("T")

# View column -> API field name (the view's readable names -> snake_case JSON)
SELECT_COLUMNS = """
    Reading_ID            AS reading_id,
    `Timestamp`           AS `timestamp`,
    Latitude              AS latitude,
    Longitude             AS longitude,
    Current_Temperature_C AS temperature_c,
    ETA_Variation_Hours   AS eta_variation_hours,
    Port_Congestion_Level AS port_congestion_level,
    Delay_Probability     AS delay_probability,
    Risk_Classification   AS risk_classification,
    Cargo_Condition_Code  AS cargo_condition_code,
    Route_Risk_Index      AS route_risk_index
"""


class ReadingRepository:
    def __init__(self, settings: Settings, engine: AsyncEngine | None = None):
        self.settings = settings
        self.view = settings.view_name
        self.audit_table = settings.audit_table
        self.max_ms = int(settings.DB_QUERY_TIMEOUT_MS)
        self.engine = engine or create_async_engine(
            URL.create(
                "mysql+aiomysql",
                username=settings.RULE_SVC_USER,
                password=settings.RULE_SVC_PASSWORD.get_secret_value(),
                host=settings.MYSQL_HOST,
                port=settings.MYSQL_PORT,
            ),
            pool_size=5,
            max_overflow=5,
            pool_pre_ping=True,      # replace connections that MySQL has closed
            pool_recycle=1800,
            connect_args={"connect_timeout": settings.DB_CONNECT_TIMEOUT_S, "charset": "utf8mb4"},
        )

    async def close(self) -> None:
        await self.engine.dispose()

    # -- helpers ------------------------------------------------------------
    def _hint(self) -> str:
        return f"/*+ MAX_EXECUTION_TIME({self.max_ms}) */"

    async def _timed(self, coro: Awaitable[T]) -> T:
        try:
            return await asyncio.wait_for(coro, timeout=self.max_ms / 1000 + 2)
        except asyncio.TimeoutError:
            raise ServiceUnavailableError(
                "The legacy database did not answer in time. Try again shortly."
            ) from None

    async def _fetch_all(self, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        async def run() -> list[dict[str, Any]]:
            async with self.engine.connect() as conn:
                result = await conn.execute(text(sql), params)
                return [dict(row) for row in result.mappings().all()]

        return await self._timed(run())

    @staticmethod
    def _window(
        from_time: datetime | None,
        to_time: datetime | None,
        area: Any | None,
    ) -> tuple[str, dict[str, Any]]:
        parts = ["1 = 1"]
        params: dict[str, Any] = {}
        if from_time is not None:
            parts.append("`Timestamp` >= :from_time")
            params["from_time"] = from_time.replace(tzinfo=None)
        if to_time is not None:
            parts.append("`Timestamp` <= :to_time")
            params["to_time"] = to_time.replace(tzinfo=None)
        if area is not None:
            parts.append("Latitude BETWEEN :lat_min AND :lat_max AND Longitude BETWEEN :lon_min AND :lon_max")
            params.update(lat_min=area.lat_min, lat_max=area.lat_max, lon_min=area.lon_min, lon_max=area.lon_max)
        return " AND ".join(parts), params

    # -- readings -------------------------------------------------------------
    async def count_readings(self) -> int:
        rows = await self._fetch_all(f"SELECT {self._hint()} COUNT(*) AS n FROM {self.view}", {})
        return int(rows[0]["n"])

    async def get_reading(self, reading_id: int) -> dict[str, Any] | None:
        rows = await self._fetch_all(
            f"SELECT {self._hint()} {SELECT_COLUMNS} FROM {self.view} WHERE Reading_ID = :rid",
            {"rid": reading_id},
        )
        return rows[0] if rows else None

    async def latest(self, limit: int, area: Any | None = None) -> list[dict[str, Any]]:
        where, params = self._window(None, None, area)
        params["limit"] = limit
        return await self._fetch_all(
            f"SELECT {self._hint()} {SELECT_COLUMNS} FROM {self.view} "
            f"WHERE {where} ORDER BY `Timestamp` DESC, Reading_ID DESC LIMIT :limit",
            params,
        )

    # -- bulk checks (the rules are counted inside MySQL) ---------------------
    async def scan(
        self,
        ruleset: RuleSet,
        from_time: datetime | None,
        to_time: datetime | None,
        area: Any | None,
        examples: int,
    ) -> tuple[int, dict[str, int], dict[str, int], list[dict[str, Any]]]:
        where, params = self._window(from_time, to_time, area)
        sums: list[str] = []
        rule_conds: list[str] = []
        gap_conds: list[str] = []
        for kind, rule in ruleset.all_defs():
            cond, cond_params = ruleset.sql_condition(rule)
            cond = f"COALESCE({cond}, FALSE)"     # a missing value never fires a rule
            params.update(cond_params)
            sums.append(f"SUM(CASE WHEN {cond} THEN 1 ELSE 0 END) AS `{rule.id}`")
            (rule_conds if kind == "rule" else gap_conds).append(cond)
        any_rule = "(" + " OR ".join(rule_conds) + ")"
        any_gap = "(" + " OR ".join(gap_conds) + ")" if gap_conds else "FALSE"
        sums.append(f"SUM(CASE WHEN {any_rule} THEN 1 ELSE 0 END) AS action_required")
        sums.append(f"SUM(CASE WHEN NOT {any_rule} AND {any_gap} THEN 1 ELSE 0 END) AS review")

        count_sql = f"SELECT {self._hint()} COUNT(*) AS total, {', '.join(sums)} FROM {self.view} WHERE {where}"
        row = (await self._fetch_all(count_sql, params))[0]
        total = int(row["total"] or 0)
        rule_counts = {rule.id: int(row[rule.id] or 0) for _, rule in ruleset.all_defs()}
        action = int(row["action_required"] or 0)
        review = int(row["review"] or 0)
        outcome_counts = {"ACTION_REQUIRED": action, "REVIEW": review, "NO_ACTION": total - action - review}

        example_rows: list[dict[str, Any]] = []
        if examples > 0 and action > 0:
            ex_params = dict(params, limit=examples)
            example_rows = await self._fetch_all(
                f"SELECT {self._hint()} {SELECT_COLUMNS} FROM {self.view} WHERE {where} AND {any_rule} "
                f"ORDER BY `Timestamp` DESC, Reading_ID DESC LIMIT :limit",
                ex_params,
            )
        return total, rule_counts, outcome_counts, example_rows

    # -- audit ------------------------------------------------------------------
    async def write_audit(self, row: dict[str, Any]) -> None:
        sql = (
            f"INSERT INTO {self.audit_table} "
            "(Request_ID, Caller, Caller_Role, Auth_Method, Endpoint, Reading_ID, Rules_Version, "
            "Outcome, Fired_Rules, Detail_JSON) VALUES "
            "(:request_id, :caller, :caller_role, :auth_method, :endpoint, :reading_id, :rules_version, "
            ":outcome, :fired_rules, :detail_json)"
        )
        params = dict(row)
        params["detail_json"] = json.dumps(row.get("detail_json"), default=str, ensure_ascii=False)

        async def run() -> None:
            async with self.engine.begin() as conn:
                await conn.execute(text(sql), params)

        await self._timed(run())
