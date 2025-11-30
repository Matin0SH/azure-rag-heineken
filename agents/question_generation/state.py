"""
State schema for question generation workflow.

Defines the shared state that flows through all nodes in the LangGraph.
"""

from typing import TypedDict, List, Dict, Optional


class QuestionGenerationState(TypedDict):
    """State for question generation workflow."""

    # Input
    pdf_id: str
    pdf_name: str
    operator_summary: str  # The operator summary to generate questions from
    num_questions: int  # Target number of questions (default: 10)

    # Processing
    generated_questions: List[Dict]  # [{question, answer, difficulty, topic}, ...]

    # Reflection
    critique: str
    needs_revision: bool
    iteration: int

    # Output
    final_questions: List[Dict]  # Approved questions after reflection
    processing_time: float

    # Error tracking
    error_message: Optional[str]
