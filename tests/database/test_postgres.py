from importlib.resources import files

from wealthplan.config import Settings
from wealthplan.database.postgres import (
    PostgresWealthPlanRepository,
    SessionOnlyReportRepository,
    _json_dumps,
    report_repository_from_settings,
)


def settings_without_postgres() -> Settings:
    return Settings(
        openai_api_key=None,
        openai_model="test-model",
        pinecone_api_key=None,
        pinecone_index_name=None,
        pinecone_namespace="sec-filings",
        cohere_api_key=None,
        cohere_rerank_model="rerank-v3.5",
        postgres_dsn=None,
    )


def test_session_repository_is_explicitly_non_durable():
    result = SessionOnlyReportRepository().save_approved_report(
        thread_id="thread-1",
        request={},
        report={},
        approval={"decision": "approve"},
    )

    assert result.mode == "session_only"
    assert result.saved is False
    assert SessionOnlyReportRepository().list_approved_reports(
        user_id="user-1"
    ) == []


def test_settings_without_dsn_select_session_repository():
    repository = report_repository_from_settings(settings_without_postgres())

    assert isinstance(repository, SessionOnlyReportRepository)


def test_postgres_json_serialization_removes_unsupported_values():
    payload = _json_dumps(
        {
            "evidence": "filing text before\x00after",
            "score": float("nan"),
        }
    )

    assert "\\u0000" not in payload
    assert "\x00" not in payload
    assert '"score": null' in payload


def test_initial_migration_contains_required_domain_tables():
    migration = (
        files("wealthplan.database")
        .joinpath("migrations/001_initial.sql")
        .read_text(encoding="utf-8")
    )

    for table in (
        "wealthplan_users",
        "investor_profiles",
        "goals",
        "portfolios",
        "holdings",
        "workflow_runs",
        "approvals",
        "approved_reports",
        "price_snapshots",
        "ingestion_records",
    ):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in migration


class FakeCursor:
    def __init__(self):
        self.executions = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def execute(self, query, params=None):
        self.executions.append((str(query), params))


class FakeConnection:
    def __init__(self, cursor):
        self._cursor = cursor

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def cursor(self):
        return self._cursor


def test_postgres_approval_transaction_includes_profile_goal_and_holdings(monkeypatch):
    cursor = FakeCursor()
    connection = FakeConnection(cursor)
    monkeypatch.setattr(
        PostgresWealthPlanRepository,
        "_connect",
        staticmethod(lambda dsn: connection),
    )
    repository = PostgresWealthPlanRepository("postgresql://test")

    result = repository.save_approved_report(
        thread_id="thread-1",
        request={
            "user_id": "investor-1",
            "display_name": "Investor One",
            "risk_level": "Moderate",
            "time_horizon_years": 15,
            "primary_goal": "Build long-term wealth",
            "use_demo_portfolio": False,
            "holdings": [
                {
                    "ticker": "MSFT",
                    "name": "Microsoft",
                    "sector": "Technology",
                    "quantity": 10,
                    "cost_basis_per_share": 300,
                    "illustrative_price": 400,
                }
            ],
        },
        report={
            "status": "approved",
            "evidence": "filing text before\x00after",
        },
        approval={"decision": "approve", "reviewer": "test"},
    )

    sql = "\n".join(query for query, _ in cursor.executions)
    assert "INSERT INTO wealthplan_users" in sql
    assert "INSERT INTO investor_profiles" in sql
    assert "INSERT INTO goals" in sql
    assert "INSERT INTO portfolios" in sql
    assert "DELETE FROM holdings" in sql
    assert "INSERT INTO holdings" in sql
    assert "INSERT INTO approved_reports" in sql
    serialized_parameters = " ".join(
        str(parameter)
        for _, parameters in cursor.executions
        for parameter in (parameters or ())
    )
    assert "\x00" not in serialized_parameters
    assert result.saved is True
