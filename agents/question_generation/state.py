"""
State schema for question generation workflow.

ARCHITECTURE (Same as Summarization):
1. Fetch chunks from DB
2. Regroup chunks by pages
3. Create batches (5 pages per batch)
4. MAP: Generate 5-7 questions per batch using ai_query
5. REDUCE: Hierarchical 3-to-1 for 2 levels (deduplicate + polish)
6. Result: Array of 15-45 question chunks
"""

from typing import TypedDict, List, Dict, Optional


class QuestionGenerationState(TypedDict):
    """
    Main state for question generation workflow.

    Flow:
    1. Fetch chunks from DB
    2. Regroup chunks by pages
    3. Create batches (5 pages per batch)
    4. MAP: Generate questions from each batch (parallel)
    5. REDUCE: Combine and polish hierarchically (2 levels)
    6. Output: Array of 15-45 question chunks
    """

    # Input
    pdf_id: str
    pdf_name: str

    # Fetched data
    chunks: List[Dict]              # Raw chunks from Unity Catalog
    total_chunks: int
    total_pages: int

    # Regrouped by pages
    pages: List[Dict]               # Chunks combined by page_number

    # Batched (5 pages per batch)
    batches: List[Dict]             # Groups of 5 pages
    total_batches: int

    # MAP phase results
    batch_questions: List[str]      # One question set per batch (JSON strings)

    # REDUCE phase results (hierarchical - stops at level 2)
    reduce_levels: List[List[str]]  # Each level has fewer items
    question_chunks: List[str]      # Final array of 15-45 question chunks (JSON strings)
    questions_full_text: str        # All questions concatenated for display
    num_question_chunks: int        # Number of chunks in final output
    total_questions: int            # Total count of all questions

    # Metadata
    processing_time: float
    error_message: Optional[str]
