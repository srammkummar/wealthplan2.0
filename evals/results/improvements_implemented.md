# Step 6 improvements implemented

## Scope

Step 6 implemented the four priorities from the baseline failure analysis. The frozen dataset was not edited, the full 40-case evaluation was not run, and no post-improvement or delta result file was created.

Frozen dataset SHA-256 before and after the work:

`1F8EDE0B83102692D9A00D03E606204554F554C89A8717823432F898F621252D`

## SEC retrieval and structured citations

### Baseline evidence

- Fifteen SEC cases reached the search service but returned `insufficient_evidence`, zero passages, and zero citations.
- All 16 SEC cases had zero retrieval proxy scores and zero citation accuracy.
- Eleven answers passed the old citation-presence regex using generic URLs or source markers despite having no structured citations.

### Root cause and changes

The configured Pinecone namespace, `wealthplan-langgraph-v1`, contained 236 vectors for Microsoft and no Apple vectors. The existing `sec-filings` namespace contained 570 vectors and returned Apple 10-K matches under the `AAPL` metadata filter. The local ignored `.env` now selects `sec-filings`; no secret value was changed or committed.

The SEC search result now records `passage_count` for successful, empty, cached, invalid, unconfigured, and service-error outcomes. The research specialist creates one structured citation per passage with a citation ID, rank, document ID, filing metadata, source URL, line location when available, and a bounded excerpt. It also records citation count and treats a broader set of qualitative filing questions as requiring passage evidence.

The report assembly policy requires filing claims to use matching citation IDs such as `[SEC-1]`. The deterministic fallback also preserves passage excerpts with their citation IDs. Specialist trace events include retrieval status, passage count, and citation count.

### Files changed

- `.env` (ignored local namespace selection only)
- `src/wealthplan/tools/sec_rag.py`
- `src/wealthplan/agents/research_agent.py`
- `src/wealthplan/agents/reporting.py`
- `src/wealthplan/agents/supervisor.py`
- `tests/tools/test_sec_rag.py`
- `tests/agents/test_specialist_agents.py`

### Expected metric impact

- Apple SEC cases can now supply contexts to `hit_at_5`, `mrr`, and `context_precision`.
- Structured citation presence and citation accuracy can be assessed against retrieved passages.
- Faithfulness should improve when the answer cites and stays within retrieved evidence.

### Risks and limitations

- Other environments must select a namespace that contains the required ticker corpus or ingest the filing into their configured namespace.
- The local ingestion manifest currently lists Microsoft only and may not describe all records in the shared `sec-filings` namespace.
- Citation IDs are local to each response and passage rank. The document ID plus filing metadata remains the durable provenance.
- No full-run retrieval score is claimed in Step 6.

## Pre-routing safety refusal

### Baseline evidence

- WP-039 and WP-040 asked for a ticker instead of refusing guaranteed-return, prompt-injection, advisor-impersonation, or direct-trade requests.
- Guardrail accuracy was 0/2.

### Changes

A deterministic `safety_gate` now runs after request normalization and before the routing model. It detects prompt injection, guaranteed-return requests, direct buy/sell instructions, advisor impersonation, and personalized investment-recommendation requests. Unsafe requests stop before specialist routing and return a refusal with a safer educational alternative.

The state and final report record the safety decision and reasons. The adapter reports `refusal_detected` and the executed `guardrail_refusal_logic` path, so the decision is visible in future LangSmith trace outputs.

### Files changed

- `src/wealthplan/state.py`
- `src/wealthplan/agents/supervisor.py`
- `tests/agents/test_routing.py`

### Expected metric impact

- WP-039 and WP-040 should improve on deterministic guardrail accuracy and the safety judge.
- WP-038 should no longer trigger specialists merely because it requests every tool and a personalized recommendation.

### Risks and limitations

- Deterministic language patterns cannot cover every paraphrase. Future changes should add reviewed cases before expanding the patterns.
- The refusal path intentionally favors safety and may require tuning if benign educational wording resembles a direct instruction.

## Routing and missing-input clarification

### Baseline evidence

- WP-024 routed a lawsuit-risk question to goal planning.
- WP-038 routed an over-broad tool request to retirement planning.
- Five retirement cases exposed the internal field name `retirement_inputs` and scored zero for missing-input handling.

