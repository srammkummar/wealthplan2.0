# WealthPlan demo playbook

This playbook provides two independent live demos of the same application. The
user demo explains the outcome without implementation jargon. The technical
demo explains how the build satisfies the Week 3 agent framework.

## Before either demo

Start the application from the `wealthplan-langgraph` directory:

```powershell
uv run streamlit run streamlit_app.py
```

Confirm the sidebar reports configuration status without displaying any secret
values. For the strongest filing-search demonstration, select a ticker already
indexed in the configured Pinecone namespace. MSFT is the known indexed example.
Use AAPL when demonstrating historical SEC Company Facts independently of filing
passage indexing. PostgreSQL must report **Ready** if the demo needs to show a
new approved report in History; otherwise the approval is explicitly session-only.

Keep this distinction clear:

- SEC Company Facts supplies standardized historical financial metrics and does
  not require a Pinecone vector for the ticker.
- Pinecone supplies searchable filing passages only for filings deliberately
  ingested into the current namespace.
- Cohere reranks the retrieved filing passages; it does not create the source
  evidence.
- Portfolio prices in the prototype are illustrative, not live market quotes.

## Demo 1: user walkthrough

**Audience:** A prospective user who wants to understand what WealthPlan does.

**Suggested duration:** 5 to 7 minutes.

**User story:** An investor wants one educational workspace that combines a
portfolio review, retirement scenarios, and grounded company research before
they decide which questions to discuss with a qualified adviser.

### Setup

Use the following repeatable inputs:

| Input | Demo value |
| --- | --- |
| Profile name | Course Investor |
| Profile ID | `course-investor` |
| Company | MSFT |
| Primary goal | Build long-term wealth |
| Risk profile | Moderate |
| Time horizon | 15 years |
| Analyses | Company research, portfolio analysis, goal planning |
| Portfolio | Demonstration portfolio |
| Research question | Summarize reported fundamentals and principal risks, then explain what deserves further review. |

Leave the default retirement assumptions in place unless the audience asks to
see a scenario change.

### Live flow and talk track

1. **Frame the problem.**

   Say: “Wealth planning usually means switching among a portfolio spreadsheet,
   retirement calculators, and long SEC filings. WealthPlan brings those inputs
   into one reviewable educational workflow.”

2. **Enter the investor context.**

   Show the profile, goal, risk level, time horizon, ticker, and selected analyses.
   Explain that the user controls the scope; selecting fewer analyses causes the
   unneeded specialist branches to be skipped.

3. **Generate the plan.**

   Click **Generate WealthPlan** and point to the live workflow navigator.
   Say: “The supervisor validates the request and delegates independent work. It
   is not answering with one model call.”

4. **Review the outputs.**

   Open these tabs in order:

   - **Overview:** summarize the combined findings and visible warnings.
   - **Company research:** distinguish historical SEC metrics from retrieved,
     cited filing passages.
   - **Portfolio dashboard:** show allocation, gain/loss, diversification, and
     concentration results from deterministic calculations.
   - **Goals & scenarios:** compare the configured return scenarios and funding
     gap without presenting them as guaranteed outcomes.

5. **Demonstrate human control.**

   Open **Review & approval**. First choose **Edit**, enter “Add a next step to
   review concentration risk,” and resume. Show that review runs again and the
   workflow pauses again. Then choose **Approve**.

6. **Show durable history.**

   Open **History** and show the approved report. Explain that the database write
   happened only after approval. A rejected report would not be saved as an
   approved plan.

7. **Close with the safety boundary.**

   Say: “This is an educational planning prototype. It reports historical and
   illustrative information, does not provide live valuation, and never places
   a trade.”

### Expected user-demo result

- The requested specialists complete while unselected branches are skipped.
- Filing evidence identifies its filing, section, date, and source.
- The report pauses before any durable approval write.
- An edit loops through review and returns to human approval.
- Approval creates a History entry; rejection does not create an approved entry.

If filing retrieval is unavailable, do not hide it. Show the explicit
insufficient-evidence or service warning and explain that safe degradation is an
agent requirement, not merely a happy-path feature.

