# WealthPlan LangGraph

This folder is a clean Python/LangGraph recreation of the WealthPlan n8n course MVP. It does not copy credentials, execution histories, or private values from the n8n exports.

## Week 4 Evaluation: WealthPlan 2.0

WealthPlan 2.0 is a multi-agent financial research and planning assistant. Its frozen golden dataset contains 40 cases covering SEC RAG, fundamentals, portfolio analysis, retirement planning, multi-tool routing, edge cases, known failures, and adversarial guardrail prompts. Evaluation traces are recorded in the LangSmith project `wealthplan-week4-evals`.

| Run | Passed | Pass rate | Runtime failures |
| --- | ---: | ---: | ---: |
| `baseline_v1` | 6/40 | 15.00% | 0 |
| `post_improvement_v2` | 16/40 | 40.00% | 0 |

Measured improvement: **+10 passing cases and +25 percentage points**.

Major metric improvements:

- `citation_accuracy`: 0.0000 -> 0.9031
- `faithfulness`: 0.3750 -> 0.9063
- `expected_tool_selected`: 0.6000 -> 1.0000
- `guardrail_accuracy`: 0.0000 -> 1.0000
- `missing_input_handling`: 0.0000 -> 1.0000
- `safety`: 0.7500 -> 1.0000

Remaining limitations include retrieval proxy misses, pending numeric-correctness and trajectory metrics, unavailable agent-cost measurement, and increased p95 latency that remained below the pass bar. See the [full Week 4 evaluation report](docs/week4_evaluation_report.md), [measured delta report](evals/results/delta_report.md), [frozen golden dataset](evals/golden_dataset_v1.jsonl), and [LangSmith trace evidence](docs/langsmith_trace_evidence.md).

### Evaluation artifacts

- [Week 4 evaluation report](docs/week4_evaluation_report.md)
- [LangSmith trace evidence](docs/langsmith_trace_evidence.md)
- [Golden dataset review workbook](evals/golden_dataset_review.xlsx)
- [Frozen golden dataset v1](evals/golden_dataset_v1.jsonl)
- [Golden dataset validation](evals/golden_dataset_validation.md)
- [Baseline summary](evals/results/baseline_summary.md)
- [Failure analysis](evals/results/failure_analysis.md)
- [Priority improvement plan](evals/results/priority_improvement_plan.md)
- [Improvements implemented](evals/results/improvements_implemented.md)
- [Post-improvement summary](evals/results/post_improvement_summary.md)
- [Delta report](evals/results/delta_report.md)

## Project structure

```text
wealthplan-langgraph/
├── src/wealthplan/
│   ├── state.py      # Shared request, specialist-output, and graph-state contracts
│   ├── prompts.py    # Shared model instructions
│   ├── config.py     # Environment-backed settings
│   ├── multi_agent.py # Public multi-agent graph entry point used by Streamlit
│   ├── resilience.py # Retry and timestamped-cache utilities
│   ├── agents/
│   │   ├── supervisor.py
│   │   ├── goal_agent.py
│   │   ├── portfolio_agent.py
│   │   ├── research_agent.py
│   │   └── review_agent.py
│   ├── tools/
│   │   ├── retirement.py
│   │   ├── portfolio.py
│   │   ├── fundamentals.py
│   │   └── sec_rag.py
│   ├── database/     # PostgreSQL repository, checkpoints, migrations, and CLI
│   ├── ingestion/    # SEC discovery, chunking, download, and Pinecone indexing
│   ├── ui/           # Streamlit application and UI adapters
│   └── cli.py        # Terminal chat entry point
├── tests/            # Tests mirror agents/tools/database/ingestion/ui
├── docs/             # Design and operating documentation
└── streamlit_app.py  # Small Streamlit launcher
```

Imports follow the same boundaries—for example, the supervisor lives at
`wealthplan.agents.supervisor` and PostgreSQL persistence lives at
`wealthplan.database.postgres`.

The version 1 runtime graph mirrors the original n8n canvas:

```text
user -> agent -> selected tool(s) -> agent -> grounded response
                  |-- SEC filing search (OpenAI -> Pinecone -> Cohere)
                  |-- retirement goal calculator
                  |-- portfolio analytics
                  `-- company financial metrics
```

The retirement and portfolio tools are deterministic. The model routes requests and explains results; it does not perform financial arithmetic. SEC ticker-to-CIK resolution and Company Facts provide multi-ticker historical fundamentals; filing search returns no evidence when a ticker has not been indexed or external RAG services are not configured.

The Streamlit application runs the WealthPlan 2.0 supervised graph through
`wealthplan.multi_agent.build_graph`:

```text
Streamlit request
    -> normalize -> plan/route -> validate
    -> parallel goal / portfolio / market-research specialists
    -> grounded report assembly -> risk review
    -> human approval interrupt
         |-- approve -> optional PostgreSQL persistence -> approved report
         |-- edit ----> apply edits -> risk review -> approval interrupt
         `-- reject ------------------------------------> rejected report
```

