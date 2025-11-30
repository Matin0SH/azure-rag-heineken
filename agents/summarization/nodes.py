"""
Summarization Agent Nodes - Clean, Optimized Implementation

PHILOSOPHY: EXTRACTION over summarization - preserve ALL details.
No hidden bottlenecks. Every parameter is explicit and tunable.
"""

import time
import os
from typing import List
from dotenv import load_dotenv

# Import tiktoken for accurate token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

# Import Databricks ChatModel
from databricks_langchain import ChatDatabricks

# Import state and prompts
from .state import SummarizationState
from .prompts import (
    TECH_MAP_SYSTEM, TECH_MAP_HUMAN,
    OPERATOR_MAP_SYSTEM, OPERATOR_MAP_HUMAN,
    INTERMEDIATE_REDUCE_SYSTEM, INTERMEDIATE_REDUCE_HUMAN,
    REDUCE_SYSTEM, REDUCE_HUMAN,
    CRITIQUE_SYSTEM, CRITIQUE_HUMAN,
    TOPIC_EXTRACTION_SYSTEM, TOPIC_EXTRACTION_HUMAN
)


# ==============================================================================
# HYPERPARAMETERS - All Configuration in One Place
# ==============================================================================

class Config:
    """Centralized configuration for summarization agent"""

    # LLM Configuration
    LLM_ENDPOINT = "databricks-llama-4-maverick"
    EXTRACTION_TEMPERATURE = 0.1       # Low for deterministic extraction
    EXTRACTION_MAX_TOKENS = 4000       # Balanced output for 7-chunk batches
    CRITIQUE_TEMPERATURE = 0.05        # Very low for consistent evaluation
    CRITIQUE_MAX_TOKENS = 2000         # Critiques are concise

    # Token Budgets
    PROMPT_BUDGET_TOKENS = 8000        # Max tokens in input prompt
    CONTEXT_TOKEN_LIMIT = 4000         # Max tokens for context window

    # Batch Configuration (QUALITY FOCUSED)
    DEFAULT_BATCH_SIZE = 7             # Chunks per batch (sweet spot)
    MIN_BATCH_SIZE = 1                 # Minimum when token budget exceeded
    CONTEXT_WINDOW_SIZE = 3            # Keep last N batch summaries

    # Hierarchical Reduce Configuration
    REDUCE_GROUP_SIZE = 4              # Combine 4 summaries at a time

    # Reflection Configuration
    MAX_ITERATIONS = 2                 # Max reflection iterations


# ==============================================================================
# LLM INITIALIZATION - Lazy Loading with Caching
# ==============================================================================

_extraction_llm = None
_critique_llm = None


def get_extraction_llm() -> ChatDatabricks:
    """Get or create extraction LLM instance (singleton pattern)"""
    global _extraction_llm

    if _extraction_llm is None:
        # Load environment variables if not already loaded
        if not os.getenv("DATABRICKS_HOST"):
            load_dotenv()

        _extraction_llm = ChatDatabricks(
            endpoint=Config.LLM_ENDPOINT,
            temperature=Config.EXTRACTION_TEMPERATURE,
            max_tokens=Config.EXTRACTION_MAX_TOKENS,
            streaming=False
        )

    return _extraction_llm


def get_critique_llm() -> ChatDatabricks:
    """Get or create critique LLM instance (singleton pattern)"""
    global _critique_llm

    if _critique_llm is None:
        # Load environment variables if not already loaded
        if not os.getenv("DATABRICKS_HOST"):
            load_dotenv()

        _critique_llm = ChatDatabricks(
            endpoint=Config.LLM_ENDPOINT,
            temperature=Config.CRITIQUE_TEMPERATURE,
            max_tokens=Config.CRITIQUE_MAX_TOKENS,
            streaming=False
        )

    return _critique_llm


# ==============================================================================
# UTILITY FUNCTIONS - Token Counting and Trimming
# ==============================================================================

