"""Explicit LangGraph agent and tool execution loop."""

from __future__ import annotations

from typing import Any

from langchain.messages import SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition

from wealthplan.config import Settings
from wealthplan.prompts import SYSTEM_PROMPT
from wealthplan.tools.registry import build_tools


def build_graph(settings: Settings, *, checkpointer: Any = None):
    """Compile the WealthPlan graph with an optional LangGraph checkpointer."""

    if not settings.openai_api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is required to run the chat agent. "
            "The deterministic tools and tests do not require it."
        )

    tools = build_tools(settings)
    model = ChatOpenAI(
        model=settings.openai_model,
        api_key=settings.openai_api_key,
    ).bind_tools(tools)

    def call_model(state: MessagesState):
        response = model.invoke([SystemMessage(content=SYSTEM_PROMPT), *state["messages"]])
        return {"messages": [response]}

    builder = StateGraph(MessagesState)
    builder.add_node("agent", call_model)
    builder.add_node("tools", ToolNode(tools, handle_tool_errors=True))
    builder.add_edge(START, "agent")
    builder.add_conditional_edges(
        "agent",
        tools_condition,
        {"tools": "tools", END: END},
    )
    builder.add_edge("tools", "agent")
    return builder.compile(checkpointer=checkpointer)
