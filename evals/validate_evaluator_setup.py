"""Validate Week 4 evaluator imports and the frozen dataset without agent calls."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
import sys


if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from evals.config import DATASET_PATH
from evals.evaluation_schema import AgentRunResult, GoldenDatasetCase
from evals.evaluators import (
    aggregate_case_score,
    citation_accuracy_placeholder,
    citation_presence_check,
    completeness_judge_placeholder,
    context_precision_proxy,
    expected_tool_selected,
    faithfulness_judge_placeholder,
    guardrail_refusal_check,
    mean_reciprocal_rank,
    missing_input_handling_check,
    mrr,
    numeric_correctness_placeholder,
    reciprocal_rank,
    retrieval_hit_at_k,
    safety_check_placeholder,
    task_completion_proxy,
    trajectory_eval_placeholder,
)
from evals.llm_judges import JudgeResponse, run_llm_judges
from evals.retrieval_proxy import (
    SEC_RETRIEVAL_CONCEPT_LABELS,
    score_retrieval_proxy,
)


EXPECTED_SCENARIOS = {
    "happy_path": 20,
    "edge_case": 12,
    "known_failure": 6,
    "adversarial": 2,
}


def load_cases() -> list[GoldenDatasetCase]:
    """Load and validate every nonblank JSONL line with the frozen schema."""

    cases: list[GoldenDatasetCase] = []
    with DATASET_PATH.open(encoding="utf-8") as dataset:
        for line_number, line in enumerate(dataset, start=1):
            if not line.strip():
                continue
            try:
                cases.append(GoldenDatasetCase.model_validate_json(line))
            except Exception as exc:
                raise ValueError(
                    f"Invalid golden dataset row at line {line_number}: {exc}"
                ) from exc
    return cases


def main() -> None:
    """Validate schema, counts, IDs, and evaluator imports only."""

    cases = load_cases()
    if len(cases) != 40:
        raise ValueError(f"Expected 40 cases, found {len(cases)}")
    if len({case.case_id for case in cases}) != len(cases):
        raise ValueError("Golden dataset contains duplicate case_id values")

    distribution = Counter(case.scenario_type for case in cases)
    if dict(distribution) != EXPECTED_SCENARIOS:
        raise ValueError(f"Unexpected scenario distribution: {dict(distribution)}")

    # Referencing the imports makes this check explicit without executing an evaluator.
    evaluator_functions = (
        aggregate_case_score,
        citation_accuracy_placeholder,
        citation_presence_check,
        completeness_judge_placeholder,
        context_precision_proxy,
        expected_tool_selected,
        faithfulness_judge_placeholder,
        guardrail_refusal_check,
        mean_reciprocal_rank,
        missing_input_handling_check,
        mrr,
        numeric_correctness_placeholder,
        reciprocal_rank,
        retrieval_hit_at_k,
        safety_check_placeholder,
        task_completion_proxy,
        trajectory_eval_placeholder,
    )
    if not all(callable(evaluator) for evaluator in evaluator_functions):
        raise TypeError("One or more evaluator exports are not callable")

    sec_case = next(case for case in cases if case.case_id == "WP-001")
    sample_run = AgentRunResult(
        case_id=sec_case.case_id,
        answer="The retrieved filing describes reportable geographic segments.",
        retrieved_contexts=[
            "The Company manages its business primarily on a geographic basis. "
            "Its reportable segments include the Americas and Greater China."
        ],
        retrieved_doc_ids=["sample-doc"],
        structured_citations=[
            {
                "citation_id": "SEC-1",
                "passage_rank": 1,
                "document_id": "sample-doc",
                "accession_number": "sample",
                "excerpt": "The Americas and Greater China are reportable segments.",
            }
        ],
    )
    retrieval_proxy = score_retrieval_proxy(sec_case, sample_run)
    if retrieval_proxy is None or retrieval_proxy.scores["hit_at_5"] != 1.0:
        raise AssertionError("Retrieval proxy validation failed")

    class FakeJudge:
        def invoke(self, messages, config=None):
            del messages, config
            metric = {
                "applicable": True,
                "score": 1.0,
                "rationale": "The sample answer is supported and complete.",
            }
            not_requested = {
                "applicable": False,
                "score": 0.0,
                "rationale": "Not requested.",
            }
            return JudgeResponse(
                faithfulness=metric,
                completeness=not_requested,
                citation_accuracy=metric,
                safety=not_requested,
            )

    judge = run_llm_judges(
        sec_case,
        sample_run,
        run_name="validation_only",
        structured_model=FakeJudge(),
    )
    if judge.scores.get("faithfulness") != 1.0:
        raise AssertionError("LLM judge adapter validation failed")
    if len(SEC_RETRIEVAL_CONCEPT_LABELS) != 16:
        raise AssertionError("Expected proxy labels for all 16 SEC cases")

    print(f"Total case count: {len(cases)}")
    print("Scenario distribution:")
    for scenario, count in EXPECTED_SCENARIOS.items():
        print(f"  {scenario}: {count}")
    print("Evaluator imports: OK")
    print("Retrieval proxy and fake structured judge: OK")
    print("Evaluator setup validation passed")


if __name__ == "__main__":
    main()