Specialist fan-out uses LangGraph `Send`; report assembly is a deferred fan-in
node. OpenAI structured routing and report assembly are used when configured,
with deterministic fallbacks when they are unavailable. Goal and portfolio
calculations remain deterministic. No persistence write is authorized before
the human approval node returns `approve`.

See [the implementation plan](docs/implementation_plan.md) and [the SEC chunk-construction strategy](docs/chunking_strategy.md).
See [SEC ingestion](docs/sec_ingestion.md) for the end-to-end indexing command.

## Week 3 submission documentation

The [complete Week 3 project documentation](docs/week3_project_documentation.md)
includes the project one-liner, all framework fields, datasets, runtime and
vibe-coding prompts, implementation iterations, state boundaries, human approval,
error handling, requirements scorecard, known limitations, and demo checklist.
It includes two reusable infographics:

- [WealthPlan2.0 illustrated project infographic](docs/WealthPlan2.0.png)
- [Multi-agent workflow infographic](docs/week3_workflow_infographic.svg)
- [State, safety, and error-handling infographic](docs/week3_state_safety_infographic.svg)

## Demo playbook

Two presentation-ready walkthroughs are available in the
[demo playbook](docs/demo_playbook.md):

- a 5-to-7-minute user demo focused on the investor experience, review loop,
  approval, and report history;
- an 8-to-10-minute technical demo that maps the implementation to every Week 3
  agent-framework field and identifies the corresponding UI and code proof
  points.

The technical walkthrough includes the project one-liner, control flow, state
and memory boundaries, read/write tool classification, failure recovery,
human-in-the-loop behavior, a measurable success target, and limitations that
should be disclosed during evaluation.

The Streamlit left navigation supports an embedded 4-minute 46-second guided
walkthrough with Microsoft Zira female narration, visible cursor cues, and
optional English captions. It shows an actual multi-agent run, SEC and Pinecone
evidence, deterministic outputs, the review loop, and a final rejection with no
approved write. The generated MP4 is distributed separately and intentionally
excluded from Git; lightweight captured frames and subtitles remain under
`assets/demos/`. The complete narration is in
[`docs/technical_demo_script.md`](docs/technical_demo_script.md).

## Current milestone

Implemented:

- Explicit LangGraph `agent -> tools -> agent` loop
- OpenAI tool calling
- Thread-scoped checkpoint memory
- Optional PostgreSQL checkpointer
- Retirement scenarios matching the original README demo checks
- Illustrative five-holding portfolio matching the documented aggregate totals
- Multi-ticker historical annual fundamentals from SEC Company Facts
- Fixed Apple FY2025 fallback for credential-free demonstrations
- Optional Pinecone top-10 retrieval and Cohere top-5 reranking
- One bounded retry for transient SEC/RAG failures, timestamped in-process caches, and clearly labeled stale-data fallback
- Insufficient-evidence guardrails
- Unit tests that require no credentials
- Typed WealthPlan 2.0 shared state
- Supervisor validation and specialist selection
- OpenAI Structured Outputs supervisor routing with explicit-selection priority and deterministic fallback
- Parallel specialist fan-out and reviewed fan-in
- Grounded structured report assembly with OpenAI and a deterministic fallback
- PostgreSQL schema and approval-gated durable report persistence
- Human approve/edit/reject interrupt, including edit/re-review cycles
- Polished Streamlit workspace with selectable/custom tickers, investor goal, risk profile, time horizon, editable holdings, dashboards, SEC citations, scenarios, and human approval
- Live n8n-style LangGraph workflow navigator with parallel-agent status, human-interrupt state, checkpoint-memory backend, Pinecone namespace, SEC, Cohere, and approval persistence visibility
- Write authorization only after approval
- Execution-event audit trails embedded in drafts and approved/rejected reports
- Section-aware SEC Item and paragraph chunk construction
- SEC submissions discovery and compliant filing download
- HTML cleaning and table-of-contents Item deduplication
- Accession manifest with duplicate skipping and ingestion status
- Stable-ID Pinecone batch indexing command

Still to migrate or extend:

- Exact original eight-quarter fundamentals series
- PostgreSQL batch portfolio import and database-backed calculation loading
- Production DOM-aware SEC subsection extraction and scheduled ingestion
- Retrieval evaluation command and the five-question dataset
- API interface and production UI hardening

## Setup with uv

Requirements: Python 3.11 or newer and `uv`.

```powershell
cd wealthplan-langgraph
Copy-Item .env.example .env
uv sync --extra dev
```

Dependency installation is intentionally separate from validation. Choose only
the optional extras required by your environment:

To enable the external SEC RAG adapter:

```powershell
uv sync --extra rag --extra dev
```

Ingest the latest 10-K for any ticker in the SEC company map after configuring Pinecone and the SEC user agent. The CIK is resolved automatically:

```powershell
uv run wealthplan-ingest --ticker MSFT --form 10-K
```

`--cik` remains available as an optional override.

For PostgreSQL-backed conversation checkpoints:

```powershell
uv sync --extra postgres --extra dev
```

Configure and create the WealthPlan domain tables:

```env
WEALTHPLAN_POSTGRES_DSN=postgresql://user:password@host:5432/wealthplan
```

