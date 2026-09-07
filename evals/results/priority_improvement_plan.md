# Priority improvement plan after baseline_v1

This plan is based on the frozen `golden_dataset_v1` and the updated `baseline_v1` failure analysis. It proposes work for a later improvement phase; it does not implement any agent or evaluator change in Step 5. Any evaluator-contract correction should be applied identically to a rescored baseline and `post_improvement_v2` so the comparison remains fair.

## Priority 1: restore evidence-bearing SEC retrieval and citations

Target clusters:

- Retrieval proxy miss: 16 cases
- Missing or unverifiable SEC citations: 16 cases
- SEC answer faithfulness and scope: 16 cases

Work to evaluate later:

- Audit the Apple filing ingestion, Pinecone index and namespace, ticker metadata, and query filter against known Apple 10-K passages.
- Add retrieval-stage diagnostics for candidate count, reranked count, status, cache status, attempts, and sanitized error type.
- Require every SEC narrative intent to be marked `needs_input` when filing evidence is absent, not only queries containing the current keyword subset.
- When evidence is absent, keep the response narrowly focused on the evidence gap instead of appending unrelated company-facts metrics.
- When evidence exists, preserve passage metadata as structured citations through the final report and adapter.

Expected post-improvement metric impact:

- `hit_at_5`, `mrr`, and `context_precision` should rise from zero on cases backed by the indexed filing.
- `citation_accuracy` and structured citation coverage should become measurable from actual passage references and move toward the 0.90 pass bar.
- SEC `faithfulness` should improve as answers use retrieved passages and avoid unsupported or off-scope fallback material.

## Priority 2: add an explicit safety decision before ordinary routing

Target clusters:

- Unsafe financial advice/guarantee: WP-039 and WP-040

Work to evaluate later:

- Detect prompt injection, guaranteed-return requests, advisor impersonation, and direct buy/sell commands before ticker or specialist validation.
- Return a clear refusal that rejects guarantees and personalized trade instructions while offering a neutral educational framework.
- Ensure unsafe user wording cannot be converted into a normal market-research request by the structured router.

Expected post-improvement metric impact:

- `guardrail_accuracy` should improve from 0/2 to 2/2.
- `safety` should improve from 0/2 to 2/2 for the guardrail cases.
- Guardrail cases should no longer end in a misleading missing-ticker clarification.

## Priority 3: correct intent routing and make clarification user-facing

Target clusters:

- Routing failures: WP-024 and WP-038
- Missing-input handling: WP-018, WP-019, WP-029, WP-030, and WP-037
- SEC specialist success-status inconsistency: WP-003, WP-008, WP-010, WP-022, and WP-034

Work to evaluate later:

- Make litigation/legal-risk language route to SEC research and treat “use every tool” as a request requiring scope clarification, not retirement planning.
- Map internal bundles such as `retirement_inputs` to the minimum concrete fields needed for that query, while recognizing values the user already provided.
- Keep specialist and final statuses consistent with source requirements: an SEC-only question without filing passages must not report a successful research result.

Expected post-improvement metric impact:

- `missing_input_handling` should improve from 0/5 to 5/5 for the affected retirement cases.
- WP-024 should begin producing meaningful retrieval, citation, and faithfulness measurements instead of a retirement clarification.
- WP-038 task completion and the future trajectory metric should improve when the agent rejects unnecessary tool use and requests the actual planning goal.

## Priority 4: repair the evaluator and adapter evidence contract

Target clusters:

- Tool-selection false failures: WP-018, WP-019, WP-029, WP-030, WP-037, and WP-038
- Faithfulness evidence mismatch across SEC cases
- Citation-presence false positives
- Retrieval and tool-path observability gaps

Work to evaluate later:

- Make expected-tool scoring conditional on input sufficiency. Do not require a calculator when the approved behavior is to ask for inputs, and do not require an unnecessary specialist for WP-038.
- Include structured fundamentals and their provenance in the judge evidence whenever the answer uses them.
- Tighten `citation_presence` so generic URLs, bracketed text, and source labels do not count as SEC passage citations.
- Persist retrieval contexts or safe context references, retrieval status, answerability, candidate/reranked counts, cache status, attempts, structured citations, and normalized route/tool events in result artifacts.
- Rename the all-zero citation cluster to `missing/unverifiable citation` unless a supplied citation was actually checked and found inaccurate.
- Add approved numeric references/tolerances and route/tool-event expectations if numeric correctness and trajectory are to become measurable.

Expected post-improvement metric impact:

- `expected_tool_selected` should stop creating false failures for correct missing-input stops.
- `faithfulness` should reflect all evidence actually supplied to the agent, rather than penalizing supported company facts that were omitted from the judge payload.
- `citation_presence` and `citation_accuracy` should align around structured, resolvable filing citations.
- `numeric_correctness` and `trajectory` can move from pending only after approved references are added.

## Recommended order and comparison rule

Implement Priority 1 first because it blocks all SEC evidence and citation metrics. Priority 2 addresses the highest-risk behavioral defect. Priority 3 fixes incorrect task handling and poor clarification. Priority 4 should be finalized before comparing runs; if it changes scoring semantics, rescore the unchanged baseline artifacts with the same evaluator version used for `post_improvement_v2` and report both the original and comparable baseline without overwriting provenance.
