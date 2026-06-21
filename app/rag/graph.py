"""
LangGraph graph definition and entry point for the RAG pipeline.

Wires together the router, retrieval, live search (fallback), generation,
digest, and trend nodes into a compiled state graph with conditional edges.
Provides a cached singleton accessor and a convenience function for running
queries end-to-end.
"""

import logging
from typing import Any

from langgraph.graph import END, START, StateGraph

from app.rag.nodes.digest_node import digest_node
from app.rag.nodes.generation_node import generation_node
from app.rag.nodes.live_search_node import live_search_node
from app.rag.nodes.retrieval_node import retrieval_node
from app.rag.nodes.router_node import router_node
from app.rag.nodes.trend_node import trend_node
from app.rag.state import RAGState

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Conditional-edge routing functions
# ---------------------------------------------------------------------------

def route_by_type(state: RAGState) -> str:
    """Determine the next node after the router."""
    route = state.get("route", "qa")
    if route == "trend":
        return "trend"
    elif route == "digest":
        return "retrieval_digest"
    else:
        return "retrieval_qa"


def route_after_retrieval(state: RAGState) -> str:
    """Determine which generation node to invoke after retrieval.
    
    If QA route and retrieval results are weak/empty, route to live search.
    """
    route = state.get("route", "qa")
    
    if route == "digest":
        return "digest"
        
    if state.get("use_live_search", False):
        print("[GRAPH] Routing to live_search_node (weak local results)")
        return "live_search"
        
    return "generation"


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_graph() -> Any:
    """Construct and compile the RAG LangGraph state graph.

    Graph topology::

        START → router
                  ├─ (qa)     → retrieval → [strong] → generation → END
                  │                       → [weak]   → live_search → generation → END
                  ├─ (digest) → retrieval → digest     → END
                  └─ (trend)  → trend                   → END
    """
    graph = StateGraph(RAGState)

    # --- Add nodes ---
    graph.add_node("router", router_node)
    graph.add_node("retrieval", retrieval_node)
    graph.add_node("live_search", live_search_node)
    graph.add_node("generation", generation_node)
    graph.add_node("digest", digest_node)
    graph.add_node("trend", trend_node)

    # --- Edges ---
    # START → router
    graph.add_edge(START, "router")

    # router → retrieval (for qa/digest) or trend
    graph.add_conditional_edges(
        "router",
        route_by_type,
        {
            "retrieval_qa": "retrieval",
            "retrieval_digest": "retrieval",
            "trend": "trend",
        },
    )

    # retrieval → generation (strong qa), live_search (weak qa), or digest
    graph.add_conditional_edges(
        "retrieval",
        route_after_retrieval,
        {
            "generation": "generation",
            "live_search": "live_search",
            "digest": "digest",
        },
    )

    # live_search → generation
    graph.add_edge("live_search", "generation")

    # Terminal edges
    graph.add_edge("generation", END)
    graph.add_edge("digest", END)
    graph.add_edge("trend", END)

    compiled = graph.compile()
    logger.info("RAG graph compiled successfully")
    return compiled


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

_compiled_graph: Any | None = None


def get_rag_graph() -> Any:
    """Return a cached singleton of the compiled RAG graph."""
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


# ---------------------------------------------------------------------------
# Convenience entry point
# ---------------------------------------------------------------------------

async def run_rag_query(query: str) -> dict[str, Any]:
    """Run a user query through the full RAG pipeline."""
    logger.info("Running RAG query: %s", query[:100])

    graph = get_rag_graph()

    initial_state: RAGState = {
        "query": query,
        "route": "",
        "filters": {},
        "retrieved_articles": [],
        "live_search_results": [],
        "response": "",
        "citations": [],
    }

    final_state = await graph.ainvoke(initial_state)

    logger.info(
        "RAG query complete: route=%s, response_len=%d, citations=%d",
        final_state.get("route", "unknown"),
        len(final_state.get("response", "")),
        len(final_state.get("citations", [])),
    )

    return dict(final_state)