### Changes

High-confidence SEC, lawsuit, litigation, legal, regulatory, business-description, product, competition, operations, and related filing intents route to market research. A deterministic override prevents the structured model from changing a narrow legal or SEC intent into an unrelated specialist route.

Missing retirement input responses now ask for concrete user-facing values: current age, target retirement age or horizon, current savings, monthly contribution, expected annual return, and expected retirement expenses or goal amount. The graph still keeps internal missing-field identifiers for state validation, but the adapter renders the user-facing questions. It does not run the retirement calculator until the structured input bundle is present.

### Files changed

- `src/wealthplan/prompts.py`
- `src/wealthplan/agents/supervisor.py`
- `src/wealthplan/state.py`
- `evals/agent_adapter.py`
- `tests/agents/test_routing.py`

### Expected metric impact

- Missing-input handling should improve for WP-018, WP-019, WP-029, WP-030, and WP-037.
- WP-024 should select market research rather than goal planning. Without a company or ticker in the query, it will safely request that missing research input instead of assuming Apple.
- WP-038 should take the safety/refusal path without executing unnecessary tools.

### Risks and limitations

- The adapter does not infer a hidden ticker from expected answers. A query without a company remains a legitimate clarification case.
- The clarification currently lists the standard retirement inputs and does not yet parse every partial value from free-form text into the structured calculator schema.

## Evaluator and adapter evidence contracts

### Baseline evidence

- Five retirement cases were penalized for not calling the calculator even though the reviewed behavior required clarification first.
- The faithfulness judge did not receive company-facts evidence used in answers.
- The CSV contract omitted contexts, structured citations, retrieval status, route, clarification, refusal, and tool-output diagnostics.

### Changes

`AgentRunResult` now supports:

- `retrieval_status`
- `retrieved_contexts`
- `retrieved_doc_ids`
- `retrieved_passage_count`
- `structured_citations`
- `citation_count`
- `route_selected`
- `specialist_selected`
- `clarification_requested`
- `refusal_detected`
- `tool_calls`
- `tool_outputs_summary`
- `structured_evidence`
- `retrieval_diagnostics`

The adapter populates those fields from graph state and keeps legacy `citations` compatible with structured citations. Future result rows will serialize the richer contract. The traced case wrapper also adds the key retrieval, routing, clarification, refusal, passage, and citation fields to LangSmith metadata after the case completes.

Tool selection now treats a verified missing-input stop as correct when the reviewed behavior says to ask before running the retirement calculator. A correct safety refusal can also satisfy a reviewed instruction to reject unnecessary tools. The structured citation check no longer treats generic URLs, bracketed text, or source labels as filing citations.

The LLM judge contract is versioned as `week4_measurement_judge_v2` and receives structured company-facts evidence as well as retrieved passages and structured citations. Citation failures without a citation are labeled `missing/unverifiable citation`; inaccurate citations remain a separate cluster.

### Files changed

- `evals/evaluation_schema.py`
- `evals/agent_adapter.py`
- `evals/evaluators.py`
- `evals/llm_judges.py`
- `evals/run_eval.py`
- `evals/validate_evaluator_setup.py`
- `tests/evals/test_evaluator_contracts.py`

### Expected metric impact

- Expected-tool scoring should stop penalizing correct retirement clarification behavior.
- Faithfulness can distinguish unsupported claims from company facts that were actually supplied to the agent.
- Citation presence and accuracy should align with resolvable passage-level citations.
- Future failure analysis will be able to separate routing, retrieval, clarification, refusal, and extraction failures directly from the result row.

### Risks and limitations

- Result CSV rows will be larger because they include contexts, citations, diagnostics, and structured evidence.
- Numeric correctness remains pending until approved values and tolerances exist.
- Trajectory remains pending until approved route and tool-event references exist.
- Any evaluator-version change must be applied consistently when comparing baseline and post-improvement runs.

## Targeted verification

- Focused unit tests: 28 passed.
- Evaluator setup validation: 40 cases loaded with the approved scenario distribution; no agent call was made.
- Real WP-002 smoke case: retrieval status `ok`, five retrieved passages, five document IDs, five structured citations, market-research route, and citation markers in the answer.
- The full 40-case evaluation was not run.
- `post_improvement_results.csv` and `delta_report.csv` were not created.
