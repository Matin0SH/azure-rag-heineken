"""
Question Generation Agent Nodes - Clean MAP-REDUCE Implementation

PHILOSOPHY: Generate high-quality multiple-choice questions from chunks.
Batch size: ~50 chunks per batch → 10-15 questions per batch
EXACTLY like summarization agent structure.
"""

import time
import os
import json
import uuid
from typing import List, Dict
from dotenv import load_dotenv

# Import tiktoken for token counting
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    TIKTOKEN_AVAILABLE = False

# Import Databricks ChatModel
from databricks_langchain import ChatDatabricks

# Import state and prompts
from .state import QuestionGenerationState
from .prompts import (
    GENERATE_SYSTEM, GENERATE_HUMAN,
    CRITIQUE_SYSTEM, CRITIQUE_HUMAN
)


# ==============================================================================
# HYPERPARAMETERS - All Configuration in One Place
# ==============================================================================

class Config:
    """Centralized configuration for question generation agent"""

    # LLM Configuration
    LLM_ENDPOINT = "databricks-llama-4-maverick"
    GENERATION_TEMPERATURE = 0.3       # Slightly higher for creative questions
    GENERATION_MAX_TOKENS = 6000       # Enough for 10-15 questions
    CRITIQUE_TEMPERATURE = 0.05        # Very low for consistent evaluation
    CRITIQUE_MAX_TOKENS = 2000         # Critiques are concise

    # Token Budgets
    PROMPT_BUDGET_TOKENS = 12000       # Max tokens in input prompt
    CONTEXT_TOKEN_LIMIT = 4000         # Max tokens for context window

    # Batch Configuration (QUALITY FOCUSED)
    DEFAULT_BATCH_SIZE = 50            # Chunks per batch (generates ~10-15 questions)
    MIN_BATCH_SIZE = 10                # Minimum when token budget exceeded
    CONTEXT_WINDOW_SIZE = 2            # Keep last 2 batches to avoid duplicate questions

    # Question Generation Configuration
    QUESTIONS_PER_BATCH = 12           # Target questions per batch
    TOTAL_QUESTIONS_TARGET = 70        # Target total questions per PDF

    # Difficulty Distribution
    EASY_RATIO = 0.40                  # 40% easy
    MEDIUM_RATIO = 0.40                # 40% medium
    HARD_RATIO = 0.20                  # 20% hard

    # Hierarchical Reduce Configuration
    REDUCE_GROUP_SIZE = 4              # Combine 4 batches at a time

    # Reflection Configuration
    MAX_ITERATIONS = 2                 # Max reflection iterations


# ==============================================================================
# LLM INITIALIZATION - Lazy Loading with Caching
# ==============================================================================

_generation_llm = None
_critique_llm = None


def get_generation_llm() -> ChatDatabricks:
    """Get or create question generation LLM instance (singleton pattern)"""
    global _generation_llm

    if _generation_llm is None:
        # Load environment variables if not already loaded
        if not os.getenv("DATABRICKS_HOST"):
            load_dotenv()

        _generation_llm = ChatDatabricks(
            endpoint=Config.LLM_ENDPOINT,
            temperature=Config.GENERATION_TEMPERATURE,
            max_tokens=Config.GENERATION_MAX_TOKENS,
            streaming=False
        )

    return _generation_llm


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
# UTILITY FUNCTIONS - Token Counting and Question Parsing
# ==============================================================================

