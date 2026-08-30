from wealthplan.config import Settings
from wealthplan.tools.sec_rag import SecFilingSearchService


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


def test_retrieval_accepts_other_valid_tickers_before_configuration_check():
    result = SecFilingSearchService(settings_without_secrets()).search(
        "What are its risks?", ticker="TSLA"
    )
    assert result["status"] == "not_configured"
    assert result["answerable"] is False


def test_retrieval_rejects_invalid_ticker_syntax():
    result = SecFilingSearchService(settings_without_secrets()).search(
        "What are its risks?", ticker="not a ticker"
    )
    assert result["status"] == "invalid_ticker"
    assert result["answerable"] is False


def test_retrieval_does_not_guess_when_unconfigured():
    result = SecFilingSearchService(settings_without_secrets()).search(
        "What are Apple's supply chain risks?", ticker="AAPL"
    )
    assert result["status"] == "not_configured"
    assert result["evidence"] == []


def test_retrieval_retries_once_then_returns_live_evidence():
    calls = 0

    def flaky_backend(query, ticker):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise ConnectionError("simulated Pinecone outage")
        return [{"text": f"Evidence for {query}", "metadata": {"ticker": ticker}}]

    service = SecFilingSearchService(
        settings_without_secrets(), backend=flaky_backend, retry_attempts=2
    )
    result = service.search("What are its risks?", ticker="MSFT")

    assert result["status"] == "ok"
    assert result["cache_status"] == "live"
    assert result["attempts"] == 2
    assert calls == 2


def test_retrieval_uses_fresh_cache_without_an_external_call():
    calls = 0

    def backend(_query, ticker):
        nonlocal calls
        calls += 1
        return [{"text": "Evidence", "metadata": {"ticker": ticker}}]

    service = SecFilingSearchService(settings_without_secrets(), backend=backend)
    service.search("What are its risks?", ticker="MSFT")
    cached = service.search("  What are its risks?  ", ticker="msft")

    assert cached["cache_status"] == "fresh_cache"
    assert cached["attempts"] == 0
    assert calls == 1


def test_retrieval_uses_labeled_stale_evidence_during_outage():
    should_fail = False

    def backend(_query, ticker):
        if should_fail:
            raise ConnectionError("simulated Pinecone outage")
        return [{"text": "Evidence", "metadata": {"ticker": ticker}}]

    service = SecFilingSearchService(
        settings_without_secrets(),
        backend=backend,
        cache_ttl_seconds=0,
        retry_attempts=2,
    )
    service.search("What are its risks?", ticker="MSFT")
    should_fail = True
    stale = service.search("What are its risks?", ticker="MSFT")

    assert stale["answerable"] is True
    assert stale["cache_status"] == "stale_cache"
    assert stale["warnings"] == ["Cached evidence may not include newer filings."]


def test_retrieval_returns_safe_service_error_without_cache():
    def unavailable_backend(_query, _ticker):
        raise ConnectionError("secret connection detail")

    result = SecFilingSearchService(
        settings_without_secrets(),
        backend=unavailable_backend,
        retry_attempts=2,
    ).search("What are its risks?", ticker="MSFT")

    assert result["status"] == "service_error"
    assert result["answerable"] is False
    assert result["attempts"] == 2
    assert "secret connection detail" not in result["message"]
