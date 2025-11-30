"""
State schema for summarization workflow.

Defines the shared state that flows through all nodes in the LangGraph.
"""

from typing import TypedDict, List, Dict, Optional


class SummarizationState(TypedDict):
    """State for summarization workflow."""

    # Input
    pdf_id: str
    pdf_name: str
    chunks: List[Dict]  # [{chunk_id, text, page_number}, ...]
    summary_type: str  # 'technical' or 'operator'
    total_pages: int  # Total pages in document
    total_chunks: int  # Total chunks in document

    # Processing (MAP phase)
    batch_summaries: List[str]
    context_window: List[str]  # Last 3 batch extractions for context
    current_batch: int  # Track progress

    # Processing (REDUCE phase)
    intermediate_summaries: List[str]  # For hierarchical combination
    final_summary: str

    # Reflection
    critique: str
    needs_revision: bool
    iteration: int

    # Output
    key_topics: List[str]
    processing_time: float

    # Error tracking
    error_message: Optional[str]
