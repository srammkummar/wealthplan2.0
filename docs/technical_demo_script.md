# WealthPlan real-app technical demo transcript

**Target runtime:** under five minutes

**Voice:** Microsoft Zira Desktop, female, en-US

**Format:** 1080p narrated walkthrough captured from the running Streamlit app

## 1. Configure the request

This is WealthPlan, our bring-your-own Week 3 use case. In Streamlit, an investor
supplies a profile, chooses a company, sets risk and time horizon, and asks a
research question. The one-line job is to turn that context into a grounded
educational plan that combines company research, portfolio analysis, goal
scenarios, review, and a human decision. This is the actual application, not a
mockup.

## 2. Choose bounded specialists

This is a multi-agent workflow, not one model calling every tool. A supervisor
agent receives the request and selects three bounded specialists: a company
research agent, a portfolio analysis agent, and a goal planning agent. Each
specialist owns a focused task, bounded tools, and a structured result. Shared
typed WealthPlan state carries routing, outputs, review findings, approval
responses, audit events, and write authorization without giving any specialist
unrestricted control.

## 3. Watch LangGraph execute

Generate WealthPlan invokes the LangGraph supervisor. After normalization and
Pydantic validation, it fans work out with LangGraph Send. The research,
portfolio, and goal agents run independently and may complete in parallel. Each
writes a structured result into shared state. LangGraph fans those results back
in at report assembly, sends the combined draft to risk review, and pauses at
human approval. That supervisor-specialist fan-out and fan-in is the core
multi-agent pattern. The badges identify checkpoint memory and the retrieval
services.

## 4. Ground the answer in SEC evidence

The company screen shows two data paths. Historical fundamentals come from the
SEC Company Facts XBRL API, independent of Pinecone. Filing questions use an
indexed 10-K corpus: embeddings search the LangGraph Pinecone namespace with a
ticker filter, then Cohere reranks candidates. The five Microsoft passages
retain filing section, accession, date, ticker, and source URL.

## 5. Keep financial arithmetic deterministic

The portfolio specialist calculates position value, allocation, gains, sector
exposure, and concentration from fixed holdings and illustrative prices. Those
numbers are produced by deterministic tools, not invented in model prose. The
model may explain the result, but it does not own the arithmetic. The application
labels the price basis and highlights concentration so the output remains
auditable and educational.

## 6. Make assumptions visible

The goal specialist projects the retirement target and compares four, six, and
eight percent return assumptions. Inputs such as savings, contribution,
inflation, withdrawal rate, and retirement age remain visible. The tool explicitly
warns that these are scenarios, not forecasts, and that taxes, fees, volatility,
and sequence-of-returns risk are outside this deterministic prototype.

## 7. Stop at a human approval gate

After report assembly, policy checks verify specialist completion, narrative
presence, deterministic calculations, data labels, and no write before approval.
LangGraph interrupt then pauses. Reads and calculations are autonomous, but a
consequential approved record requires a human choice. Approve can authorize one
PostgreSQL transaction. Edit loops through policy review. Reject must stop without
an approved write. The prototype never executes a trade.

## 8. Separate checkpoint memory from records

Memory has three roles. Typed graph state exists for the run. A thread
checkpointer supports pause and resume by thread ID. Approved profiles, holdings,
decisions, and reports live in the repository and appear in History. Pinecone
stores filing chunks only; it is evidence storage, not conversation memory.
Service failures retry or use labeled cache, while missing evidence remains
explicit.

## 9. Reviewer edits re-enter the graph

Request edits resumes the interrupted thread, applies reviewer instructions,
reruns risk review, and returns to the same human gate. Failures have deliberate
paths: missing inputs request clarification, model failures use deterministic
fallbacks, specialist errors become structured warnings, and persistence
failures display as failed rather than false success.

## 10. Reject ends safely with no write

The final decision is Reject. The navigator records rejected without a write, and
the workspace confirms that no write was authorized. This demonstrates the Week 3
framework end to end: a supervisor coordinating specialized agents, parallel
delegation, typed state, bounded tools, visible recovery, and human control of the
durable action. Success means a reviewable, grounded result with correct
calculations and zero unapproved writes, not simply a convincing model response.
