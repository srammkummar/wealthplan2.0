"""Deterministic retirement projections used by the agent tool."""

from __future__ import annotations

from pydantic import BaseModel, Field, model_validator


class RetirementRequest(BaseModel):
    current_age: int = Field(ge=18, le=100)
    retirement_age: int = Field(ge=19, le=110)
    current_savings: float = Field(ge=0)
    monthly_contribution: float = Field(ge=0)
    desired_monthly_income_today: float = Field(gt=0)
    inflation_rate: float = Field(ge=0, lt=1)
    withdrawal_rate: float = Field(gt=0, lt=1)
    annual_return_rates: list[float] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_timeline_and_rates(self) -> "RetirementRequest":
        if self.retirement_age <= self.current_age:
            raise ValueError("retirement_age must be greater than current_age")
        if any(rate <= -1 or rate >= 1 for rate in self.annual_return_rates):
            raise ValueError("annual return rates must be decimals between -1 and 1")
        return self


class RetirementScenario(BaseModel):
    annual_return_rate: float
    projected_assets: float
    retirement_target: float
    funding_gap: float
    required_monthly_contribution: float
    additional_monthly_contribution: float


class RetirementProjection(BaseModel):
    years_to_retirement: int
    future_annual_income_need: float
    retirement_target: float
    scenarios: list[RetirementScenario]
    assumptions: dict[str, float | str]
    disclaimer: str


def _future_value_annuity_factor(monthly_rate: float, months: int) -> float:
    if monthly_rate == 0:
        return float(months)
    return ((1 + monthly_rate) ** months - 1) / monthly_rate


def calculate_retirement_projection(
    request: RetirementRequest,
) -> RetirementProjection:
    """Calculate repeatable retirement scenarios without using an LLM."""

    years = request.retirement_age - request.current_age
    months = years * 12
    future_annual_income = (
        request.desired_monthly_income_today
        * 12
        * (1 + request.inflation_rate) ** years
    )
    target = future_annual_income / request.withdrawal_rate
    scenarios: list[RetirementScenario] = []

    for annual_rate in request.annual_return_rates:
        monthly_rate = annual_rate / 12
        growth = (1 + monthly_rate) ** months
        annuity_factor = _future_value_annuity_factor(monthly_rate, months)
        projected = (
            request.current_savings * growth
            + request.monthly_contribution * annuity_factor
        )
        gap = max(target - projected, 0.0)
        required_monthly = max(
            (target - request.current_savings * growth) / annuity_factor,
            0.0,
        )
        scenarios.append(
            RetirementScenario(
                annual_return_rate=annual_rate,
                projected_assets=round(projected, 2),
                retirement_target=round(target, 2),
                funding_gap=round(gap, 2),
                required_monthly_contribution=round(required_monthly, 2),
                additional_monthly_contribution=round(
                    max(required_monthly - request.monthly_contribution, 0.0), 2
                ),
            )
        )

    return RetirementProjection(
        years_to_retirement=years,
        future_annual_income_need=round(future_annual_income, 2),
        retirement_target=round(target, 2),
        scenarios=scenarios,
        assumptions={
            "contribution_timing": "end of month",
            "compounding": "monthly",
            "inflation_rate": request.inflation_rate,
            "withdrawal_rate": request.withdrawal_rate,
        },
        disclaimer=(
            "Educational projection only. Returns are assumptions, not forecasts, "
            "and taxes, fees, and sequence-of-returns risk are not modeled."
        ),
    )
