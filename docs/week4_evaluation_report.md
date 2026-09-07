# Week 4 evaluation report

## Executive summary

WealthPlan was evaluated twice against the same frozen 40-case golden dataset. `baseline_v1` passed 6 of 40 cases, or 15.00%. After the prioritized retrieval, citation, safety, routing, clarification, and evaluator-contract changes, `post_improvement_v2` passed 16 of 40 cases, or 40.00%. The measured gain is 10 cases and 25 percentage points. Neither run had an agent/runtime failure.

The largest improvements were citation accuracy from 0.0000 to 0.9031, faithfulness from 0.3750 to 0.9063, expected tool selection from 0.6000 to 1.0000, guardrail accuracy from 0.0000 to 1.0000, and missing-input handling from 0.0000 to 1.0000. SEC retrieval proxies also moved above zero after the namespace and evidence-propagation fixes. Retrieval quality remains below its target bars, and numeric correctness and multi-tool trajectory remain pending.

## Agent under test

The system under test is the WealthPlan multi-agent workflow in this repository. A supervisor normalizes and routes requests to market research, retirement planning, portfolio analysis, and related specialist paths. The workflow can retrieve SEC filing evidence, invoke deterministic financial tools, assemble a final report, request missing inputs, or refuse unsafe financial instructions.

The baseline measured the agent before the Week 4 improvements. The post-improvement run measured the updated agent and evaluator contract. Both runs used `golden_dataset_v1` without changing its questions or expected behavior.

## Evaluation objective

The evaluation measures whether WealthPlan selects the appropriate path, retrieves relevant filing evidence, supports its claims with citations, completes the requested task, asks for missing inputs, refuses unsafe advice, and stays within the latency target. It also separates measured failures from pending metrics and runtime exceptions so missing labels are not presented as agent failures.

## Golden dataset design

The review workflow began with `evals/golden_dataset_review.xlsx`. All 40 approved rows were exported to `evals/golden_dataset_v1.jsonl`; no rows remain pending human review.

Scenario distribution:

| Scenario | Cases |
| --- | ---: |
| Happy path | 20 |
| Edge case | 12 |
| Known failure | 6 |
| Adversarial | 2 |

Task distribution:

| Task type | Cases |
| --- | ---: |
| SEC RAG | 16 |
| Fundamentals | 7 |
| Portfolio | 6 |
| Retirement | 5 |
| Multi-tool | 4 |
| Guardrail | 2 |

The frozen dataset SHA-256 is `1F8EDE0B83102692D9A00D03E606204554F554C89A8717823432F898F621252D`. The same hash applied to both evaluation runs.

## Metrics and pass bars

| Metric | Pass bar | Measurement method |
| --- | ---: | --- |
| Hit@5 | >= 0.95 | Interim SEC keyword/context proxy |
| MRR | >= 0.85 | Interim SEC keyword/context proxy |
| Context precision | >= 0.60 | Interim SEC keyword/context proxy |
| Faithfulness | >= 0.90 | Structured LLM judge |
| Citation accuracy | >= 0.90 | Structured citation evidence and LLM judge |
| Completeness | >= 0.85 | Structured LLM judge |
| Safety | >= 0.90 | Deterministic checks and structured LLM judge |
| Tool/task completion | >= 0.90 | Deterministic tool and task checks |
| Guardrail accuracy | = 1.00 | Deterministic refusal check |
| p95 latency | < 60,000 ms | Observed agent latency |
| Average cost | < $0.10 where measurable | Requires exposed usage and cost data |

Expected tool selection and missing-input handling are also reported as deterministic case-level diagnostics. Numeric correctness returns pending without approved expected values and tolerances. Multi-tool trajectory returns pending without approved route and tool-event references. Unmeasurable scores are never replaced with synthetic values.

## LangSmith instrumentation

Tracing uses the LangSmith project `wealthplan-week4-evals`. Step 1 established the smoke trace `SMOKE-001 WealthPlan LangSmith Setup`. Evaluation traces include case ID, scenario type, task type, agent version, dataset version, run name, and expected tools. The post-improvement verification confirmed 40 trace IDs under the project.

The richer post-improvement adapter contract also exposes retrieval status, passage and citation counts, route selection, clarification state, refusal state, tool events, and structured evidence. This makes it possible to distinguish an empty retrieval result from a routing miss or extraction failure.

The screenshot plan, selected trace IDs, and current evidence inventory are documented in `docs/langsmith_trace_evidence.md`. The final submission uses eight canonical screenshot filenames under `Screenshots/`.

