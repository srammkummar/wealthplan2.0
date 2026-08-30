# SEC ingestion

The ingestion command discovers the latest requested filing through the SEC submissions API, downloads the primary HTML document, removes executable and visual markup, extracts SEC Item sections, builds paragraph-aligned chunks, and indexes those chunks in Pinecone.

## Configuration

Copy `.env.example` to `.env` and provide:

```env
OPENAI_API_KEY=
PINECONE_API_KEY=
WEALTHPLAN_PINECONE_INDEX_NAME=
WEALTHPLAN_PINECONE_NAMESPACE=sec-filings

WEALTHPLAN_SEC_USER_AGENT=Your Name your.email@example.com
WEALTHPLAN_SEC_REQUEST_INTERVAL_SECONDS=0.2
WEALTHPLAN_INGESTION_MANIFEST_PATH=.data/ingestion_manifest.json
```

The Pinecone index must use 1,536 dimensions and cosine similarity because ingestion uses OpenAI `text-embedding-3-small`.

The SEC user agent must identify the requester and include a contact email. The default 0.2-second interval limits this command to five requests per second, below the SEC's published maximum of 10 requests per second.

## Install and run

```powershell
uv sync --extra rag --extra dev
uv run wealthplan-ingest --ticker MSFT --form 10-K
```

The command resolves `MSFT` (or another SEC-listed ticker) to its CIK using the SEC company-ticker file. Supply `--cik` only when you need to override that mapping.

The result reports the accession, source URL, section count, chunk count, and indexed count. The local manifest records `started`, `completed`, or `failed` for each accession.

Running the command again for a completed accession returns `skipped_duplicate`. Pinecone receives stable chunk IDs, so an interrupted rerun also replaces matching vectors rather than generating random duplicates.

## Processing sequence

```text
SEC ticker map -> ticker-to-CIK resolution
  -> SEC submissions JSON
  -> select latest requested form
  -> download primary filing HTML
  -> remove scripts/styles and preserve block boundaries
  -> extract SEC Item sections
  -> discard shorter duplicate Item occurrences (usually table of contents)
  -> construct paragraph-aligned chunks inside each Item
  -> embed in batches and upsert stable IDs to Pinecone
  -> record completion in the manifest
```

## Verification without credentials

The tests use local HTML and fake SEC/Pinecone adapters; they do not contact external services:

```powershell
uv run pytest tests/ingestion/test_pipeline.py -v
```

## Current boundary

This is the course-ready ingestion path. A later PostgreSQL phase will replace the local JSON manifest with a transactional ingestion table. Production hardening should also add DOM-aware subsection headings, repeated page-header removal, richer retries, and scheduled discovery.

Official references:

- <https://www.sec.gov/search-filings/edgar-application-programming-interfaces>
- <https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data>
