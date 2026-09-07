# Week 4 submission checklist

## Evaluation artifacts

- [x] Golden dataset: `evals/golden_dataset_v1.jsonl`
- [x] Golden dataset review workbook: `evals/golden_dataset_review.xlsx`
- [x] Golden dataset validation: `evals/golden_dataset_validation.md`
- [x] Baseline results: `evals/results/baseline_results.csv`
- [x] Baseline summary: `evals/results/baseline_summary.md`
- [x] Failure analysis: `evals/results/failure_analysis.md`
- [x] Priority improvement plan: `evals/results/priority_improvement_plan.md`
- [x] Improvements implemented: `evals/results/improvements_implemented.md`
- [x] Post-improvement results: `evals/results/post_improvement_results.csv`
- [x] Post-improvement summary: `evals/results/post_improvement_summary.md`
- [x] Measured delta report: `evals/results/delta_report.md`
- [x] Machine-readable delta report: `evals/results/delta_report.csv`

## Submission documentation

- [x] Final evaluation report: `docs/week4_evaluation_report.md`
- [x] LangSmith trace evidence guide: `docs/langsmith_trace_evidence.md`
- [x] Loom walkthrough script: `docs/loom_script.md`
- [x] Remaining limitations documented
- [x] Production monitoring plan documented

## Canonical screenshot package

- [ ] `Screenshots/01_langsmith_project_overview.png` — capture still needed
- [ ] `Screenshots/02_step1_smoke_trace_attributes.png` — source image exists; copy or rename needed
- [ ] `Screenshots/03_baseline_failure_analysis_sec_rag.png` — source image exists; copy or rename needed
- [ ] `Screenshots/04_baseline_summary_metrics.png` — source image exists; copy or rename needed
- [ ] `Screenshots/05_baseline_wp002_trace_attributes.png` — source image exists; copy or rename needed
- [ ] `Screenshots/06_post_improvement_wp002_output_with_citations.png` — capture still needed
- [ ] `Screenshots/07_safety_refusal_input_output.png` — combine the existing input and output captures
- [ ] `Screenshots/08_delta_report_metrics.png` — source image exists; copy or rename needed

The source filenames and capture instructions are listed in `docs/langsmith_trace_evidence.md`. Mark an item complete only after the exact canonical file exists in `Screenshots/` and its content has been checked.

## Integrity checks

- [x] Baseline and post-improvement runs each contain 40 cases
- [x] Dataset remained unchanged between runs
- [x] Dataset SHA-256 is `1F8EDE0B83102692D9A00D03E606204554F554C89A8717823432F898F621252D`
- [x] Baseline pass rate is 15.00% (6/40)
- [x] Post-improvement pass rate is 40.00% (16/40)
- [x] Measured delta is +25 percentage points and +10 passing cases
- [x] Runtime failures are 0 in both runs
- [x] Baseline p95 latency is 24,950.0 ms
- [x] Post-improvement p95 latency is 44,178.1 ms
- [x] Both p95 latency values are below the 60,000 ms pass bar
- [x] Agent cost is reported as not measurable from the graph result
- [x] Baseline and post-improvement result CSVs were not modified during final packaging
- [x] No evaluation was rerun during final packaging

## Final handoff

- [ ] Finish the canonical screenshot package
- [ ] Record the 3–5 minute Loom walkthrough using `docs/loom_script.md`
- [ ] Add the Loom URL to the submission form or requested handoff location
- [ ] Review the final repository diff for secrets and unrelated files
- [ ] Submit the repository, documentation, screenshots, and Loom link
