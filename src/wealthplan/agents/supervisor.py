"""WealthPlan 2.0 supervisor and specialist workflow."""

from __future__ import annotations

import json
from typing import Any, Literal

from langchain.messages import HumanMessage, SystemMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send, interrupt
from pydantic import BaseModel, Field

from wealthplan.agents.goal_agent import run_goal_agent
from wealthplan.agents.portfolio_agent import run_portfolio_agent
from wealthplan.agents.reporting import ReportAssembler
from wealthplan.agents.research_agent import run_research_agent
from wealthplan.agents.review_agent import (
    finalize_needs_revision,
    route_after_review,
    run_review_agent,
)
from wealthplan.config import Settings
from wealthplan.database.postgres import (
    ApprovedReportRepository,
    report_repository_from_settings,
)
from wealthplan.prompts import SUPERVISOR_ROUTING_POLICY
from wealthplan.state import (
    SpecialistName,
    SupervisorRequest,
    WealthPlanState,
    execution_event as _event,
)
from wealthplan.tools.fundamentals import SecCompanyFactsService
from wealthplan.tools.sec_rag import SecFilingSearchService


class SupervisorRoute(BaseModel):
    """Strict model output for selecting the minimum required specialists."""

    analyses: list[SpecialistName] = Field(min_length=1, max_length=3)
    rationale: str = Field(min_length=1, max_length=400)


class RoutingResult(BaseModel):
    analyses: list[SpecialistName]
    rationale: str
    mode: Literal["user_selected", "openai_structured", "deterministic_fallback"]
    warning: str | None = None


def infer_analyses(query: str) -> list[SpecialistName]:
    """Transparent fallback router until model-based planning is introduced."""

    lowered = query.lower()
    selected: list[SpecialistName] = []
    if any(word in lowered for word in ("retire", "retirement", "goal", "scenario")):
        selected.append("goal_planning")
    if any(word in lowered for word in ("portfolio", "holding", "allocation", "concentration")):
        selected.append("portfolio_analysis")
    if any(
        word in lowered
        for word in ("sec", "filing", "fundamental", "risk", "company", "stock")
    ):
        selected.append("market_research")
    return selected or ["market_research"]


class SupervisorRouter:
    """Route with OpenAI Structured Outputs and a deterministic fallback."""

    def __init__(self, settings: Settings, *, structured_model: Any = None) -> None:
        self.settings = settings
        self.structured_model = structured_model

    def route(self, request: SupervisorRequest) -> RoutingResult:
        if request.analyses:
            selected = list(dict.fromkeys(request.analyses))
            return RoutingResult(
                analyses=selected,
                rationale="The user explicitly selected these specialist analyses.",
                mode="user_selected",
            )

        fallback = infer_analyses(request.user_query)
        if self.structured_model is None and not self.settings.openai_api_key:
            return RoutingResult(
                analyses=fallback,
                rationale="Matched the request to specialist responsibilities using deterministic routing rules.",
                mode="deterministic_fallback",
                warning="OpenAI routing is unavailable because OPENAI_API_KEY is not configured.",
            )

        try:
            model = self.structured_model
            if model is None:
                model = ChatOpenAI(
                    model=self.settings.openai_model,
                    api_key=self.settings.openai_api_key,
                ).with_structured_output(SupervisorRoute, method="json_schema")
            context = {
                "user_query": request.user_query,
                "has_ticker": bool(request.ticker),
                "uses_demo_portfolio": request.use_demo_portfolio,
                "has_user_holdings": bool(request.holdings),
                "has_retirement_inputs": bool(request.retirement_inputs),
                "primary_goal": request.primary_goal,
                "risk_level": request.risk_level,
                "time_horizon_years": request.time_horizon_years,
            }
            response = model.invoke(
                [
                    SystemMessage(content=SUPERVISOR_ROUTING_POLICY),
                    HumanMessage(
                        content="Route this request context:\n"
                        + json.dumps(context, default=str)
                    ),
                ]
            )
            route = SupervisorRoute.model_validate(response)
            selected = list(dict.fromkeys(route.analyses))
            return RoutingResult(
                analyses=selected,
                rationale=route.rationale,
                mode="openai_structured",
            )
        except Exception as exc:
            return RoutingResult(
                analyses=fallback,
                rationale="The structured router failed, so deterministic routing rules were used.",
                mode="deterministic_fallback",
                warning=(
                    "OpenAI structured routing failed; deterministic fallback used "
                    f"({type(exc).__name__})."
                ),
            )


def normalize_request(state: WealthPlanState) -> dict[str, Any]:
    request = SupervisorRequest.model_validate(state["request"])
    normalized = request.model_dump(mode="json")
    return {
        "request": normalized,
        "status": "received",
        "specialist_outputs": [],
        "execution_events": [
            _event(
                "normalize_request",
                "ok",
                requested_analyses=normalized["analyses"],
            )
        ],
        "write_authorized": False,
    }


