"""Typed contracts shared by future WealthPlan evaluation runs."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


ScenarioType = Literal["happy_path", "edge_case", "known_failure", "adversarial"]
TaskType = Literal[
    "sec_rag",
    "fundamentals",
    "portfolio",
    "retirement",
    "multi_tool",
    "guardrail",
]
Difficulty = Literal["easy", "medium", "hard"]
ReviewerStatus = Literal["pending_review", "approved", "needs_change", "remove"]
EvaluationStatus = Literal[
    "passed",
    "measured_failure",
    "pending_only",
    "measured_failure_with_pending",
    "agent_failure",
]
ToolCall = str | dict[str, Any]
Citation = str | dict[str, Any]


class GoldenDatasetCase(BaseModel):
    """One frozen case loaded from ``golden_dataset_v1.jsonl``."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    scenario_type: ScenarioType
    task_type: TaskType
    user_query: str = Field(min_length=1)
    expected_behavior: str = Field(min_length=1)
    expected_answer_points: str = Field(min_length=1)
    expected_tools: str = Field(min_length=1)
    judge_methods: str = Field(min_length=1)
    difficulty: Difficulty
    needs_human_review: bool
    reviewer_status: ReviewerStatus | None = None
    reviewer_notes: str | None = None


class AgentRunResult(BaseModel):
    """Normalized output captured from a future WealthPlan agent run."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    answer: str = ""
    retrieval_status: str | None = None
    retrieved_contexts: list[str] = Field(default_factory=list)
    retrieved_doc_ids: list[str] = Field(default_factory=list)
    retrieved_passage_count: int = Field(default=0, ge=0)
    tool_calls: list[ToolCall] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    structured_citations: list[dict[str, Any]] = Field(default_factory=list)
    citation_count: int = Field(default=0, ge=0)
    route_selected: list[str] = Field(default_factory=list)
    specialist_selected: list[str] = Field(default_factory=list)
    clarification_requested: bool = False
    refusal_detected: bool = False
    tool_outputs_summary: list[dict[str, Any]] = Field(default_factory=list)
    structured_evidence: list[dict[str, Any]] = Field(default_factory=list)
    retrieval_diagnostics: dict[str, Any] = Field(default_factory=dict)
    latency_ms: float | None = Field(default=None, ge=0)
    token_usage: dict[str, int | float] = Field(default_factory=dict)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
    error: str | None = None

    @model_validator(mode="after")
    def infer_observability_counts(self) -> "AgentRunResult":
        """Keep backward-compatible callers consistent with the richer contract."""

        if not self.structured_citations:
            self.structured_citations = [
                dict(citation)
                for citation in self.citations
                if isinstance(citation, dict)
            ]
        if not self.citations and self.structured_citations:
            self.citations = list(self.structured_citations)
        if self.retrieved_passage_count == 0 and self.retrieved_contexts:
            self.retrieved_passage_count = len(self.retrieved_contexts)
        if self.citation_count == 0 and self.structured_citations:
            self.citation_count = len(self.structured_citations)
        return self


class EvaluationResult(BaseModel):
    """Per-case metric outputs and their pass/pending explanation."""

    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(min_length=1)
    scenario_type: ScenarioType
    task_type: TaskType
    metric_scores: dict[str, float | None] = Field(default_factory=dict)
    metric_sources: dict[str, str] = Field(default_factory=dict)
    metric_details: dict[str, str] = Field(default_factory=dict)
    status: EvaluationStatus
    passed: bool
    failure_reasons: list[str] = Field(default_factory=list)
    measured_failure_reasons: list[str] = Field(default_factory=list)
    pending_reasons: list[str] = Field(default_factory=list)
    agent_failure_reasons: list[str] = Field(default_factory=list)
    latency_ms: float | None = Field(default=None, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0)