```powershell
uv run wealthplan-db setup
```

The schema includes users, investor profiles, goals, portfolios, holdings, price snapshots, workflow runs, approvals, approved reports, and ingestion records. Approved reports, the approved profile context, and user-entered holdings are written in one transaction only after the LangGraph human-approval interrupt returns `approve`. Streamlit shows durable report history by non-secret Profile ID. Without a DSN, approvals remain explicitly session-only.

Fill `.env` locally. Never paste keys into source files or commit `.env`.

### Environment configuration

| Variable | Required for | Default / behavior when absent |
| --- | --- | --- |
| `OPENAI_API_KEY` | Model routing, report prose, and v1 chat | Multi-agent routing and report assembly use deterministic fallbacks |
| `WEALTHPLAN_OPENAI_MODEL` | OpenAI model selection | `gpt-5-mini` |
| `WEALTHPLAN_SEC_USER_AGENT` | SEC Company Facts and ingestion requests | SEC network retrieval is unavailable |
| `PINECONE_API_KEY` + `WEALTHPLAN_PINECONE_INDEX_NAME` | Filing retrieval/indexing | Filing RAG is unavailable |
| `COHERE_API_KEY` | Filing reranking | Filing RAG is unavailable |
| `WEALTHPLAN_POSTGRES_DSN` | Durable checkpoints and approved-report history | In-memory checkpoints and session-only approval results |
| `WEALTHPLAN_INGESTION_MANIFEST_PATH` | Local ingestion manifest | `.data/ingestion_manifest.json` |
| Retry/cache variables in `.env.example` | Reliability tuning | Safe defaults from `Settings.from_env()` |

The Streamlit sidebar reports only `Ready`, `Missing`, or `Session only`; it
never renders credential or DSN values. Variables omitted from `.env` use the
documented defaults.

## Run

Streamlit WealthPlan 2.0 interface:

```powershell
uv run streamlit run streamlit_app.py
```

The browser interface starts a checkpointed supervisor run and presents readable financial cards, tables, charts, SEC evidence, scenario comparisons, and Approve/Edit/Reject controls. Users can analyze the course portfolio or edit their own holdings and price snapshot. With PostgreSQL configured, approved profile context, custom holdings, and reports are saved and appear in report history.

The live workflow navigator consumes LangGraph task and state streams. It marks
nodes running/completed/failed, shows unselected specialist branches as skipped,
and pauses at the human approval interrupt. Infrastructure badges identify the
active checkpoint backend, SEC Company Facts, Pinecone namespace, and Cohere
reranking path without exposing credentials.

Version 1 interactive terminal chat:

```powershell
uv run wealthplan
```

One request:

```powershell
uv run wealthplan --once "Analyze my demo portfolio."
```

Reuse `--thread-id` to continue the same checkpointed conversation:

```powershell
uv run wealthplan --thread-id demo-session
```

## Data labels and safety

- Portfolio prices are fixed illustrative values, not current market prices.
- Company fundamentals are historical filing facts, not current market data.
- Valuation data is intentionally unavailable.
- The application does not execute trades.
- Outputs are educational and are not financial, investment, tax, or legal advice.
- Cached SEC data is labeled with its retrieval timestamp; stale evidence is used only as an explicit outage fallback.

## Public fundamentals sources

When `WEALTHPLAN_SEC_USER_AGENT` is configured, the application resolves tickers using the SEC company-ticker map and requests standardized annual facts from the SEC Company Facts API. Coverage depends on SEC registration and the issuer's reported taxonomy concepts; this is broad public-company support, not a guarantee that every symbol or metric is available.

The credential-free Apple FY2025 fallback uses Apple's Form 10-K filed with the SEC:

<https://www.sec.gov/Archives/edgar/data/320193/000032019325000079/aapl-20250927.htm>

Free cash flow is calculated as operating cash flow minus payments for property, plant, and equipment.

Live quotes, intraday prices, and valuation multiples require a separate market-data provider and are not supplied by SEC filing data.

## Validation and known limitation

Safe offline validation for this change is limited to Python syntax compilation,
package import checks, and `pytest --collect-only`. Those checks must not invoke
OpenAI, Pinecone, Cohere, SEC, PostgreSQL, or any other external service.

The full automated `pytest` suite is deferred because the previous run hung.
This is a known validation limitation, not a passing full-suite result. Run the
full suite later in an environment where the hanging test can be isolated:

```powershell
uv run pytest
```

## Manual demo checklist

1. Start Streamlit and confirm the sidebar shows connection status without secret values.
2. Select only **Portfolio analysis**, keep the demonstration portfolio enabled, and generate a plan.
3. Review the portfolio dashboard and confirm the draft pauses at the human approval gate.
4. Request an edit, confirm the reviewer note appears in the revised next steps, then approve or reject.
5. Select company research or goal scenarios and confirm missing inputs are reported before specialist work starts.
6. If PostgreSQL is not configured, confirm approval is labeled session-only; if configured, confirm the report appears in History.

Start the application from this directory with:

```powershell
uv run streamlit run streamlit_app.py
```
