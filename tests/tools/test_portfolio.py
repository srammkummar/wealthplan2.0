from wealthplan.tools.portfolio import DEMO_HOLDINGS, analyze_portfolio


def test_demo_portfolio_matches_readme_totals():
    result = analyze_portfolio(DEMO_HOLDINGS)

    assert result.total_market_value == 795_500
    assert result.total_cost_basis == 675_000
    assert result.unrealized_gain_loss == 120_500
    assert result.positions[0].ticker == "AAPL"
    assert any("Technology" in flag for flag in result.concentration_flags)
