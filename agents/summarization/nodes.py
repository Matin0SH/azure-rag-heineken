"""
Node functions for summarization workflow.

Each node is a pure function that takes state and returns updated state.
Follows EXTRACTION philosophy: preserve completeness, not reduce.
"""

import time
from typing import List, Dict
from langchain_community.chat_models import ChatDatabricks
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
# LLM INITIALIZATION (using databricks-llama-4-maverick)
# ==============================================================================

# Extraction LLM (temp 0.1 - deterministic but not rigid)
extraction_llm = ChatDatabricks(
    endpoint="databricks-llama-4-maverick",
    temperature=0.1,
    max_tokens=4000
)

# Critique LLM (temp 0.05 - very deterministic)
critique_llm = ChatDatabricks(
    endpoint="databricks-llama-4-maverick",
    temperature=0.05,
    max_tokens=1000
)


# ==============================================================================
# NODE 1: BATCH EXTRACT (MAP PHASE)
# ==============================================================================

def batch_extract_node(state: SummarizationState) -> SummarizationState:
    """
    MAP phase: Extract information from chunks in batches with cumulative context.

    CRITICAL: This is EXTRACTION, not summarization.
    - Batch size: 10 chunks (optimized for context fit)
    - Context window: Last 3 batch extractions (prevents duplication)
    - Temperature: 0.1 (deterministic)
    - Goal: Preserve ALL technical/operator information verbatim

    Args:
        state: Current workflow state

    Returns:
        Updated state with batch_summaries and context_window populated
    """
    start_time = time.time()

    chunks = state["chunks"]
    summary_type = state["summary_type"]
    batch_size = 10  # Optimized for better context fit
    CONTEXT_WINDOW = 3  # Keep last 3 batch extractions

    batch_summaries = []
    context_window = state.get("context_window", [])

    try:
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            batch_num = (i // batch_size) + 1

            # Combine batch text
            batch_text = "\n\n".join([c["text"] for c in batch])

            # Build context from recent batches (prevents repetition, NOT loss)
            if context_window:
                context_str = "\n\n---PREVIOUS BATCH---\n\n".join(context_window)
            else:
                context_str = "This is the first batch."

            # Select prompts based on summary type
            if summary_type == "technical":
                system_prompt = TECH_MAP_SYSTEM
                human_prompt = TECH_MAP_HUMAN
            else:  # operator
                system_prompt = OPERATOR_MAP_SYSTEM
                human_prompt = OPERATOR_MAP_HUMAN

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

            response = extraction_llm.invoke(messages)
            batch_summaries.append(response.content)

            # Update context window (keep last 3 for next batch)
            context_window.append(response.content)
            if len(context_window) > CONTEXT_WINDOW:
                context_window = context_window[-CONTEXT_WINDOW:]

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
# NODE 2: COMBINE (REDUCE PHASE - HIERARCHICAL)
# ==============================================================================

def combine_node(state: SummarizationState) -> SummarizationState:
    """
    REDUCE phase: Combine batch extractions hierarchically.

    CRITICAL: This is COMBINATION, not reduction.
    - If ≤4 batches: Direct combination into final_summary
    - If >4 batches: Two-stage hierarchical combination
      - Stage 1: Combine every 4 batches → intermediate_summaries
      - Stage 2: Combine intermediates → final_summary
    - Temperature: 0.1 (deterministic)
    - Goal: Preserve ALL information, ONLY remove exact duplicates

    Args:
        state: Current workflow state with batch_summaries populated

    Returns:
        Updated state with final_summary populated
    """
    start_time = time.time()

    batch_summaries = state["batch_summaries"]

    try:
        # Strategy depends on number of batches
        if len(batch_summaries) <= 4:
            # DIRECT COMBINATION: Few enough batches to combine directly
            combined_text = "\n\n---BATCH---\n\n".join(batch_summaries)

            messages = [
                ("system", REDUCE_SYSTEM),
                ("human", REDUCE_HUMAN.format(extractions=combined_text))
            ]

            response = extraction_llm.invoke(messages)
            final_summary = response.content
            intermediate_summaries = []  # No intermediates needed

        else:
            # HIERARCHICAL COMBINATION: Too many batches, use two stages

            # STAGE 1: Combine every 4 batches into intermediates
            intermediate_summaries = []
            batch_group_size = 4

            for i in range(0, len(batch_summaries), batch_group_size):
                batch_group = batch_summaries[i:i+batch_group_size]
                start_idx = i + 1
                end_idx = min(i + batch_group_size, len(batch_summaries))

                combined_text = "\n\n---BATCH---\n\n".join(batch_group)

                messages = [
                    ("system", INTERMEDIATE_REDUCE_SYSTEM),
                    ("human", INTERMEDIATE_REDUCE_HUMAN.format(
                        batch_extractions=combined_text,
                        start=start_idx,
                        end=end_idx
                    ))
                ]

                response = extraction_llm.invoke(messages)
                intermediate_summaries.append(response.content)

            # STAGE 2: Combine intermediates into final
            combined_intermediates = "\n\n---INTERMEDIATE---\n\n".join(intermediate_summaries)

            messages = [
                ("system", REDUCE_SYSTEM),
                ("human", REDUCE_HUMAN.format(extractions=combined_intermediates))
            ]

            response = extraction_llm.invoke(messages)
            final_summary = response.content

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
    Reflection phase: Critique final summary and decide if revision needed.

    CRITICAL: Quality check, not content reduction.
    - Check: Are all procedures present and separate?
    - Check: Are technical values preserved correctly?
    - Check: Is structure complete?
    - Temperature: 0.05 (very deterministic)
    - Max iterations: 2 (avoid infinite loops)
    - Accept threshold: 90%+ meets standards

    Args:
        state: Current workflow state with final_summary populated

    Returns:
        Updated state with critique and needs_revision flag
    """
    start_time = time.time()

    final_summary = state["final_summary"]
    iteration = state.get("iteration", 0)

    try:
        # Critique the final summary
        messages = [
            ("system", CRITIQUE_SYSTEM),
            ("human", CRITIQUE_HUMAN.format(summary=final_summary))
        ]

        response = critique_llm.invoke(messages)
        critique = response.content

        # Check if revision needed
        needs_revision = "FAIL" in critique.upper() and iteration < 2

        processing_time = time.time() - start_time

        return {
            **state,
            "critique": critique,
            "needs_revision": needs_revision,
            "iteration": iteration + 1,
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
    Extract 5-10 key topics from final summary.

    Purpose: Generate searchable topics for document indexing.
    - Temperature: 0.1 (deterministic)
    - Output: Comma-separated list of topics
    - Focus: Major systems, procedures, safety topics, technical domains

    Args:
        state: Current workflow state with final_summary populated

    Returns:
        Updated state with key_topics populated
    """
    start_time = time.time()

    final_summary = state["final_summary"]

    try:
        messages = [
            ("system", TOPIC_EXTRACTION_SYSTEM),
            ("human", TOPIC_EXTRACTION_HUMAN.format(summary=final_summary))
        ]

        response = extraction_llm.invoke(messages)

        # Parse comma-separated topics
        topics_str = response.content.strip()
        key_topics = [t.strip() for t in topics_str.split(",") if t.strip()]

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
