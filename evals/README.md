# WealthPlan evaluations

## LangSmith smoke test

From the repository root, run:

```powershell
uv run python evals/langsmith_smoke_test.py
```

The script loads `.env`, invokes the real WealthPlan multi-agent graph with the
SMOKE-001 question, and verifies that the named root trace and required metadata
were uploaded to the `wealthplan-week4-evals` LangSmith project.

## Step 2: golden dataset review

The Excel review workbook was created for human review. The 40 approved cases
were exported to `golden_dataset_v1.jsonl` after review. This frozen dataset
will be reused unchanged for `baseline_v1` and `post_improvement_v2`.

## Step 3: evaluator framework

Step 3 created the reusable schemas, configuration, and deterministic evaluator
functions. Step 4 then captured the first `baseline_v1` run.

Validate the setup without calling the WealthPlan agent:

```powershell
uv run python evals/validate_evaluator_setup.py
```

The command loads and validates the frozen JSONL, confirms its case count and
scenario distribution, and imports the evaluator functions. It does not create
result files.

### Metric groups

- Retrieval: Hit@5, reciprocal rank/MRR, and context precision. Exact document
  labels are used when available.
- Execution: expected-tool selection and a minimal task-completion proxy.
- Grounding: citation presence is deterministic for SEC RAG cases.
- Safety and inputs: guardrail refusal and missing-input handling are
  deterministic proxies. Broader non-guardrail safety review remains pending.
- Judge metrics: faithfulness, completeness, citation accuracy, and safety use
  the Step 4A structured judge. Numeric correctness and trajectory review remain
  pending until approved references are connected.

An uncomputed metric remains `None` and adds a pending reason. It is never
replaced with a fabricated score.

### Pass bars

| Metric | Pass bar |
| --- | ---: |
| Hit@5 | >= 0.95 |
| MRR | >= 0.85 |
| Context precision | >= 0.60 |
| Faithfulness | >= 0.90 |
| Citation accuracy | >= 0.90 |
| Completeness | >= 0.85 |
| Tool/task completion | >= 0.90 |
| Guardrail accuracy | = 1.00 |
| p95 latency | < 60,000 ms |
| Average cost | < $0.10 per measurable run |

The latency and average-cost pass bars are population metrics and will be
calculated only after a future run set exists.

## Step 4A: baseline measurement coverage

Step 4A changed evaluator code and reporting only. It did not change the
WealthPlan graph, prompts, tools, retrieval implementation, routing, guardrails,
or the frozen dataset.

Run the measured baseline from the repository root:

```powershell
uv run python evals/run_eval.py --run-name baseline_v1
```

The current baseline contains 40 cases and has a 15.00% fully measured pass
rate. The results distinguish four states: `passed`, `measured_failure`,
`pending_only`, and `measured_failure_with_pending`. A separate
`agent_failure` state is reserved for true agent/runtime exceptions; the Step
4A rerun had none.

### Measurement additions

- `week4_measurement_judge_v1` provides structured LLM-as-judge scores and
  rationales for faithfulness, completeness, citation accuracy, and safety. Set
  `WEALTHPLAN_EVALUATOR_MODEL` to override the default evaluator model without
  changing the production agent model.
- `keyword_context_proxy_v1` scores SEC Hit@5, reciprocal rank/MRR, and context
  precision against case-specific expected concepts in
  `evals/retrieval_proxy.py` when exact relevant document IDs are unavailable.
- Guardrail refusal and missing-input handling remain deterministic and are
  labeled with evaluator versions in the results.
- Each result records metric source, metric rationale, judge version, retrieval
  proxy labels, measured failures, pending reasons, and true agent failures.

The retrieval proxy is an interim indicator, not passage-level ground truth. A
context is proxy-relevant when it contains a reviewed case-specific concept
phrase. Exact document or passage relevance labels should replace this proxy in
a later dataset-review step.

Numeric correctness remains unmeasurable for 12 cases because the frozen
dataset has no approved numeric values and tolerances. Trajectory remains
unmeasurable for four multi-tool cases because no approved route/tool-event
reference exists. Agent cost also remains unavailable because the production
graph result does not expose token usage or cost; judge cost is not substituted.
