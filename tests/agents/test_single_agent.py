from langgraph.checkpoint.memory import InMemorySaver

from wealthplan.agents.single_agent import build_graph
from wealthplan.config import Settings


def test_explicit_agent_tool_graph_compiles():
    settings = Settings(
        openai_api_key="test-key-not-used",
        openai_model="test-model",
        pinecone_api_key=None,
        pinecone_index_name=None,
        pinecone_namespace="sec-filings",
        cohere_api_key=None,
        cohere_rerank_model="rerank-v3.5",
        postgres_dsn=None,
    )

    graph = build_graph(settings, checkpointer=InMemorySaver())
    node_names = set(graph.get_graph().nodes)

    assert {"agent", "tools"}.issubset(node_names)
