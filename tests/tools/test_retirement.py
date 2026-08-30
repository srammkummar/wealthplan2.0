from wealthplan.tools.retirement import (
    RetirementRequest,
    calculate_retirement_projection,
)


def test_readme_retirement_scenario_matches_expected_demo_values():
    result = calculate_retirement_projection(
        RetirementRequest(
            current_age=45,
            retirement_age=50,
            current_savings=800_000,
            monthly_contribution=8_000,
            desired_monthly_income_today=15_000,
            inflation_rate=0.025,
            withdrawal_rate=0.04,
            annual_return_rates=[0.04, 0.06, 0.08],
        )
    )

    base = next(s for s in result.scenarios if s.annual_return_rate == 0.06)
    assert round(result.retirement_target / 10_000) == 509
    assert round(base.projected_assets / 10_000) == 164
    assert round(base.funding_gap / 10_000) == 345
    assert 57_000 < base.required_monthly_contribution < 58_000


def test_zero_return_rate_is_supported():
    result = calculate_retirement_projection(
        RetirementRequest(
            current_age=40,
            retirement_age=41,
            current_savings=12_000,
            monthly_contribution=1_000,
            desired_monthly_income_today=1_000,
            inflation_rate=0,
            withdrawal_rate=0.04,
            annual_return_rates=[0],
        )
    )
    assert result.scenarios[0].projected_assets == 24_000
