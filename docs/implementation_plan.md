# WealthPlan 2.0 completion plan

The target is a supervised, stateful research-and-planning workflow with four specialist responsibilities, human approval, recoverable execution, and a Streamlit interface. Work should proceed in vertical slices so each phase remains demonstrable and testable.

## Phase 1 — Orchestration foundation

Status: implemented and tested.

- [x] Define typed shared workflow state.
- [x] Validate requests and name missing fields.
- [x] Select only the necessary specialists.
- [x] Fan out independent specialist work and fan results into review.
- [x] Keep all external writes unauthorized until approval.
- [x] Add execution events for node outcomes.

Acceptance: a portfolio-only request invokes only portfolio analysis, produces a reviewed draft, pauses for approval, and writes no approved result until resumed.

## Phase 2 — SEC ingestion and evidence construction

Status: initial end-to-end command implemented and tested.

- [x] Download filings using an SEC-compliant user agent.
- [x] Resolve ticker symbols to SEC CIK identifiers.
- [x] Parse the document body and remove executable markup and table-of-contents Item duplicates.
- [x] Extract Item boundaries.
- [x] Create paragraph-aligned, evidence-sized chunks.
- [x] Add accession-number duplicate detection and ingestion status records in a local manifest.
- [x] Embed and upsert to Pinecone with the complete metadata contract.
- [ ] Add DOM-aware subsection boundaries and repeated page-header removal.
- [ ] Move ingestion status from the local manifest to PostgreSQL.
- [ ] Add scheduled discovery and production retry/backoff policies.

Acceptance: no chunk crosses an Item boundary; rerunning an accession does not duplicate vectors; every retrieved passage has auditable source and section metadata.

## Phase 3 — PostgreSQL domain data

Status: schema, approval-gated profile/portfolio/report persistence, and approved-report history implemented.

- [x] Add migrations for users, profiles, goals, holdings, prices, workflow runs, approvals, and approved reports.
- [x] Add a database setup command.
- [x] Persist approved workflow runs, approval records, and reports only after approval.
- [x] Persist approved profile context, goals, and user-entered holdings in the approval transaction.
- [x] Read approved report history by profile ID.
- Add a portfolio seed/import command for batch onboarding.
- Keep current/illustrative prices explicitly labeled with timestamps.
- Separate thread checkpoints from approved long-term user facts.

Acceptance: portfolio calculations run from seeded PostgreSQL data, and unapproved generated text never becomes durable profile data.

## Phase 4 — Specialist agents

Status: structured specialist outputs and grounded report assembly implemented.

- Goal Planning: collect/validate profile and retirement inputs, then call deterministic scenario tools.
- Portfolio Analysis: query approved holdings and calculate allocation, gains, diversification, and concentration.
- Market Research: combine multi-ticker SEC Company Facts with section-aware SEC evidence and citations.
- Risk & Review: verify calculations, citations, freshness labels, assumptions, and policy constraints.
- [x] Assemble a stable executive summary, key findings, risk considerations, and next steps using OpenAI Structured Outputs with a deterministic fallback.
- Give each specialist only its required context and tools.

Acceptance: combined requests can invoke multiple specialists, while each output conforms to a structured schema and exposes warnings and evidence.

## Phase 5 — Supervisor planning and recovery

Status: structured model routing, bounded service recovery, and auditable reports implemented; bounded revise loops remain.

- [x] Replace the transparent keyword fallback with structured OpenAI routing while retaining deterministic validation and fallback.
- Add a bounded plan/revise loop.
- [x] Retry transient external failures once for SEC Company Facts and filing retrieval.
- [x] Fall back to cached data with a timestamp when permitted.
- [x] Stop and ask the user when required information is absent.
- [x] Include node outcomes, routing, authorization, and persistence events in reviewed reports.
- Persist detailed tool-call and citation audit records in dedicated PostgreSQL tables.

Acceptance: routing tests cover single-agent and multi-agent requests; injected service failures demonstrate retry, cache fallback, and safe stop behavior.

## Phase 6 — Human approval and controlled writes

- Present the assembled report and proposed watchlist changes through a LangGraph interrupt.
- Support approve, edit, and reject.
- Re-run review after edits.
- Save reports or update a simulated watchlist only after approval.
- Never execute trades or guarantee returns.

Acceptance: automated tests prove that every write path requires an approval checkpoint and that rejected plans remain non-mutating.

## Phase 7 — Streamlit experience

Status: initial end-to-end interface implemented.

- [x] Investor input for selectable/custom ticker, goal, risk profile, time horizon, holdings, research question, selected analyses, and retirement scenarios.
- [x] Readable portfolio, market-research, and goal-planning cards, tables, and charts without raw JSON.
- [x] Review screen with approve/edit/reject controls.
- [x] Citation cards showing filing, section, date, and source URL.
- [x] Session-scoped user holdings and risk-profile fields.
- [x] Persist approved user holdings and risk profiles in PostgreSQL.
- [x] Approved report history and richer external-service error status.

Acceptance: a user can complete the full demo without command-line interaction and can resume an interrupted run by thread ID.

## Phase 8 — Evaluation and release readiness

- Expand retrieval evaluation beyond five questions.
- Add agent-routing, calculation, citation, refusal, approval, and recovery tests.
- Measure answer faithfulness and claim-level citation completeness.
- Add threat tests for prompt injection inside retrieved filings.
- Add Docker configuration, CI, health checks, and operating documentation.

Acceptance: all success measures in the target diagram are reported: routing, calculations, grounded citations, approval enforcement, and failure recovery.