## Baseline results

`baseline_v1` evaluated all 40 cases:

- Passed: 6
- Pass rate: 15.00%
- Cases with measured failures: 25
- Cases with both measured failures and pending metrics: 7
- Pending-only cases: 9
- Agent/runtime failures: 0
- p95 latency: 24,950.0 ms

The SEC metrics were all zero: citation accuracy 0.0000, Hit@5 0.0000, MRR 0.0000, and context precision 0.0000. Faithfulness averaged 0.3750. Expected tool selection was 0.6000, guardrail accuracy was 0.0000, missing-input handling was 0.0000, and safety was 0.7500.

## Failure analysis

The baseline analysis separated behavior problems from evaluator and adapter defects.

- Fifteen SEC cases reached search but returned `insufficient_evidence` with no passages; one SEC case was misrouted. The evaluator therefore received empty contexts for all 16 SEC cases.
- Structured citations were absent. A permissive citation-presence regex still counted generic URLs and source markers, overstating citation coverage.
- The faithfulness judge did not receive structured company-facts evidence used by several answers, mixing true scope problems with an evaluator evidence gap.
- Five retirement cases correctly stopped before calculation but exposed the internal name `retirement_inputs`. The tool evaluator also penalized those legitimate stops.
- WP-039 and WP-040 requested a ticker instead of refusing guaranteed-return, advisor-impersonation, or direct-trade instructions.

The failures were therefore mixed: retrieval and routing defects, unsafe or unclear user-facing behavior, and evaluator/adapter contract limitations. No case ended with an agent/runtime exception.

## Prioritized improvements

The failure analysis produced four priorities, implemented through six targeted changes:

| Order | Change | Failure addressed |
| ---: | --- | --- |
| 1 | Changed SEC retrieval from the Microsoft-only namespace to `sec-filings`, which contains the Apple 10-K corpus | Empty SEC retrieval and all-zero retrieval proxies |
| 2 | Propagated structured SEC citations through research, reporting, the adapter, and `[SEC-n]` answer markers | Missing or unverifiable filing support |
| 3 | Added a deterministic safety gate before ordinary routing | Guaranteed-return, direct-trade, advisor-impersonation, and prompt-injection requests |
| 4 | Routed legal and lawsuit-risk questions to SEC research | Misrouted filing questions |
| 5 | Replaced the internal `retirement_inputs` message with concrete user-facing clarification | Missing-input handling failures |
| 6 | Expanded evaluator and adapter evidence contracts | Tool-selection false failures and incomplete judge evidence |

The order prioritized blocked SEC evidence first, then high-risk safety behavior, task routing and clarification, and finally measurement reliability.

## Post-improvement results

`post_improvement_v2` evaluated the same 40 cases:

- Passed: 16
- Pass rate: 40.00%
- Cases with measured failures: 10
- Cases with both measured failures and pending metrics: 2
- Pending-only cases: 14
- Agent/runtime failures: 0
- p95 latency: 44,178.1 ms

The post-improvement run achieved citation accuracy of 0.9031, faithfulness of 0.9063, Hit@5 of 0.6875, MRR of 0.6063, context precision of 0.4750, expected tool selection of 1.0000, guardrail accuracy of 1.0000, missing-input handling of 1.0000, and safety of 1.0000.

## Measured impact / delta

| Metric | baseline_v1 | post_improvement_v2 | Delta |
| --- | ---: | ---: | ---: |
| Pass rate | 15.00% | 40.00% | +25 percentage points |
| Citation accuracy | 0.0000 | 0.9031 | +0.9031 |
| Faithfulness | 0.3750 | 0.9063 | +0.5313 |
| Hit@5 | 0.0000 | 0.6875 | +0.6875 |
| MRR | 0.0000 | 0.6063 | +0.6063 |
| Context precision | 0.0000 | 0.4750 | +0.4750 |
| Expected tool selected | 0.6000 | 1.0000 | +0.4000 |
| Guardrail accuracy | 0.0000 | 1.0000 | +1.0000 |
| Missing-input handling | 0.0000 | 1.0000 | +1.0000 |
| Safety | 0.7500 | 1.0000 | +0.2500 |

The SEC namespace fix and citation propagation drove the retrieval, citation, and faithfulness gains. The pre-routing safety gate drove the guardrail and safety gains. Routing changes improved tool selection, retirement clarification improved missing-input handling, and evaluator/adapter changes made the comparison more reliable.

## Remaining limitations

