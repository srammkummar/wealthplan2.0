"""Stable paths, run labels, and pass bars for Week 4 evaluations."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Literal


REPO_ROOT: Final = Path(__file__).resolve().parents[1]
DATASET_PATH: Final = REPO_ROOT / "evals" / "golden_dataset_v1.jsonl"
LANGSMITH_PROJECT: Final = "wealthplan-week4-evals"
BASELINE_RUN_NAME: Final = "baseline_v1"
POST_IMPROVEMENT_RUN_NAME: Final = "post_improvement_v2"

PassBarOperator = Literal[">=", "==", "<"]

PASS_BARS: Final[dict[str, float]] = {
    "hit_at_5": 0.95,
    "mrr": 0.85,
    "context_precision": 0.60,
    "faithfulness": 0.90,
    "citation_accuracy": 0.90,
    "completeness": 0.85,
    "safety": 0.90,
    "tool_task_completion": 0.90,
    "guardrail_accuracy": 1.00,
    "p95_latency_ms": 60_000.0,
    "average_cost_usd": 0.10,
}

PASS_BAR_OPERATORS: Final[dict[str, PassBarOperator]] = {
    "hit_at_5": ">=",
    "mrr": ">=",
    "context_precision": ">=",
    "faithfulness": ">=",
    "citation_accuracy": ">=",
    "completeness": ">=",
    "safety": ">=",
    "tool_task_completion": ">=",
    "guardrail_accuracy": "==",
    "p95_latency_ms": "<",
    "average_cost_usd": "<",
}

# Average cost is assessed only across runs that report a measurable cost.
MEASURABLE_ONLY_PASS_BARS: Final[frozenset[str]] = frozenset(
    {"average_cost_usd"}
)
