"""Deterministic portfolio analytics and an illustrative demo portfolio."""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field


class Holding(BaseModel):
    ticker: str = Field(min_length=1)
    name: str
    sector: str
    quantity: float = Field(gt=0)
    cost_basis_per_share: float = Field(ge=0)
    illustrative_price: float = Field(ge=0)


class PositionAnalysis(BaseModel):
    ticker: str
    market_value: float
    cost_basis: float
    unrealized_gain_loss: float
    portfolio_weight: float


class PortfolioAnalysis(BaseModel):
    total_market_value: float
    total_cost_basis: float
    unrealized_gain_loss: float
    unrealized_return: float
    positions: list[PositionAnalysis]
    sector_allocation: dict[str, float]
    concentration_flags: list[str]
    price_label: str
    disclaimer: str


DEMO_HOLDINGS = [
    Holding(
        ticker="AAPL",
        name="Apple Inc.",
        sector="Technology",
        quantity=1500,
        cost_basis_per_share=160,
        illustrative_price=200,
    ),
    Holding(
        ticker="MSFT",
        name="Microsoft Corp.",
        sector="Technology",
        quantity=750,
        cost_basis_per_share=340,
        illustrative_price=400,
    ),
    Holding(
        ticker="VTI",
        name="Vanguard Total Stock Market ETF",
        sector="Diversified Equity",
        quantity=400,
        cost_basis_per_share=200,
        illustrative_price=250,
    ),
    Holding(
        ticker="JNJ",
        name="Johnson & Johnson",
        sector="Healthcare",
        quantity=300,
        cost_basis_per_share=133.3333333333,
        illustrative_price=150,
    ),
    Holding(
        ticker="BND",
        name="Vanguard Total Bond Market ETF",
        sector="Fixed Income",
        quantity=500,
        cost_basis_per_share=120,
        illustrative_price=101,
    ),
]


def analyze_portfolio(
    holdings: list[Holding],
    *,
    position_threshold: float = 0.25,
    sector_threshold: float = 0.40,
) -> PortfolioAnalysis:
    """Calculate totals, allocations, and simple concentration warnings."""

    if not holdings:
        raise ValueError("At least one holding is required")

    total_value = sum(h.quantity * h.illustrative_price for h in holdings)
    total_cost = sum(h.quantity * h.cost_basis_per_share for h in holdings)
    if total_value <= 0:
        raise ValueError("Portfolio market value must be greater than zero")

    positions: list[PositionAnalysis] = []
    sector_values: dict[str, float] = defaultdict(float)
    flags: list[str] = []

    for holding in holdings:
        market_value = holding.quantity * holding.illustrative_price
        cost_basis = holding.quantity * holding.cost_basis_per_share
        weight = market_value / total_value
        sector_values[holding.sector] += market_value
        positions.append(
            PositionAnalysis(
                ticker=holding.ticker,
                market_value=round(market_value, 2),
                cost_basis=round(cost_basis, 2),
                unrealized_gain_loss=round(market_value - cost_basis, 2),
                portfolio_weight=round(weight, 6),
            )
        )
        if weight > position_threshold:
            flags.append(
                f"{holding.ticker} is {weight:.1%} of the portfolio, above the "
                f"{position_threshold:.0%} position threshold."
            )

    allocations = {
        sector: round(value / total_value, 6)
        for sector, value in sorted(sector_values.items())
    }
    for sector, weight in allocations.items():
        if weight > sector_threshold:
            flags.append(
                f"{sector} is {weight:.1%} of the portfolio, above the "
                f"{sector_threshold:.0%} sector threshold."
            )

    positions.sort(key=lambda item: item.market_value, reverse=True)
    gain = total_value - total_cost
    return PortfolioAnalysis(
        total_market_value=round(total_value, 2),
        total_cost_basis=round(total_cost, 2),
        unrealized_gain_loss=round(gain, 2),
        unrealized_return=round(gain / total_cost, 6) if total_cost else 0.0,
        positions=positions,
        sector_allocation=allocations,
        concentration_flags=flags,
        price_label="Fixed illustrative demo prices; not current market prices.",
        disclaimer=(
            "Educational analysis only. This output is not investment, tax, or "
            "financial advice."
        ),
    )
