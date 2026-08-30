"""SEC filing discovery, cleaning, chunking, deduplication, and indexing."""

from __future__ import annotations

from datetime import UTC, datetime
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Protocol

from bs4 import BeautifulSoup
import httpx
from pydantic import BaseModel, Field

from wealthplan.ingestion.chunking import (
    ChunkingConfig,
    FilingChunk,
    FilingSection,
    chunk_filing_sections,
    extract_item_sections,
)
from wealthplan.config import Settings


SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik}.json"
TICKER_MAP_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANY_FACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
ARCHIVE_URL = (
    "https://www.sec.gov/Archives/edgar/data/{cik}/{accession_compact}/{document}"
)


class SecFilingReference(BaseModel):
    cik: str
    ticker: str
    company_name: str
    form_type: str
    filing_date: str
    report_date: str | None = None
    accession_number: str
    primary_document: str
    source_url: str

    @property
    def document_id(self) -> str:
        return f"{self.ticker.lower()}-{self.accession_number}"


class IngestionResult(BaseModel):
    status: str
    accession_number: str
    document_id: str
    source_url: str
    section_count: int = 0
    chunk_count: int = 0
    indexed_count: int = 0
    manifest_path: str


class SecFilingSource(Protocol):
    def discover_latest(
        self, *, cik: str | None, ticker: str, form_type: str
    ) -> SecFilingReference: ...

    def download_filing(self, filing: SecFilingReference) -> str: ...


class ChunkIndexer(Protocol):
    def index_chunks(self, chunks: list[FilingChunk]) -> int: ...


