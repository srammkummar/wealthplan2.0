"""Development and production checkpoint configuration."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Any

from langgraph.checkpoint.memory import InMemorySaver

from wealthplan.config import Settings


@contextmanager
def open_checkpointer(settings: Settings) -> Iterator[Any]:
    """Use PostgreSQL when configured; otherwise keep thread memory in-process."""

    if not settings.postgres_dsn:
        yield InMemorySaver()
        return

    try:
        from langgraph.checkpoint.postgres import PostgresSaver
    except ImportError as exc:
        raise RuntimeError(
            "Install PostgreSQL checkpoint dependencies with: uv sync --extra postgres"
        ) from exc

    with PostgresSaver.from_conn_string(settings.postgres_dsn) as checkpointer:
        checkpointer.setup()
        yield checkpointer
