"""Testable workflow helpers shared by the Streamlit interface."""

from __future__ import annotations

import json
from pathlib import Path
from collections.abc import Callable
from typing import Any, Literal

from langgraph.types import Command

from wealthplan.state import SpecialistName, SupervisorRequest


ApprovalDecision = Literal["approve", "edit", "reject"]
WorkflowCallback = Callable[[dict[str, Any]], None]


def build_ui_request(
    *,
    user_query: str,
    analyses: list[SpecialistName],
    user_id: str | None = None,
    display_name: str | None = None,
    ticker: str | None = None,
    use_demo_portfolio: bool = True,
    holdings: list[dict[str, Any]] | None = None,
    primary_goal: str | None = None,
    risk_level: Literal["Conservative", "Moderate", "Growth", "Aggressive"] | None = None,
    time_horizon_years: int | None = None,
    retirement_inputs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate and normalize form inputs for the supervisor graph."""

    normalized_ticker = ticker.strip().upper() if ticker else None
    request = SupervisorRequest(
        user_query=user_query.strip(),
        analyses=analyses,
        user_id=user_id,
        display_name=display_name.strip() if display_name else None,
        ticker=normalized_ticker or None,
        use_demo_portfolio=use_demo_portfolio,
        holdings=holdings,
        primary_goal=primary_goal,
        risk_level=risk_level,
        time_horizon_years=time_horizon_years,
        retirement_inputs=retirement_inputs,
    )
    return request.model_dump(mode="json", exclude_none=True)


def _stream_graph_run(
    graph: Any,
    graph_input: Any,
    *,
    thread_id: str,
    on_event: WorkflowCallback | None = None,
) -> dict[str, Any]:
    """Stream task lifecycle events and return the latest checkpointed state."""

    latest_state: dict[str, Any] = {}
    latest_interrupts: tuple[Any, ...] = ()
    task_specialists: dict[str, str] = {}
    config = {"configurable": {"thread_id": thread_id}}
    for part in graph.stream(
        graph_input,
        config=config,
        stream_mode=["tasks", "values"],
        version="v2",
    ):
        part_type = part.get("type")
        data = part.get("data", {})
        if part_type == "values":
            latest_state = dict(data)
            latest_interrupts = tuple(part.get("interrupts", ()))
            continue
        if part_type != "tasks" or not on_event:
            continue

        task_id = str(data.get("id", ""))
        node = str(data.get("name", ""))
        if "input" in data:
            task_input = data.get("input")
            specialist = (
                str(task_input.get("specialist"))
                if node == "run_specialist" and isinstance(task_input, dict)
                else ""
            )
            if specialist:
                task_specialists[task_id] = specialist
            on_event(
                {
                    "node": node,
                    "specialist": specialist or None,
                    "status": "running",
                    "detail": "Node is executing",
                }
            )
            continue

        specialist = task_specialists.pop(task_id, "")
        error = data.get("error")
        interrupts = data.get("interrupts") or []
        on_event(
            {
                "node": node,
                "specialist": specialist or None,
                "status": "failed" if error else "waiting" if interrupts else "completed",
                "detail": (
                    "Node failed"
                    if error
                    else "Waiting for human input"
                    if interrupts
                    else "Node completed"
                ),
            }
        )

    if latest_interrupts:
        latest_state["__interrupt__"] = latest_interrupts
    return latest_state


def start_ui_run(
    graph: Any,
    request: dict[str, Any],
    *,
    thread_id: str,
    on_event: WorkflowCallback | None = None,
) -> dict:
    """Start a checkpointed run while optionally streaming workflow events."""

    return _stream_graph_run(
        graph,
        {"request": request},
        thread_id=thread_id,
        on_event=on_event,
    )


def resume_ui_run(
    graph: Any,
    *,
    thread_id: str,
    decision: ApprovalDecision,
    reason: str | None = None,
    edit_notes: str | None = None,
    on_event: WorkflowCallback | None = None,
) -> dict:
    """Resume the graph from its interrupt while streaming workflow events."""

    response: dict[str, Any] = {
        "decision": decision,
        "reviewer": "streamlit-user",
    }
    if reason and reason.strip():
        response["reason"] = reason.strip()
    if decision == "edit" and edit_notes and edit_notes.strip():
        response["edits"] = {"reviewer_notes": edit_notes.strip()}
    return _stream_graph_run(
        graph,
        Command(resume=response),
        thread_id=thread_id,
        on_event=on_event,
    )


def is_awaiting_approval(result: dict[str, Any] | None) -> bool:
    return bool(
        result
        and result.get("status") == "awaiting_approval"
        and result.get("__interrupt__")
    )


def report_for_display(result: dict[str, Any] | None) -> dict[str, Any] | None:
    if not result:
        return None
    return result.get("final_report") or result.get("draft_report")


def collect_citations(report: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Collect unique citation metadata from every specialist result."""

    if not report:
        return []
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for specialist in report.get("specialist_results", []):
        for citation in specialist.get("citations", []):
            identity = json.dumps(citation, sort_keys=True, default=str)
            if identity not in seen:
                seen.add(identity)
                citations.append(citation)
    return citations


def load_indexed_tickers(manifest_path: str | Path) -> list[str]:
    """Return completed tickers from the local ingestion manifest."""

    path = Path(manifest_path)
    if not path.exists():
        return []
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return sorted(
        {
            str(record.get("ticker", "")).upper()
            for record in manifest.get("accessions", {}).values()
            if record.get("status") == "completed" and record.get("ticker")
        }
    )
