"""
LangGraph workflow for summarization agent.

Assembles nodes into a graph with conditional edges and state management.
Follows EXTRACTION philosophy: preserve completeness, organize information.
"""

from langgraph.graph import StateGraph, END
from .state import SummarizationState
from .nodes import (
    batch_extract_node,
    combine_node,
    reflect_node,
    extract_topics_node
)


def create_summarization_graph():
    """
    Create the summarization workflow graph.

    Workflow:
    1. START → batch_extract (MAP: Extract from chunks in batches)
    2. batch_extract → combine (REDUCE: Hierarchical combination)
    3. combine → reflect (CRITIQUE: Quality check)
    4. reflect → combine (if needs_revision) OR → extract_topics
    5. extract_topics → END

    Returns:
        Compiled LangGraph workflow
    """
    # Initialize graph with state schema
    workflow = StateGraph(SummarizationState)

    # Add nodes
    workflow.add_node("batch_extract", batch_extract_node)
    workflow.add_node("combine", combine_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("extract_topics", extract_topics_node)

    # Set entry point
    workflow.set_entry_point("batch_extract")

    # Add edges
    workflow.add_edge("batch_extract", "combine")

    # Conditional edge: reflect → revise OR continue
    def should_revise(state: SummarizationState) -> str:
        """Decide if revision needed based on critique."""
        if state.get("needs_revision", False):
            return "batch_extract"  # Re-run extraction/combination
        else:
            return "extract_topics"  # Proceed to topic extraction

    workflow.add_edge("combine", "reflect")
    workflow.add_conditional_edges(
        "reflect",
        should_revise,
        {
            "batch_extract": "batch_extract",  # Revision path (fresh extraction)
            "extract_topics": "extract_topics"  # Success path
        }
    )

    # Final edge to END
    workflow.add_edge("extract_topics", END)

    # Compile graph
    graph = workflow.compile()

    return graph


# ==============================================================================
# HELPER: Run graph with input state
# ==============================================================================

def run_summarization(
    pdf_id: str,
    pdf_name: str,
    chunks: list,
    summary_type: str = "technical",
    total_pages: int = None,
    total_chunks: int = None
) -> dict:
    """
    Run summarization workflow on document chunks.

    Args:
        pdf_id: Unique identifier for PDF
        pdf_name: Display name of PDF
        chunks: List of chunk dicts [{chunk_id, text, page_number}, ...]
        summary_type: 'technical' or 'operator'
        total_pages: Total pages in document (optional)
        total_chunks: Total chunks in document (optional)

    Returns:
        Final state dict with results
    """
    # Create graph
    graph = create_summarization_graph()

    # Prepare initial state
    initial_state = {
        "pdf_id": pdf_id,
        "pdf_name": pdf_name,
        "chunks": chunks,
        "summary_type": summary_type,
        "total_pages": total_pages or 0,
        "total_chunks": total_chunks or len(chunks),
        "batch_summaries": [],
        "context_window": [],
        "current_batch": 0,
        "intermediate_summaries": [],
        "final_summary": "",
        "critique": "",
        "needs_revision": False,
        "iteration": 0,
        "key_topics": [],
        "processing_time": 0.0,
        "error_message": None
    }

    # Run graph
    final_state = graph.invoke(initial_state)

    return final_state
