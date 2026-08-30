"""LangChain tool definitions exposed to the WealthPlan agent."""

from __future__ import annotations

from langchain.tools import tool

from wealthplan.config import Settings
from wealthplan.tools.fundamentals import SecCompanyFactsService
from wealthplan.tools.portfolio import DEMO_HOLDINGS, analyze_portfolio
from wealthplan.tools.retirement import (
    RetirementRequest,
    calculate_retirement_projection,
)
from wealthplan.tools.sec_rag import SecFilingSearchService


def build_tools(settings: Settings):
    retrieval = SecFilingSearchService(settings)
    fundamentals = SecCompanyFactsService(settings)

    @tool("sec_filing_search")
    def sec_filing_search(query: str, ticker: str) -> dict:
        """Search indexed SEC filing evidence for qualitative company claims and risks. Use this before making filing-based claims."""

        return retrieval.search(query=query, ticker=ticker)

    @tool("company_financial_metrics")
    def company_financial_metrics(ticker: str) -> dict:
        """Return historical annual company metrics from SEC facts. This does not provide live prices or valuation."""

        normalized = ticker.strip().upper()
        try:
            snapshot = fundamentals.get(normalized)
        except (LookupError, RuntimeError, ValueError) as exc:
            return {
                "status": "unavailable",
                "ticker": normalized,
                "message": str(exc),
            }
        if snapshot is None:
            return {
                "status": "insufficient_evidence",
                "ticker": normalized,
                "message": (
                    "No matching annual US-GAAP fundamentals were found. "
                    "Configure WEALTHPLAN_SEC_USER_AGENT for multi-ticker SEC data."
                ),
            }
        return {"status": "ok", **snapshot.model_dump()}

    @tool("retirement_goal_calculator")
    def retirement_goal_calculator(
        current_age: int,
        retirement_age: int,
        current_savings: float,
        monthly_contribution: float,
        desired_monthly_income_today: float,
        inflation_rate_percent: float,
        withdrawal_rate_percent: float,
        annual_return_rates_percent: list[float],
    ) -> dict:
        """Calculate retirement targets, projected assets, funding gaps, and required contributions. Percent inputs use ordinary values such as 2.5, 4, and [4, 6, 8]."""

        request = RetirementRequest(
            current_age=current_age,
            retirement_age=retirement_age,
            current_savings=current_savings,
            monthly_contribution=monthly_contribution,
            desired_monthly_income_today=desired_monthly_income_today,
            inflation_rate=inflation_rate_percent / 100,
            withdrawal_rate=withdrawal_rate_percent / 100,
            annual_return_rates=[rate / 100 for rate in annual_return_rates_percent],
        )
        return calculate_retirement_projection(request).model_dump()

    @tool("portfolio_analytics")
    def portfolio_analytics() -> dict:
        """Analyze the five-holding educational demo portfolio using fixed illustrative prices. Returns totals, gains, allocations, largest positions, and concentration flags."""

        return analyze_portfolio(DEMO_HOLDINGS).model_dump()

    return [
        sec_filing_search,
        company_financial_metrics,
        retirement_goal_calculator,
        portfolio_analytics,
    ]
