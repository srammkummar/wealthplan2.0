CREATE TABLE IF NOT EXISTS wealthplan_users (
    id TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS investor_profiles (
    user_id TEXT PRIMARY KEY REFERENCES wealthplan_users(id) ON DELETE CASCADE,
    risk_level TEXT,
    time_horizon_years INTEGER,
    profile_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS goals (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES wealthplan_users(id) ON DELETE CASCADE,
    goal_type TEXT NOT NULL,
    goal_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS portfolios (
    id TEXT PRIMARY KEY,
    user_id TEXT REFERENCES wealthplan_users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS holdings (
    id TEXT PRIMARY KEY,
    portfolio_id TEXT NOT NULL REFERENCES portfolios(id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    name TEXT NOT NULL,
    sector TEXT NOT NULL,
    quantity NUMERIC NOT NULL CHECK (quantity > 0),
    cost_basis_per_share NUMERIC NOT NULL CHECK (cost_basis_per_share >= 0),
    price_snapshot NUMERIC NOT NULL CHECK (price_snapshot >= 0),
    price_as_of TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS workflow_runs (
    id TEXT PRIMARY KEY,
    thread_id TEXT NOT NULL,
    user_id TEXT REFERENCES wealthplan_users(id) ON DELETE SET NULL,
    status TEXT NOT NULL,
    request_json JSONB NOT NULL,
    report_json JSONB,
    started_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS approvals (
    id TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
    decision TEXT NOT NULL,
    reviewer TEXT,
    response_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS approved_reports (
    id TEXT PRIMARY KEY,
    workflow_run_id TEXT NOT NULL UNIQUE REFERENCES workflow_runs(id) ON DELETE CASCADE,
    approval_id TEXT NOT NULL REFERENCES approvals(id) ON DELETE RESTRICT,
    report_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS price_snapshots (
    id TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    price NUMERIC NOT NULL CHECK (price >= 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    source_label TEXT NOT NULL,
    price_as_of TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_records (
    accession_number TEXT PRIMARY KEY,
    ticker TEXT NOT NULL,
    form_type TEXT NOT NULL,
    status TEXT NOT NULL,
    metadata_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS workflow_runs_thread_id_idx ON workflow_runs(thread_id);
CREATE INDEX IF NOT EXISTS holdings_portfolio_id_idx ON holdings(portfolio_id);
CREATE INDEX IF NOT EXISTS approved_reports_created_at_idx ON approved_reports(created_at DESC);
CREATE INDEX IF NOT EXISTS ingestion_records_ticker_idx ON ingestion_records(ticker);
