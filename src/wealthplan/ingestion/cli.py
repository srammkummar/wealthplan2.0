"""Command-line entry point for SEC filing ingestion."""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from wealthplan.config import Settings
from wealthplan.ingestion.pipeline import (
    JsonIngestionRegistry,
    PineconeChunkIndexer,
    SecEdgarClient,
    SecIngestionPipeline,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover and ingest the latest SEC filing into Pinecone"
    )
    parser.add_argument(
        "--ticker",
        required=True,
        help="Public-company ticker to resolve through the SEC ticker map.",
    )
    parser.add_argument(
        "--cik",
        default=None,
        help="Optional SEC CIK. When omitted, it is resolved from --ticker.",
    )
    parser.add_argument("--form", default="10-K")
    args = parser.parse_args()

    load_dotenv()
    settings = Settings.from_env()
    if not settings.sec_user_agent:
        raise RuntimeError(
            "WEALTHPLAN_SEC_USER_AGENT is required, for example: "
            "Your Name your.email@example.com"
        )

    registry = JsonIngestionRegistry(settings.ingestion_manifest_path)
    indexer = PineconeChunkIndexer(settings)
    with SecEdgarClient(
        settings.sec_user_agent,
        request_interval_seconds=settings.sec_request_interval_seconds,
    ) as source:
        result = SecIngestionPipeline(source, indexer, registry).ingest_latest(
            cik=args.cik,
            ticker=args.ticker,
            form_type=args.form,
        )
    print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    main()