## Demo 2: Week 3 technical walkthrough

**Audience:** Instructors, reviewers, and developers evaluating the agentic
architecture.

**Suggested duration:** 8 to 10 minutes.

### The one-liner

> WealthPlan helps an individual investor turn a profile, holdings, goals, and
> an SEC research question into a reviewed educational plan in Streamlit,
> replacing manual switching among filings, spreadsheets, and retirement
> calculators. It autonomously routes work to research, portfolio, and goal
> specialists using SEC data, filing retrieval, and deterministic calculators;
> it hands off before persistence, and its target is for at least four of five
> representative runs to produce a correctly routed, grounded or explicitly
> insufficient-evidence report in under five minutes with zero unapproved writes.

The “four of five” success rate is an evaluation target, not a measured claim.
The retrieval evaluation dataset and repeatable end-to-end scorecard remain
future work.

### Framework mapping

| Week 3 field | WealthPlan implementation |
| --- | --- |
| Agent goal | Produce a multi-part, reviewed educational WealthPlan from investor context and grounded evidence. |
| Where people use it | A Streamlit web workspace. The LangGraph entry point is UI-independent and can support other surfaces later. |
| Steps in order | Normalize request → route → validate → delegate → run specialists in parallel → assemble → risk review → human decision → approve, edit, or reject. |
| What it can do | Read SEC Company Facts; retrieve and rerank indexed filing passages; calculate portfolio analytics; calculate retirement scenarios; assemble and review a report; write an approved report to PostgreSQL only after authorization. |
| What it remembers | Typed state for the active run; thread checkpoints in memory or PostgreSQL; Streamlit session context; approved profile, holdings, and report records in PostgreSQL after approval. Pinecone is the filing corpus, not user memory. |
| What it should never do | Never trade, move money, guarantee returns, invent unavailable evidence, expose credentials, treat illustrative prices as live, or persist an approved report before approval. |
| Human in the loop | A LangGraph `interrupt` pauses on the draft. Approve authorizes persistence, edit loops back through risk review, and reject ends without an approved write. |
| When something breaks | Missing inputs stop with a clarification request; model failures use deterministic fallbacks; transient SEC/RAG failures retry once and may use timestamped stale cache; missing evidence is labeled; specialist and persistence failures remain visible. |
| How we know it worked | Target: at least four of five representative workflows complete in under five minutes with correct routing, valid deterministic calculations, grounded citations or an insufficiency response, and zero unapproved writes. |

### Capability and authorization boundary

| Capability | Type | Runs autonomously? | Notes |
| --- | --- | --- | --- |
| SEC Company Facts lookup | Read | Yes | Retrieves historical standardized filing facts. |
| Pinecone filing search | Read | Yes | Searches only the configured namespace and filters by ticker. |
| Cohere passage reranking | Compute | Yes | Reorders retrieved evidence; it does not create source facts. |
| Portfolio analytics | Compute | Yes | Uses deterministic arithmetic over supplied or demonstration holdings. |
| Retirement scenarios | Compute | Yes | Uses deterministic assumptions and labels projections as scenarios. |
| Routing and report assembly | Model/compute | Yes | Uses LangChain model integrations when configured and deterministic fallbacks otherwise. |
| Workflow checkpoint | Operational state | Yes | Saves resumable graph state by thread; it is not an approved business record. |
| Approved-plan persistence | Durable write | No | The approve branch alone writes the profile context, holdings, approval, and report transaction. |
| Filing ingestion | Administrative write | No interactive path | A separate CLI command downloads, chunks, embeds, and indexes an explicitly selected filing. |

The approval rule applies to durable user/business records and external actions.
Automatic checkpointing is internal workflow state required to pause and resume
the graph; it does not publish a plan, execute a trade, or mark a draft approved.

### Five technical proof points

1. **It is a graph, not a one-shot response.**

   Open `src/wealthplan/agents/supervisor.py`. Show the `StateGraph`, explicit
   nodes, conditional edges, parallel `Send` fan-out, deferred report fan-in, and
   approval routes. In the UI, the workflow navigator makes those state
   transitions visible during execution.

