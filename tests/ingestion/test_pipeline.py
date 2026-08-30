from pathlib import Path

from wealthplan.ingestion.pipeline import (
    JsonIngestionRegistry,
    SecEdgarClient,
    SecFilingReference,
    SecIngestionPipeline,
    clean_filing_html,
    deduplicate_item_sections,
)
from wealthplan.ingestion.chunking import extract_item_sections


SUBMISSIONS_PAYLOAD = {
    "name": "Apple Inc.",
    "filings": {
        "recent": {
            "form": ["10-Q", "10-K"],
            "filingDate": ["2026-08-01", "2025-10-31"],
            "reportDate": ["2026-06-27", "2025-09-27"],
            "accessionNumber": [
                "0000320193-26-000001",
                "0000320193-25-000079",
            ],
            "primaryDocument": ["aapl-20260627.htm", "aapl-20250927.htm"],
        }
    },
}


SAMPLE_HTML = """
<html><head><style>hidden css</style><script>do_not_keep()</script></head><body>
  <h2>ITEM 1. BUSINESS</h2><p>1</p>
  <h2>ITEM 1A. RISK FACTORS</h2><p>5</p>
  <h1>ITEM 1. BUSINESS</h1>
  <p>Apple designs and sells products and services around the world.</p>
  <p>Its operating model depends on suppliers and manufacturing partners.</p>
  <h1>ITEM 1A. RISK FACTORS</h1>
  <p>Supply disruptions and geopolitical events could affect production.</p>
  <p>These risks may also increase costs or delay product availability.</p>
</body></html>
"""


class StubDiscoveryClient(SecEdgarClient):
    def __init__(self, payload):
        self.payload = payload

    def _get_json(self, url):
        return self.payload


class RoutingDiscoveryClient(SecEdgarClient):
    def __init__(self, ticker_payload, submissions_payload):
        self.ticker_payload = ticker_payload
        self.submissions_payload = submissions_payload
        self._ticker_map = None

    def _get_json(self, url):
        if "company_tickers" in url:
            return self.ticker_payload
        return self.submissions_payload


class FakeSource:
    def __init__(self):
        self.download_calls = 0
        self.filing = SecFilingReference(
            cik="0000320193",
            ticker="AAPL",
            company_name="Apple Inc.",
            form_type="10-K",
            filing_date="2025-10-31",
            report_date="2025-09-27",
            accession_number="0000320193-25-000079",
            primary_document="aapl-20250927.htm",
            source_url=(
                "https://www.sec.gov/Archives/edgar/data/320193/"
                "000032019325000079/aapl-20250927.htm"
            ),
        )

    def discover_latest(self, *, cik, ticker, form_type):
        return self.filing

    def download_filing(self, filing):
        self.download_calls += 1
        return SAMPLE_HTML


class CapturingIndexer:
    def __init__(self):
        self.calls = 0
        self.chunks = []

    def index_chunks(self, chunks):
        self.calls += 1
        self.chunks = chunks
        return len(chunks)


def test_discovers_latest_requested_form_and_builds_archive_url():
    client = StubDiscoveryClient(SUBMISSIONS_PAYLOAD)
    filing = client.discover_latest(cik="320193", ticker="aapl", form_type="10-K")

    assert filing.company_name == "Apple Inc."
    assert filing.accession_number == "0000320193-25-000079"
    assert filing.source_url.endswith(
        "/320193/000032019325000079/aapl-20250927.htm"
    )


def test_resolves_ticker_and_discovers_filing_without_supplied_cik():
    ticker_payload = {
        "0": {
            "cik_str": 320193,
            "ticker": "AAPL",
            "title": "Apple Inc.",
        }
    }
    client = RoutingDiscoveryClient(ticker_payload, SUBMISSIONS_PAYLOAD)

    resolved = client.resolve_ticker("aapl")
    filing = client.discover_latest(cik=None, ticker="aapl", form_type="10-K")

    assert resolved == {
        "ticker": "AAPL",
        "cik": "0000320193",
        "company_name": "Apple Inc.",
    }
    assert filing.cik == "0000320193"
    assert filing.ticker == "AAPL"


def test_cleaning_removes_executable_markup_and_toc_sections_are_deduplicated():
    cleaned = clean_filing_html(SAMPLE_HTML.replace("Apple designs", "Apple\x00 designs"))
    assert "do_not_keep" not in cleaned
    assert "hidden css" not in cleaned
    assert "\x00" not in cleaned

    sections = extract_item_sections(
        cleaned,
        document_id="aapl-test",
        ticker="AAPL",
        form_type="10-K",
        filing_date="2025-10-31",
        accession_number="0000320193-25-000079",
        source_url="https://example.test/filing",
    )
    sections = deduplicate_item_sections(sections)

    assert [section.section_id for section in sections] == ["item-1", "item-1a"]
    assert "manufacturing partners" in sections[0].text
    assert sections[0].text != "1"


def test_pipeline_indexes_once_and_skips_completed_accession(tmp_path: Path):
    source = FakeSource()
    indexer = CapturingIndexer()
    registry = JsonIngestionRegistry(tmp_path / "ingestion_manifest.json")
    pipeline = SecIngestionPipeline(source, indexer, registry)

    first = pipeline.ingest_latest(cik="320193", ticker="AAPL")
    second = pipeline.ingest_latest(cik="320193", ticker="AAPL")

    assert first.status == "completed"
    assert first.section_count == 2
    assert first.chunk_count == len(indexer.chunks)
    assert first.indexed_count == len(indexer.chunks)
    assert second.status == "skipped_duplicate"
    assert second.indexed_count == 0
    assert source.download_calls == 1
    assert indexer.calls == 1
    assert all(chunk.accession_number == first.accession_number for chunk in indexer.chunks)
    assert all(chunk.section_id in {"item-1", "item-1a"} for chunk in indexer.chunks)


def test_sec_client_requires_declared_contact_user_agent():
    try:
        SecEdgarClient("anonymous-bot")
    except ValueError as exc:
        assert "contact email" in str(exc)
    else:
        raise AssertionError("Expected an undeclared user agent to be rejected")