def make_plan_request_node(router: SupervisorRouter):
    def plan_request(state: WealthPlanState) -> dict[str, Any]:
        request = SupervisorRequest.model_validate(state["request"])
        routing = router.route(request)
        request.analyses = routing.analyses
        return {
            "request": request.model_dump(mode="json"),
            "routing_mode": routing.mode,
            "routing_rationale": routing.rationale,
            "routing_warning": routing.warning,
            "execution_events": [
                _event(
                    "plan_request",
                    routing.mode,
                    analyses=routing.analyses,
                    rationale=routing.rationale,
                    warning=routing.warning,
                )
            ],
        }

    return plan_request


def validate_request(state: WealthPlanState) -> dict[str, Any]:
    request = SupervisorRequest.model_validate(state["request"])
    missing: list[str] = []
    if "goal_planning" in request.analyses and request.retirement_inputs is None:
        missing.append("retirement_inputs")
    if (
        "portfolio_analysis" in request.analyses
        and not request.use_demo_portfolio
        and not request.holdings
    ):
        missing.append("portfolio_holdings_or_user_id")
    if "market_research" in request.analyses and not request.ticker:
        missing.append("ticker")
    return {
        "missing_fields": missing,
        "status": "needs_input" if missing else "planned",
        "execution_events": [
            _event("validate_request", "needs_input" if missing else "ok", missing=missing)
        ],
    }


def route_after_validation(state: WealthPlanState) -> Literal[
    "request_clarification", "select_specialists"
]:
    return "request_clarification" if state.get("missing_fields") else "select_specialists"


def request_clarification(state: WealthPlanState) -> dict[str, Any]:
    missing = state.get("missing_fields", [])
    return {
        "final_report": {
            "status": "needs_input",
            "message": "More information is required before the plan can run.",
            "missing_fields": missing,
        },
        "execution_events": [_event("request_clarification", "stopped", missing=missing)],
    }


def select_specialists(state: WealthPlanState) -> dict[str, Any]:
    selected = list(dict.fromkeys(state["request"]["analyses"]))
    return {
        "selected_specialists": selected,
        "execution_events": [
            _event(
                "select_specialists",
                "ok",
                selected=selected,
                routing_mode=state.get("routing_mode", "unknown"),
            )
        ],
    }


def route_to_specialists(state: WealthPlanState) -> list[Send]:
    return [
        Send(
            "run_specialist",
            {"specialist": specialist, "request": state["request"]},
        )
        for specialist in state["selected_specialists"]
    ]


def make_specialist_node(settings: Settings):
    retrieval = SecFilingSearchService(settings)
    fundamentals = SecCompanyFactsService(settings)

    def run_specialist(state: dict[str, Any]) -> dict[str, Any]:
        specialist: SpecialistName = state["specialist"]
        request = SupervisorRequest.model_validate(state["request"])
        try:
            if specialist == "goal_planning":
                output = run_goal_agent(request)
            elif specialist == "portfolio_analysis":
                output = run_portfolio_agent(request)
            else:
                output = run_research_agent(request, retrieval, fundamentals)
        except (LookupError, ValueError, RuntimeError) as exc:
            output = {
                "specialist": specialist,
                "status": "error",
                "summary": "The specialist could not complete its task.",
                "data": {},
                "citations": [],
                "warnings": [str(exc)],
            }
        return {
            "specialist_outputs": [output],
            "execution_events": [
                _event("run_specialist", output["status"], specialist=specialist)
            ],
        }

    return run_specialist


def make_report_assembler_node(settings: Settings):
    assembler = ReportAssembler(settings)

    def assemble_plan(state: WealthPlanState) -> dict[str, Any]:
        outputs = sorted(
            state.get("specialist_outputs", []), key=lambda item: item["specialist"]
        )
        narrative, mode, warning = assembler.assemble(state["request"], outputs)
        result: dict[str, Any] = {
            "narrative": narrative.model_dump(mode="json"),
            "assembly_mode": mode,
            "assembly_warning": warning,
            "execution_events": [
                _event("assemble_plan", "fallback" if warning else "ok", mode=mode)
            ],
        }
        return result

    return assemble_plan


def human_approval(state: WealthPlanState) -> dict[str, Any]:
    response = interrupt(
        {
            "action": "review_wealth_plan",
            "allowed_decisions": ["approve", "edit", "reject"],
            "draft_report": state["draft_report"],
            "message": "Approve, edit, or reject this educational plan.",
        }
    )
    if isinstance(response, str):
        response = {"decision": response}
    if not isinstance(response, dict):
        response = {"decision": "reject", "reason": "Invalid approval response."}
    return {"approval_response": response}


def route_approval(state: WealthPlanState) -> Literal[
    "save_approved_report", "apply_human_edits", "reject_report"
]:
    decision = state.get("approval_response", {}).get("decision", "reject")
    if decision == "approve":
        return "save_approved_report"
    if decision == "edit":
        return "apply_human_edits"
    return "reject_report"