class SecEdgarClient:
    """Small SEC client that identifies itself and throttles every request."""

    def __init__(
        self,
        user_agent: str,
        *,
        request_interval_seconds: float = 0.2,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not user_agent or "@" not in user_agent:
            raise ValueError(
                "WEALTHPLAN_SEC_USER_AGENT must identify you and include a contact email"
            )
        if request_interval_seconds < 0.1:
            raise ValueError(
                "SEC request interval must be at least 0.1 seconds (10 requests/second)"
            )
        self.request_interval_seconds = request_interval_seconds
        self._last_request_at = 0.0
        self._ticker_map: dict[str, dict[str, str]] | None = None
        self._client = httpx.Client(
            headers={
                "User-Agent": user_agent,
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json, text/html;q=0.9, */*;q=0.8",
            },
            timeout=timeout_seconds,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "SecEdgarClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        remaining = self.request_interval_seconds - elapsed
        if remaining > 0:
            time.sleep(remaining)

    def _get(self, url: str) -> httpx.Response:
        self._throttle()
        response = self._client.get(url)
        self._last_request_at = time.monotonic()
        response.raise_for_status()
        return response

    def _get_json(self, url: str) -> dict[str, Any]:
        return self._get(url).json()

    def resolve_ticker(self, ticker: str) -> dict[str, str]:
        """Resolve a listed-company ticker to its zero-padded SEC CIK."""

        normalized = ticker.strip().upper()
        if not normalized:
            raise ValueError("ticker is required")
        if self._ticker_map is None:
            payload = self._get_json(TICKER_MAP_URL)
            self._ticker_map = {
                str(entry["ticker"]).upper(): {
                    "ticker": str(entry["ticker"]).upper(),
                    "cik": str(entry["cik_str"]).zfill(10),
                    "company_name": str(entry["title"]),
                }
                for entry in payload.values()
            }
        try:
            return self._ticker_map[normalized]
        except KeyError as exc:
            raise LookupError(f"Ticker {normalized} was not found in the SEC map") from exc

    def get_company_facts(self, cik: str) -> dict[str, Any]:
        normalized_cik = str(cik).lstrip("0").zfill(10)
        return self._get_json(COMPANY_FACTS_URL.format(cik=normalized_cik))

    def discover_latest(
        self, *, cik: str | None, ticker: str, form_type: str
    ) -> SecFilingReference:
        resolved = self.resolve_ticker(ticker) if cik is None else None
        normalized_cik = (
            resolved["cik"]
            if resolved
            else str(cik).lstrip("0").zfill(10)
        )
        payload = self._get_json(SUBMISSIONS_URL.format(cik=normalized_cik))
        recent = payload.get("filings", {}).get("recent", {})
        forms = recent.get("form", [])
        try:
            index = next(
                position
                for position, form in enumerate(forms)
                if form.upper() == form_type.upper()
            )
        except StopIteration as exc:
            raise LookupError(
                f"No recent {form_type} filing found for CIK {normalized_cik}"
            ) from exc

        accession = recent["accessionNumber"][index]
        primary_document = recent["primaryDocument"][index]
        archive_cik = str(int(normalized_cik))
        source_url = ARCHIVE_URL.format(
            cik=archive_cik,
            accession_compact=accession.replace("-", ""),
            document=primary_document,
        )
        report_dates = recent.get("reportDate", [])
        return SecFilingReference(
            cik=normalized_cik,
            ticker=ticker.upper(),
            company_name=payload.get("name", ticker.upper()),
            form_type=recent["form"][index],
            filing_date=recent["filingDate"][index],
            report_date=report_dates[index] if index < len(report_dates) else None,
            accession_number=accession,
            primary_document=primary_document,
            source_url=source_url,
        )

    def download_filing(self, filing: SecFilingReference) -> str:
        return self._get(filing.source_url).text


def clean_filing_html(html: str) -> str:
    """Remove executable/visual markup while preserving block and table boundaries."""

    soup = BeautifulSoup(html, "html.parser")
    for element in soup(["script", "style", "noscript", "svg", "canvas"]):
        element.decompose()
    for element in soup.find_all(["br"]):
        element.replace_with("\n")
    for element in soup.find_all(
        [
            "p",
            "div",
            "section",
            "article",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "tr",
            "li",
        ]
    ):
        element.insert_before("\n")
        element.append("\n")
    for element in soup.find_all(["td", "th"]):
        element.append(" ")

    text = (
        soup.get_text("", strip=False)
        .replace("\xa0", " ")
        .replace("\x00", "")
    )
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    compact = "\n".join(lines)
    compact = re.sub(r"\n{3,}", "\n\n", compact)
    return compact.strip()


def deduplicate_item_sections(sections: list[FilingSection]) -> list[FilingSection]:
    """Keep the longest occurrence of repeated Item sections (usually TOC copies)."""

    best: dict[str, tuple[int, FilingSection]] = {}
    for position, section in enumerate(sections):
        current = best.get(section.section_id)
        if current is None or len(section.text) > len(current[1].text):
            best[section.section_id] = (position, section)
    return [section for _, section in sorted(best.values(), key=lambda item: item[0])]


class JsonIngestionRegistry:
    """Local manifest used until the PostgreSQL ingestion table is introduced."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"accessions": {}}
        return json.loads(self.path.read_text(encoding="utf-8"))

    def get(self, accession_number: str) -> dict[str, Any] | None:
        return self._read().get("accessions", {}).get(accession_number)

    def record(
        self,
        filing: SecFilingReference,
        *,
        status: str,
        section_count: int = 0,
        chunk_count: int = 0,
        indexed_count: int = 0,
        error: str | None = None,
    ) -> None:
        manifest = self._read()
        manifest.setdefault("accessions", {})[filing.accession_number] = {
            "status": status,
            "document_id": filing.document_id,
            "ticker": filing.ticker,
            "form_type": filing.form_type,
            "filing_date": filing.filing_date,
            "source_url": filing.source_url,
            "section_count": section_count,
            "chunk_count": chunk_count,
            "indexed_count": indexed_count,
            "error": error,
            "updated_at": datetime.now(UTC).isoformat(),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(f"{self.path.suffix}.tmp")
        temporary.write_text(
            json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
        )
        os.replace(temporary, self.path)


class PineconeChunkIndexer:
    def __init__(self, settings: Settings, *, batch_size: int = 100) -> None:
        if not settings.indexing_is_configured:
            raise RuntimeError(
                "Pinecone indexing requires OPENAI_API_KEY, PINECONE_API_KEY, "
                "and WEALTHPLAN_PINECONE_INDEX_NAME"
            )
        self.settings = settings
        self.batch_size = batch_size

    def index_chunks(self, chunks: list[FilingChunk]) -> int:
        try:
            from langchain_core.documents import Document
            from langchain_openai import OpenAIEmbeddings
            from langchain_pinecone import PineconeVectorStore
            from pinecone import Pinecone
        except ImportError as exc:
            raise RuntimeError(
                "Install ingestion dependencies with: uv sync --extra rag"
            ) from exc

        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=self.settings.openai_api_key,
        )
        pinecone = Pinecone(api_key=self.settings.pinecone_api_key)
        vector_store = PineconeVectorStore(
            index=pinecone.Index(self.settings.pinecone_index_name),
            embedding=embeddings,
            namespace=self.settings.pinecone_namespace,
        )
        indexed = 0
        for start in range(0, len(chunks), self.batch_size):
            batch = chunks[start : start + self.batch_size]
            documents = []
            ids = []
            for chunk in batch:
                metadata = chunk.model_dump(exclude={"text", "chunk_id"})
                documents.append(Document(page_content=chunk.text, metadata=metadata))
                ids.append(chunk.chunk_id)
            vector_store.add_documents(documents=documents, ids=ids)
            indexed += len(batch)
        return indexed


class SecIngestionPipeline:
    def __init__(
        self,
        source: SecFilingSource,
        indexer: ChunkIndexer,
        registry: JsonIngestionRegistry,
        *,
        chunking_config: ChunkingConfig | None = None,
    ) -> None:
        self.source = source
        self.indexer = indexer
        self.registry = registry
        self.chunking_config = chunking_config or ChunkingConfig()

    def ingest_latest(
        self, *, cik: str | None = None, ticker: str, form_type: str = "10-K"
    ) -> IngestionResult:
        filing = self.source.discover_latest(
            cik=cik, ticker=ticker, form_type=form_type
        )
        existing = self.registry.get(filing.accession_number)
        if existing and existing.get("status") == "completed":
            return IngestionResult(
                status="skipped_duplicate",
                accession_number=filing.accession_number,
                document_id=filing.document_id,
                source_url=filing.source_url,
                section_count=existing.get("section_count", 0),
                chunk_count=existing.get("chunk_count", 0),
                indexed_count=0,
                manifest_path=str(self.registry.path),
            )

        self.registry.record(filing, status="started")
        try:
            cleaned = clean_filing_html(self.source.download_filing(filing))
            sections = extract_item_sections(
                cleaned,
                document_id=filing.document_id,
                ticker=filing.ticker,
                form_type=filing.form_type,
                filing_date=filing.filing_date,
                accession_number=filing.accession_number,
                source_url=filing.source_url,
            )
            sections = deduplicate_item_sections(sections)
            if not sections:
                raise ValueError("No SEC Item sections were extracted from the filing")
            chunks = chunk_filing_sections(sections, self.chunking_config)
            if not chunks:
                raise ValueError("No chunks were constructed from the filing sections")
            indexed_count = self.indexer.index_chunks(chunks)
            self.registry.record(
                filing,
                status="completed",
                section_count=len(sections),
                chunk_count=len(chunks),
                indexed_count=indexed_count,
            )
            return IngestionResult(
                status="completed",
                accession_number=filing.accession_number,
                document_id=filing.document_id,
                source_url=filing.source_url,
                section_count=len(sections),
                chunk_count=len(chunks),
                indexed_count=indexed_count,
                manifest_path=str(self.registry.path),
            )
        except Exception as exc:
            self.registry.record(filing, status="failed", error=str(exc))
            raise
