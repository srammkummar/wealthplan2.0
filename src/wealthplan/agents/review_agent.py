"""Risk-and-review specialist for report quality and safety checks."""

from __future__ import annotations

from typing import Any, Literal

from wealthplan.state import WealthPlanState, execution_event


def run_review_agent(state: WealthPlanState) -> dict[str, Any]:
    """Review specialist results before the human approval checkpoint."""

    outputs = sorted(
        state.get("specialist_outputs", []), key=lambda item: item["specialist"]
    )
    failures = [
        output["specialist"] for output in outputs if output["status"] != "ok"
    ]
    checks = {
        "all_specialists_completed": not failures,
        "narrative_present": bool(state.get("narrative", {}).get("executive_summary")),
        "deterministic_calculations_used": all(
            output["specialist"] != "goal_planning" or bool(output["data"])
            for output in outputs
        ),
        "data_labels_present": all(bool(output["warnings"]) for output in outputs),
        "no_write_before_approval": not state.get("write_authorized", False),
    }
    decision = "pass" if all(checks.values()) else "revise"
    review_event = execution_event("risk_review", decision, failures=failures)
    draft = {
        "status": "draft",
        "request": state["request"],
        "specialist_results": outputs,
        "narrative": state.get("narrative", {}),
        "assembly_mode": state.get("assembly_mode", "unknown"),
        "assembly_warning": state.get("assembly_warning"),
        "routing": {
            "mode": state.get("routing_mode", "unknown"),
            "rationale": state.get("routing_rationale", ""),
            "warning": state.get("routing_warning"),
        },
        "review_checks": checks,
        "human_edits": state.get("human_edits", {}),
        "execution_events": [*state.get("execution_events", []), review_event],
        "disclaimer": (
            "Educational prototype only; not financial, investment, tax, or legal advice."
        ),
    }
    return {
        "status": "awaiting_approval" if decision == "pass" else "needs_revision",
        "review": {"decision": decision, "checks": checks, "failures": failures},
        "draft_report": draft,
        "execution_events": [review_event],
    }


def route_after_review(state: WealthPlanState) -> Literal[
    "human_approval", "finalize_needs_revision"
]:
    return (
        "human_approval"
        if state["review"]["decision"] == "pass"
        else "finalize_needs_revision"
    )


def finalize_needs_revision(state: WealthPlanState) -> dict[str, Any]:
    stop_event = execution_event("finalize_needs_revision", "stopped")
    return {
        "final_report": {
            **state["draft_report"],
            "status": "needs_revision",
            "review": state["review"],
            "execution_events": [*state.get("execution_events", []), stop_event],
        },
        "execution_events": [stop_event],
    }
