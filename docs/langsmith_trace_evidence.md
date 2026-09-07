# LangSmith trace evidence

## Evaluation identifiers

- LangSmith project: `wealthplan-week4-evals`
- Step 1 smoke trace: `SMOKE-001 WealthPlan LangSmith Setup`
- Baseline run: `baseline_v1`
- Post-improvement run: `post_improvement_v2`
- Dataset: `evals/golden_dataset_v1.jsonl`
- Dataset size: 40 cases
- Dataset SHA-256: `1F8EDE0B83102692D9A00D03E606204554F554C89A8717823432F898F621252D`
- Post-improvement trace verification: 40 trace IDs verified under `wealthplan-week4-evals`

## Screenshot Evidence

The smoke-trace capture proves that `SMOKE-001 WealthPlan LangSmith Setup` reached the correct project with its setup metadata.

![Step 1 LangSmith smoke trace attributes](../Screenshots/Wealth-Plan-02_step1_smoke_trace_attributes.png)

The baseline SEC RAG analysis capture documents why the baseline retrieval metrics were zero and why the problem was not simply adapter extraction.

![Baseline SEC RAG failure analysis](../Screenshots/Wealth-Plan-03_baseline_failure_analysis_sec_rag.png)

The first baseline trace capture proves that WP-002 was recorded as a `baseline_v1` SEC RAG case in `wealthplan-week4-evals`.

![Baseline SEC RAG trace attributes](../Screenshots/Wealth-Plan-03_baseline_sec_rag_trace_attributes.png)

The supporting baseline metrics capture shows metric coverage and confirms the 24,950.0 ms p95 latency remained below the 60,000 ms pass bar.

![Supporting baseline metrics and latency](../Screenshots/Wealth-Plan-03-1_baseline_sec_rag_trace_attributes.png)

The baseline summary capture proves the recorded baseline metric averages, including the all-zero SEC retrieval metrics.

![Baseline summary metrics](../Screenshots/Wealth-Plan-04_baseline_summary_metrics.png)

The detailed WP-002 capture proves the case ID, expected SEC tool, dataset version, run name, and baseline agent version recorded in LangSmith.

![Baseline WP-002 trace attributes](../Screenshots/Wealth-Plan-05_baseline_wp002_trace_attributes.png)

The safety input capture proves that WP-039 preserved the adversarial guaranteed-return request and invoked the pre-routing safety path.

![Safety refusal input](../Screenshots/Wealth-Plan-07_safety_refusal_input.png)

The safety output capture proves that WP-039 refused guarantees and direct buy/sell instructions and supplied a safer educational alternative.

![Safety refusal output](../Screenshots/Wealth-Plan-07_safety_refusal_output.png)

The delta-report capture proves the baseline-to-post comparison, including the 15.00% to 40.00% pass-rate change and approved metric deltas.

![Measured delta report metrics](../Screenshots/Wealth-Plan-08_delta_report_metrics.png)

## Evidence gaps

The current `Screenshots/` folder does not contain a dedicated LangSmith project-overview capture or a post-improvement WP-002 output capture with readable `[SEC-n]` citations. Those images should be added if the final submission rubric requires direct evidence for those two views.

All embedded filenames were matched exactly against files in `Screenshots/`. The images were reviewed and do not show API keys, `.env` contents, or other secrets.
