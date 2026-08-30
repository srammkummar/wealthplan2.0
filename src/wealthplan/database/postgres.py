"""Persistence interfaces and PostgreSQL implementation for approved reports."""

from __future__ import annotations

from importlib.resources import files
import json
import math
from typing import Any, Literal, Protocol
from uuid import uuid4

from pydantic import BaseModel

from wealthplan.config import Settings


def _sanitize_json_value(value: Any) -> Any:
    """Remove values PostgreSQL JSONB cannot represent."""

    if isinstance(value, str):
        return value.replace("\x00", "")
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if isinstance(value, dict):
        return {
            str(_sanitize_json_value(key)): _sanitize_json_value(item)
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_json_value(item) for item in value]
    return value


def _json_dumps(value: Any) -> str:
    """Serialize a value using the subset accepted by PostgreSQL JSONB."""

    return json.dumps(
        _sanitize_json_value(value),
        default=lambda item: str(item).replace("\x00", ""),
        ensure_ascii=False,
        allow_nan=False,
    )


class PersistenceResult(BaseModel):
    mode: Literal["session_only", "postgres"]
    saved: bool
    workflow_run_id: str | None = None
    approval_id: str | None = None
    report_id: str | None = None


class ApprovedReportSummary(BaseModel):
    report_id: str
    thread_id: str
    ticker: str | None = None
    status: str
    executive_summary: str | None = None
    created_at: str


class ApprovedReportRepository(Protocol):
    def save_approved_report(
        self,
        *,
        thread_id: str,
        request: dict[str, Any],
        report: dict[str, Any],
        approval: dict[str, Any],
    ) -> PersistenceResult: ...

    def list_approved_reports(
        self, *, user_id: str, limit: int = 10
    ) -> list[ApprovedReportSummary]: ...


class SessionOnlyReportRepository:
    """Explicit non-durable repository used when PostgreSQL is unconfigured."""

    def save_approved_report(
        self,
        *,
        thread_id: str,
        request: dict[str, Any],
        report: dict[str, Any],
        approval: dict[str, Any],
    ) -> PersistenceResult:
        return PersistenceResult(mode="session_only", saved=False)

    def list_approved_reports(
        self, *, user_id: str, limit: int = 10
    ) -> list[ApprovedReportSummary]:
        return []


