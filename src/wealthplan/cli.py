"""Small local chat interface for the WealthPlan graph."""

from __future__ import annotations

import argparse
from uuid import uuid4

from dotenv import load_dotenv
from langchain.messages import HumanMessage

from wealthplan.agents.single_agent import build_graph
from wealthplan.config import Settings
from wealthplan.database.checkpointing import open_checkpointer


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content
    return str(content)


def main() -> None:
    parser = argparse.ArgumentParser(description="Chat with the WealthPlan agent")
    parser.add_argument("--thread-id", default=str(uuid4()))
    parser.add_argument("--once", help="Run one prompt and exit")
    args = parser.parse_args()

    load_dotenv()
    settings = Settings.from_env()
    config = {"configurable": {"thread_id": args.thread_id}}

    with open_checkpointer(settings) as checkpointer:
        graph = build_graph(settings, checkpointer=checkpointer)

        def ask(text: str) -> None:
            result = graph.invoke(
                {"messages": [HumanMessage(content=text)]},
                config=config,
            )
            print(_message_text(result["messages"][-1].content))

        if args.once:
            ask(args.once)
            return

        print(f"WealthPlan educational chat (thread {args.thread_id}). Type 'exit' to stop.")
        while True:
            try:
                prompt = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return
            if prompt.lower() in {"exit", "quit"}:
                return
            if prompt:
                ask(prompt)


if __name__ == "__main__":
    main()