- Retrieval proxy miss remains in 5 cases.
- Incomplete answers remain in 2 cases.
- Retrieval proxy quality is below the pass bar in 2 cases.
- Unfaithful or unsupported answers remain in 2 cases.
- Numeric correctness is pending for 12 cases.
- Multi-tool trajectory is pending for 4 cases.
- The SEC retrieval metrics are interim concept and keyword proxies rather than human-reviewed passage-level relevance labels.
- Agent cost is not measurable because the graph result does not expose token usage or cost.
- The higher post-improvement p95 latency, 44,178.1 ms, remains within the 60,000 ms pass bar but should be monitored.
- The available screenshot evidence is embedded below; the folder does not currently contain a project-overview image or a post-improvement WP-002 output image with visible citations.

Because a required pending metric prevents a case from passing, the 40.00% pass rate reflects both remaining measured failures and incomplete metric coverage.

## Production monitoring plan

Production monitoring should retain the same versioned trace metadata used in evaluation and track:

- request volume and outcome by route, specialist, scenario, and agent version;
- retrieval status, passage count, document IDs, citation count, and empty-evidence rates;
- refusal and clarification decisions, including the triggering reason category;
- expected versus observed tool paths for sampled reviewed cases;
- unsupported-citation and faithfulness review outcomes;
- p50 and p95 latency, timeout rates, and tool-loop or runtime errors;
- token usage and estimated cost once the graph exposes those fields;
- drift by dataset version, evaluator version, model version, and retrieval namespace.

Alerts should focus on changes from an established production baseline, especially empty SEC retrievals, missing structured citations, unsafe requests that reach specialists, and latency above the 60-second p95 target. New failure patterns should become reviewed regression cases before prompts, routing rules, or guardrails are changed.

## Screenshot Evidence

The smoke-trace capture proves that `SMOKE-001 WealthPlan LangSmith Setup` reached the `wealthplan-week4-evals` project with the expected setup metadata.

![Step 1 LangSmith smoke trace attributes](../Screenshots/Wealth-Plan-02_step1_smoke_trace_attributes.png)

The baseline SEC RAG analysis capture documents the empty-evidence root cause and the distinction between retrieval and adapter failures.

![Baseline SEC RAG failure analysis](../Screenshots/Wealth-Plan-03_baseline_failure_analysis_sec_rag.png)

The first baseline trace capture proves that WP-002 ran as a `baseline_v1` SEC RAG case in the correct LangSmith project and dataset version.

![Baseline SEC RAG trace attributes](../Screenshots/Wealth-Plan-03_baseline_sec_rag_trace_attributes.png)

The supporting baseline metrics capture shows the baseline metric coverage and the 24,950.0 ms p95 latency.

![Supporting baseline metrics and latency](../Screenshots/Wealth-Plan-03-1_baseline_sec_rag_trace_attributes.png)

The baseline summary capture proves the all-zero SEC retrieval metrics and the other reported baseline averages.

![Baseline summary metrics](../Screenshots/Wealth-Plan-04_baseline_summary_metrics.png)

The detailed WP-002 trace capture proves the baseline case metadata, expected SEC tool, and `baseline_v1` run identity.

![Baseline WP-002 trace attributes](../Screenshots/Wealth-Plan-05_baseline_wp002_trace_attributes.png)

The safety input capture proves that adversarial case WP-039 reached the pre-routing `safety_gate` with the guaranteed-return request preserved in the trace.

![Safety refusal input](../Screenshots/Wealth-Plan-07_safety_refusal_input.png)

The safety output capture proves that WP-039 refused guaranteed returns and direct buy/sell instructions while offering an educational alternative.

![Safety refusal output](../Screenshots/Wealth-Plan-07_safety_refusal_output.png)

The delta-report capture proves the 15.00% to 40.00% pass-rate comparison and the approved metric deltas.

![Measured delta report metrics](../Screenshots/Wealth-Plan-08_delta_report_metrics.png)

## What I would try next

1. Capture the missing project overview and post-improvement WP-002 cited-output evidence if those views are required for submission.
2. Add human-reviewed relevant passage or document labels for SEC cases so Hit@5, MRR, and context precision no longer depend on the interim proxy.
3. Add approved numeric reference values and tolerances for the 12 pending numeric-correctness cases.
4. Add approved route and tool-event sequences for the 4 pending trajectory cases.
5. Expose agent token usage and estimated cost without substituting judge usage.
6. Keep `golden_dataset_v1` frozen for this comparison; create a new version for future test additions.
