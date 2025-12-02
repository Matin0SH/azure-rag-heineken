"""
Summarization workflow graph using LangGraph.

Orchestrates Spark SQL nodes in a linear workflow:
1. Regroup pages
2. Create batches
3. MAP extract
4. REDUCE combine (stops at level 2 for 15-45 detailed chunks)
"""

# LangGraph
from langgraph.graph import StateGraph, END

# Our modules
from .state import SummarizationState
from .nodes import (
    regroup_pages_node,
    create_batches_node,
    map_extract_node,
    reduce_combine_node
)
from .utils import save_stage_results


# Wrapper functions that save results after each node
def regroup_pages_with_save(state: SummarizationState) -> SummarizationState:
    """Regroup pages and save results"""
    result = regroup_pages_node(state)
    save_stage_results("regroup_pages", result)
    return result


def create_batches_with_save(state: SummarizationState) -> SummarizationState:
    """Create batches and save results"""
    result = create_batches_node(state)
    save_stage_results("create_batches", result)
    return result


def map_extract_with_save(state: SummarizationState) -> SummarizationState:
    """MAP extract and save results"""
    result = map_extract_node(state)
    save_stage_results("map_extract", result)
    return result


def reduce_combine_with_save(state: SummarizationState) -> SummarizationState:
    """REDUCE combine and save results"""
    result = reduce_combine_node(state)
    save_stage_results("reduce_combine", result)
    return result


def create_summarization_graph():
    """
    Create and compile the summarization workflow graph.

    Returns:
        Compiled LangGraph application
    """

    # Step 1: Initialize graph with state schema
    workflow = StateGraph(SummarizationState)

    # Step 2: Add all nodes (with auto-save wrappers)
    workflow.add_node("regroup_pages", regroup_pages_with_save)
    workflow.add_node("create_batches", create_batches_with_save)
    workflow.add_node("map_extract", map_extract_with_save)
    workflow.add_node("reduce_combine", reduce_combine_with_save)

    # Step 3: Set entry point (first node to run)
    workflow.set_entry_point("regroup_pages")

    # Step 4: Define edges (workflow order)
    workflow.add_edge("regroup_pages", "create_batches")
    workflow.add_edge("create_batches", "map_extract")
    workflow.add_edge("map_extract", "reduce_combine")
    workflow.add_edge("reduce_combine", END)  # End after reduce (no topics)

    # Step 5: Compile and return
    graph = workflow.compile()

    return graph
