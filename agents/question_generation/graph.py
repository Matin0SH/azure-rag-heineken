"""
LangGraph workflow for question generation - MAP-REDUCE pattern.

WORKFLOW (Same as Summarization):
1. regroup_pages: Combine chunks into pages
2. create_batches: Group pages into batches (5 pages per batch)
3. map_generate: Generate 5-7 questions per batch using ai_query (parallel)
4. reduce_combine: Hierarchical 3-to-1 for 2 levels (deduplicate + polish)

Output: Array of 15-45 question chunks
"""

from langgraph.graph import StateGraph, END
from .state import QuestionGenerationState
from .nodes import (
    regroup_pages_node,
    create_batches_node,
    map_generate_node,
    reduce_combine_node
)


def create_question_generation_graph():
    """
    Create the question generation workflow graph.

    Workflow:
    START → regroup_pages → create_batches → map_generate → reduce_combine → END

    Returns:
        Compiled LangGraph workflow
    """
    # Initialize graph with state schema
    workflow = StateGraph(QuestionGenerationState)

    # Add nodes
    workflow.add_node("regroup_pages", regroup_pages_node)
    workflow.add_node("create_batches", create_batches_node)
    workflow.add_node("map_generate", map_generate_node)
    workflow.add_node("reduce_combine", reduce_combine_node)

    # Set entry point
    workflow.set_entry_point("regroup_pages")

    # Linear edges
    workflow.add_edge("regroup_pages", "create_batches")
    workflow.add_edge("create_batches", "map_generate")
    workflow.add_edge("map_generate", "reduce_combine")
    workflow.add_edge("reduce_combine", END)

    # Compile graph
    graph = workflow.compile()

    return graph