2. **State is explicit and scoped.**

   Open `src/wealthplan/state.py`. `WealthPlanState` contains the request, routing
   decision, specialist outputs, review, draft, approval response, final report,
   audit events, and `write_authorized`. Open
   `src/wealthplan/database/checkpointing.py` to show thread-level
   `InMemorySaver` or `PostgresSaver`. Approved long-term records use a separate
   repository rather than treating the vector index as memory.

3. **Specialists use bounded capabilities.**

   Goal and portfolio agents perform deterministic arithmetic. Market research
   combines SEC Company Facts with ticker-filtered Pinecone retrieval and Cohere
   top-five reranking. LangChain integrations provide model messages, structured
   output, embeddings, vector-store access, and reranking; LangGraph owns the
   control flow and state transitions.

4. **Failures change the control flow.**

   Show input validation and the clarification branch, then explain the bounded
   retry and timestamped-cache behavior in `src/wealthplan/resilience.py`.
   Structured routing and report assembly have deterministic fallbacks. An
   unindexed ticker can still have SEC Company Facts while correctly returning
   no indexed filing evidence. A database persistence error is shown as failed,
   not reported as a successful save.

5. **The write boundary is enforced.**

   At the approval node, show `write_authorized` is false. Resume with Edit to
   demonstrate the review loop, or Reject to demonstrate a non-mutating end.
   Resume with Approve and show that only the approval branch calls the
   PostgreSQL repository and creates the History record.

### Architecture narration

```text
Streamlit request
    ↓
LangGraph supervisor: normalize → route → validate
    ↓
LangGraph Send fan-out
    ├── Goal specialist ───── deterministic retirement calculator
    ├── Portfolio specialist  deterministic portfolio analytics
    └── Research specialist ─ SEC Company Facts
                              Pinecone ticker-filtered filing search
                              Cohere reranking
    ↓ deferred fan-in
Report assembly → policy/risk review
    ↓
LangGraph human interrupt
    ├── Edit ──── review loop
    ├── Reject ── stop without approved write
    └── Approve ─ PostgreSQL transaction → History

Thread state: InMemorySaver or PostgreSQL checkpointer
Filing corpus: Pinecone namespace (not conversation memory)
```

### Requirement checklist to state aloud

- **Bring-your-own use case:** wealth planning and SEC-grounded research.
- **Code-heavy track:** Python with LangChain integrations and LangGraph control
  flow.
- **Autonomous next-step decisions:** supervisor routing and conditional edges.
- **Multiple tools/capabilities:** SEC facts, filing RAG, portfolio analytics,
  retirement scenarios, report assembly, and approved persistence.
- **State across steps:** typed shared state plus thread checkpoints.
- **Failure recovery:** validation, bounded retry, cache fallback, deterministic
  model fallback, and visible safe stops.
- **Human handoff:** approval interrupt before the only durable write path.
- **End-to-end task:** the user moves from inputs to a reviewed and optionally
  persisted plan, rather than receiving one isolated lookup.

### Current limitations to disclose

- This is educational software, not financial advice or trade execution.
- SEC facts and filing passages are historical; live quotes and valuation data
  are not implemented.
- Filing passage search requires the selected ticker to be ingested into the
  configured Pinecone namespace.
- Portfolio price snapshots are illustrative unless a separate data source is
  added.
- The four-of-five end-to-end success target has not yet been formally measured.
- Full automated test execution is currently deferred because a previous full
  run hung; syntax, imports, collection, and focused regression tests have been
  used as the quick validation boundary.

## Presenter reset checklist

Before switching between demos:

1. Use a fresh Streamlit session or generate a new plan.
2. Confirm MSFT is selected when filing-passage retrieval must be visible.
3. Confirm all three analyses are selected for the complete workflow.
4. Verify the workflow navigator starts with unselected paths marked skipped.
5. Use a unique Profile ID if you want the newest History row to be obvious.
6. Never open `.env` or display API keys or the PostgreSQL DSN during the demo.
