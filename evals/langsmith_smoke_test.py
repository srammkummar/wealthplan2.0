"""Create and verify one LangSmith trace for the real WealthPlan agent."""

from __future__ import annotations

import asyncio
import os
from pathlib import Path
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
from langgraph.checkpoint.memory import InMemorySaver
from langsmith import Client, traceable

from wealthplan.config import Settings
from wealthplan.multi_agent import build_graph


REPO_ROOT = Path(__file__).resolve().parents[1]
TRACE_NAME = "SMOKE-001 WealthPlan LangSmith Setup"
QUESTION = "What are Apple's major risk factors according to the 10-K?"
PROJECT_NAME = "wealthplan-week4-evals"
TRACE_METADATA = {
    "case_id": "SMOKE-001",
    "run_type": "langsmith_setup",
    "agent_version": "setup_only",
    "dataset_version": "none_yet",
    "project": PROJECT_NAME,
}


def _validate_langsmith_environment() -> None:
    """Fail clearly instead of silently sending the trace to the wrong project."""

    if os.getenv("LANGSMITH_TRACING", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        raise RuntimeError("LANGSMITH_TRACING must be set to true in .env")
    if not os.getenv("LANGSMITH_API_KEY"):
        raise RuntimeError("LANGSMITH_API_KEY must be set in .env")
    if os.getenv("LANGSMITH_PROJECT") != PROJECT_NAME:
        raise RuntimeError(f"LANGSMITH_PROJECT must be set to {PROJECT_NAME}")


def _invoke_real_wealthplan_agent(
    question: str,
    *,
    run_tree: Any = None,
) -> dict[str, Any]:
    """Invoke the production graph without changing or persisting app behavior."""

    if run_tree is None:
        raise RuntimeError("LangSmith did not provide a root run")

    graph = build_graph(Settings.from_env(), checkpointer=InMemorySaver())
    result = graph.invoke(
        {
            "request": {
                "user_query": question,
                "analyses": ["market_research"],
                "ticker": "AAPL",
            }
        },
        config={
            "configurable": {
                "thread_id": f"langsmith-smoke-{uuid4()}",
            }
        },
    )
    report = result.get("final_report") or result.get("draft_report") or {}
    narrative = report.get("narrative") or {}
    return {
        "trace_id": str(run_tree.id),
        "workflow_status": result.get("status", "unknown"),
        "answer": narrative.get("executive_summary", ""),
        "citation_count": sum(
            len(item.get("citations", []))
            for item in report.get("specialist_results", [])
        ),
    }


def _read_uploaded_run(client: Client, trace_id: str) -> Any:
    """Read the root run back through the current LangSmith runs API."""

    project = client.read_project(project_name=PROJECT_NAME)

    async def retrieve() -> Any:
        return await client.runs.retrieve(
            trace_id,
            project_id=str(project.id),
            selects=["NAME", "METADATA"],
        )

    return asyncio.run(retrieve())


def main() -> None:
    """Load local configuration, emit the trace, and confirm it was uploaded."""

    load_dotenv(REPO_ROOT / ".env")
    _validate_langsmith_environment()

    client = Client()
    traced_agent_call = traceable(
        name=TRACE_NAME,
        run_type="chain",
        metadata=TRACE_METADATA,
        project_name=PROJECT_NAME,
        client=client,
    )(_invoke_real_wealthplan_agent)

    try:
        summary = traced_agent_call(QUESTION)
        client.flush()
        uploaded_run = _read_uploaded_run(client, summary["trace_id"])
    finally:
        client.close()

    if uploaded_run.name != TRACE_NAME:
        raise RuntimeError(
            f"Uploaded trace has unexpected name: {uploaded_run.name!r}"
        )
    uploaded_metadata = uploaded_run.metadata or {}
    missing_metadata = {
        key: value
        for key, value in TRACE_METADATA.items()
        if uploaded_metadata.get(key) != value
    }
    if missing_metadata:
        raise RuntimeError(
            f"Uploaded trace is missing required metadata: {missing_metadata}"
        )

    print(f"LangSmith smoke trace verified in project: {PROJECT_NAME}")
    print(f"Trace name: {TRACE_NAME}")
    print(f"Trace ID: {summary['trace_id']}")
    print(f"WealthPlan workflow status: {summary['workflow_status']}")


if __name__ == "__main__":
    main()
