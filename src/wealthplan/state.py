"""Typed state contracts for the WealthPlan 2.0 supervisor workflow."""

from __future__ import annotations

from datetime import UTC, datetime
import operator
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field
from typing_extensions import TypedDict


SpecialistName = Literal[
    "goal_planning",
    "portfolio_analysis",
    "market_research",
]
WorkflowStatus = Literal[
    "received",
    "needs_input",
    "planned",
    "reviewing",
    "needs_revision",
    "awaiting_approval",
    "approved",
    "rejected",
    "persistence_failed",
]


class SupervisorRequest(BaseModel):
    """Validated request shared by the supervisor and specialist agents."""

    user_query: str = Field(min_length=1)
    user_id: str | None = None
    display_name: str | None = None
    analyses: list[SpecialistName] = Field(default_factory=list)
    ticker: str | None = None
    use_demo_portfolio: bool = True
    holdings: list[dict[str, Any]] | None = None
    primary_goal: str | None = None
    risk_level: Literal[
        "Conservative", "Moderate", "Growth", "Aggressive"
    ] | None = None
    time_horizon_years: int | None = Field(default=None, ge=1, le=80)
    retirement_inputs: dict[str, Any] | None = None


def execution_event(node: str, outcome: str, **details: Any) -> dict[str, Any]:
    """Create one timestamped workflow audit event."""

    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "node": node,
        "outcome": outcome,
        "details": details,
    }


class SpecialistOutput(TypedDict):
    specialist: SpecialistName
    status: Literal["ok", "needs_input", "error"]
    summary: str
    data: dict[str, Any]
    citations: list[dict[str, Any]]
    warnings: list[str]


class WealthPlanState(TypedDict, total=False):
    request: dict[str, Any]
    status: WorkflowStatus
    missing_fields: list[str]
    selected_specialists: list[SpecialistName]
    routing_mode: str
    routing_rationale: str
    routing_warning: str | None
    specialist_outputs: Annotated[list[SpecialistOutput], operator.add]
    review: dict[str, Any]
    narrative: dict[str, Any]
    assembly_mode: str
    assembly_warning: str | None
    draft_report: dict[str, Any]
    human_edits: dict[str, Any]
    approval_response: dict[str, Any]
    final_report: dict[str, Any]
    execution_events: Annotated[list[dict[str, Any]], operator.add]
    write_authorized: bool
