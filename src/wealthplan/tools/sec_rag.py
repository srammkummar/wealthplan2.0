"""Optional Pinecone plus Cohere SEC filing retrieval adapter."""

from __future__ import annotations

from collections.abc import Callable
from copy import deepcopy
import re
from typing import Any

from wealthplan.config import Settings
from wealthplan.resilience import TimestampedTTLCache, retry_call


class SecFilingSearchService:
    def __init__(
        self,
        settings: Settings,
        *,
        top_k: int = 10,
        top_n: int = 5,
        backend: Callable[[str, str], list[dict[str, Any]]] | None = None,
        cache_ttl_seconds: float | None = None,
        retry_attempts: int | None = None,
    ):
        self.settings = settings
        self.top_k = top_k
        self.top_n = top_n
        self.backend = backend
        self.retry_attempts = max(
            1,
            settings.external_retry_attempts
            if retry_attempts is None
            else retry_attempts,
        )
        self._cache = TimestampedTTLCache[
            tuple[str, str], dict[str, Any]
        ](
            settings.retrieval_cache_ttl_seconds
            if cache_ttl_seconds is None
            else cache_ttl_seconds
        )

    def search(self, query: str, ticker: str = "AAPL") -> dict[str, Any]:
        """Retrieve top-10 Pinecone passages and rerank to the best five."""

        ticker = ticker.strip().upper()
        if not re.fullmatch(r"[A-Z][A-Z0-9.-]{0,9}", ticker):
            return {
                "status": "invalid_ticker",
                "ticker": ticker,
                "answerable": False,
                "message": "Enter a valid public-company ticker symbol.",
                "evidence": [],
                "passage_count": 0,
            }
        if self.backend is None and not self.settings.rag_is_configured:
            return {
                "status": "not_configured",
                "ticker": ticker,
                "answerable": False,
                "message": (
                    "SEC retrieval requires OpenAI, Pinecone, and Cohere environment "
                    "configuration. No unsupported answer should be inferred."
                ),
                "evidence": [],
                "passage_count": 0,
            }

        cache_key = (ticker, " ".join(query.split()).casefold())
        cached = self._cache.get_fresh(cache_key)
        if cached is not None:
            result = deepcopy(cached.value)
            result.update(
                {
                    "cache_status": "fresh_cache",
                    "retrieved_at": cached.stored_at_iso,
                    "attempts": 0,
                    "passage_count": len(result.get("evidence", [])),
                }
            )
            return result

        try:
            evidence, attempts = retry_call(
                lambda: self._retrieve_once(query, ticker),
                attempts=self.retry_attempts,
                is_retryable=lambda exc: not isinstance(
                    exc, (ImportError, LookupError, ValueError)
                ),
            )
        except Exception as exc:
            stale = self._cache.get_stale(cache_key)
            if stale is not None:
                result = deepcopy(stale.value)
                result.update(
                    {
                        "cache_status": "stale_cache",
                        "retrieved_at": stale.stored_at_iso,
                        "attempts": self.retry_attempts,
                        "message": (
                            "The retrieval service is temporarily unavailable; "
                            "using clearly labeled cached filing evidence from "
                            f"{stale.stored_at_iso}."
                        ),
                        "passage_count": len(result.get("evidence", [])),
                    }
                )
                result["warnings"] = [
                    *result.get("warnings", []),
                    "Cached evidence may not include newer filings.",
                ]
                return result
            return {
                "status": "service_error",
                "ticker": ticker,
                "answerable": False,
                "message": (
                    "SEC filing retrieval is temporarily unavailable after "
                    f"{self.retry_attempts} attempts. Try again later."
                ),
                "evidence": [],
                "passage_count": 0,
                "cache_status": "unavailable",
                "retrieved_at": None,
                "attempts": self.retry_attempts,
                "error_type": type(exc).__name__,
            }

        result = {
            "status": "ok" if evidence else "insufficient_evidence",
            "ticker": ticker,
            "answerable": bool(evidence),
            "message": (
                "Use only the returned evidence and preserve its source metadata."
                if evidence
                else "No supporting passages were retrieved."
            ),
            "evidence": evidence,
            "passage_count": len(evidence),
            "cache_status": "live",
            "attempts": attempts,
        }
        record = self._cache.set(cache_key, deepcopy(result))
        result["retrieved_at"] = record.stored_at_iso
        return result

    def _retrieve_once(self, query: str, ticker: str) -> list[dict[str, Any]]:
        """Perform one retrieval attempt; retry and fallback are handled by search."""

        if self.backend is not None:
            return self.backend(query, ticker)

        try:
            from langchain_cohere import CohereRerank
            from langchain_openai import OpenAIEmbeddings
            from langchain_pinecone import PineconeVectorStore
            from pinecone import Pinecone
        except ImportError as exc:
            raise RuntimeError(
                "Install the RAG dependencies with: uv sync --extra rag"
            ) from exc

        embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            api_key=self.settings.openai_api_key,
        )
        pinecone = Pinecone(api_key=self.settings.pinecone_api_key)
        index = pinecone.Index(self.settings.pinecone_index_name)
        vector_store = PineconeVectorStore(
            index=index,
            embedding=embeddings,
            namespace=self.settings.pinecone_namespace,
        )
        candidates = vector_store.similarity_search(
            query,
            k=self.top_k,
            filter={"ticker": ticker},
        )
        reranker = CohereRerank(
            model=self.settings.cohere_rerank_model,
            top_n=self.top_n,
        )
        ranked = reranker.compress_documents(candidates, query)
        evidence = [
            {
                "text": document.page_content,
                "metadata": document.metadata,
            }
            for document in ranked
        ]
        return evidence
