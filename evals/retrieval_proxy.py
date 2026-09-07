"""Interim concept-label proxy for SEC retrieval quality.

These labels are evaluator references, not modifications to the frozen golden
dataset. They provide practical measurement coverage until passage-level
relevance judgments or exact relevant document IDs are reviewed and approved.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from evals.evaluation_schema import AgentRunResult, GoldenDatasetCase


RETRIEVAL_PROXY_VERSION = "keyword_context_proxy_v1"

# A passage is considered proxy-relevant when it contains at least one
# case-specific phrase. These labels intentionally favor transparent recall and
# are not a substitute for human passage-relevance judgments.
SEC_RETRIEVAL_CONCEPT_LABELS: dict[str, tuple[str, ...]] = {
    "WP-001": (
        "reportable segment",
        "geographic segment",
        "americas",
        "greater china",
        "rest of asia pacific",
    ),
    "WP-002": ("risk factors", "business risks", "could adversely", "material adverse"),
    "WP-003": ("competition", "competitive", "product cycles", "pricing", "innovation"),
    "WP-004": ("supply chain", "supplier", "manufacturing", "outsourcing", "components"),
    "WP-005": ("services net sales", "services revenue", "services business", "services"),
    "WP-006": ("iphone", "mac", "ipad", "wearables", "products"),
    "WP-007": ("legal proceedings", "litigation", "regulatory", "antitrust", "legal risk"),
    "WP-008": ("international", "foreign currency", "trade", "geopolitical", "greater china"),
    "WP-009": ("products", "services", "customers", "distribution", "geographic"),
    "WP-010": ("research and development", "r&d", "innovation", "development expense"),
    "WP-021": ("risk factors", "business risks", "could adversely", "material adverse"),
    "WP-022": ("china", "greater china"),
    "WP-023": ("risk factors", "business risks", "could adversely", "material adverse"),
    "WP-024": ("lawsuit", "litigation", "legal proceedings", "intellectual property"),
    "WP-033": ("net sales", "revenue", "416,161", "fiscal 2025"),
    "WP-034": ("growth", "strategy", "forward-looking", "research and development"),
}


@dataclass(frozen=True, slots=True)
class RetrievalProxyResult:
    scores: dict[str, float]
    labels: tuple[str, ...]
    relevant_positions: tuple[int, ...]
    version: str = RETRIEVAL_PROXY_VERSION

    @property
    def detail(self) -> str:
        positions = ", ".join(str(value) for value in self.relevant_positions)
        return (
            f"{self.version}; labels={list(self.labels)!r}; "
            f"proxy-relevant ranks=[{positions}]"
        )


def _normalized_text(value: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9%$]+", " ", value.casefold()).split())


def _fallback_labels(case: GoldenDatasetCase) -> tuple[str, ...]:
    stop_words = {
        "about",
        "according",
        "answer",
        "apple",
        "available",
        "filing",
        "from",
        "only",
        "retrieved",
        "should",
        "supporting",
        "their",
        "using",
        "what",
        "when",
        "with",
    }
    tokens = re.findall(
        r"[a-z][a-z0-9-]{3,}",
        f"{case.user_query} {case.expected_answer_points}".casefold(),
    )
    return tuple(dict.fromkeys(token for token in tokens if token not in stop_words))[:12]


def score_retrieval_proxy(
    case: GoldenDatasetCase,
    run: AgentRunResult,
    *,
    k: int = 5,
) -> RetrievalProxyResult | None:
    """Score top-k contexts against transparent case-specific concept labels.

    Returns ``None`` for non-SEC cases. No retrieved contexts is a measurable
    retrieval miss (all three proxy scores are zero), not an unavailable metric.
    """

    if case.task_type != "sec_rag":
        return None
    if k <= 0:
        raise ValueError("k must be greater than zero")

    labels = SEC_RETRIEVAL_CONCEPT_LABELS.get(case.case_id) or _fallback_labels(case)
    normalized_labels = tuple(_normalized_text(label) for label in labels)
    contexts = run.retrieved_contexts[:k]
    relevant_positions = tuple(
        rank
        for rank, context in enumerate(contexts, start=1)
        if any(label in _normalized_text(context) for label in normalized_labels)
    )
    hit_at_5 = 1.0 if relevant_positions else 0.0
    reciprocal_rank = 1.0 / relevant_positions[0] if relevant_positions else 0.0
    context_precision = (
        len(relevant_positions) / len(contexts) if contexts else 0.0
    )
    return RetrievalProxyResult(
        scores={
            "hit_at_5": hit_at_5,
            "mrr": reciprocal_rank,
            "context_precision": context_precision,
        },
        labels=labels,
        relevant_positions=relevant_positions,
    )


__all__ = [
    "RETRIEVAL_PROXY_VERSION",
    "SEC_RETRIEVAL_CONCEPT_LABELS",
    "RetrievalProxyResult",
    "score_retrieval_proxy",
]