def count_tokens(text: str) -> int:
    """Count tokens using tiktoken if available, else heuristic"""
    if not text:
        return 0

    if TIKTOKEN_AVAILABLE:
        try:
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except Exception:
            pass

    return max(1, len(text) // 4)


def trim_context_by_tokens(context_window: List[str], token_limit: int) -> List[str]:
    """Trim context window from front until within token limit"""
    trimmed = list(context_window)

    while trimmed:
        total_tokens = sum(count_tokens(c) for c in trimmed)
        if total_tokens <= token_limit:
            break
        trimmed.pop(0)

    return trimmed


def parse_questions_from_response(response_text: str) -> List[Dict]:
    """
    Parse questions from LLM JSON response.

    Expected format:
    {
      "questions": [
        {
          "question_text": "...",
          "option_a": "...",
          "option_b": "...",
          "option_c": "...",
          "option_d": "...",
          "correct_answer": "A",
          "explanation": "...",
          "difficulty_level": "easy",
          "topic_category": "safety"
        },
        ...
      ]
    }
    """
    try:
        # Try to parse as JSON
        data = json.loads(response_text)
        if "questions" in data:
            return data["questions"]
        return []
    except json.JSONDecodeError:
        # If not valid JSON, return empty list
        print(f"[WARNING] Failed to parse questions from response")
        return []


# ==============================================================================
# NODE 1: BATCH GENERATE (MAP PHASE)
# ==============================================================================

def batch_generate_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    MAP PHASE: Generate questions from chunks in batches.

    Process:
    1. Sort chunks by page_number, chunk_index
    2. Split into batches of ~50 chunks
    3. For each batch:
       - Include last 2 batches as context (avoid duplicate questions)
       - Call generation LLM → 10-15 multiple choice questions
       - Parse and validate questions
       - Add to batch_questions
    4. Adaptive batch sizing if token budget exceeded

    Args:
        state: Current workflow state

    Returns:
        Updated state with batch_questions and context_window
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

    batch_size = Config.DEFAULT_BATCH_SIZE
    questions_per_batch = Config.QUESTIONS_PER_BATCH

    # Calculate difficulty distribution per batch
    easy_count = int(questions_per_batch * Config.EASY_RATIO)
    medium_count = int(questions_per_batch * Config.MEDIUM_RATIO)
    hard_count = questions_per_batch - easy_count - medium_count

    batch_questions = []
    context_window = state.get("context_window", [])

    print("=" * 80)
    print(f"MAP PHASE: Generating OPERATOR QUESTIONS")
    print(f"Total chunks: {len(chunks)} | Batch size: {batch_size} | Estimated batches: {(len(chunks) + batch_size - 1) // batch_size}")
    print(f"Questions per batch: {questions_per_batch} ({easy_count} easy, {medium_count} medium, {hard_count} hard)")
    print("=" * 80)

    try:
        total_batches = (len(chunks) + batch_size - 1) // batch_size

        # Process each batch
        for i in range(0, len(chunks), batch_size):
            # Adaptive batch sizing
            current_batch_size = min(batch_size, len(chunks) - i)

            while True:
                batch = chunks[i:i+current_batch_size]
                batch_text = "\n\n".join([c["text"] for c in batch])

                # Trim context window
                context_window = trim_context_by_tokens(
                    context_window,
                    Config.CONTEXT_TOKEN_LIMIT
                )

                # Build context string
                if context_window:
                    context_str = "\n\n---PREVIOUS BATCH QUESTIONS---\n\n".join(context_window)
                    context_str = f"Already generated questions (DO NOT DUPLICATE):\n{context_str}"
                else:
                    context_str = "This is the first batch."

                # Check token budget
                prompt_tokens = count_tokens(batch_text) + count_tokens(context_str)

                if prompt_tokens <= Config.PROMPT_BUDGET_TOKENS:
                    break

                if current_batch_size <= Config.MIN_BATCH_SIZE:
                    break

                # Shrink batch
                current_batch_size -= 5

            batch_num = (i // batch_size) + 1

            # TRACER
            print(f"[MAP {batch_num}/{total_batches}] Generating questions from {len(batch)} chunks...")

            # Call LLM for question generation
            messages = [
                ("system", GENERATE_SYSTEM),
                ("human", GENERATE_HUMAN.format(
                    summary=batch_text,
                    num_questions=questions_per_batch,
                    easy_count=easy_count,
                    medium_count=medium_count,
                    hard_count=hard_count
                ))
            ]

            response = get_generation_llm().invoke(messages)

            # Parse questions from response
            questions = parse_questions_from_response(response.content)

            if questions:
                batch_questions.extend(questions)
                print(f"[MAP {batch_num}/{total_batches}] ✓ Generated {len(questions)} questions")
            else:
                print(f"[MAP {batch_num}/{total_batches}] ✗ Failed to parse questions")

            # Update context window (keep last N batches to avoid duplicates)
            context_window.append(response.content)
            if len(context_window) > Config.CONTEXT_WINDOW_SIZE:
                context_window = context_window[-Config.CONTEXT_WINDOW_SIZE:]

            context_window = trim_context_by_tokens(
                context_window,
                Config.CONTEXT_TOKEN_LIMIT
            )

        processing_time = time.time() - start_time

        return {
            **state,
            "batch_questions": batch_questions,
            "context_window": context_window,
            "current_batch": total_batches,
            "processing_time": state.get("processing_time", 0.0) + processing_time
        }

    except Exception as e:
        return {
            **state,
            "error_message": f"Batch question generation failed: {str(e)}",
            "batch_questions": batch_questions,
            "context_window": context_window
        }


# ==============================================================================
# NODE 2: COMBINE (REDUCE PHASE) - Deduplicate & Select Best
# ==============================================================================

def combine_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    REDUCE PHASE: Deduplicate questions and select best 70.

    Process:
    1. Remove exact duplicates
    2. Score questions by:
       - Clarity (simple language)
       - Completeness (good options + explanation)
       - Coverage (diverse topics)
    3. Select top 70 questions
    4. Ensure difficulty distribution (40% easy, 40% medium, 20% hard)

    Args:
        state: Current workflow state with batch_questions

    Returns:
        Updated state with final_questions
    """
    # Skip if already errored
    if state.get("error_message"):
        return state

    start_time = time.time()
    batch_questions = state.get("batch_questions", [])

    print("=" * 80)
    print(f"REDUCE PHASE: Deduplication & Selection")
    print(f"Total questions generated: {len(batch_questions)}")
    print("=" * 80)

    try:
        # Step 1: Remove exact duplicates
        unique_questions = []
        seen_texts = set()

        for q in batch_questions:
            q_text = q.get("question_text", "").strip().lower()
            if q_text and q_text not in seen_texts:
                unique_questions.append(q)
                seen_texts.add(q_text)

        print(f"[REDUCE] After deduplication: {len(unique_questions)} unique questions")

        # Step 2: Separate by difficulty
        easy_questions = [q for q in unique_questions if q.get("difficulty_level") == "easy"]
        medium_questions = [q for q in unique_questions if q.get("difficulty_level") == "medium"]
        hard_questions = [q for q in unique_questions if q.get("difficulty_level") == "hard"]

        print(f"[REDUCE] Distribution: {len(easy_questions)} easy, {len(medium_questions)} medium, {len(hard_questions)} hard")

        # Step 3: Select target amounts from each difficulty
        target_easy = int(Config.TOTAL_QUESTIONS_TARGET * Config.EASY_RATIO)
        target_medium = int(Config.TOTAL_QUESTIONS_TARGET * Config.MEDIUM_RATIO)
        target_hard = Config.TOTAL_QUESTIONS_TARGET - target_easy - target_medium

        selected_questions = []
        selected_questions.extend(easy_questions[:target_easy])
        selected_questions.extend(medium_questions[:target_medium])
        selected_questions.extend(hard_questions[:target_hard])

        # Step 4: Add question numbers
        for idx, q in enumerate(selected_questions, 1):
            q["question_number"] = idx

        print(f"[REDUCE] ✓ Selected {len(selected_questions)} final questions")

        processing_time = time.time() - start_time

        return {
            **state,
            "final_questions": selected_questions,
            "processing_time": state.get("processing_time", 0.0) + processing_time
        }

    except Exception as e:
        return {
            **state,
            "error_message": f"Question combination failed: {str(e)}"
        }


# ==============================================================================
# NODE 3: REFLECT (CRITIQUE & QUALITY CHECK)
# ==============================================================================

def reflect_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    REFLECTION PHASE: Critique questions and decide if revision needed.

    Quality Checks:
    - Are questions based on content?
    - Is language simple (8th grade)?
    - Are answers complete and correct?
    - Are explanations clear?
    - Do questions cover diverse topics?

    Decision:
    - PASS → Accept questions
    - FAIL + iteration < MAX_ITERATIONS → Re-run generation
    - FAIL + iteration ≥ MAX_ITERATIONS → Accept anyway

    Args:
        state: Current workflow state with final_questions

    Returns:
        Updated state with critique and needs_revision flag
    """
    # Skip if already errored
    if state.get("error_message"):
        return state

    start_time = time.time()
    final_questions = state.get("final_questions", [])
    iteration = state.get("iteration", 0)

    try:
        print(f"[REFLECT] Iteration {iteration + 1}/{Config.MAX_ITERATIONS} - Critiquing {len(final_questions)} questions...")

        # Format questions for critique
        questions_text = json.dumps(final_questions[:10], indent=2)  # Sample first 10

        messages = [
            ("system", CRITIQUE_SYSTEM),
            ("human", CRITIQUE_HUMAN.format(
                summary="Operator summary (from chunks)",
                questions=questions_text
            ))
        ]

        response = get_critique_llm().invoke(messages)
        critique = response.content

        # Check if revision needed
        needs_revision = (
            "FAIL" in critique.upper() and
            iteration < Config.MAX_ITERATIONS
        )

        if needs_revision:
            print(f"[REFLECT] ✗ FAIL - Needs revision (will retry)")
        else:
            print(f"[REFLECT] ✓ PASS - Questions accepted")

        processing_time = time.time() - start_time

        return {
            **state,
            "critique": critique,
            "needs_revision": needs_revision,
            "iteration": iteration + 1,
            # Reset if revision needed
            "batch_questions": [] if needs_revision else state.get("batch_questions", []),
            "context_window": [] if needs_revision else state.get("context_window", []),
            "processing_time": state.get("processing_time", 0.0) + processing_time
        }

    except Exception as e:
        return {
            **state,
            "error_message": f"Reflection failed: {str(e)}",
            "needs_revision": False
        }
