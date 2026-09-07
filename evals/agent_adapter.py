"""Adapter from frozen evaluation cases to the production WealthPlan graph."""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from time import perf_counter
from typing import Any, Mapping
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver

from evals.evaluation_schema import AgentRunResult, GoldenDatasetCase
from wealthplan.config import Settings
from wealthplan.multi_agent import build_graph


_TICKER_BY_COMPANY = {
    "apple": "AAPL",
    "microsoft": "MSFT",
}


@lru_cache(maxsize=1)
def _wealthplan_graph() -> Any:
    """Build the same graph used by the application with an in-memory checkpoint."""

    return build_graph(Settings.from_env(), checkpointer=InMemorySaver())


def _ticker_from_query(query: str) -> str | None:
    """Bridge company names in text to the graph's required ticker input."""

    lowered = query.casefold()
    for company, ticker in _TICKER_BY_COMPANY.items():
        if re.search(rf"\b{re.escape(company)}(?:'s|’s)?\b", lowered):
            return ticker
    ticker_match = re.search(r"\b(?:ticker\s+)?([A-Z]{1,5})\b", query)
    return ticker_match.group(1) if ticker_match else None


def _build_request(case: GoldenDatasetCase) -> dict[str, Any]:
    """Create only the structured fields inferable from a frozen case.

    The adapter deliberately does not force specialist routing or manufacture
    holdings/retirement inputs. The graph therefore exposes its current routing
    and missing-input behavior during the baseline.
    """

    request: dict[str, Any] = {"user_query": case.user_query}
    if ticker := _ticker_from_query(case.user_query):
        request["ticker"] = ticker
    return request


def _report_from_state(state: Mapping[str, Any]) -> Mapping[str, Any]:
    report = state.get("final_report") or state.get("draft_report") or {}
    return report if isinstance(report, Mapping) else {}


def _answer_from_state(state: Mapping[str, Any]) -> str:
    """Render the graph's structured report into one readable answer string."""

    report = _report_from_state(state)
    narrative = report.get("narrative")
    if isinstance(narrative, Mapping):
        sections: list[str] = []
        summary = str(narrative.get("executive_summary") or "").strip()
        if summary:
            sections.append(summary)
        for heading, field in (
            ("Key findings", "key_findings"),
            ("Risk considerations", "risk_considerations"),
            ("Next steps", "next_steps"),
        ):
            values = narrative.get(field) or []
            if isinstance(values, list) and values:
                bullets = "\n".join(f"- {value}" for value in values if value)
                if bullets:
                    sections.append(f"{heading}:\n{bullets}")
        disclaimer = str(report.get("disclaimer") or "").strip()
        if disclaimer:
            sections.append(disclaimer)
        if sections:
            return "\n\n".join(sections)

    message = str(report.get("message") or "").strip()
    questions = report.get("missing_questions") or []
    if isinstance(questions, list) and questions:
        question_text = "\n".join(f"- {item}" for item in questions if item)
        return "\n".join(item for item in (message, question_text) if item)
    missing = report.get("missing_fields") or state.get("missing_fields") or []
    if isinstance(missing, list) and missing:
        missing_text = ", ".join(str(item) for item in missing)
        return "\n".join(
            item for item in (message, f"Missing inputs: {missing_text}") if item
        )
    return message


