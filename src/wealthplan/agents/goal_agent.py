"""Goal-planning specialist backed by deterministic retirement calculations."""

from __future__ import annotations

from wealthplan.state import SpecialistOutput, SupervisorRequest
from wealthplan.tools.retirement import (
    RetirementRequest,
    calculate_retirement_projection,
)


def run_goal_agent(request: SupervisorRequest) -> SpecialistOutput:
    """Validate retirement inputs and calculate educational goal scenarios."""

    if request.retirement_inputs is None:
        return {
            "specialist": "goal_planning",
            "status": "needs_input",
            "summary": "Retirement inputs are required.",
            "data": {},
            "citations": [],
            "warnings": [],
        }
    projection = calculate_retirement_projection(
        RetirementRequest.model_validate(request.retirement_inputs)
    )
    return {
        "specialist": "goal_planning",
        "status": "ok",
        "summary": "Calculated deterministic retirement scenarios.",
        "data": projection.model_dump(mode="json"),
        "citations": [],
        "warnings": [projection.disclaimer],
    }