def apply_human_edits(state: WealthPlanState) -> dict[str, Any]:
    edits = state.get("approval_response", {}).get("edits", {})
    if not isinstance(edits, dict):
        edits = {}

    accumulated_edits = {**state.get("human_edits", {}), **edits}
    narrative = dict(state.get("narrative", {}))
    for field in (
        "executive_summary",
        "key_findings",
        "risk_considerations",
        "next_steps",
    ):
        if field in edits:
            narrative[field] = edits[field]

    reviewer_notes = edits.get("reviewer_notes")
    if isinstance(reviewer_notes, str) and reviewer_notes.strip():
        next_steps = list(narrative.get("next_steps", []))
        requested_step = f"Reviewer requested: {reviewer_notes.strip()}"
        if requested_step not in next_steps:
            next_steps.append(requested_step)
        narrative["next_steps"] = next_steps

    return {
        "human_edits": accumulated_edits,
        "narrative": narrative,
        "approval_response": {},
        "status": "reviewing",
        "execution_events": [
            _event(
                "apply_human_edits",
                "ok",
                edited_fields=sorted(edits),
            )
        ],
    }


def make_save_approved_report_node(repository: ApprovedReportRepository):
    def save_approved_report(
        state: WealthPlanState, config: RunnableConfig
    ) -> dict[str, Any]:
        authorization_event = _event(
            "save_approved_report", "authorized", decision="approve"
        )
        final_report = {
            **state["draft_report"],
            "status": "approved",
            "approval": state["approval_response"],
            "execution_events": [
                *state.get("execution_events", []),
                authorization_event,
            ],
        }
        thread_id = str(config.get("configurable", {}).get("thread_id", "untracked"))
        try:
            persistence = repository.save_approved_report(
                thread_id=thread_id,
                request=state["request"],
                report=final_report,
                approval=state["approval_response"],
            )
        except Exception as exc:
            persistence_event = _event(
                "save_approved_report", "error", error_type=type(exc).__name__
            )
            final_report["status"] = "persistence_failed"
            final_report["persistence"] = {
                "saved": False,
                "error": "The approved report could not be persisted.",
            }
            final_report["execution_events"].append(persistence_event)
            return {
                "status": "persistence_failed",
                "write_authorized": True,
                "final_report": final_report,
                "execution_events": [
                    authorization_event,
                    persistence_event,
                ],
            }
        final_report["persistence"] = persistence.model_dump(mode="json")
        persistence_event = _event(
            "save_approved_report",
            "saved" if persistence.saved else "session_only",
            mode=persistence.mode,
        )
        final_report["execution_events"].append(persistence_event)
        return {
            "status": "approved",
            "write_authorized": True,
            "final_report": final_report,
            "execution_events": [authorization_event, persistence_event],
        }

    return save_approved_report


def reject_report(state: WealthPlanState) -> dict[str, Any]:
    rejection_event = _event("reject_report", "rejected")
    return {
        "status": "rejected",
        "write_authorized": False,
        "final_report": {
            **state["draft_report"],
            "status": "rejected",
            "approval": state["approval_response"],
            "execution_events": [
                *state.get("execution_events", []),
                rejection_event,
            ],
        },
        "execution_events": [rejection_event],
    }


def build_multi_agent_graph(
    settings: Settings,
    *,
    checkpointer: Any = None,
    report_repository: ApprovedReportRepository | None = None,
    supervisor_router: SupervisorRouter | None = None,
):
    """Compile the complete WealthPlan 2.0 supervisor workflow."""

    repository = report_repository or report_repository_from_settings(settings)
    router = supervisor_router or SupervisorRouter(settings)
    builder = StateGraph(WealthPlanState)
    builder.add_node("normalize_request", normalize_request)
    builder.add_node("plan_request", make_plan_request_node(router))
    builder.add_node("validate_request", validate_request)
    builder.add_node("request_clarification", request_clarification)
    builder.add_node("select_specialists", select_specialists)
    builder.add_node("run_specialist", make_specialist_node(settings))
    builder.add_node(
        "assemble_plan", make_report_assembler_node(settings), defer=True
    )
    builder.add_node("risk_review", run_review_agent)
    builder.add_node("finalize_needs_revision", finalize_needs_revision)
    builder.add_node("human_approval", human_approval)
    builder.add_node("apply_human_edits", apply_human_edits)
    builder.add_node(
        "save_approved_report", make_save_approved_report_node(repository)
    )
    builder.add_node("reject_report", reject_report)

    builder.add_edge(START, "normalize_request")
    builder.add_edge("normalize_request", "plan_request")
    builder.add_edge("plan_request", "validate_request")
    builder.add_conditional_edges("validate_request", route_after_validation)
    builder.add_edge("request_clarification", END)
    builder.add_conditional_edges(
        "select_specialists", route_to_specialists, ["run_specialist"]
    )
    builder.add_edge("run_specialist", "assemble_plan")
    builder.add_edge("assemble_plan", "risk_review")
    builder.add_conditional_edges("risk_review", route_after_review)
    builder.add_edge("finalize_needs_revision", END)
    builder.add_conditional_edges("human_approval", route_approval)
    builder.add_edge("apply_human_edits", "risk_review")
    builder.add_edge("save_approved_report", END)
    builder.add_edge("reject_report", END)
    return builder.compile(checkpointer=checkpointer)
