"""
State schema for summarization workflow.

CLEAN ARCHITECTURE:
1. Fetch chunks from DB
2. Regroup chunks by pages
3. Create batches (5 pages per batch)
4. MAP: Extract summaries from each batch (max 3 workers in parallel)
5. REDUCE: Combine batches hierarchically (3-to-1) until 1 final summary
"""

from typing import TypedDict, List, Dict, Optional


class SummarizationState(TypedDict):
    """
    Main state for summarization workflow.

    Flow:
    1. Fetch chunks from DB
    2. Regroup chunks by pages
    3. Create batches (5 pages per batch)
    4. MAP: Extract summary from each batch (max 3 workers in parallel)
    5. REDUCE: Combine batches hierarchically (3-to-1) until 1 final result
    """

    # Input
    pdf_id: str
    pdf_name: str
    summary_type: str               # 'technical' or 'operator'

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
    batch_extractions: List[str]    # One extraction per batch

    # REDUCE phase results (hierarchical)
    reduce_levels: List[List[str]]  # Each level has fewer items than previous
    final_summary: str              # The final combined result

    # Output
    key_topics: List[str]           # Extracted keywords from final summary

    # Metadata
    processing_time: float
    error_message: Optional[str]
