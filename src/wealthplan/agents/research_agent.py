"""Market-research specialist grounded in SEC facts and filing passages."""

from __future__ import annotations

from typing import Literal

from wealthplan.state import SpecialistOutput, SupervisorRequest
from wealthplan.tools.fundamentals import SecCompanyFactsService
from wealthplan.tools.sec_rag import SecFilingSearchService


def run_research_agent(
    request: SupervisorRequest,
    retrieval: SecFilingSearchService,
    fundamentals: SecCompanyFactsService,
) -> SpecialistOutput:
    """Combine historical company facts with citation-preserving SEC RAG."""

    ticker = (request.ticker or "").upper()
    snapshot = fundamentals.get(ticker)
    search = retrieval.search(query=request.user_query, ticker=ticker)
    evidence = search.get("evidence", [])
    citations = [item.get("metadata", {}) for item in evidence]
    warnings = []
    if snapshot:
        warnings.append(snapshot.snapshot_label)
    if not search.get("answerable"):
        warnings.append(search["message"])
    requires_sec_evidence = any(
        word in request.user_query.lower()
        for word in (
            "risk",
            "sec",
            "filing",
            "business",
            "supply chain",
            "management",
        )
    )
    status: Literal["ok", "needs_input", "error"] = (
        "ok"
        if search.get("answerable")
        or (snapshot is not None and not requires_sec_evidence)
        else "needs_input"
    )
    return {
        "specialist": "market_research",
        "status": status,
        "summary": "Combined historical SEC fundamentals with filing retrieval status.",
        "data": {
            "fundamentals": snapshot.model_dump(mode="json") if snapshot else None,
            "sec_research": search,
        },
        "citations": citations,
        "warnings": warnings,
    }
