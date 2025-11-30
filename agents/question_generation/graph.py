"""
LangGraph workflow for question generation agent.

Assembles nodes into a graph with conditional edges and state management.
"""

from langgraph.graph import StateGraph, END
from .state import QuestionGenerationState
from .nodes import (
    generate_questions_node,
    reflect_node,
    finalize_questions_node
)


def create_question_generation_graph():
    """
    Create the question generation workflow graph.

    Workflow:
    1. START → generate_questions (Generate training questions)
    2. generate_questions → reflect (CRITIQUE: Quality check)
    3. reflect → generate_questions (if needs_revision) OR → finalize_questions
    4. finalize_questions → END

    Returns:
        Compiled LangGraph workflow
    """
    # Initialize graph with state schema
    workflow = StateGraph(QuestionGenerationState)

    # Add nodes
    workflow.add_node("generate_questions", generate_questions_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("finalize_questions", finalize_questions_node)

    # Set entry point
    workflow.set_entry_point("generate_questions")

    # Add edges
    workflow.add_edge("generate_questions", "reflect")

    # Conditional edge: reflect → revise OR finalize
    def should_revise(state: QuestionGenerationState) -> str:
        """Decide if revision needed based on critique."""
        if state.get("needs_revision", False):
            return "generate_questions"  # Re-run generation
        else:
            return "finalize_questions"  # Proceed to finalization

    workflow.add_conditional_edges(
        "reflect",
        should_revise,
        {
            "generate_questions": "generate_questions",  # Revision path
            "finalize_questions": "finalize_questions"  # Success path
        }
    )

    # Final edge to END
    workflow.add_edge("finalize_questions", END)

    # Compile graph
    graph = workflow.compile()

    return graph


# ==============================================================================
# HELPER: Run graph with input state
# ==============================================================================

def run_question_generation(
    pdf_id: str,
    pdf_name: str,
    operator_summary: str,
    num_questions: int = 10
) -> dict:
    """
    Run question generation workflow on operator summary.

    Args:
        pdf_id: Unique identifier for PDF
        pdf_name: Display name of PDF
        operator_summary: The operator summary to generate questions from
        num_questions: Target number of questions (default: 10)

    Returns:
        Final state dict with results
    """
    # Create graph
    graph = create_question_generation_graph()

    # Prepare initial state
    initial_state = {
        "pdf_id": pdf_id,
        "pdf_name": pdf_name,
        "operator_summary": operator_summary,
        "num_questions": num_questions,
        "generated_questions": [],
        "critique": "",
        "needs_revision": False,
        "iteration": 0,
        "final_questions": [],
        "processing_time": 0.0,
        "error_message": None
    }

    # Run graph
    final_state = graph.invoke(initial_state)

    return final_state
