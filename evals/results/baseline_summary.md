# baseline_v1 summary

This is the `baseline_v1` measurement captured before any improvements to prompts, tools, retrieval, routing, or guardrails.

## Outcome

- Total cases: 40
- Passed: 6
- Cases with measured failures: 25
- Cases with both measured failures and pending metrics: 7
- Pending-only cases: 9
- True agent/runtime failures: 0
- Pass rate: 15.00%

Measured failures, pending metrics, and true agent/runtime failures are reported separately. A case with a required pending metric does not pass.

## Scenario distribution

- adversarial: 2
- edge_case: 12
- happy_path: 20
- known_failure: 6

## Task type distribution

- fundamentals: 7
- guardrail: 2
- multi_tool: 4
- portfolio: 6
- retirement: 5
- sec_rag: 16

## Metric coverage and averages

- citation_accuracy: 0.0000 average; coverage 16/16 (100.0%)
- citation_presence: 0.6875 average; coverage 16/16 (100.0%)
- completeness: 0.9614 average; coverage 7/7 (100.0%)
- context_precision: 0.0000 average; coverage 16/16 (100.0%)
- expected_tool_selected: 0.6000 average; coverage 15/15 (100.0%)
- faithfulness: 0.3750 average; coverage 16/16 (100.0%)
- guardrail_accuracy: 0.0000 average; coverage 2/2 (100.0%)
- hit_at_5: 0.0000 average; coverage 16/16 (100.0%)
- missing_input_handling: 0.0000 average; coverage 5/5 (100.0%)
- mrr: 0.0000 average; coverage 16/16 (100.0%)
- numeric_correctness: not measurable; coverage 0/12 (0.0%)
- safety: 0.7500 average; coverage 8/8 (100.0%)
- task_completion: 1.0000 average; coverage 17/17 (100.0%)
- tool_task_completion: 0.9500 average; coverage 10/10 (100.0%)
- trajectory: not measurable; coverage 0/4 (0.0%)

## Performance

- p95 latency: 24,950.0 ms (< 60,000 ms pass bar)
- Average estimated cost: not measurable; the graph result does not expose token usage or cost.

## Top measured failure reasons

- Failed: hit_at_5 scored 0.0000. (16 cases)
- Failed: mrr scored 0.0000. (16 cases)
- Failed: context_precision scored 0.0000. (16 cases)
- Failed: citation_accuracy scored 0.0000. (16 cases)
- Failed: faithfulness scored 0.5000. (12 cases)
- Failed: expected_tool_selected scored 0.0000. (6 cases)
- Failed: citation_presence scored 0.0000. (5 cases)
- Failed: missing_input_handling scored 0.0000. (5 cases)
- Failed: faithfulness scored 0.0000. (4 cases)
- Failed: safety scored 0.0000. (2 cases)

## Pending or unmeasurable metrics

- Pending: numeric_correctness lacks an approved judge or required reference data. (12 cases)
- Pending: trajectory lacks an approved judge or required reference data. (4 cases)

## True agent/runtime failures

- None

## Failure clusters

### Measured failure clusters

- inaccurate/unsupported citation: 16 cases
- retrieval proxy miss: 16 cases
- unfaithful/unsupported answer: 16 cases
- wrong or missing tool: 6 cases
- missing citation/source: 5 cases
- missing input not handled: 5 cases
- unsafe financial advice/guarantee: 2 cases
- incomplete answer: 1 cases

### Agent failure clusters

- None

### Pending metric clusters

- pending metric: numeric_correctness: 12 cases
- pending metric: trajectory: 4 cases

## Measurement limitations

- Metrics with incomplete coverage: numeric_correctness, trajectory
- SEC Hit@5, reciprocal rank/MRR, and context precision use the transparent `keyword_context_proxy_v1` concept-label proxy. They are interim retrieval indicators, not passage-level ground truth.
- Faithfulness, completeness, citation accuracy, and safety use the versioned `week4_measurement_judge_v1` structured LLM judge when requested.
- Numeric correctness remains pending without approved expected values and tolerances. Trajectory remains pending without an approved route and tool-event reference for each multi-tool case.
- Agent cost remains unmeasurable because the production graph result does not expose token usage or cost; judge cost is not substituted.
- LangSmith project: `wealthplan-week4-evals`.
