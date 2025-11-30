"""
Node functions for question generation workflow.

Each node is a pure function that takes state and returns updated state.
"""

import time
import json
from typing import List, Dict
from langchain_community.chat_models import ChatDatabricks
from .state import QuestionGenerationState
from .prompts import (
    GENERATE_SYSTEM, GENERATE_HUMAN,
    CRITIQUE_SYSTEM, CRITIQUE_HUMAN
)


# ==============================================================================
# LLM INITIALIZATION (using databricks-llama-4-maverick)
# ==============================================================================

# Question generation LLM (temp 0.2 - slightly creative but controlled)
generation_llm = ChatDatabricks(
    endpoint="databricks-llama-4-maverick",
    temperature=0.2,
    max_tokens=3000
)

# Critique LLM (temp 0.05 - very deterministic)
critique_llm = ChatDatabricks(
    endpoint="databricks-llama-4-maverick",
    temperature=0.05,
    max_tokens=1000
)


# ==============================================================================
# NODE 1: GENERATE QUESTIONS
# ==============================================================================

def generate_questions_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    Generate training questions from operator summary.

    Difficulty distribution:
    - Easy: 40% (basic recall)
    - Medium: 40% (application)
    - Hard: 20% (troubleshooting/understanding)

    Args:
        state: Current workflow state

    Returns:
        Updated state with generated_questions populated
    """
    start_time = time.time()

    operator_summary = state["operator_summary"]
    num_questions = state.get("num_questions", 10)

    # Calculate difficulty distribution
    easy_count = int(num_questions * 0.4)
    medium_count = int(num_questions * 0.4)
    hard_count = num_questions - easy_count - medium_count

    try:
        messages = [
            ("system", GENERATE_SYSTEM),
            ("human", GENERATE_HUMAN.format(
                summary=operator_summary,
                num_questions=num_questions,
                easy_count=easy_count,
                medium_count=medium_count,
                hard_count=hard_count
            ))
        ]

        response = generation_llm.invoke(messages)

        # Parse JSON response
        response_text = response.content.strip()

        # Handle markdown code blocks if present
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0].strip()
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0].strip()

        parsed = json.loads(response_text)
        generated_questions = parsed.get("questions", [])

        processing_time = time.time() - start_time

        return {
            **state,
            "generated_questions": generated_questions,
            "processing_time": state.get("processing_time", 0.0) + processing_time
        }

    except json.JSONDecodeError as e:
        return {
            **state,
            "error_message": f"Failed to parse questions JSON: {str(e)}",
            "generated_questions": []
        }
    except Exception as e:
        return {
            **state,
            "error_message": f"Question generation failed: {str(e)}",
            "generated_questions": []
        }


# ==============================================================================
# NODE 2: REFLECT (CRITIQUE)
# ==============================================================================

def reflect_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    Critique generated questions and decide if revision needed.

    Quality checks:
    - Questions based only on summary content
    - Simple language (8th-grade level)
    - Complete and correct answers
    - Topic variety
    - Difficulty distribution

    Args:
        state: Current workflow state with generated_questions populated

    Returns:
        Updated state with critique and needs_revision flag
    """
    start_time = time.time()

    operator_summary = state["operator_summary"]
    generated_questions = state["generated_questions"]
    iteration = state.get("iteration", 0)

    try:
        # Format questions for critique
        questions_text = json.dumps(generated_questions, indent=2)

        messages = [
            ("system", CRITIQUE_SYSTEM),
            ("human", CRITIQUE_HUMAN.format(
                summary=operator_summary,
                questions=questions_text
            ))
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
# NODE 3: FINALIZE QUESTIONS
# ==============================================================================

def finalize_questions_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    Finalize approved questions.

    Simple pass-through that copies generated_questions to final_questions.
    This is where we could add additional formatting or validation if needed.

    Args:
        state: Current workflow state

    Returns:
        Updated state with final_questions populated
    """
    start_time = time.time()

    generated_questions = state["generated_questions"]

    try:
        # For now, just copy generated to final
        # In future, could add formatting, deduplication, etc.
        final_questions = generated_questions

        processing_time = time.time() - start_time

        return {
            **state,
            "final_questions": final_questions,
            "processing_time": state.get("processing_time", 0.0) + processing_time
        }

    except Exception as e:
        return {
            **state,
            "error_message": f"Finalization failed: {str(e)}",
            "final_questions": []
        }
