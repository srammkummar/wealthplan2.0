from wealthplan.agents.reporting import ReportAssembler, deterministic_narrative
from wealthplan.config import Settings


def settings_without_secrets() -> Settings:
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


def portfolio_output():
    return {
        "specialist": "portfolio_analysis",
        "status": "ok",
        "summary": "Analyzed a portfolio snapshot.",
        "data": {
            "total_market_value": 500_000,
            "unrealized_return": 0.12,
            "concentration_flags": ["MSFT exceeds the position threshold."],
        },
        "citations": [],
        "warnings": ["User-provided price snapshot."],
    }


def test_deterministic_narrative_summarizes_verified_specialist_data():
    narrative = deterministic_narrative(
        {
            "primary_goal": "Build long-term wealth",
            "time_horizon_years": 15,
        },
        [portfolio_output()],
    )

    assert "15-year horizon" in narrative.executive_summary
    assert "$500,000" in narrative.key_findings[0]
    assert any("MSFT exceeds" in item for item in narrative.risk_considerations)
    assert narrative.next_steps


def test_report_assembler_uses_deterministic_mode_without_openai():
    narrative, mode, warning = ReportAssembler(
        settings_without_secrets()
    ).assemble({}, [portfolio_output()])

    assert narrative.executive_summary
    assert mode == "deterministic"
    assert warning is None