def _specialist_results(state: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    report = _report_from_state(state)
    raw = report.get("specialist_results") or state.get("specialist_outputs") or []
    return [item for item in raw if isinstance(item, Mapping)]


def _extract_citations(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    citations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for specialist in _specialist_results(state):
        for citation in specialist.get("citations") or []:
            if not isinstance(citation, Mapping):
                continue
            normalized = dict(citation)
            identity = json.dumps(normalized, sort_keys=True, default=str)
            if identity not in seen:
                seen.add(identity)
                citations.append(normalized)
    return citations


def _extract_structured_evidence(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Preserve non-passage evidence and provenance used to compose the answer."""

    evidence: list[dict[str, Any]] = []
    for specialist in _specialist_results(state):
        data = specialist.get("data") or {}
        if not isinstance(data, Mapping):
            continue
        fundamentals = data.get("fundamentals")
        if isinstance(fundamentals, Mapping) and fundamentals:
            evidence.append(
                {
                    "evidence_type": "sec_company_facts",
                    "specialist": specialist.get("specialist"),
                    "data": dict(fundamentals),
                }
            )
    return evidence


def _document_id(metadata: Mapping[str, Any], position: int) -> str:
    for key in ("document_id", "doc_id", "chunk_id", "id"):
        value = metadata.get(key)
        if value is not None and str(value).strip():
            return str(value)
    parts = [
        metadata.get("accession_number") or metadata.get("accession"),
        metadata.get("section") or metadata.get("item"),
        metadata.get("source") or metadata.get("source_url"),
    ]
    compact = "|".join(str(value) for value in parts if value)
    return compact or f"retrieved-context-{position}"


def _extract_retrieval(state: Mapping[str, Any]) -> tuple[list[str], list[str]]:
    contexts: list[str] = []
    doc_ids: list[str] = []
    for specialist in _specialist_results(state):
        data = specialist.get("data") or {}
        if not isinstance(data, Mapping):
            continue
        research = data.get("sec_research") or {}
        if not isinstance(research, Mapping):
            continue
        for position, item in enumerate(research.get("evidence") or [], start=1):
            if not isinstance(item, Mapping):
                continue
            contexts.append(str(item.get("text") or ""))
            metadata = item.get("metadata") or {}
            if not isinstance(metadata, Mapping):
                metadata = {}
            doc_ids.append(_document_id(metadata, position))
    return contexts, doc_ids


def _extract_retrieval_diagnostics(state: Mapping[str, Any]) -> dict[str, Any]:
    for specialist in _specialist_results(state):
        data = specialist.get("data") or {}
        if not isinstance(data, Mapping):
            continue
        research = data.get("sec_research")
        if not isinstance(research, Mapping):
            continue
        evidence = research.get("evidence") or []
        return {
            "status": research.get("status"),
            "answerable": research.get("answerable"),
            "passage_count": len(evidence),
            "citation_count": len(specialist.get("citations") or []),
            "cache_status": research.get("cache_status"),
            "attempts": research.get("attempts"),
            "message": research.get("message"),
            "error_type": research.get("error_type"),
        }
    return {}


def _route_selected(state: Mapping[str, Any]) -> list[str]:
    request = state.get("request") or {}
    if not isinstance(request, Mapping):
        return []
    analyses = request.get("analyses") or []
    return [str(item) for item in analyses]


def _specialists_executed(state: Mapping[str, Any]) -> list[str]:
    return [
        str(item.get("specialist"))
        for item in _specialist_results(state)
        if item.get("specialist")
    ]


def _tool_outputs_summary(state: Mapping[str, Any]) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    for item in _specialist_results(state):
        data = item.get("data") or {}
        research = data.get("sec_research") if isinstance(data, Mapping) else None
        summary: dict[str, Any] = {
            "specialist": item.get("specialist"),
            "status": item.get("status"),
            "summary": item.get("summary"),
            "citation_count": len(item.get("citations") or []),
        }
        if isinstance(research, Mapping):
            summary.update(
                {
                    "retrieval_status": research.get("status"),
                    "retrieved_passage_count": len(research.get("evidence") or []),
                    "retrieval_answerable": research.get("answerable"),
                }
            )
        summaries.append(summary)
    return summaries


def _extract_tool_calls(state: Mapping[str, Any]) -> list[str]:
    """Record production nodes/services that demonstrably executed."""

    report = _report_from_state(state)
    refusal_detected = bool(
        report.get("refusal_detected")
        or state.get("safety_decision", {}).get("decision") == "refuse"
    )
    if refusal_detected:
        return ["guardrail_refusal_logic"]

    calls: list[str] = []
    if state.get("routing_mode") or state.get("request"):
        calls.append("supervisor_router")
    for output in _specialist_results(state):
        specialist = output.get("specialist")
        data = output.get("data") or {}
        if specialist == "portfolio_analysis":
            calls.append("portfolio_analytics")
        elif specialist == "goal_planning":
            calls.append("retirement_goal_calculator")
        elif specialist == "market_research" and isinstance(data, Mapping):
            if data.get("fundamentals") is not None:
                calls.append("company_financial_metrics")
            if "sec_research" in data:
                calls.append("sec_filing_search")
    return list(dict.fromkeys(calls))


def _safe_error(exc: Exception) -> str:
    message = str(exc)
    for variable in (
        "OPENAI_API_KEY",
        "PINECONE_API_KEY",
        "COHERE_API_KEY",
        "LANGSMITH_API_KEY",
    ):
        secret = os.getenv(variable)
        if secret:
            message = message.replace(secret, "[REDACTED]")
    return f"{type(exc).__name__}: {message}"[:2_000]


def run_wealthplan_case(case: GoldenDatasetCase) -> AgentRunResult:
    """Run one frozen case through the real, unmodified WealthPlan graph."""

    started = perf_counter()
    try:
        state = _wealthplan_graph().invoke(
            {"request": _build_request(case)},
            config={
                "configurable": {
                    "thread_id": f"eval-baseline-{case.case_id}-{uuid4()}"
                }
            },
        )
        contexts, doc_ids = _extract_retrieval(state)
        citations = _extract_citations(state)
        retrieval_diagnostics = _extract_retrieval_diagnostics(state)
        report = _report_from_state(state)
        refusal_detected = bool(
            report.get("refusal_detected")
            or state.get("safety_decision", {}).get("decision") == "refuse"
        )
        return AgentRunResult(
            case_id=case.case_id,
            answer=_answer_from_state(state),
            retrieval_status=retrieval_diagnostics.get("status"),
            retrieved_contexts=contexts,
            retrieved_doc_ids=doc_ids,
            retrieved_passage_count=len(contexts),
            tool_calls=_extract_tool_calls(state),
            citations=citations,
            structured_citations=citations,
            citation_count=len(citations),
            route_selected=_route_selected(state),
            specialist_selected=_specialists_executed(state),
            clarification_requested=bool(
                report.get("clarification_requested")
                or state.get("clarification_requested")
            ),
            refusal_detected=refusal_detected,
            tool_outputs_summary=_tool_outputs_summary(state),
            structured_evidence=_extract_structured_evidence(state),
            retrieval_diagnostics=retrieval_diagnostics,
            latency_ms=(perf_counter() - started) * 1_000,
            # Token usage and cost are not exposed by the current graph result.
            token_usage={},
            estimated_cost_usd=None,
            error=None,
        )
    except Exception as exc:  # Keep one failed case from aborting the run set.
        return AgentRunResult(
            case_id=case.case_id,
            latency_ms=(perf_counter() - started) * 1_000,
            error=_safe_error(exc),
        )


__all__ = ["run_wealthplan_case"]
