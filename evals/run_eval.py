"""Run a frozen WealthPlan evaluation set and write reproducible artifacts."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import json
import math
import os
from pathlib import Path
import re
import sys
from statistics import fmean
from typing import Any, Iterable


# Direct execution sets sys.path[0] to evals/. Add the repo and src roots so
# ``python evals/run_eval.py`` and ``uv run python ...`` both work on Windows.
REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = REPO_ROOT / "src"
for import_root in (REPO_ROOT, SRC_ROOT):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from dotenv import load_dotenv
from langsmith import Client, traceable

from evals.agent_adapter import run_wealthplan_case
from evals.config import (
    BASELINE_RUN_NAME,
    DATASET_PATH,
    LANGSMITH_PROJECT,
    PASS_BARS,
    PASS_BAR_OPERATORS,
    POST_IMPROVEMENT_RUN_NAME,
)
from evals.evaluation_schema import (
    AgentRunResult,
    EvaluationResult,
    GoldenDatasetCase,
)
from evals.evaluators import aggregate_case_score
from evals.llm_judges import JUDGE_VERSION, JudgeBundle, run_llm_judges
from evals.retrieval_proxy import RetrievalProxyResult, score_retrieval_proxy


EXPECTED_CASE_COUNT = 40
RESULTS_DIR = REPO_ROOT / "evals" / "results"
RESULT_COLUMNS = [
    "case_id",
    "scenario_type",
    "task_type",
    "user_query",
    "answer",
    "expected_tools",
    "predicted_tools",
    "route_selected",
    "specialist_selected",
    "clarification_requested",
    "refusal_detected",
    "retrieval_status",
    "retrieved_passage_count",
    "retrieved_contexts",
    "retrieved_doc_ids",
    "structured_citations",
    "citation_count",
    "retrieval_diagnostics",
    "tool_outputs_summary",
    "structured_evidence",
    "retrieval_hit_at_5",
    "mrr",
    "context_precision",
    "citation_accuracy",
    "tool_task_completion",
    "guardrail_accuracy",
    "missing_input_handling",
    "numeric_correctness",
    "passed",
    "evaluation_status",
    "failure_reasons",
    "measured_failure_reasons",
    "pending_metric_reasons",
    "agent_failure_reasons",
    "latency_ms",
    "estimated_cost_usd",
    "error",
    "citation_presence",
    "faithfulness",
    "completeness",
    "expected_tool_selected",
    "task_completion",
    "trajectory",
    "safety",
    "token_usage",
    "langsmith_trace_id",
    "metric_sources",
    "metric_details",
    "retrieval_metric_basis",
    "retrieval_proxy_labels",
    "judge_model",
    "judge_version",
    "judge_error",
]


def load_dataset(path: Path = DATASET_PATH) -> list[GoldenDatasetCase]:
    cases: list[GoldenDatasetCase] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                cases.append(GoldenDatasetCase.model_validate_json(line))
            except Exception as exc:
                raise ValueError(f"Invalid dataset row at line {line_number}: {exc}") from exc
    if len(cases) != EXPECTED_CASE_COUNT:
        raise ValueError(
            f"Frozen baseline dataset must contain {EXPECTED_CASE_COUNT} cases; "
            f"found {len(cases)}."
        )
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("Frozen baseline dataset contains duplicate case IDs.")
    return cases


def _validate_environment() -> None:
    if os.getenv("LANGSMITH_TRACING", "").strip().lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }:
        raise RuntimeError("LANGSMITH_TRACING must be true for the baseline run.")
    if not os.getenv("LANGSMITH_API_KEY"):
        raise RuntimeError("LANGSMITH_API_KEY is required for the baseline run.")
    configured_project = os.getenv("LANGSMITH_PROJECT")
    if configured_project != LANGSMITH_PROJECT:
        raise RuntimeError(
            f"LANGSMITH_PROJECT must be {LANGSMITH_PROJECT!r}; "
            f"found {configured_project!r}."
        )


def _run_traced_case(
    case: GoldenDatasetCase,
    *,
    run_tree: Any = None,
) -> dict[str, Any]:
    result = run_wealthplan_case(case)
    if run_tree is not None:
        run_tree.add_metadata(
            {
                "retrieval_status": result.retrieval_status,
                "retrieved_passage_count": result.retrieved_passage_count,
                "citation_count": result.citation_count,
                "route_selected": result.route_selected,
                "specialist_selected": result.specialist_selected,
                "clarification_requested": result.clarification_requested,
                "refusal_detected": result.refusal_detected,
            }
        )
    return {
        "agent_run": result.model_dump(mode="json"),
        "trace_id": str(run_tree.id) if run_tree is not None else "",
    }


TRACED_CASE_RUNNER = traceable(run_type="chain")(_run_traced_case)


def _metric(scores: dict[str, float | None], name: str) -> float | None:
    return scores.get(name)


def _csv_value(value: Any) -> Any:
    return "" if value is None else value


def _result_row(
    case: GoldenDatasetCase,
    run: AgentRunResult,
    evaluation: EvaluationResult,
    trace_id: str,
    retrieval_proxy: RetrievalProxyResult | None,
    judge: JudgeBundle,
) -> dict[str, Any]:
    scores = evaluation.metric_scores
    return {
        "case_id": case.case_id,
        "scenario_type": case.scenario_type,
        "task_type": case.task_type,
        "user_query": case.user_query,
        "answer": run.answer,
        "expected_tools": case.expected_tools,
        "predicted_tools": json.dumps(run.tool_calls, ensure_ascii=False),
        "route_selected": json.dumps(run.route_selected, ensure_ascii=False),
        "specialist_selected": json.dumps(
            run.specialist_selected, ensure_ascii=False
        ),
        "clarification_requested": run.clarification_requested,
        "refusal_detected": run.refusal_detected,
        "retrieval_status": run.retrieval_status or "",
        "retrieved_passage_count": run.retrieved_passage_count,
        "retrieved_contexts": json.dumps(run.retrieved_contexts, ensure_ascii=False),
        "retrieved_doc_ids": json.dumps(run.retrieved_doc_ids, ensure_ascii=False),
        "structured_citations": json.dumps(
            run.structured_citations, ensure_ascii=False
        ),
        "citation_count": run.citation_count,
        "retrieval_diagnostics": json.dumps(
            run.retrieval_diagnostics, ensure_ascii=False, sort_keys=True
        ),
        "tool_outputs_summary": json.dumps(
            run.tool_outputs_summary, ensure_ascii=False, sort_keys=True
        ),
        "structured_evidence": json.dumps(
            run.structured_evidence, ensure_ascii=False, sort_keys=True
        ),
        "retrieval_hit_at_5": _csv_value(_metric(scores, "hit_at_5")),
        "mrr": _csv_value(_metric(scores, "mrr")),
        "context_precision": _csv_value(_metric(scores, "context_precision")),
        "citation_accuracy": _csv_value(_metric(scores, "citation_accuracy")),
        "tool_task_completion": _csv_value(
            _metric(scores, "tool_task_completion")
        ),
        "guardrail_accuracy": _csv_value(_metric(scores, "guardrail_accuracy")),
        "missing_input_handling": _csv_value(
            _metric(scores, "missing_input_handling")
        ),
        "numeric_correctness": _csv_value(_metric(scores, "numeric_correctness")),
        "passed": evaluation.passed,
        "evaluation_status": evaluation.status,
        "failure_reasons": " | ".join(evaluation.failure_reasons),
        "measured_failure_reasons": " | ".join(
            evaluation.measured_failure_reasons
        ),
        "pending_metric_reasons": " | ".join(evaluation.pending_reasons),
        "agent_failure_reasons": " | ".join(
            evaluation.agent_failure_reasons
        ),
        "latency_ms": _csv_value(
            round(run.latency_ms, 3) if run.latency_ms is not None else None
        ),
        "estimated_cost_usd": _csv_value(run.estimated_cost_usd),
        "error": run.error or "",
        "citation_presence": _csv_value(_metric(scores, "citation_presence")),
        "faithfulness": _csv_value(_metric(scores, "faithfulness")),
        "completeness": _csv_value(_metric(scores, "completeness")),
        "expected_tool_selected": _csv_value(
            _metric(scores, "expected_tool_selected")
        ),
        "task_completion": _csv_value(_metric(scores, "task_completion")),
        "trajectory": _csv_value(_metric(scores, "trajectory")),
        "safety": _csv_value(_metric(scores, "safety")),
        "token_usage": json.dumps(run.token_usage, ensure_ascii=False),
        "langsmith_trace_id": trace_id,
        "metric_sources": json.dumps(
            evaluation.metric_sources, ensure_ascii=False, sort_keys=True
        ),
        "metric_details": json.dumps(
            evaluation.metric_details, ensure_ascii=False, sort_keys=True
        ),
        "retrieval_metric_basis": retrieval_proxy.version if retrieval_proxy else "",
        "retrieval_proxy_labels": json.dumps(
            list(retrieval_proxy.labels) if retrieval_proxy else [],
            ensure_ascii=False,
        ),
        "judge_model": judge.model if judge.scores else "",
        "judge_version": judge.version if judge.scores else "",
        "judge_error": judge.error or "",
    }


def _write_csv(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _case_failure_clusters(
    run: AgentRunResult,
    evaluation: EvaluationResult,
) -> set[tuple[str, str]]:
    scores = evaluation.metric_scores
    clusters: set[tuple[str, str]] = set()
    if run.error:
        clusters.add(("agent_failure", "agent/runtime error"))
    if scores.get("citation_presence") == 0.0:
        clusters.add(("measured_failure", "missing citation/source"))
    if scores.get("expected_tool_selected") == 0.0:
        clusters.add(("measured_failure", "wrong or missing tool"))
    if scores.get("missing_input_handling") == 0.0:
        clusters.add(("measured_failure", "missing input not handled"))
    if scores.get("guardrail_accuracy") == 0.0 or (
        scores.get("safety") is not None
        and scores["safety"] < PASS_BARS["safety"]
    ):
        clusters.add(("measured_failure", "unsafe financial advice/guarantee"))
    if scores.get("hit_at_5") == 0.0:
        clusters.add(("measured_failure", "retrieval proxy miss"))
    elif (
        scores.get("mrr") is not None
        and scores["mrr"] < PASS_BARS["mrr"]
    ) or (
        scores.get("context_precision") is not None
        and scores["context_precision"] < PASS_BARS["context_precision"]
    ):
        clusters.add(("measured_failure", "retrieval proxy quality below pass bar"))
    if scores.get("faithfulness") is not None and scores["faithfulness"] < PASS_BARS["faithfulness"]:
        clusters.add(("measured_failure", "unfaithful/unsupported answer"))
    if scores.get("completeness") is not None and scores["completeness"] < PASS_BARS["completeness"]:
        clusters.add(("measured_failure", "incomplete answer"))
    if scores.get("citation_accuracy") is not None and scores["citation_accuracy"] < PASS_BARS["citation_accuracy"]:
        citation_cluster = (
            "missing/unverifiable citation"
            if not (run.structured_citations or run.citations)
            else "inaccurate/unsupported citation"
        )
        clusters.add(("measured_failure", citation_cluster))
    if scores.get("numeric_correctness") == 0.0:
        clusters.add(("measured_failure", "unsupported exact number"))
    if scores.get("task_completion") == 0.0:
        clusters.add(("measured_failure", "task incomplete"))
    if run.latency_ms is not None and run.latency_ms >= PASS_BARS["p95_latency_ms"]:
        clusters.add(("measured_failure", "latency/tool loop"))
    for metric, score in scores.items():
        if score is None:
            clusters.add(("pending_metric", f"pending metric: {metric}"))
    if not evaluation.passed and not clusters:
        clusters.add(("measured_failure", "other evaluator failure"))
    return clusters


def _cluster_rows(
    records: list[tuple[GoldenDatasetCase, AgentRunResult, EvaluationResult]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str], list[str]] = defaultdict(list)
    failed_count = sum(not evaluation.passed for _, _, evaluation in records)
    for case, run, evaluation in records:
        if evaluation.passed:
            continue
        for category_and_cluster in _case_failure_clusters(run, evaluation):
            grouped[category_and_cluster].append(case.case_id)
    rows = [
        {
            "category_type": category,
            "failure_cluster": cluster,
            "case_count": len(case_ids),
            "case_ids": ", ".join(case_ids),
            "share_of_failed_cases": (
                round(len(case_ids) / failed_count, 4) if failed_count else 0.0
            ),
        }
        for (category, cluster), case_ids in grouped.items()
    ]
    category_order = {"measured_failure": 0, "agent_failure": 1, "pending_metric": 2}
    return sorted(
        rows,
        key=lambda row: (
            category_order.get(row["category_type"], 9),
            -row["case_count"],
            row["failure_cluster"],
        ),
    )


def _nearest_rank_p95(values: list[float]) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(0.95 * len(ordered)) - 1)]


def _distribution(values: Iterable[str]) -> Counter[str]:
    return Counter(values)


def _format_distribution(distribution: Counter[str]) -> list[str]:
    return [f"- {name}: {count}" for name, count in sorted(distribution.items())]


def _write_summary(
    path: Path,
    *,
    run_name: str,
    records: list[tuple[GoldenDatasetCase, AgentRunResult, EvaluationResult]],
    cluster_rows: list[dict[str, Any]],
) -> None:
    evaluations = [evaluation for _, _, evaluation in records]
    runs = [run for _, run, _ in records]
    passed = sum(evaluation.passed for evaluation in evaluations)
    measured_failures = sum(
        bool(evaluation.measured_failure_reasons)
        for evaluation in evaluations
        if not evaluation.agent_failure_reasons
    )
    pending_only = sum(
        evaluation.status == "pending_only" for evaluation in evaluations
    )
    measured_with_pending = sum(
        evaluation.status == "measured_failure_with_pending"
        for evaluation in evaluations
    )
    agent_failures = sum(
        bool(evaluation.agent_failure_reasons) for evaluation in evaluations
    )
    scenario_distribution = _distribution(case.scenario_type for case, _, _ in records)
    task_distribution = _distribution(case.task_type for case, _, _ in records)

    metric_values: dict[str, list[float]] = defaultdict(list)
    metric_required_counts: Counter[str] = Counter()
    for evaluation in evaluations:
        for name, value in evaluation.metric_scores.items():
            metric_required_counts[name] += 1
            if value is not None:
                metric_values[name].append(value)

    measured_reason_counts = Counter(
        reason
        for evaluation in evaluations
        for reason in evaluation.measured_failure_reasons
    )
    pending_reason_counts = Counter(
        reason
        for evaluation in evaluations
        for reason in evaluation.pending_reasons
    )
    agent_reason_counts = Counter(
        reason
        for evaluation in evaluations
        for reason in evaluation.agent_failure_reasons
    )
    latency_values = [run.latency_ms for run in runs if run.latency_ms is not None]
    cost_values = [
        run.estimated_cost_usd
        for run in runs
        if run.estimated_cost_usd is not None
    ]
    p95_latency = _nearest_rank_p95(latency_values)
    average_cost = fmean(cost_values) if cost_values else None

    run_note = (
        "This is the `baseline_v1` measurement captured before any improvements "
        "to prompts, tools, retrieval, routing, or guardrails."
        if run_name == BASELINE_RUN_NAME
        else f"This summary records the `{run_name}` evaluation run."
    )
    lines = [
        f"# {run_name} summary",
        "",
        run_note,
        "",
        "## Outcome",
        "",
        f"- Total cases: {len(records)}",
        f"- Passed: {passed}",
        f"- Cases with measured failures: {measured_failures}",
        f"- Cases with both measured failures and pending metrics: {measured_with_pending}",
        f"- Pending-only cases: {pending_only}",
        f"- True agent/runtime failures: {agent_failures}",
        f"- Pass rate: {(passed / len(records)):.2%}",
        "",
        "Measured failures, pending metrics, and true agent/runtime failures are "
        "reported separately. A case with a required pending metric does not pass.",
        "",
        "## Scenario distribution",
        "",
        *_format_distribution(scenario_distribution),
        "",
        "## Task type distribution",
        "",
        *_format_distribution(task_distribution),
        "",
        "## Metric coverage and averages",
        "",
    ]
    for metric in sorted(metric_required_counts):
        values = metric_values.get(metric, [])
        if values:
            coverage = len(values) / metric_required_counts[metric]
            lines.append(
                f"- {metric}: {fmean(values):.4f} average; "
                f"coverage {len(values)}/{metric_required_counts[metric]} "
                f"({coverage:.1%})"
            )
        else:
            lines.append(
                f"- {metric}: not measurable; coverage "
                f"0/{metric_required_counts[metric]} (0.0%)"
            )

    lines.extend(
        [
            "",
            "## Performance",
            "",
            (
                f"- p95 latency: {p95_latency:,.1f} ms "
                f"({PASS_BAR_OPERATORS['p95_latency_ms']} "
                f"{PASS_BARS['p95_latency_ms']:,.0f} ms pass bar)"
                if p95_latency is not None
                else "- p95 latency: not measurable"
            ),
            (
                f"- Average estimated cost: ${average_cost:.6f} "
                f"({PASS_BAR_OPERATORS['average_cost_usd']} "
                f"${PASS_BARS['average_cost_usd']:.2f} pass bar)"
                if average_cost is not None
                else "- Average estimated cost: not measurable; the graph result "
                "does not expose token usage or cost."
            ),
            "",
            "## Top measured failure reasons",
            "",
        ]
    )
    if measured_reason_counts:
        lines.extend(
            f"- {reason} ({count} cases)"
            for reason, count in measured_reason_counts.most_common(10)
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Pending or unmeasurable metrics", ""])
    if pending_reason_counts:
        lines.extend(
            f"- {reason} ({count} cases)"
            for reason, count in pending_reason_counts.most_common()
        )
    else:
        lines.append("- None")

    lines.extend(["", "## True agent/runtime failures", ""])
    if agent_reason_counts:
        lines.extend(
            f"- {reason} ({count} cases)"
            for reason, count in agent_reason_counts.most_common()
        )
    else:
        lines.append("- None")

    lines.extend(["", "## Failure clusters", ""])
    for category, heading in (
        ("measured_failure", "Measured failure clusters"),
        ("agent_failure", "Agent failure clusters"),
        ("pending_metric", "Pending metric clusters"),
    ):
        category_rows = [
            row for row in cluster_rows if row["category_type"] == category
        ]
        lines.extend([f"### {heading}", ""])
        if category_rows:
            lines.extend(
                f"- {row['failure_cluster']}: {row['case_count']} cases"
                for row in category_rows
            )
        else:
            lines.append("- None")
        lines.append("")

    unmeasurable = sorted(
        metric
        for metric, required_count in metric_required_counts.items()
        if len(metric_values.get(metric, [])) < required_count
    )
    lines.extend(
        [
            "## Measurement limitations",
            "",
            (
                "- Metrics with incomplete coverage: " + ", ".join(unmeasurable)
                if unmeasurable
                else "- All requested per-case metrics had complete coverage."
            ),
            "- SEC Hit@5, reciprocal rank/MRR, and context precision use the "
            "transparent `keyword_context_proxy_v1` concept-label proxy. They are "
            "interim retrieval indicators, not passage-level ground truth.",
            f"- Faithfulness, completeness, citation accuracy, and safety use the "
            f"versioned `{JUDGE_VERSION}` structured LLM judge when requested.",
            "- Numeric correctness remains pending without approved expected values "
            "and tolerances. Trajectory remains pending without an approved route "
            "and tool-event reference for each multi-tool case.",
            "- Agent cost remains unmeasurable because the production graph result "
            "does not expose token usage or cost; judge cost is not substituted.",
            "- LangSmith project: `wealthplan-week4-evals`.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _output_paths(run_name: str) -> tuple[Path, Path, Path]:
    if run_name == BASELINE_RUN_NAME:
        return (
            RESULTS_DIR / "baseline_results.csv",
            RESULTS_DIR / "baseline_summary.md",
            RESULTS_DIR / "failure_clusters.csv",
        )
    if run_name == POST_IMPROVEMENT_RUN_NAME:
        return (
            RESULTS_DIR / "post_improvement_results.csv",
            RESULTS_DIR / "post_improvement_summary.md",
            RESULTS_DIR / "post_improvement_failure_clusters.csv",
        )
    return (
        RESULTS_DIR / f"{run_name}_results.csv",
        RESULTS_DIR / f"{run_name}_summary.md",
        RESULTS_DIR / f"{run_name}_failure_clusters.csv",
    )


def run_evaluation(run_name: str) -> tuple[Path, Path, Path, int, int]:
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", run_name):
        raise ValueError("run_name may contain only letters, numbers, _, -, and .")
    load_dotenv(REPO_ROOT / ".env")
    _validate_environment()
    cases = load_dataset()
    client = Client()
    records: list[tuple[GoldenDatasetCase, AgentRunResult, EvaluationResult]] = []
    csv_rows: list[dict[str, Any]] = []

    try:
        for index, case in enumerate(cases, start=1):
            metadata = {
                "case_id": case.case_id,
                "scenario_type": case.scenario_type,
                "task_type": case.task_type,
                "agent_version": run_name,
                "dataset_version": "golden_dataset_v1",
                "run_name": run_name,
                "expected_tools": case.expected_tools,
                "project": LANGSMITH_PROJECT,
                "measurement_version": "step4a_evaluator_coverage_v2",
            }
            payload = TRACED_CASE_RUNNER(
                case,
                langsmith_extra={
                    "name": f"{run_name} {case.case_id}",
                    "metadata": metadata,
                    "project_name": LANGSMITH_PROJECT,
                    "client": client,
                    "tags": [run_name, case.scenario_type, case.task_type],
                },
            )
            run = AgentRunResult.model_validate(payload["agent_run"])
            retrieval_proxy = score_retrieval_proxy(case, run)
            judge = run_llm_judges(case, run, run_name=run_name)
            metric_overrides: dict[str, float | None] = {}
            metric_sources: dict[str, str] = {}
            metric_details: dict[str, str] = {}
            if retrieval_proxy is not None:
                metric_overrides.update(retrieval_proxy.scores)
                for metric in retrieval_proxy.scores:
                    metric_sources[metric] = retrieval_proxy.version
                    metric_details[metric] = retrieval_proxy.detail
            metric_overrides.update(judge.scores)
            for metric, score in judge.scores.items():
                metric_sources[metric] = (
                    "deterministic_missing_citation_v1"
                    if metric == "citation_accuracy"
                    and score == 0.0
                    and not (run.structured_citations or run.citations)
                    else f"llm_judge:{judge.model}:{judge.version}"
                )
            metric_details.update(judge.reasons)
            evaluation = aggregate_case_score(
                case,
                run,
                relevant_doc_ids=None,
                metric_overrides=metric_overrides,
                metric_sources=metric_sources,
                metric_details=metric_details,
            )
            records.append((case, run, evaluation))
            csv_rows.append(
                _result_row(
                    case,
                    run,
                    evaluation,
                    str(payload.get("trace_id") or ""),
                    retrieval_proxy,
                    judge,
                )
            )
            print(
                f"[{index:02d}/{len(cases)}] {case.case_id}: "
                f"{evaluation.status.upper()} "
                f"({run.latency_ms or 0:.0f} ms)",
                flush=True,
            )
        client.flush()
    finally:
        client.close()

    results_path, summary_path, clusters_path = _output_paths(run_name)
    cluster_rows = _cluster_rows(records)
    _write_csv(results_path, csv_rows, RESULT_COLUMNS)
    _write_csv(
        clusters_path,
        cluster_rows,
        [
            "category_type",
            "failure_cluster",
            "case_count",
            "case_ids",
            "share_of_failed_cases",
        ],
    )
    _write_summary(
        summary_path,
        run_name=run_name,
        records=records,
        cluster_rows=cluster_rows,
    )
    passed = sum(evaluation.passed for _, _, evaluation in records)
    print(f"Evaluated {len(records)} cases; passed {passed}.")
    print(f"Results: {results_path.relative_to(REPO_ROOT)}")
    print(f"Summary: {summary_path.relative_to(REPO_ROOT)}")
    print(f"Failure clusters: {clusters_path.relative_to(REPO_ROOT)}")
    return results_path, summary_path, clusters_path, len(records), passed


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-name",
        default=BASELINE_RUN_NAME,
        help=f"Run label (default: {BASELINE_RUN_NAME})",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_evaluation(args.run_name)


if __name__ == "__main__":
    main()
