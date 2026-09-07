# Week 4 Loom walkthrough script

Target length: approximately 4 minutes.

## 0:00–0:30 — What WealthPlan is

On screen: repository overview or the Week 4 evaluation report.

“WealthPlan 2.0 is a multi-agent financial planning workflow. A supervisor routes requests to specialist paths for SEC research, fundamentals, portfolios, retirement planning, and multi-tool tasks. It can also ask for missing information or refuse unsafe financial instructions. For Week 4, my goal was to measure the existing system, analyze its failures, make targeted improvements, and then measure the same cases again.”

## 0:30–1:00 — Golden dataset

On screen: `evals/golden_dataset_validation.md`.

“I built a human-reviewed golden dataset in Excel and exported the 40 approved cases to `evals/golden_dataset_v1.jsonl`. The set includes 20 happy-path cases, 12 edge cases, 6 known failures, and 2 adversarial cases across SEC RAG, fundamentals, portfolio, retirement, multi-tool, and guardrail tasks. I froze the dataset before the baseline. Its SHA-256 is `1F8EDE0B83102692D9A00D03E606204554F554C89A8717823432F898F621252D`, and it stayed unchanged for the post-improvement run.”

## 1:00–1:30 — LangSmith tracing

On screen: `01_langsmith_project_overview.png`, then `02_step1_smoke_trace_attributes.png`.

“All tracing is in the LangSmith project `wealthplan-week4-evals`. I first verified the setup with the trace named `SMOKE-001 WealthPlan LangSmith Setup`. Each evaluation case includes metadata such as case ID, scenario type, task type, agent version, dataset version, run name, and expected tools. The post-improvement artifacts contain 40 trace IDs, and all 40 were verified under this project.”

## 1:30–2:05 — Baseline and failure analysis

On screen: `04_baseline_summary_metrics.png`, then `03_baseline_failure_analysis_sec_rag.png` and `05_baseline_wp002_trace_attributes.png`.

“The `baseline_v1` run passed 6 of 40 cases, for a 15.00% pass rate, with zero runtime failures. Its p95 latency was 24,950.0 milliseconds. The biggest issue was SEC retrieval: all 16 SEC cases had zero for Hit@5, MRR, context precision, and citation accuracy. The trace analysis showed that 15 cases reached research but returned no filing passages, while one case was misrouted. I also found weak guardrail behavior, internal rather than user-facing retirement clarification, and evaluator contract issues that obscured some supported evidence.”

## 2:05–3:00 — Improvements made

On screen: `evals/results/improvements_implemented.md`.

“I made six targeted improvements. First, I changed the SEC namespace from Microsoft-only vectors to the `sec-filings` namespace containing the Apple 10-K. Second, I propagated structured SEC citations through the workflow and added `[SEC-n]` answer markers. Third, I added a safety gate before routing. Fourth, I fixed legal and lawsuit questions so they route to SEC research. Fifth, I replaced the internal `retirement_inputs` message with concrete clarification questions. Sixth, I expanded the evaluator and adapter contracts so retrieved contexts, document IDs, citations, routes, tool events, clarification, refusal state, and structured evidence are recorded consistently.”

## 3:00–3:40 — Post-improvement result and measured delta

On screen: `06_post_improvement_wp002_output_with_citations.png`, `07_safety_refusal_input_output.png`, then `08_delta_report_metrics.png`.

“The `post_improvement_v2` run passed 16 of 40 cases, or 40.00%, again with zero runtime failures. That is an improvement of 10 passing cases and 25 percentage points. Citation accuracy moved from 0.0000 to 0.9031, faithfulness from 0.3750 to 0.9063, Hit@5 from 0.0000 to 0.6875, MRR from 0.0000 to 0.6063, and context precision from 0.0000 to 0.4750. Expected tool selection reached 1.0000. Guardrail accuracy and missing-input handling both moved from 0.0000 to 1.0000, and safety improved from 0.7500 to 1.0000.”

## 3:40–4:20 — Remaining limitations and close

On screen: remaining limitations in `docs/week4_evaluation_report.md`.

“There is still meaningful work to do. Five cases have retrieval proxy misses, two have incomplete answers, two have retrieval quality below the pass bar, and two have unfaithful or unsupported answers. Numeric correctness is pending for 12 cases, trajectory is pending for 4, and agent cost is not measurable from the graph result. Post-improvement p95 latency increased to 44,178.1 milliseconds, although it stayed below the 60,000-millisecond pass bar. My next steps would be adding human-reviewed SEC relevance labels, approved numeric tolerances, expected multi-tool trajectories, cost instrumentation, and continued latency monitoring. The key result is that the same frozen dataset measured a clear improvement from 15.00% to 40.00%, while the remaining gaps are documented rather than hidden.”

## Recording checklist

- Keep the Loom between 3 and 5 minutes.
- Show the LangSmith project name and run metadata without exposing secrets.
- Use the baseline WP-002 and post-improvement WP-002 evidence as the main before-and-after example.
- Show the safety refusal as a separate high-risk improvement.
- End on the delta and remaining limitations rather than claiming the agent is finished.
