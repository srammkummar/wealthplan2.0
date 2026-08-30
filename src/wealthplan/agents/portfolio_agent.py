"""Portfolio-analysis specialist for allocation and concentration checks."""

from __future__ import annotations

from wealthplan.state import SpecialistOutput, SupervisorRequest
from wealthplan.tools.portfolio import DEMO_HOLDINGS, Holding, analyze_portfolio


def run_portfolio_agent(request: SupervisorRequest) -> SpecialistOutput:
    """Analyze either the course portfolio or a user-provided price snapshot."""

    if not request.use_demo_portfolio and not request.holdings:
        return {
            "specialist": "portfolio_analysis",
            "status": "needs_input",
            "summary": "A portfolio user ID or holdings list is required.",
            "data": {},
            "citations": [],
            "warnings": [],
        }
    holdings = (
        DEMO_HOLDINGS
        if request.use_demo_portfolio
        else [Holding.model_validate(item) for item in request.holdings or []]
    )
    analysis = analyze_portfolio(holdings)
    data = analysis.model_dump(mode="json")
    summary = "Analyzed the fixed five-holding demonstration portfolio."
    if not request.use_demo_portfolio:
        data["price_label"] = (
            "User-provided price snapshot; not verified live market prices."
        )
        summary = "Analyzed the user-provided portfolio snapshot."
    return {
        "specialist": "portfolio_analysis",
        "status": "ok",
        "summary": summary,
        "data": data,
        "citations": [],
        "warnings": [data["price_label"], analysis.disclaimer],
    }
