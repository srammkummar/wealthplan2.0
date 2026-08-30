"""Public entry point for the WealthPlan multi-agent LangGraph workflow."""

from __future__ import annotations

from typing import Any

from wealthplan.agents.supervisor import (
    SupervisorRouter,
    build_multi_agent_graph,
)
from wealthplan.config import Settings
from wealthplan.database.postgres import ApprovedReportRepository


def build_graph(
    settings: Settings,
    *,
    checkpointer: Any = None,
    report_repository: ApprovedReportRepository | None = None,
    supervisor_router: SupervisorRouter | None = None,
):
    """Compile the application graph used by Streamlit and other front ends."""

    return build_multi_agent_graph(
        settings,
        checkpointer=checkpointer,
        report_repository=report_repository,
        supervisor_router=supervisor_router,
    )


__all__ = ["SupervisorRouter", "build_graph", "build_multi_agent_graph"]
