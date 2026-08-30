from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from wealthplan.agents.supervisor import (
    SupervisorRoute,
    SupervisorRouter,
    build_multi_agent_graph,
)
from wealthplan.config import Settings
from wealthplan.database.postgres import PersistenceResult
from wealthplan.state import SupervisorRequest


class RecordingRepository:
    def __init__(self):
        self.calls = []

    def save_approved_report(self, **kwargs):
        self.calls.append(kwargs)
        return PersistenceResult(
            mode="postgres",
            saved=True,
            workflow_run_id="run-1",
            approval_id="approval-1",
            report_id="report-1",
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


class FakeStructuredRouterModel:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages)
        if self.error:
            raise self.error
        return self.response


def test_structured_router_selects_multiple_required_specialists():
    model = FakeStructuredRouterModel(
        SupervisorRoute(
            analyses=["portfolio_analysis", "market_research"],
            rationale="The request combines holdings analysis with company research.",
        )
    )
    result = SupervisorRouter(
        settings_without_secrets(), structured_model=model
    ).route(
        SupervisorRequest(
            user_query="Review my portfolio concentration and Microsoft's filing risks.",
            ticker="MSFT",
        )
    )

    assert result.mode == "openai_structured"
    assert result.analyses == ["portfolio_analysis", "market_research"]
    assert len(model.calls) == 1


def test_explicit_agent_selection_bypasses_model_routing():
    model = FakeStructuredRouterModel(error=AssertionError("must not be called"))
    result = SupervisorRouter(
        settings_without_secrets(), structured_model=model
    ).route(
        SupervisorRequest(
            user_query="Help me plan.",
            analyses=["goal_planning"],
        )
    )

    assert result.mode == "user_selected"
    assert result.analyses == ["goal_planning"]
    assert model.calls == []


def test_structured_router_failure_uses_safe_deterministic_fallback():
    model = FakeStructuredRouterModel(error=ConnectionError("private detail"))
    result = SupervisorRouter(
        settings_without_secrets(), structured_model=model
    ).route(SupervisorRequest(user_query="Analyze portfolio concentration."))

    assert result.mode == "deterministic_fallback"
    assert result.analyses == ["portfolio_analysis"]
    assert "private detail" not in (result.warning or "")


def test_graph_routes_before_validating_selected_agent_inputs():
    model = FakeStructuredRouterModel(
        SupervisorRoute(
            analyses=["goal_planning"],
            rationale="The user asks for a retirement goal calculation.",
        )
    )
    router = SupervisorRouter(settings_without_secrets(), structured_model=model)
    graph = build_multi_agent_graph(
        settings_without_secrets(), supervisor_router=router
    )

    result = graph.invoke(
        {"request": {"user_query": "Can I retire in ten years?"}}
    )

    assert result["routing_mode"] == "openai_structured"
    assert result["status"] == "needs_input"
    assert result["final_report"]["missing_fields"] == ["retirement_inputs"]


def test_supervisor_runs_specialist_review_and_approval_gate():
    graph = build_multi_agent_graph(
        settings_without_secrets(), checkpointer=InMemorySaver()
    )
    config = {"configurable": {"thread_id": "portfolio-approval-test"}}

    paused = graph.invoke(
        {
            "request": {
                "user_query": "Analyze my demo portfolio allocation and concentration.",
                "analyses": ["portfolio_analysis"],
                "use_demo_portfolio": True,
            }
        },
        config=config,
    )

    assert "__interrupt__" in paused
    assert paused["status"] == "awaiting_approval"
    assert paused["write_authorized"] is False
    assert paused["draft_report"]["narrative"]["executive_summary"]
    assert paused["draft_report"]["assembly_mode"] == "deterministic"
    assert paused["draft_report"]["routing"]["mode"] == "user_selected"
    assert paused["draft_report"]["execution_events"]
    assert paused["draft_report"]["execution_events"][-1]["node"] == "risk_review"

    completed = graph.invoke(
        Command(resume={"decision": "approve", "reviewer": "course-demo"}),
        config=config,
    )
    assert completed["status"] == "approved"
    assert completed["write_authorized"] is True
    assert completed["final_report"]["status"] == "approved"
    assert completed["final_report"]["execution_events"][-1]["outcome"] in {
        "saved",
        "session_only",
    }


def test_supervisor_stops_and_names_missing_information():
    graph = build_multi_agent_graph(settings_without_secrets())
    result = graph.invoke(
        {
            "request": {
                "user_query": "Build my retirement scenarios.",
                "analyses": ["goal_planning"],
            }
        }
    )

    assert result["status"] == "needs_input"
    assert result["final_report"]["missing_fields"] == ["retirement_inputs"]


def test_repository_write_occurs_only_after_human_approval():
    repository = RecordingRepository()
    graph = build_multi_agent_graph(
        settings_without_secrets(),
        checkpointer=InMemorySaver(),
        report_repository=repository,
    )
    config = {"configurable": {"thread_id": "durable-approval-test"}}

    paused = graph.invoke(
        {
            "request": {
                "user_query": "Analyze the demonstration portfolio.",
                "user_id": "approval-test-user",
                "display_name": "Approval Test User",
                "analyses": ["portfolio_analysis"],
                "use_demo_portfolio": True,
            }
        },
        config=config,
    )

    assert paused["status"] == "awaiting_approval"
    assert repository.calls == []

    completed = graph.invoke(
        Command(resume={"decision": "approve", "reviewer": "test-reviewer"}),
        config=config,
    )

    assert len(repository.calls) == 1
    assert repository.calls[0]["thread_id"] == "durable-approval-test"
    assert repository.calls[0]["request"]["user_id"] == "approval-test-user"
    assert completed["final_report"]["persistence"]["saved"] is True
    persisted_events = repository.calls[0]["report"]["execution_events"]
    assert any(event["outcome"] == "authorized" for event in persisted_events)


def test_rejected_report_is_never_written():
    repository = RecordingRepository()
    graph = build_multi_agent_graph(
        settings_without_secrets(),
        checkpointer=InMemorySaver(),
        report_repository=repository,
    )
    config = {"configurable": {"thread_id": "rejection-test"}}
    graph.invoke(
        {
            "request": {
                "user_query": "Analyze the demonstration portfolio.",
                "analyses": ["portfolio_analysis"],
            }
        },
        config=config,
    )

    rejected = graph.invoke(
        Command(resume={"decision": "reject", "reviewer": "test-reviewer"}),
        config=config,
    )

    assert rejected["status"] == "rejected"
    assert repository.calls == []
    assert rejected["final_report"]["execution_events"][-1]["outcome"] == "rejected"


def test_human_edits_are_applied_and_return_to_approval():
    graph = build_multi_agent_graph(
        settings_without_secrets(), checkpointer=InMemorySaver()
    )
    config = {"configurable": {"thread_id": "edit-cycle-test"}}
    graph.invoke(
        {
            "request": {
                "user_query": "Analyze the demonstration portfolio.",
                "analyses": ["portfolio_analysis"],
            }
        },
        config=config,
    )

    edited = graph.invoke(
        Command(
            resume={
                "decision": "edit",
                "edits": {"reviewer_notes": "Compare the largest position to the threshold."},
            }
        ),
        config=config,
    )

    assert edited["status"] == "awaiting_approval"
    assert edited["human_edits"]["reviewer_notes"].startswith("Compare")
    assert any(
        "Reviewer requested" in step
        for step in edited["draft_report"]["narrative"]["next_steps"]
    )
    assert edited["write_authorized"] is False
