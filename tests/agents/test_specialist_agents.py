from wealthplan.agents.goal_agent import run_goal_agent
from wealthplan.agents.portfolio_agent import run_portfolio_agent
from wealthplan.agents.research_agent import run_research_agent
from wealthplan.agents.review_agent import run_review_agent
from wealthplan.state import SupervisorRequest


def test_goal_agent_runs_retirement_tool():
    request = SupervisorRequest(
        user_query="Build retirement scenarios.",
        retirement_inputs={
            "current_age": 45,
            "retirement_age": 50,
            "current_savings": 800_000,
            "monthly_contribution": 8_000,
            "desired_monthly_income_today": 15_000,
            "inflation_rate": 0.025,
            "withdrawal_rate": 0.04,
            "annual_return_rates": [0.04, 0.06, 0.08],
        },
    )

    output = run_goal_agent(request)

    assert output["specialist"] == "goal_planning"
    assert output["status"] == "ok"
    assert len(output["data"]["scenarios"]) == 3


def test_portfolio_agent_runs_portfolio_tool():
    output = run_portfolio_agent(
        SupervisorRequest(user_query="Analyze my portfolio.")
    )

    assert output["specialist"] == "portfolio_analysis"
    assert output["status"] == "ok"
    assert output["data"]["positions"]


class FakeSnapshot:
    snapshot_label = "Historical test facts."

    def model_dump(self, mode="python"):
        return {"ticker": "MSFT", "mode": mode}


class FakeFundamentals:
    def get(self, ticker):
        assert ticker == "MSFT"
        return FakeSnapshot()


class FakeRetrieval:
    def search(self, *, query, ticker):
        assert query == "Summarize the SEC filing."
        assert ticker == "MSFT"
        return {
            "answerable": True,
            "message": "Grounded evidence returned.",
            "evidence": [
                {
                    "text": "Filing evidence",
                    "metadata": {"ticker": "MSFT", "form_type": "10-K"},
                }
            ],
        }


def test_research_agent_combines_facts_and_citations():
    output = run_research_agent(
        SupervisorRequest(
            user_query="Summarize the SEC filing.",
            ticker="MSFT",
        ),
        FakeRetrieval(),
        FakeFundamentals(),
    )

    assert output["specialist"] == "market_research"
    assert output["status"] == "ok"
    assert output["citations"][0]["form_type"] == "10-K"


def test_review_agent_passes_complete_labeled_output():
    reviewed = run_review_agent(
        {
            "request": {"user_query": "Analyze my portfolio."},
            "narrative": {"executive_summary": "Portfolio reviewed."},
            "write_authorized": False,
            "specialist_outputs": [
                {
                    "specialist": "portfolio_analysis",
                    "status": "ok",
                    "summary": "Portfolio analyzed.",
                    "data": {"total_market_value": 100_000},
                    "citations": [],
                    "warnings": ["Illustrative price snapshot."],
                }
            ],
            "execution_events": [],
        }
    )

    assert reviewed["review"]["decision"] == "pass"
    assert reviewed["status"] == "awaiting_approval"
