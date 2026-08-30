"""Environment-backed application configuration."""

from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings. Secret values are read from the environment only."""

    openai_api_key: str | None
    openai_model: str
    pinecone_api_key: str | None
    pinecone_index_name: str | None
    pinecone_namespace: str
    cohere_api_key: str | None
    cohere_rerank_model: str
    postgres_dsn: str | None
    sec_user_agent: str | None = None
    sec_request_interval_seconds: float = 0.2
    ingestion_manifest_path: str = ".data/ingestion_manifest.json"
    external_retry_attempts: int = 2
    sec_cache_ttl_seconds: float = 3600.0
    retrieval_cache_ttl_seconds: float = 900.0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("WEALTHPLAN_OPENAI_MODEL", "gpt-5-mini"),
            pinecone_api_key=os.getenv("PINECONE_API_KEY"),
            pinecone_index_name=os.getenv("WEALTHPLAN_PINECONE_INDEX_NAME"),
            pinecone_namespace=os.getenv(
                "WEALTHPLAN_PINECONE_NAMESPACE", "sec-filings"
            ),
            cohere_api_key=os.getenv("COHERE_API_KEY"),
            cohere_rerank_model=os.getenv(
                "WEALTHPLAN_COHERE_RERANK_MODEL", "rerank-v3.5"
            ),
            postgres_dsn=os.getenv("WEALTHPLAN_POSTGRES_DSN"),
            sec_user_agent=os.getenv("WEALTHPLAN_SEC_USER_AGENT"),
            sec_request_interval_seconds=float(
                os.getenv("WEALTHPLAN_SEC_REQUEST_INTERVAL_SECONDS", "0.2")
            ),
            ingestion_manifest_path=os.getenv(
                "WEALTHPLAN_INGESTION_MANIFEST_PATH",
                ".data/ingestion_manifest.json",
            ),
            external_retry_attempts=int(
                os.getenv("WEALTHPLAN_EXTERNAL_RETRY_ATTEMPTS", "2")
            ),
            sec_cache_ttl_seconds=float(
                os.getenv("WEALTHPLAN_SEC_CACHE_TTL_SECONDS", "3600")
            ),
            retrieval_cache_ttl_seconds=float(
                os.getenv("WEALTHPLAN_RETRIEVAL_CACHE_TTL_SECONDS", "900")
            ),
        )

    @property
    def rag_is_configured(self) -> bool:
        return all(
            (
                self.openai_api_key,
                self.pinecone_api_key,
                self.pinecone_index_name,
                self.cohere_api_key,
            )
        )

    @property
    def indexing_is_configured(self) -> bool:
        return all(
            (
                self.openai_api_key,
                self.pinecone_api_key,
                self.pinecone_index_name,
            )
        )
