# Week 4 measured delta report

## Comparison integrity

This report compares `baseline_v1` with `post_improvement_v2` using the same frozen 40-case golden dataset.

- Total cases in each run: 40
- Dataset SHA-256: `1F8EDE0B83102692D9A00D03E606204554F554C89A8717823432F898F621252D`
- Dataset hash changed between runs: no
- Baseline runtime failures: 0
- Post-improvement runtime failures: 0

## Outcome

| Result | baseline_v1 | post_improvement_v2 | Delta |
| --- | ---: | ---: | ---: |
| Passed cases | 6/40 | 16/40 | +10 cases |
| Pass rate | 15.00% | 40.00% | +25 percentage points |

A case with a required pending metric does not pass. Pending metrics are reported separately from measured agent failures.

## Metric deltas

| Metric | baseline_v1 | post_improvement_v2 | Delta |
| --- | ---: | ---: | ---: |
| `citation_accuracy` | 0.0000 | 0.9031 | +0.9031 |
| `faithfulness` | 0.3750 | 0.9063 | +0.5313 |
| `hit_at_5` | 0.0000 | 0.6875 | +0.6875 |
| `mrr` | 0.0000 | 0.6063 | +0.6063 |
| `context_precision` | 0.0000 | 0.4750 | +0.4750 |
| `expected_tool_selected` | 0.6000 | 1.0000 | +0.4000 |
| `guardrail_accuracy` | 0.0000 | 1.0000 | +1.0000 |
| `missing_input_handling` | 0.0000 | 1.0000 | +1.0000 |
| `safety` | 0.7500 | 1.0000 | +0.2500 |

The SEC retrieval figures use `keyword_context_proxy_v1`, an interim concept and context-keyword proxy. They show measured improvement but are not passage-level relevance ground truth.

## Impact by improvement

### SEC namespace and citation propagation

Selecting the namespace containing the Apple filing corpus restored evidence-bearing SEC retrieval. Passing structured passage citations through research, reporting, the adapter, and the evaluator improved retrieval proxy scores, citation accuracy, and faithfulness.

### Pre-routing safety gate

The deterministic safety decision now runs before ordinary routing. It prevents guaranteed-return, direct-trade, advisor-impersonation, and prompt-injection requests from being converted into normal specialist work. Guardrail accuracy improved from 0.0000 to 1.0000, and safety improved from 0.7500 to 1.0000.

### Routing fixes

High-confidence SEC and legal-risk intents now route to market research, while requests to use unnecessary tools can stop safely. Together with conditional evaluator logic for legitimate clarification and refusal paths, expected tool selection improved from 0.6000 to 1.0000.

### Retirement clarification

Missing retirement inputs are now presented as concrete, user-facing questions rather than the internal `retirement_inputs` bundle name. Missing-input handling improved from 0.0000 to 1.0000.

### Evaluator and adapter contract

The result contract now preserves retrieval status, contexts, document IDs, citations, route decisions, clarification and refusal state, tool events, and structured evidence. The judge receives the evidence used by the answer, and tool selection recognizes correct clarification or refusal stops. These changes improved measurement reliability and made agent behavior easier to distinguish from logging or scoring defects.

## Remaining failure clusters

| Cluster | Post-improvement cases |
| --- | ---: |
| Retrieval proxy miss | 5 |
| Incomplete answer | 2 |
| Retrieval proxy quality below pass bar | 2 |
| Unfaithful or unsupported answer | 2 |
| Numeric correctness pending | 12 |
| Trajectory pending | 4 |

The post-improvement summary also records one inaccurate or unsupported citation, one missing citation/source, and one missing or unverifiable citation. These are subsets of the remaining measured SEC answer-quality failures.

## Performance and limitations

- Baseline p95 latency: 24,950.0 ms
- Post-improvement p95 latency: 44,178.1 ms
- Latency pass bar: less than 60,000 ms
- Average agent cost: not measurable in either run because the graph result does not expose token usage or cost
- Numeric correctness remains pending for 12 cases without approved expected values and tolerances
- Multi-tool trajectory remains pending for 4 cases without approved route and tool-event references

The pass-rate improvement is measured, but the 40.00% result still includes cases that cannot pass while a required metric remains pending.
