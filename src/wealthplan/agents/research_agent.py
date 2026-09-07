"""Market-research specialist grounded in SEC facts and filing passages."""

from __future__ import annotations

import re
from typing import Any, Literal

from wealthplan.state import SpecialistOutput, SupervisorRequest
from wealthplan.tools.fundamentals import SecCompanyFactsService
from wealthplan.tools.sec_rag import SecFilingSearchService


_SEC_EVIDENCE_INTENT = re.compile(
    r"\b(?:10[- ]?k|annual report|sec|filing|risk|business|competition|"
    r"products?|services|supply chain|management|lawsuits?|litigation|legal|"
    r"regulatory|international|china|research and development|r&d|growth)\b",
    re.IGNORECASE,
)


def _structured_citation(
    item: dict[str, Any], rank: int
) -> dict[str, Any]:
    """Tie a stable citation record to one retrieved passage."""

    metadata = dict(item.get("metadata") or {})
    document_id = (
        metadata.get("document_id")
        or metadata.get("doc_id")
        or metadata.get("chunk_id")
        or f"sec-passage-{rank}"
    )
    source_url = metadata.get("source_url") or metadata.get("source")
    citation = {
        "citation_id": f"SEC-{rank}",
        "passage_rank": rank,
        "document_id": str(document_id),
        "ticker": metadata.get("ticker"),
        "form_type": metadata.get("form_type"),
        "filing_date": metadata.get("filing_date"),
        "report_date": metadata.get("report_date"),
        "accession_number": metadata.get("accession_number"),
        "section_id": metadata.get("section_id") or metadata.get("section"),
        "section_title": metadata.get("section_title"),
        "source_url": source_url,
        "line_start": metadata.get("loc.lines.from"),
        "line_end": metadata.get("loc.lines.to"),
        "excerpt": str(item.get("text") or "")[:500],
    }
    return {key: value for key, value in citation.items() if value is not None}


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
    citations = [
        _structured_citation(item, rank)
        for rank, item in enumerate(evidence, start=1)
        if isinstance(item, dict)
    ]
    for item, citation in zip(evidence, citations, strict=False):
        if isinstance(item, dict):
            item["citation_id"] = citation["citation_id"]
    search["passage_count"] = len(evidence)
    search["citation_count"] = len(citations)
    warnings = []
    if snapshot:
        warnings.append(snapshot.snapshot_label)
    if not search.get("answerable"):
        warnings.append(search["message"])
    requires_sec_evidence = bool(_SEC_EVIDENCE_INTENT.search(request.user_query))
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
