"""Polished Streamlit workspace for the WealthPlan 2.0 graph."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from dotenv import load_dotenv
import pandas as pd
import streamlit as st

from wealthplan.config import Settings
from wealthplan.database.checkpointing import open_checkpointer
from wealthplan.database.postgres import (
    ApprovedReportRepository,
    report_repository_from_settings,
)
from wealthplan.multi_agent import build_graph
from wealthplan.tools.portfolio import DEMO_HOLDINGS
from wealthplan.ui.adapters import (
    build_ui_request,
    collect_citations,
    is_awaiting_approval,
    load_indexed_tickers,
    report_for_display,
    resume_ui_run,
    start_ui_run,
)
from wealthplan.ui.workflow import (
    apply_workflow_event,
    finalize_workflow_progress,
    initialize_workflow_progress,
    render_workflow_html,
)
from wealthplan.state import SpecialistName

TICKER_NAMES = {"AAPL": "Apple", "AMZN": "Amazon", "GOOGL": "Alphabet", "META": "Meta Platforms", "MSFT": "Microsoft", "NVDA": "NVIDIA", "TSLA": "Tesla"}
MODULES: dict[str, SpecialistName] = {"Company & SEC research": "market_research", "Portfolio analysis": "portfolio_analysis", "Goals & scenarios": "goal_planning"}


@dataclass
class GraphRuntime:
    graph: Any
    settings: Settings
    report_repository: ApprovedReportRepository
    checkpointer_context: AbstractContextManager[Any]


@st.cache_resource(show_spinner=False)
def get_runtime() -> GraphRuntime:
    load_dotenv()
    settings = Settings.from_env()
    context = open_checkpointer(settings)
    repository = report_repository_from_settings(settings)
    graph = build_graph(
        settings,
        checkpointer=context.__enter__(),
        report_repository=repository,
    )
    return GraphRuntime(
        graph=graph,
        settings=settings,
        report_repository=repository,
        checkpointer_context=context,
    )


def _theme() -> None:
    st.markdown(
        """
        <style>
        :root {--navy:#13233f;--blue:#2459a9;--teal:#137f78;--muted:#68758a;--border:#dde4ee}
        .stApp{background:#f7f9fc;color:#172033}
        [data-testid="stSidebar"]{background:linear-gradient(180deg,#11213d,#1b3157)}
        [data-testid="stSidebar"] *{color:#f5f8ff}
        [data-testid="stSidebar"] label p{color:#dfe8f7}
        [data-testid="stSidebar"] [data-baseweb="select"] *{color:#172033}
        [data-testid="stSidebar"] input{color:#172033}
        .wp-brand{font-size:1.55rem;font-weight:800;color:white;letter-spacing:-.03em}
        .wp-brand-sub{color:#aebfda;font-size:.82rem;margin-bottom:1.3rem}
        .wp-hero{background:linear-gradient(120deg,#13233f,#2459a9 62%,#137f78);border-radius:20px;padding:2rem 2.2rem;color:white;box-shadow:0 14px 32px rgba(20,45,80,.16);margin-bottom:1.2rem}
        .wp-hero small{color:#a8e2dc;text-transform:uppercase;letter-spacing:.13em;font-weight:750}
        .wp-hero h1{color:white;margin:.45rem 0 0;font-size:2.2rem;line-height:1.08}
        .wp-hero p{color:#dce8f7;max-width:760px;margin:.7rem 0 0}
        .wp-card{background:white;border:1px solid var(--border);border-radius:16px;padding:1rem 1.1rem;height:100%;box-shadow:0 4px 14px rgba(22,38,64,.05)}
        .wp-card-label{color:var(--muted);font-size:.72rem;text-transform:uppercase;letter-spacing:.08em}
        .wp-card-value{color:var(--navy);font-weight:750;font-size:1.02rem;margin:.3rem 0}
        .wp-steps{display:grid;grid-template-columns:repeat(4,1fr);gap:.65rem;margin:1rem 0}
        .wp-step{background:#effaf8;border:1px solid #79b8b2;border-radius:12px;padding:.75rem;color:var(--muted);font-size:.8rem}
        .wp-step strong{display:block;color:var(--navy)}
        [data-testid="stMetric"]{background:white;border:1px solid var(--border);border-radius:14px;padding:.9rem 1rem;box-shadow:0 3px 12px rgba(22,38,64,.04)}
        [data-testid="stMetricValue"]{color:var(--navy)}
        .stButton>button[kind="primary"]{background:linear-gradient(100deg,#2459a9,#137f78);border:0;border-radius:10px;font-weight:700}
        .wp-note{background:#fff9e9;border:1px solid #f0dfa6;border-radius:12px;padding:.75rem 1rem;color:#735d1e;font-size:.82rem}
        .wp-flow-canvas{background:#fff;border:1px solid var(--border);border-radius:18px;padding:1rem;box-shadow:0 4px 14px rgba(22,38,64,.05);margin-bottom:1.2rem}
        .wp-flow-infra{display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:.9rem;padding-bottom:.8rem;border-bottom:1px solid var(--border)}
        .wp-flow-infra span{background:#f2f6fb;border:1px solid #d9e2ef;border-radius:999px;padding:.35rem .65rem;color:#4d5d73;font-size:.72rem}
        .wp-flow-infra strong{color:var(--navy)}
        .wp-flow-lane{display:grid;grid-template-columns:100px 1fr;gap:.7rem;align-items:start;margin:.55rem 0}
        .wp-flow-lane-title{color:var(--muted);font-size:.69rem;text-transform:uppercase;letter-spacing:.08em;font-weight:800;padding-top:.7rem}
        .wp-flow-row{display:flex;gap:.45rem;overflow-x:auto;padding:.12rem .1rem .4rem}
        .wp-flow-node{position:relative;min-width:142px;max-width:180px;border:1px solid #dbe2ec;border-radius:12px;padding:.62rem .7rem;background:#f8fafc;color:var(--navy);transition:all .2s ease}
        .wp-flow-node strong{display:block;font-size:.78rem;margin:.2rem 0}
        .wp-flow-node small{display:block;color:var(--muted);font-size:.66rem;line-height:1.25}
        .wp-flow-node em{display:block;color:#77859a;font-size:.61rem;font-style:normal;margin-top:.25rem}
        .wp-flow-state{font-size:.61rem;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);font-weight:800}
        .wp-flow-node.running{border-color:#2459a9;background:#eaf1ff;box-shadow:0 0 0 3px rgba(36,89,169,.11)}
        .wp-flow-node.running .wp-flow-state{color:#2459a9;animation:wp-pulse 1s ease-in-out infinite}
        .wp-flow-node.completed{border-color:#65a69f;background:#edfaf7}
        .wp-flow-node.completed .wp-flow-state{color:#137f78}
        .wp-flow-node.waiting{border-color:#d8a62a;background:#fff8df}
        .wp-flow-node.waiting .wp-flow-state{color:#8a6810}
        .wp-flow-node.failed{border-color:#dc6b72;background:#fff0f1}
        .wp-flow-node.failed .wp-flow-state{color:#a92f39}
        .wp-flow-node.skipped{opacity:.48;background:#f3f4f6}
        @keyframes wp-pulse{50%{opacity:.45}}
        @media(max-width:800px){.wp-steps{grid-template-columns:1fr 1fr}.wp-hero h1{font-size:1.7rem}.wp-flow-lane{grid-template-columns:1fr}.wp-flow-lane-title{padding-top:0}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _money(value: float | int | None, compact: bool = False) -> str:
    if value is None:
        return "Not reported"
    number = float(value)
    if compact and abs(number) >= 1_000_000_000:
        return f"${number / 1_000_000_000:,.1f}B"
    if compact and abs(number) >= 1_000_000:
        return f"${number / 1_000_000:,.1f}M"
    return f"${number:,.0f}"


def _metrics(items: list[tuple[str, str, str | None]]) -> None:
    for column, (label, value, help_text) in zip(st.columns(len(items)), items, strict=True):
        column.metric(label, value, help=help_text)


def _specialist(report: dict[str, Any], name: str) -> dict[str, Any] | None:
    return next((item for item in report.get("specialist_results", []) if item.get("specialist") == name), None)


def _retirement_inputs() -> dict[str, Any]:
    st.caption("Adjust the assumptions used by the deterministic scenario calculator.")
    columns = st.columns(4)
    with columns[0]:
        current_age = st.number_input("Current age", 18, 90, 40)
        savings = st.number_input("Current savings ($)", 0.0, value=100_000.0)
    with columns[1]:
        retirement_age = st.number_input("Retirement age", 19, 100, 65)
        contribution = st.number_input("Monthly contribution ($)", 0.0, value=1_000.0)
    with columns[2]:
        income = st.number_input("Monthly income goal ($)", 1.0, value=5_000.0)
        inflation = st.number_input("Inflation (%)", 0.0, value=2.5, step=0.1)
    with columns[3]:
        withdrawal = st.number_input("Withdrawal rate (%)", 0.1, value=4.0, step=0.1)
        rates = st.text_input("Return scenarios (%)", value="4, 6, 8")
    return {
        "current_age": int(current_age), "retirement_age": int(retirement_age),
        "current_savings": savings, "monthly_contribution": contribution,
        "desired_monthly_income_today": income, "inflation_rate": inflation / 100,
        "withdrawal_rate": withdrawal / 100,
        "annual_return_rates": [float(rate.strip()) / 100 for rate in rates.split(",") if rate.strip()],
    }


def _editable_holdings() -> list[dict[str, Any]]:
    initial = pd.DataFrame([holding.model_dump() for holding in DEMO_HOLDINGS])
    edited = st.data_editor(
        initial, num_rows="dynamic", hide_index=True, use_container_width=True,
        column_config={
            "ticker": st.column_config.TextColumn("Ticker", required=True),
            "name": st.column_config.TextColumn("Company / fund", required=True),
            "sector": st.column_config.TextColumn("Asset class", required=True),
            "quantity": st.column_config.NumberColumn("Quantity", min_value=0.01),
            "cost_basis_per_share": st.column_config.NumberColumn("Cost / share", min_value=0.0, format="$%.2f"),
            "illustrative_price": st.column_config.NumberColumn("Price snapshot", min_value=0.0, format="$%.2f"),
        }, key="holdings_editor",
    )
    records = []
    for record in edited.to_dict(orient="records"):
        if str(record.get("ticker", "")).strip():
            record["ticker"] = str(record["ticker"]).strip().upper()
            records.append(record)
    return records


def _sidebar(
    runtime: GraphRuntime,
) -> tuple[str, str, str, str, str, int, list[SpecialistName]]:
    with st.sidebar:
        st.markdown('<div class="wp-brand">WealthPlan 2.0</div>', unsafe_allow_html=True)
        st.markdown('<div class="wp-brand-sub">Research · Plan · Review</div>', unsafe_allow_html=True)
        st.page_link(
            "pages/1_Technical_Demo.py",
            label="Watch technical demo · 4:46",
        )
        st.page_link(
            "pages/2_WealthPlan2_Infographic.py",
            label="View WealthPlan2.0 workflow",
        )
        st.divider()
        st.markdown("#### Investor profile")
        display_name = st.text_input("Profile name", value="Course Investor")
        user_id = st.text_input(
            "Profile ID",
            value="course-investor",
            help="Use the same non-secret ID to retrieve approved history later.",
        ).strip()
        indexed = load_indexed_tickers(runtime.settings.ingestion_manifest_path)
        common = ["MSFT", "AAPL", "NVDA", "AMZN", "GOOGL", "META", "TSLA"]
        choices = list(dict.fromkeys([*indexed, *common])) + ["Other ticker…"]
        selected = st.selectbox(
            "Select company ticker", choices,
            format_func=lambda ticker: f"{ticker} · {TICKER_NAMES.get(ticker, 'Indexed filing')}" if ticker != "Other ticker…" else ticker,
        )
        ticker = selected
        if selected == "Other ticker…":
            ticker = st.text_input("Enter ticker", placeholder="e.g., JPM").upper().strip()
        if ticker in indexed:
            st.success(f"{ticker} SEC filing is indexed")
        elif ticker:
            st.caption(f"{ticker} filing citations require ingestion.")
        goal = st.selectbox("Primary goal", ["Build long-term wealth", "Plan for retirement", "Review portfolio risk", "Research a company", "Preserve capital"])
        risk = st.select_slider("Risk profile", options=["Conservative", "Moderate", "Growth", "Aggressive"], value="Moderate")
        horizon = st.slider("Time horizon", 1, 40, 15, format="%d years")
        st.markdown("#### Analysis modules")
        labels = st.multiselect("Choose specialist work", list(MODULES), default=["Company & SEC research", "Portfolio analysis"], label_visibility="collapsed")
        analyses = [MODULES[label] for label in labels]
        st.divider()
        if st.button("Start a new plan", use_container_width=True):
            st.session_state.pop("run_result", None)
            st.session_state.pop("thread_id", None)
            st.session_state.pop("workflow_progress", None)
            st.rerun()
        with st.expander("Data connections"):
            statuses = {"OpenAI": bool(runtime.settings.openai_api_key), "SEC": bool(runtime.settings.sec_user_agent), "Pinecone": runtime.settings.indexing_is_configured, "Cohere": bool(runtime.settings.cohere_api_key)}
            for name, ready in statuses.items():
                st.write(f"{name}: {'Ready' if ready else 'Missing'}")
            st.write(f"PostgreSQL: {'Ready' if runtime.settings.postgres_dsn else 'Session only'}")
    return user_id, display_name, ticker, goal, risk, horizon, analyses


def _status(result: dict[str, Any]) -> None:
    status = result.get("status", "unknown")
    messages = {
        "approved": (st.success, "Approved plan — the human review gate was completed."),
        "awaiting_approval": (st.info, "Draft complete — approve, edit, or reject it."),
        "needs_revision": (st.warning, "The review gate found missing evidence or incomplete work."),
        "rejected": (st.error, "The plan was rejected and no write was authorized."),
        "persistence_failed": (
            st.error,
            "The plan was approved, but durable storage failed. Review the storage message before retrying.",
        ),
    }
    renderer, message = messages.get(status, (st.info, f"Workflow status: {status.replace('_', ' ').title()}"))
    renderer(message)


def _overview(result: dict[str, Any], report: dict[str, Any]) -> None:
    request = report.get("request", result.get("request", {}))
    _metrics([
        ("Ticker", request.get("ticker", "—"), "Selected research company"),
        ("Primary goal", request.get("primary_goal", "Not specified"), None),
        ("Risk profile", request.get("risk_level", "Not specified"), None),
        ("Time horizon", f"{request.get('time_horizon_years', '—')} years", None),
    ])
    st.markdown("""<div class="wp-steps"><div class="wp-step"><strong>1 · Validate</strong>Request checked</div><div class="wp-step"><strong>2 · Delegate</strong>Specialists selected</div><div class="wp-step"><strong>3 · Review</strong>Evidence checked</div><div class="wp-step"><strong>4 · Approve</strong>Human controlled</div></div>""", unsafe_allow_html=True)
    routing = report.get("routing", {})
    if routing:
        st.caption(
            "Supervisor routing: "
            f"{routing.get('mode', 'unknown').replace('_', ' ')} · "
            f"{routing.get('rationale', '')}"
        )
        if routing.get("warning"):
            st.warning(routing["warning"])
    narrative = report.get("narrative", {})
    if narrative:
        st.markdown("#### Executive summary")
        st.write(narrative.get("executive_summary", ""))
        findings, considerations = st.columns(2)
        with findings:
            st.markdown("**Key findings**")
            for finding in narrative.get("key_findings", []):
                st.write(f"• {finding}")
        with considerations:
            st.markdown("**Risk considerations**")
            for consideration in narrative.get("risk_considerations", []):
                st.write(f"• {consideration}")
        if report.get("assembly_warning"):
            st.warning(report["assembly_warning"])
        st.caption(
            f"Report assembly: {report.get('assembly_mode', 'unknown').replace('_', ' ')}"
        )
    st.markdown("#### Specialist progress")
    for column, item in zip(st.columns(3), report.get("specialist_results", []), strict=False):
        with column:
            st.markdown(f"**{item.get('specialist', '').replace('_', ' ').title()}**")
            st.caption(item.get("summary", ""))
            (st.success if item.get("status") == "ok" else st.warning)(item.get("status", "unknown").replace("_", " ").title())


def _research(item: dict[str, Any] | None) -> None:
    if not item:
        st.info("Company research was not selected for this run.")
        return
    data = item.get("data", {})
    facts = data.get("fundamentals")
    if facts:
        annual = facts.get("annual", {})
        st.markdown(f"### {facts.get('company', facts.get('ticker', 'Company'))}")
        st.caption(f"Fiscal year {annual.get('fiscal_year', '—')} · As of {facts.get('as_of', '—')} · Historical SEC data")
        facts_cache_status = facts.get("cache_status")
        facts_retrieved_at = facts.get("retrieved_at")
        if facts_cache_status == "stale_cache":
            st.warning(
                f"Using cached company facts from {facts_retrieved_at}; newer SEC data may exist."
            )
        elif facts_retrieved_at:
            st.caption(
                f"Data retrieval: {facts_cache_status or 'live'} · {facts_retrieved_at}"
            )
        _metrics([
            ("Revenue", _money((annual.get("revenue_millions") or 0) * 1_000_000, True), None),
            ("Diluted EPS", f"${annual['diluted_eps']:,.2f}" if annual.get("diluted_eps") is not None else "Not reported", None),
            ("Operating cash flow", _money(annual.get("operating_cash_flow_millions") * 1_000_000, True) if annual.get("operating_cash_flow_millions") is not None else "Not reported", None),
            ("Free cash flow", _money(annual.get("free_cash_flow_millions") * 1_000_000, True) if annual.get("free_cash_flow_millions") is not None else "Not reported", "Operating cash flow less capital expenditures"),
        ])
        with st.expander("Methodology and source notes"):
            for note in facts.get("notes", []):
                st.write(f"• {note}")
            if facts.get("source_url"):
                st.link_button("Open SEC Company Facts", facts["source_url"])
    else:
        st.warning("No standardized annual SEC fundamentals were available.")
    st.markdown("### Grounded SEC evidence")
    research = data.get("sec_research", {})
    retrieval_status = research.get("cache_status")
    retrieved_at = research.get("retrieved_at")
    if retrieval_status == "stale_cache":
        st.warning(
            f"Using cached filing evidence from {retrieved_at}; it may not include newer filings."
        )
    elif retrieved_at:
        st.caption(
            f"Evidence retrieval: {retrieval_status or 'live'} · {retrieved_at}"
        )
    if not research.get("answerable"):
        st.warning(research.get("message", "No filing evidence was returned."))
        return
    evidence = research.get("evidence", [])
    st.success(f"{len(evidence)} reranked filing passages support this request.")
    for position, evidence_item in enumerate(evidence, start=1):
        metadata = evidence_item.get("metadata", {})
        title = metadata.get("section_title") or metadata.get("section_id") or "SEC evidence"
        with st.expander(f"Evidence {position} · {title}", expanded=position == 1):
            st.write(evidence_item.get("text", ""))
            st.caption(f"{metadata.get('form_type', 'Form')} · Filed {metadata.get('filing_date', '—')} · {metadata.get('ticker', '—')}")
            if metadata.get("source_url"):
                st.link_button("Open source filing", metadata["source_url"])


def _portfolio(item: dict[str, Any] | None) -> None:
    if not item:
        st.info("Portfolio analysis was not selected for this run.")
        return
    data = item.get("data", {})
    _metrics([
        ("Portfolio value", _money(data.get("total_market_value")), None),
        ("Cost basis", _money(data.get("total_cost_basis")), None),
        ("Unrealized gain", _money(data.get("unrealized_gain_loss")), None),
        ("Return", f"{data.get('unrealized_return', 0):.1%}", None),
    ])
    positions = pd.DataFrame(data.get("positions", [])).rename(columns={"ticker": "Ticker", "market_value": "Market value", "cost_basis": "Cost basis", "unrealized_gain_loss": "Gain / loss", "portfolio_weight": "Weight"})
    if not positions.empty:
        left, right = st.columns([1.35, 1])
        with left:
            st.markdown("#### Holdings")
            st.dataframe(positions, hide_index=True, use_container_width=True)
        with right:
            st.markdown("#### Position allocation")
            st.bar_chart(positions[["Ticker", "Weight"]].set_index("Ticker") * 100, color="#2459a9")
    allocations = data.get("sector_allocation", {})
    if allocations:
        st.markdown("#### Asset-class allocation")
        frame = pd.DataFrame({"Asset class": allocations.keys(), "Allocation (%)": [value * 100 for value in allocations.values()]}).set_index("Asset class")
        st.bar_chart(frame, horizontal=True, color="#137f78")
    st.markdown("#### Concentration review")
    if data.get("concentration_flags"):
        for flag in data["concentration_flags"]:
            st.warning(flag)
    else:
        st.success("No configured concentration threshold was exceeded.")
    st.caption(data.get("price_label", ""))


def _goals(item: dict[str, Any] | None) -> None:
    if not item:
        st.info("Goal planning was not selected for this run.")
        return
    data = item.get("data", {})
    _metrics([
        ("Years to retirement", str(data.get("years_to_retirement", "—")), None),
        ("Future annual income", _money(data.get("future_annual_income_need")), None),
        ("Retirement target", _money(data.get("retirement_target")), None),
    ])
    scenarios = pd.DataFrame(data.get("scenarios", []))
    if scenarios.empty:
        st.info("No retirement scenarios were calculated.")
        return
    scenarios["Return"] = scenarios["annual_return_rate"].map(lambda value: f"{value:.1%}")
    table = scenarios.rename(columns={"projected_assets": "Projected assets", "retirement_target": "Target", "funding_gap": "Funding gap", "required_monthly_contribution": "Required monthly", "additional_monthly_contribution": "Additional monthly"})[["Return", "Projected assets", "Target", "Funding gap", "Required monthly", "Additional monthly"]]
    st.markdown("#### Scenario comparison")
    st.dataframe(table, hide_index=True, use_container_width=True)
    st.bar_chart(table.set_index("Return")[["Projected assets", "Target"]], color=["#2459a9", "#d8a62a"])
    st.caption(data.get("disclaimer", ""))


def _citations(report: dict[str, Any]) -> None:
    citations = collect_citations(report)
    st.markdown("#### Evidence register")
    if not citations:
        st.info("No SEC citations were returned for this plan.")
        return
    for position, citation in enumerate(citations, start=1):
        title = citation.get("section_title") or citation.get("section_id") or "Filing evidence"
        with st.expander(f"{position}. {title}"):
            st.write(f"Ticker: {citation.get('ticker', '—')}")
            st.write(f"Form: {citation.get('form_type', '—')}")
            st.write(f"Filed: {citation.get('filing_date', '—')}")
            st.write(f"Accession: {citation.get('accession_number', '—')}")
            if citation.get("source_url"):
                st.link_button("Open SEC source", citation["source_url"])


def _workflow_memory_label(runtime: GraphRuntime) -> str:
    return (
        "PostgreSQL checkpointer"
        if runtime.settings.postgres_dsn
        else "In-memory thread checkpointer"
    )


def _render_workflow(
    runtime: GraphRuntime,
    placeholder: Any,
    progress: dict[str, dict[str, str]],
) -> None:
    placeholder.markdown(
        render_workflow_html(
            progress,
            memory_label=_workflow_memory_label(runtime),
            pinecone_namespace=runtime.settings.pinecone_namespace,
        ),
        unsafe_allow_html=True,
    )


def _workflow_event_handler(runtime: GraphRuntime, placeholder: Any):
    def handle(event: dict[str, Any]) -> None:
        progress = st.session_state.get("workflow_progress", {})
        progress = apply_workflow_event(progress, event)
        st.session_state.workflow_progress = progress
        _render_workflow(runtime, placeholder, progress)

    return handle


def _resume(
    runtime: GraphRuntime,
    decision: str,
    workflow_placeholder: Any,
    **kwargs: Any,
) -> None:
    try:
        with st.spinner("Resuming the approval workflow..."):
            result = resume_ui_run(
                runtime.graph,
                thread_id=st.session_state.thread_id,
                decision=decision,
                on_event=_workflow_event_handler(runtime, workflow_placeholder),
                **kwargs,
            )
            progress = finalize_workflow_progress(
                st.session_state.workflow_progress,
                result,
            )
            st.session_state.workflow_progress = progress
            st.session_state.run_result = result
            _render_workflow(runtime, workflow_placeholder, progress)
        st.rerun()
    except Exception as exc:
        st.error(f"The workflow could not be resumed: {exc}")


def _review(
    runtime: GraphRuntime,
    result: dict[str, Any],
    report: dict[str, Any],
    workflow_placeholder: Any,
) -> None:
    review = result.get("review") or report.get("review", {})
    checks = review.get("checks", report.get("review_checks", {}))
    if checks:
        st.markdown("#### Automated review checks")
        for column, (check, passed) in zip(st.columns(len(checks)), checks.items(), strict=True):
            column.metric(check.replace("_", " ").title(), "Pass" if passed else "Review")
    if review.get("failures"):
        st.warning(f"Specialists requiring attention: {', '.join(review['failures'])}")
    next_steps = report.get("narrative", {}).get("next_steps", [])
    if next_steps:
        st.markdown("#### Proposed next steps")
        for position, step in enumerate(next_steps, start=1):
            st.write(f"{position}. {step}")
    _citations(report)
    if is_awaiting_approval(result):
        st.markdown("#### Human approval gate")
        st.write("Nothing becomes an approved plan until you approve it. This prototype never executes a trade.")
        notes = st.text_area("Reviewer instructions", placeholder="Corrections, missing context, or rejection reason.")
        approve, edit, reject = st.columns(3)
        if approve.button("Approve plan", type="primary", use_container_width=True):
            _resume(runtime, "approve", workflow_placeholder)
        if edit.button("Request edits", use_container_width=True):
            _resume(runtime, "edit", workflow_placeholder, edit_notes=notes) if notes.strip() else st.warning("Enter edit instructions first.")
        if reject.button("Reject plan", use_container_width=True):
            _resume(runtime, "reject", workflow_placeholder, reason=notes)
    elif result.get("status") == "approved":
        persistence = report.get("persistence", {})
        if persistence.get("saved"):
            st.success("Approved action plan saved to PostgreSQL.")
            st.caption(f"Report ID: {persistence.get('report_id')}")
        else:
            st.info("Approved action plan recorded for this session; PostgreSQL is not configured.")
    elif result.get("status") == "persistence_failed":
        st.error(report.get("persistence", {}).get("error", "Durable storage failed."))
    elif result.get("status") == "needs_revision":
        st.info("Resolve the warnings and run again; missing evidence cannot pass approval.")


def _history(runtime: GraphRuntime, user_id: str) -> None:
    st.markdown("#### Approved report history")
    try:
        reports = runtime.report_repository.list_approved_reports(
            user_id=user_id, limit=20
        )
    except Exception as exc:
        st.error(f"Report history could not be loaded: {exc}")
        return
    if not reports:
        st.info("No durable approved reports exist for this profile yet.")
        return
    frame = pd.DataFrame(
        [
            {
                "Created": report.created_at,
                "Ticker": report.ticker or "—",
                "Status": report.status,
                "Summary": report.executive_summary or "—",
                "Report ID": report.report_id,
            }
            for report in reports
        ]
    )
    st.dataframe(frame, hide_index=True, use_container_width=True)


def _results(
    runtime: GraphRuntime,
    result: dict[str, Any],
    *,
    user_id: str,
    workflow_placeholder: Any,
) -> None:
    report = report_for_display(result)
    st.markdown("### Your WealthPlan workspace")
    _status(result)
    if not report:
        st.info("No report is available yet.")
        return
    tabs = st.tabs(["Overview", "Company research", "Portfolio dashboard", "Goals & scenarios", "Review & approval", "History"])
    with tabs[0]:
        _overview(result, report)
    with tabs[1]:
        _research(_specialist(report, "market_research"))
    with tabs[2]:
        _portfolio(_specialist(report, "portfolio_analysis"))
    with tabs[3]:
        _goals(_specialist(report, "goal_planning"))
    with tabs[4]:
        _review(runtime, result, report, workflow_placeholder)
    with tabs[5]:
        _history(runtime, user_id)
    st.markdown(f'<div class="wp-note">{report.get("disclaimer", "Educational prototype only; not financial advice.")}</div>', unsafe_allow_html=True)


def main() -> None:
    st.set_page_config(page_title="WealthPlan 2.0", page_icon="📈", layout="wide")
    _theme()
    try:
        runtime = get_runtime()
    except Exception as exc:
        st.error(f"WealthPlan could not start: {exc}")
        st.stop()
    user_id, display_name, ticker, goal, risk, horizon, analyses = _sidebar(runtime)
    st.markdown("""<div class="wp-hero"><small>Multi-agent financial research & planning</small><h1>See the whole plan, not just the numbers.</h1><p>Coordinate company research, portfolio analytics, retirement scenarios, risk review, and human approval in one grounded workspace.</p></div>""", unsafe_allow_html=True)
    st.markdown("### Build your analysis")
    with st.container(border=True):
        question = st.text_area("Research chat", value="Summarize reported fundamentals and principal risks, then explain what deserves further review.")
        use_demo = True
        holdings = None
        if "portfolio_analysis" in analyses:
            with st.expander("Portfolio holdings"):
                use_demo = st.toggle("Use the course demonstration portfolio", value=True)
                if use_demo:
                    demo = pd.DataFrame([holding.model_dump() for holding in DEMO_HOLDINGS])[["ticker", "name", "sector", "quantity"]]
                    st.dataframe(demo, hide_index=True, use_container_width=True)
                    st.caption("Calculations use fixed illustrative prices, not live quotes.")
                else:
                    holdings = _editable_holdings()
                    st.caption("Enter a price snapshot; values are not verified as live market data.")
        retirement_inputs = None
        if "goal_planning" in analyses:
            with st.expander("Retirement scenario planner", expanded=True):
                try:
                    retirement_inputs = _retirement_inputs()
                except ValueError:
                    st.error("Return scenarios must be comma-separated numbers, such as 4, 6, 8.")
        run = st.button("Generate WealthPlan", type="primary", use_container_width=True)
    st.markdown("### Live workflow navigator")
    st.caption(
        "Follow LangGraph execution across supervision, parallel specialists, "
        "review, memory, retrieval, and approval-gated persistence."
    )
    workflow_placeholder = st.empty()
    visible_progress = st.session_state.get("workflow_progress") or initialize_workflow_progress(analyses)
    _render_workflow(runtime, workflow_placeholder, visible_progress)
    if run:
        if not analyses:
            st.warning("Select at least one analysis module in the sidebar.")
        elif "market_research" in analyses and not ticker:
            st.warning("Select or enter a ticker for company research.")
        elif "portfolio_analysis" in analyses and not use_demo and not holdings:
            st.warning("Add at least one holding or use the demonstration portfolio.")
        elif "goal_planning" in analyses and retirement_inputs is None:
            st.warning("Provide valid retirement scenario inputs.")
        else:
            try:
                request = build_ui_request(
                    user_query=question, analyses=analyses,
                    user_id=user_id, display_name=display_name, ticker=ticker,
                    use_demo_portfolio=use_demo, holdings=holdings,
                    primary_goal=goal, risk_level=risk,
                    time_horizon_years=horizon, retirement_inputs=retirement_inputs,
                )
                st.session_state.thread_id = str(uuid4())
                st.session_state.workflow_progress = initialize_workflow_progress(analyses)
                _render_workflow(
                    runtime,
                    workflow_placeholder,
                    st.session_state.workflow_progress,
                )
                with st.spinner("Supervisor is coordinating the selected specialists..."):
                    result = start_ui_run(
                        runtime.graph,
                        request,
                        thread_id=st.session_state.thread_id,
                        on_event=_workflow_event_handler(runtime, workflow_placeholder),
                    )
                    progress = finalize_workflow_progress(
                        st.session_state.workflow_progress,
                        result,
                    )
                    st.session_state.workflow_progress = progress
                    st.session_state.run_result = result
                    _render_workflow(runtime, workflow_placeholder, progress)
            except Exception as exc:
                st.error(f"The analysis could not be completed: {exc}")
    result = st.session_state.get("run_result")
    if result:
        _results(
            runtime,
            result,
            user_id=user_id,
            workflow_placeholder=workflow_placeholder,
        )
    else:
        st.markdown("### What this workspace produces")
        cards = [
            ("Portfolio insights", "Allocation, gains, diversification, and concentration flags."),
            ("Grounded SEC research", "Historical fundamentals and auditable filing evidence."),
            ("Retirement scenarios", "Deterministic targets, projections, and funding gaps."),
            ("Approved action plan", "A reviewed output controlled by a human approval gate."),
        ]
        for column, (title, description) in zip(st.columns(4), cards, strict=True):
            column.markdown(f'<div class="wp-card"><div class="wp-card-label">Output</div><div class="wp-card-value">{title}</div><p>{description}</p></div>', unsafe_allow_html=True)
    st.divider()
    st.caption("Educational prototype · Historical SEC information and illustrative calculations · No live prices, trade execution, or guaranteed returns")


if __name__ == "__main__":
    main()