def count_tokens(text: str) -> int:
    """
    Count tokens in text using tiktoken if available, else heuristic.

    Args:
        text: Text to count tokens for

    Returns:
        Approximate token count
    """
    if not text:
        return 0

    if TIKTOKEN_AVAILABLE:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            pass  # Fall through to heuristic

    # Heuristic: ~4 characters per token
    return max(1, len(text) // 4)


def trim_context_by_tokens(context_window: List[str], token_limit: int) -> List[str]:
    """
    Trim context window from the front until within token limit.

    Args:
        context_window: List of context strings
        token_limit: Maximum total tokens allowed

    Returns:
        Trimmed context window
    """
    trimmed = list(context_window)

    while trimmed:
        total_tokens = sum(count_tokens(c) for c in trimmed)
        if total_tokens <= token_limit:
            break
        trimmed.pop(0)  # Remove oldest context

    return trimmed


# ==============================================================================
# NODE 1: BATCH EXTRACT (MAP PHASE)
# ==============================================================================

def batch_extract_node(state: SummarizationState) -> SummarizationState:
    """
    MAP PHASE: Extract information from chunks in batches.

    Process:
    1. Sort chunks by page_number, chunk_index (deterministic ordering)
    2. Split into batches of DEFAULT_BATCH_SIZE chunks
    3. For each batch:
       - Include last CONTEXT_WINDOW_SIZE batch summaries as context
       - Call extraction LLM
       - Add result to batch_summaries
       - Update rolling context window
    4. Adaptive batch sizing if token budget exceeded

    Args:
        state: Current workflow state

    Returns:
        Updated state with batch_summaries and context_window
    """
    # Skip if already errored
    if state.get("error_message"):
        return state

    start_time = time.time()

    # Sort chunks deterministically
    chunks = sorted(
        state["chunks"],
        key=lambda c: (c.get("page_number", 0), c.get("chunk_index", 0))
    )

    summary_type = state["summary_type"]
    batch_size = Config.DEFAULT_BATCH_SIZE

    batch_summaries = []
    context_window = state.get("context_window", [])

    print("=" * 80)
    print(f"MAP PHASE: Extracting {summary_type.upper()} information")
    print(f"Total chunks: {len(chunks)} | Batch size: {batch_size} | Estimated batches: {(len(chunks) + batch_size - 1) // batch_size}")
    print("=" * 80)

    try:
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        # Process each batch
        for i in range(0, len(chunks), batch_size):
            # Adaptive batch sizing to stay within token budget
            current_batch_size = min(batch_size, len(chunks) - i)

            while True:
                batch = chunks[i:i+current_batch_size]
                batch_text = "\n\n".join([c["text"] for c in batch])

                # Trim context window by token limit
                context_window = trim_context_by_tokens(
                    context_window,
                    Config.CONTEXT_TOKEN_LIMIT
                )

                # Build context string
                if context_window:
                    context_str = "\n\n---PREVIOUS BATCH---\n\n".join(context_window)
                else:
                    context_str = "This is the first batch."

                # Check token budget
                prompt_tokens = count_tokens(batch_text) + count_tokens(context_str)

                if prompt_tokens <= Config.PROMPT_BUDGET_TOKENS:
                    break  # Within budget

                if current_batch_size <= Config.MIN_BATCH_SIZE:
                    break  # Can't shrink further

                # Shrink batch and retry
                current_batch_size -= 1

            batch_num = (i // batch_size) + 1

            # Select prompts based on summary type
            if summary_type == "technical":
                system_prompt = TECH_MAP_SYSTEM
                human_prompt = TECH_MAP_HUMAN
            else:  # operator
                system_prompt = OPERATOR_MAP_SYSTEM
                human_prompt = OPERATOR_MAP_HUMAN

            # TRACER: Show progress
            print(f"[MAP {batch_num}/{total_batches}] Extracting {summary_type} info from {len(batch)} chunks...")

            # Call LLM for extraction
            messages = [
                ("system", system_prompt),
                ("human", human_prompt.format(
                    context=context_str,
                    content=batch_text,
                    batch_num=batch_num,
                    total_batches=total_batches
                ))
            ]

            response = get_extraction_llm().invoke(messages)
            batch_summaries.append(response.content)
            print(f"[MAP {batch_num}/{total_batches}] ✓ Complete")

            # Update context window (keep last N batches)
            context_window.append(response.content)
            if len(context_window) > Config.CONTEXT_WINDOW_SIZE:
                context_window = context_window[-Config.CONTEXT_WINDOW_SIZE:]

            # Trim by tokens again after adding new summary
            context_window = trim_context_by_tokens(
                context_window,
                Config.CONTEXT_TOKEN_LIMIT
            )

        processing_time = time.time() - start_time

        return {
            **state,
            "batch_summaries": batch_summaries,
            "context_window": context_window,
            "current_batch": len(batch_summaries),
            "processing_time": state.get("processing_time", 0.0) + processing_time
        }

    except Exception as e:
        return {
            **state,
            "error_message": f"Batch extraction failed: {str(e)}",
            "batch_summaries": batch_summaries,
            "context_window": context_window
        }


# ==============================================================================
# NODE 2: COMBINE (REDUCE PHASE)
# ==============================================================================

def combine_node(state: SummarizationState) -> SummarizationState:
    """
    REDUCE PHASE: Hierarchically combine batch extractions.

    Strategy:
    - If ≤4 batch summaries: Direct combination → final_summary
    - If >4 batch summaries: Recursive hierarchical combination
      - Recursively group by REDUCE_GROUP_SIZE (default: 4)
      - Continue until ≤4 summaries remain
      - Final combination of remaining summaries

    Args:
        state: Current workflow state with batch_summaries

    Returns:
        Updated state with final_summary and intermediate_summaries
    """
    # Skip if already errored
    if state.get("error_message"):
        return state

    start_time = time.time()
    batch_summaries = state["batch_summaries"]

    print("=" * 80)
    print(f"REDUCE PHASE: Hierarchical combination")
    print(f"Total batch summaries: {len(batch_summaries)}")
    print("=" * 80)

    try:
        # Strategy: Direct vs Hierarchical
        if len(batch_summaries) <= Config.REDUCE_GROUP_SIZE:
            # DIRECT COMBINATION (few enough for single LLM call)
            combined_text = "\n\n---BATCH---\n\n".join(batch_summaries)

            messages = [
                ("system", REDUCE_SYSTEM),
                ("human", REDUCE_HUMAN.format(extractions=combined_text))
            ]

            response = get_extraction_llm().invoke(messages)
            final_summary = response.content
            intermediate_summaries = []

        else:
            # HIERARCHICAL COMBINATION (recursive reduction)
            current_level = list(batch_summaries)
            all_intermediates = []

            # Recursively reduce until ≤4 summaries remain
            level_num = 1
            while len(current_level) > Config.REDUCE_GROUP_SIZE:
                next_level = []
                print(f"[REDUCE Level {level_num}] Combining {len(current_level)} summaries into groups of 4...")

                for i in range(0, len(current_level), Config.REDUCE_GROUP_SIZE):
                    group = current_level[i:i+Config.REDUCE_GROUP_SIZE]
                    start_idx = i + 1
                    end_idx = min(i + Config.REDUCE_GROUP_SIZE, len(current_level))

                    combined_text = "\n\n---BATCH---\n\n".join(group)

                    messages = [
                        ("system", INTERMEDIATE_REDUCE_SYSTEM),
                        ("human", INTERMEDIATE_REDUCE_HUMAN.format(
                            batch_extractions=combined_text,
                            start=start_idx,
                            end=end_idx
                        ))
                    ]

                    response = get_extraction_llm().invoke(messages)
                    next_level.append(response.content)

                all_intermediates.extend(next_level)
                current_level = next_level
                print(f"[REDUCE Level {level_num}] ✓ Produced {len(next_level)} summaries")
                level_num += 1

            # FINAL REDUCTION (≤4 summaries → 1 final)
            print(f"[REDUCE Final] Combining final {len(current_level)} summaries...")
            combined_final = "\n\n---INTERMEDIATE---\n\n".join(current_level)

            messages = [
                ("system", REDUCE_SYSTEM),
                ("human", REDUCE_HUMAN.format(extractions=combined_final))
            ]

            response = get_extraction_llm().invoke(messages)
            final_summary = response.content
            intermediate_summaries = all_intermediates

        processing_time = time.time() - start_time

        return {
            **state,
            "intermediate_summaries": intermediate_summaries,
            "final_summary": final_summary,
            "processing_time": state.get("processing_time", 0.0) + processing_time
        }

    except Exception as e:
        return {
            **state,
            "error_message": f"Combination failed: {str(e)}"
        }


# ==============================================================================
# NODE 3: REFLECT (CRITIQUE & REVISION)
# ==============================================================================

def reflect_node(state: SummarizationState) -> SummarizationState:
    """
    REFLECTION PHASE: Critique final summary and decide if revision needed.

    Quality Checks:
    - Are all procedures preserved and separated?
    - Are technical values/specs intact?
    - Is structure complete and logical?

    Decision:
    - PASS → Accept summary
    - FAIL + iteration < MAX_ITERATIONS → Re-run MAP-REDUCE
    - FAIL + iteration ≥ MAX_ITERATIONS → Accept anyway (prevent infinite loop)

    Args:
        state: Current workflow state with final_summary

    Returns:
        Updated state with critique and needs_revision flag
    """
    # Skip if already errored
    if state.get("error_message"):
        return state

    start_time = time.time()
    final_summary = state["final_summary"]
    iteration = state.get("iteration", 0)

    try:
        # Critique the final summary
        print(f"[REFLECT] Iteration {iteration + 1}/{Config.MAX_ITERATIONS} - Critiquing summary...")

        messages = [
            ("system", CRITIQUE_SYSTEM),
            ("human", CRITIQUE_HUMAN.format(summary=final_summary))
        ]

        response = get_critique_llm().invoke(messages)
        critique = response.content

        # Check if revision needed (bounded by MAX_ITERATIONS)
        needs_revision = (
            "FAIL" in critique.upper() and
            iteration < Config.MAX_ITERATIONS
        )

        if needs_revision:
            print(f"[REFLECT] ✗ FAIL - Needs revision (will retry)")
        else:
            print(f"[REFLECT] ✓ PASS - Summary accepted")

        processing_time = time.time() - start_time

        return {
            **state,
            "critique": critique,
            "needs_revision": needs_revision,
            "iteration": iteration + 1,
            # Reset batch context if we need to re-run
            "batch_summaries": [] if needs_revision else state.get("batch_summaries", []),
            "context_window": [] if needs_revision else state.get("context_window", []),
            "processing_time": state.get("processing_time", 0.0) + processing_time
        }

    except Exception as e:
        return {
            **state,
            "error_message": f"Reflection failed: {str(e)}",
            "needs_revision": False  # Fail gracefully
        }


# ==============================================================================
# NODE 4: EXTRACT TOPICS
# ==============================================================================

def extract_topics_node(state: SummarizationState) -> SummarizationState:
    """
    TOPIC EXTRACTION: Generate 5-10 searchable keywords from final summary.

    Purpose:
    - Document indexing and discovery
    - Search functionality
    - Topic-based filtering

    Args:
        state: Current workflow state with final_summary

    Returns:
        Updated state with key_topics list
    """
    # Skip if already errored
    if state.get("error_message"):
        return state

    start_time = time.time()
    final_summary = state["final_summary"]

    try:
        print(f"[TOPICS] Extracting key topics...")

        messages = [
            ("system", TOPIC_EXTRACTION_SYSTEM),
            ("human", TOPIC_EXTRACTION_HUMAN.format(summary=final_summary))
        ]

        response = get_extraction_llm().invoke(messages)

        # Parse comma-separated topics
        topics_str = response.content.strip()
        key_topics = [t.strip() for t in topics_str.split(",") if t.strip()]

        print(f"[TOPICS] ✓ Extracted {len(key_topics)} topics: {', '.join(key_topics[:3])}...")

        processing_time = time.time() - start_time

        return {
            **state,
            "key_topics": key_topics,
            "processing_time": state.get("processing_time", 0.0) + processing_time
        }

    except Exception as e:
        return {
            **state,
            "error_message": f"Topic extraction failed: {str(e)}",
            "key_topics": []  # Fail gracefully
        }
