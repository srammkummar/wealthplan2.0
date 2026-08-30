"""Create or upgrade WealthPlan PostgreSQL tables."""

from __future__ import annotations

import argparse

from dotenv import load_dotenv

from wealthplan.config import Settings
from wealthplan.database.postgres import PostgresWealthPlanRepository


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage the WealthPlan database")
    parser.add_argument("command", choices=["setup"])
    args = parser.parse_args()
    load_dotenv()
    settings = Settings.from_env()
    if not settings.postgres_dsn:
        raise RuntimeError("WEALTHPLAN_POSTGRES_DSN is required for database setup")
    if args.command == "setup":
        PostgresWealthPlanRepository(settings.postgres_dsn).setup()
        print("WealthPlan PostgreSQL schema is ready.")
