# Golden dataset validation

- Source Excel file: `evals/golden_dataset_review.xlsx`
- Output JSONL file: `evals/golden_dataset_v1.jsonl`
- Total row count: 40
- Approved rows: 40
- Rows still pending review: 0

## Scenario distribution

| Scenario type | Rows |
| --- | ---: |
| happy_path | 20 |
| edge_case | 12 |
| known_failure | 6 |
| adversarial | 2 |

## Task type distribution

| Task type | Rows |
| --- | ---: |
| sec_rag | 16 |
| fundamentals | 7 |
| portfolio | 6 |
| retirement | 5 |
| multi_tool | 4 |
| guardrail | 2 |

## Validation checks

- Included only rows where `include_in_v1` is `yes`.
- Applied amended query and expected-behavior fields when populated.
- Confirmed exactly 40 nonblank JSONL lines.
- Parsed every line as valid JSON.
- Confirmed every row contains all required fields.
- Confirmed all 40 `case_id` values are unique.
- Confirmed the required scenario distribution.

`golden_dataset_v1.jsonl` should now remain frozen and be reused unchanged for
both `baseline_v1` and `post_improvement_v2`.
