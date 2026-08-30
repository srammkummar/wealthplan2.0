from wealthplan.config import Settings
from wealthplan.tools.fundamentals import (
    SecCompanyFactsService,
    get_company_fundamentals,
)


def settings_without_secrets() -> Settings:
    return Settings(
        openai_api_key=None,
        openai_model="test-model",
        pinecone_api_key=None,
        pinecone_index_name=None,
        pinecone_namespace="sec-filings",
        cohere_api_key=None,
        cohere_rerank_model="rerank-v3.5",
        postgres_dsn=None,
    )


def annual_fact(value, *, unit="USD"):
    return {
        "units": {
            unit: [
                {
                    "start": "2024-07-01",
                    "end": "2025-06-30",
                    "val": value,
                    "form": "10-K",
                    "fy": 2025,
                    "filed": "2025-07-30",
                    "accn": "0000789019-25-000100",
                }
            ]
        }
    }


class FakeCompanyFactsSource:
    def resolve_ticker(self, ticker):
        assert ticker == "MSFT"
        return {
            "ticker": "MSFT",
            "cik": "0000789019",
            "company_name": "MICROSOFT CORP",
        }

    def get_company_facts(self, cik):
        assert cik == "0000789019"
        return {
            "entityName": "MICROSOFT CORP",
            "facts": {
                "us-gaap": {
                    "RevenueFromContractWithCustomerExcludingAssessedTax": annual_fact(
                        250_000_000_000
                    ),
                    "EarningsPerShareDiluted": annual_fact(
                        12.34, unit="USD/shares"
                    ),
                    "NetCashProvidedByUsedInOperatingActivities": annual_fact(
                        136_000_000_000
                    ),
                    "PaymentsToAcquirePropertyPlantAndEquipment": annual_fact(
                        30_000_000_000
                    ),
                    "PaymentsForRepurchaseOfCommonStock": annual_fact(
                        20_000_000_000
                    ),
                }
            },
        }


class FlakyCompanyFactsSource(FakeCompanyFactsSource):
    def __init__(self, failures=1):
        self.failures = failures
        self.facts_calls = 0

    def get_company_facts(self, cik):
        self.facts_calls += 1
        if self.facts_calls <= self.failures:
            raise ConnectionError("simulated SEC outage")
        return super().get_company_facts(cik)


def test_aapl_snapshot_is_fixed_and_has_no_valuation():
    snapshot = get_company_fundamentals("aapl")

    assert snapshot is not None
    assert snapshot.annual.revenue_millions == 416_161
    assert snapshot.annual.free_cash_flow_millions == 98_767
    assert snapshot.valuation_available is False
    assert "not live" in snapshot.snapshot_label.lower()


def test_unsupported_ticker_returns_none():
    assert get_company_fundamentals("TSLA") is None


def test_sec_company_facts_supports_a_non_aapl_ticker():
    service = SecCompanyFactsService(
        settings_without_secrets(), source=FakeCompanyFactsSource()
    )

    snapshot = service.get("msft")

    assert snapshot is not None
    assert snapshot.ticker == "MSFT"
    assert snapshot.company == "MICROSOFT CORP"
    assert snapshot.annual.revenue_millions == 250_000
    assert snapshot.annual.diluted_eps == 12.34
    assert snapshot.annual.free_cash_flow_millions == 106_000
    assert snapshot.valuation_available is False
    assert snapshot.cik == "0000789019"
    assert snapshot.cache_status == "live"
    assert snapshot.retrieved_at


def test_sec_company_facts_retries_once_then_succeeds():
    source = FlakyCompanyFactsSource(failures=1)
    service = SecCompanyFactsService(
        settings_without_secrets(), source=source, retry_attempts=2
    )

    snapshot = service.get("MSFT")

    assert snapshot is not None
    assert snapshot.cache_status == "live"
    assert source.facts_calls == 2


def test_sec_company_facts_marks_fresh_cache():
    source = FlakyCompanyFactsSource(failures=0)
    service = SecCompanyFactsService(settings_without_secrets(), source=source)

    service.get("MSFT")
    cached = service.get("MSFT")

    assert cached is not None
    assert cached.cache_status == "fresh_cache"
    assert source.facts_calls == 1


def test_sec_company_facts_uses_labeled_stale_cache_during_outage():
    source = FlakyCompanyFactsSource(failures=0)
    service = SecCompanyFactsService(
        settings_without_secrets(),
        source=source,
        cache_ttl_seconds=0,
        retry_attempts=2,
    )
    service.get("MSFT")
    source.failures = 100

    stale = service.get("MSFT")

    assert stale is not None
    assert stale.cache_status == "stale_cache"
    assert any("cached data" in note for note in stale.notes)
    assert source.facts_calls == 3