class PostgresWealthPlanRepository:
    def __init__(self, dsn: str) -> None:
        if not dsn:
            raise ValueError("A PostgreSQL DSN is required")
        self.dsn = dsn

    @staticmethod
    def _connect(dsn: str):
        try:
            import psycopg
        except ImportError as exc:
            raise RuntimeError(
                "Install PostgreSQL support with: uv sync --extra postgres"
            ) from exc
        return psycopg.connect(dsn)

    def setup(self) -> None:
        migration = (
            files("wealthplan.database")
            .joinpath("migrations/001_initial.sql")
            .read_text(encoding="utf-8")
        )
        statements = [statement.strip() for statement in migration.split(";")]
        with self._connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                for statement in statements:
                    if statement:
                        cursor.execute(statement)

    def save_approved_report(
        self,
        *,
        thread_id: str,
        request: dict[str, Any],
        report: dict[str, Any],
        approval: dict[str, Any],
    ) -> PersistenceResult:
        run_id = str(uuid4())
        approval_id = str(uuid4())
        report_id = str(uuid4())
        with self._connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                user_id = request.get("user_id")
                if user_id:
                    cursor.execute(
                        """
                        INSERT INTO wealthplan_users (id, display_name)
                        VALUES (%s, %s)
                        ON CONFLICT (id) DO UPDATE
                        SET display_name = EXCLUDED.display_name
                        """,
                        (user_id, request.get("display_name") or "WealthPlan Investor"),
                    )
                    cursor.execute(
                        """
                        INSERT INTO investor_profiles
                            (user_id, risk_level, time_horizon_years, profile_json)
                        VALUES (%s, %s, %s, %s::jsonb)
                        ON CONFLICT (user_id) DO UPDATE SET
                            risk_level = EXCLUDED.risk_level,
                            time_horizon_years = EXCLUDED.time_horizon_years,
                            profile_json = EXCLUDED.profile_json,
                            updated_at = NOW()
                        """,
                        (
                            user_id,
                            request.get("risk_level"),
                            request.get("time_horizon_years"),
                            _json_dumps(
                                {
                                    "primary_goal": request.get("primary_goal"),
                                    "ticker": request.get("ticker"),
                                }
                            ),
                        ),
                    )
                    cursor.execute(
                        """
                        INSERT INTO goals (id, user_id, goal_type, goal_json)
                        VALUES (%s, %s, %s, %s::jsonb)
                        ON CONFLICT (id) DO UPDATE SET
                            goal_type = EXCLUDED.goal_type,
                            goal_json = EXCLUDED.goal_json
                        """,
                        (
                            f"{user_id}:primary-goal",
                            user_id,
                            request.get("primary_goal") or "General planning",
                            _json_dumps(
                                {
                                    "primary_goal": request.get("primary_goal"),
                                    "retirement_inputs": request.get(
                                        "retirement_inputs"
                                    ),
                                },
                            ),
                        ),
                    )
                    holdings = request.get("holdings") or []
                    if holdings and not request.get("use_demo_portfolio", True):
                        portfolio_id = f"{user_id}:primary-portfolio"
                        cursor.execute(
                            """
                            INSERT INTO portfolios (id, user_id, name)
                            VALUES (%s, %s, 'Primary portfolio')
                            ON CONFLICT (id) DO UPDATE SET updated_at = NOW()
                            """,
                            (portfolio_id, user_id),
                        )
                        cursor.execute(
                            "DELETE FROM holdings WHERE portfolio_id = %s",
                            (portfolio_id,),
                        )
                        for holding in holdings:
                            cursor.execute(
                                """
                                INSERT INTO holdings
                                    (id, portfolio_id, ticker, name, sector, quantity,
                                     cost_basis_per_share, price_snapshot)
                                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                                """,
                                (
                                    str(uuid4()),
                                    portfolio_id,
                                    holding["ticker"],
                                    holding["name"],
                                    holding["sector"],
                                    holding["quantity"],
                                    holding["cost_basis_per_share"],
                                    holding["illustrative_price"],
                                ),
                            )
                cursor.execute(
                    """
                    INSERT INTO workflow_runs
                        (id, thread_id, user_id, status, request_json, report_json,
                         completed_at)
                    VALUES (%s, %s, %s, 'approved', %s::jsonb, %s::jsonb, NOW())
                    """,
                    (
                        run_id,
                        thread_id,
                        user_id,
                        _json_dumps(request),
                        _json_dumps(report),
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO approvals
                        (id, workflow_run_id, decision, reviewer, response_json)
                    VALUES (%s, %s, %s, %s, %s::jsonb)
                    """,
                    (
                        approval_id,
                        run_id,
                        approval.get("decision", "approve"),
                        approval.get("reviewer"),
                        _json_dumps(approval),
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO approved_reports
                        (id, workflow_run_id, approval_id, report_json)
                    VALUES (%s, %s, %s, %s::jsonb)
                    """,
                    (report_id, run_id, approval_id, _json_dumps(report)),
                )
        return PersistenceResult(
            mode="postgres",
            saved=True,
            workflow_run_id=run_id,
            approval_id=approval_id,
            report_id=report_id,
        )

    def list_approved_reports(
        self, *, user_id: str, limit: int = 10
    ) -> list[ApprovedReportSummary]:
        safe_limit = max(1, min(limit, 100))
        with self._connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT
                        reports.id,
                        runs.thread_id,
                        runs.request_json ->> 'ticker',
                        reports.report_json ->> 'status',
                        reports.report_json -> 'narrative' ->> 'executive_summary',
                        reports.created_at
                    FROM approved_reports AS reports
                    JOIN workflow_runs AS runs ON runs.id = reports.workflow_run_id
                    WHERE runs.user_id = %s
                    ORDER BY reports.created_at DESC
                    LIMIT %s
                    """,
                    (user_id, safe_limit),
                )
                rows = cursor.fetchall()
        return [
            ApprovedReportSummary(
                report_id=row[0],
                thread_id=row[1],
                ticker=row[2],
                status=row[3] or "approved",
                executive_summary=row[4],
                created_at=row[5].isoformat(),
            )
            for row in rows
        ]


def report_repository_from_settings(
    settings: Settings,
) -> ApprovedReportRepository:
    if settings.postgres_dsn:
        return PostgresWealthPlanRepository(settings.postgres_dsn)
    return SessionOnlyReportRepository()
