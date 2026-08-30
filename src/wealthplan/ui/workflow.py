"""Presentation model for the live LangGraph workflow navigator."""

from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any, Literal

from wealthplan.state import SpecialistName


WorkflowNodeStatus = Literal[
    "pending",
    "running",
    "completed",
    "waiting",
    "failed",
    "skipped",
]


@dataclass(frozen=True, slots=True)
class WorkflowNode:
    key: str
    label: str
    technology: str
    lane: str


WORKFLOW_NODES = (
    WorkflowNode("normalize_request", "Normalize request", "Typed state", "Supervision"),
    WorkflowNode("plan_request", "Plan & route", "OpenAI / rules", "Supervision"),
    WorkflowNode("validate_request", "Validate inputs", "Pydantic", "Supervision"),
    WorkflowNode("select_specialists", "Delegate work", "LangGraph Send", "Supervision"),
    WorkflowNode("goal_planning", "Goal planning", "Retirement calculator", "Specialists"),
    WorkflowNode("portfolio_analysis", "Portfolio analysis", "Deterministic tools", "Specialists"),
    WorkflowNode("market_research", "Market research", "SEC → Pinecone → Cohere", "Specialists"),
    WorkflowNode("assemble_plan", "Assemble report", "OpenAI / fallback", "Review"),
    WorkflowNode("risk_review", "Risk review", "Policy checks", "Review"),
    WorkflowNode("human_approval", "Human approval", "LangGraph interrupt", "Review"),
    WorkflowNode("request_clarification", "Request input", "Safe stop", "Outcomes"),
    WorkflowNode("finalize_needs_revision", "Needs revision", "Safe stop", "Outcomes"),
    WorkflowNode("apply_human_edits", "Apply edits", "Review loop", "Outcomes"),
    WorkflowNode("save_approved_report", "Save approval", "PostgreSQL / session", "Outcomes"),
    WorkflowNode("reject_report", "Reject report", "No write", "Outcomes"),
)

LANES = ("Supervision", "Specialists", "Review", "Outcomes")
SPECIALIST_KEYS: dict[SpecialistName, str] = {
    "goal_planning": "goal_planning",
    "portfolio_analysis": "portfolio_analysis",
    "market_research": "market_research",
}
STATUS_ICON = {
    "pending": "○",
    "running": "▶",
    "completed": "✓",
    "waiting": "⏸",
    "failed": "✕",
    "skipped": "–",
}


def initialize_workflow_progress(
    analyses: list[SpecialistName],
) -> dict[str, dict[str, str]]:
    """Create pending state while marking unselected specialist branches skipped."""

    selected = set(analyses)
    progress: dict[str, dict[str, str]] = {}
    for node in WORKFLOW_NODES:
        status: WorkflowNodeStatus = "pending"
        if node.key in SPECIALIST_KEYS and node.key not in selected:
            status = "skipped"
        progress[node.key] = {"status": status, "detail": ""}
    return progress


def apply_workflow_event(
    progress: dict[str, dict[str, str]], event: dict[str, Any]
) -> dict[str, dict[str, str]]:
    """Return workflow progress updated by one normalized graph task event."""

    updated = {key: dict(value) for key, value in progress.items()}
    node = str(event.get("specialist") or event.get("node") or "")
    if node not in updated:
        return updated
    status = str(event.get("status", "pending"))
    if status not in STATUS_ICON:
        status = "pending"
    updated[node] = {
        "status": status,
        "detail": str(event.get("detail") or ""),
    }
    return updated


def finalize_workflow_progress(
    progress: dict[str, dict[str, str]], result: dict[str, Any]
) -> dict[str, dict[str, str]]:
    """Resolve unreachable conditional branches after a run pauses or completes."""

    updated = {key: dict(value) for key, value in progress.items()}
    status = result.get("status")
    if status == "awaiting_approval":
        updated["human_approval"] = {
            "status": "waiting",
            "detail": "Waiting for approve, edit, or reject",
        }
    elif status == "needs_input":
        updated["request_clarification"] = {
            "status": "completed",
            "detail": "More information required",
        }
    elif status == "needs_revision":
        updated["finalize_needs_revision"] = {
            "status": "completed",
            "detail": "Review checks require revision",
        }
    elif status in {"approved", "persistence_failed"}:
        updated["save_approved_report"] = {
            "status": "completed" if status == "approved" else "failed",
            "detail": (
                "Approved result persisted"
                if status == "approved"
                else "Approval completed; persistence failed"
            ),
        }
    elif status == "rejected":
        updated["reject_report"] = {
            "status": "completed",
            "detail": "Rejected without a write",
        }

    for value in updated.values():
        if value["status"] != "pending":
            continue
        value["status"] = "skipped"
    return updated


def render_workflow_html(
    progress: dict[str, dict[str, str]],
    *,
    memory_label: str,
    pinecone_namespace: str,
) -> str:
    """Render a compact workflow canvas suitable for a Streamlit placeholder."""

    infrastructure = (
        '<div class="wp-flow-infra">'
        f'<span><strong>Checkpoint memory</strong> · {escape(memory_label)}</span>'
        '<span><strong>Company facts</strong> · SEC XBRL API</span>'
        f'<span><strong>Filing index</strong> · Pinecone / {escape(pinecone_namespace)}</span>'
        '<span><strong>Evidence ranking</strong> · Cohere</span>'
        '</div>'
    )
    lanes: list[str] = []
    for lane in LANES:
        cards: list[str] = []
        for node in (item for item in WORKFLOW_NODES if item.lane == lane):
            state = progress.get(node.key, {"status": "pending", "detail": ""})
            status = state.get("status", "pending")
            detail = state.get("detail") or ""
            detail_markup = (
                f'<em>{escape(detail)}</em>' if detail else ""
            )
            cards.append(
                f'<div class="wp-flow-node {escape(status)}">'
                f'<div class="wp-flow-state">{STATUS_ICON.get(status, "○")} '
                f'{escape(status.replace("_", " ").title())}</div>'
                f'<strong>{escape(node.label)}</strong>'
                f'<small>{escape(node.technology)}</small>'
                f'{detail_markup}'
                '</div>'
            )
        lanes.append(
            '<div class="wp-flow-lane">'
            f'<div class="wp-flow-lane-title">{escape(lane)}</div>'
            f'<div class="wp-flow-row">{"".join(cards)}</div>'
            '</div>'
        )
    return f'<div class="wp-flow-canvas">{infrastructure}{"".join(lanes)}</div>'


__all__ = [
    "WORKFLOW_NODES",
    "apply_workflow_event",
    "finalize_workflow_progress",
    "initialize_workflow_progress",
    "render_workflow_html",
]
