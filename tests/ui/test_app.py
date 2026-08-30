from pathlib import Path

from langgraph.checkpoint.memory import InMemorySaver
from streamlit.testing.v1 import AppTest

from wealthplan.config import Settings
from wealthplan.multi_agent import build_graph
from wealthplan.ui.adapters import (
    build_ui_request,
    collect_citations,
    is_awaiting_approval,
    load_indexed_tickers,
    report_for_display,
    resume_ui_run,
    start_ui_run,
)
from wealthplan.ui.workflow import (
    apply_workflow_event,
    finalize_workflow_progress,
    initialize_workflow_progress,
    render_workflow_html,
)


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


def test_ui_adapter_starts_and_approves_a_checkpointed_run():
    graph = build_graph(
        settings_without_secrets(), checkpointer=InMemorySaver()
    )
    request = build_ui_request(
        user_query="Analyze the demo portfolio.",
        analyses=["portfolio_analysis"],
        user_id="course-investor",
        display_name="Course Investor",
        ticker=" msft ",
        primary_goal="Build long-term wealth",
        risk_level="Moderate",
        time_horizon_years=15,
    )

    events = []
    paused = start_ui_run(
        graph,
        request,
        thread_id="streamlit-test",
        on_event=events.append,
    )

    assert request["ticker"] == "MSFT"
    assert request["user_id"] == "course-investor"
    assert request["risk_level"] == "Moderate"
    assert request["time_horizon_years"] == 15
    assert is_awaiting_approval(paused)
    assert report_for_display(paused)["status"] == "draft"
    assert any(event["node"] == "normalize_request" for event in events)
    assert any(
        event.get("specialist") == "portfolio_analysis"
        and event["status"] == "completed"
        for event in events
    )
    assert any(
        event["node"] == "human_approval" and event["status"] == "waiting"
        for event in events
    )

    completed = resume_ui_run(
        graph,
        thread_id="streamlit-test",
        decision="approve",
    )

    assert completed["status"] == "approved"
    assert completed["write_authorized"] is True


def test_collect_citations_removes_duplicate_metadata():
    citation = {
        "ticker": "MSFT",
        "section_id": "item-1a",
        "source_url": "https://example.test/msft-10-k",
    }
    report = {
        "specialist_results": [
            {"citations": [citation]},
            {"citations": [citation]},
        ]
    }

    assert collect_citations(report) == [citation]


def test_ui_supports_user_entered_holdings():
    graph = build_graph(
        settings_without_secrets(), checkpointer=InMemorySaver()
    )
    request = build_ui_request(
        user_query="Review my portfolio concentration.",
        analyses=["portfolio_analysis"],
        use_demo_portfolio=False,
        holdings=[
            {
                "ticker": "VTI",
                "name": "Vanguard Total Stock Market ETF",
                "sector": "Diversified Equity",
                "quantity": 10,
                "cost_basis_per_share": 200,
                "illustrative_price": 250,
            }
        ],
    )

    paused = start_ui_run(graph, request, thread_id="custom-holdings-test")
    report = report_for_display(paused)
    portfolio = report["specialist_results"][0]

    assert is_awaiting_approval(paused)
    assert portfolio["data"]["total_market_value"] == 2_500
    assert "User-provided" in portfolio["data"]["price_label"]


def test_load_indexed_tickers_returns_only_completed_records(tmp_path):
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        '{"accessions":{"one":{"ticker":"MSFT","status":"completed"},'
        '"two":{"ticker":"AAPL","status":"failed"}}}',
        encoding="utf-8",
    )

    assert load_indexed_tickers(manifest) == ["MSFT"]


def test_workflow_navigator_tracks_selected_services_and_outcome():
    progress = initialize_workflow_progress(["market_research"])
    assert progress["market_research"]["status"] == "pending"
    assert progress["portfolio_analysis"]["status"] == "skipped"

    progress = apply_workflow_event(
        progress,
        {
            "node": "run_specialist",
            "specialist": "market_research",
            "status": "running",
            "detail": "Node is executing",
        },
    )
    progress = finalize_workflow_progress(
        progress,
        {"status": "awaiting_approval"},
    )
    markup = render_workflow_html(
        progress,
        memory_label="PostgreSQL checkpointer",
        pinecone_namespace="wealthplan-langgraph-v1",
    )

    assert progress["market_research"]["status"] == "running"
    assert progress["human_approval"]["status"] == "waiting"
    assert "SEC → Pinecone → Cohere" in markup
    assert "PostgreSQL checkpointer" in markup
    assert "wealthplan-langgraph-v1" in markup


def test_streamlit_landing_page_has_planning_controls():
    app_path = Path(__file__).parents[2] / "streamlit_app.py"
    app = AppTest.from_file(app_path).run(timeout=25)

    assert not app.exception
    assert "Select company ticker" in [item.label for item in app.selectbox]
    assert "Primary goal" in [item.label for item in app.selectbox]
    assert "Generate WealthPlan" in [item.label for item in app.button]
