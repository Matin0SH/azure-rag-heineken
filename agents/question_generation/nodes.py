"""
Question generation nodes using MAP-REDUCE with Spark SQL ai_query.

ARCHITECTURE (Same as Summarization):
1. Fetch chunks from DB
2. Regroup chunks by pages
3. Create batches (5 pages per batch)
4. MAP: Generate 5-7 questions per batch using ai_query (parallel in Spark)
5. REDUCE: Hierarchical 3-to-1 for 2 levels (deduplicate + polish)
6. Result: Array of 15-45 question chunks

Example with 675 pages:
- 675 pages → 135 batches (5 pages each)
- MAP: 135 batches × 6 questions = ~800 questions in parallel
- REDUCE Level 1: 135 → 45 (3-to-1)
- REDUCE Level 2: 45 → 15 (3-to-1) → STOP
- Output: 15 question chunks (each ~50 questions)
"""

import json
from typing import List, Dict
from pyspark.sql import SparkSession

from .state import QuestionGenerationState
from .prompts import (
    MAP_SYSTEM, MAP_HUMAN,
    REDUCE_SYSTEM, REDUCE_HUMAN,
    Config
)


def get_spark() -> SparkSession:
    """Get active Spark session"""
    return SparkSession.getActiveSession()


# ==============================================================================
# NODE 1: REGROUP CHUNKS BY PAGES
# ==============================================================================

def regroup_pages_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    Combine chunks into pages using Spark.

    Input: List of chunks (each chunk is part of a page)
    Output: List of pages (each page has combined text)

    This is IDENTICAL to summarization's regroup_pages_node.
    """
    chunks = state["chunks"]

    print(f"Regrouping {len(chunks)} chunks into pages...")

    spark = get_spark()

    # Create temp table from chunks
    chunks_df = spark.createDataFrame(chunks)
    chunks_df.createOrReplaceTempView("chunks_temp")

    # Group by page_number and concatenate text
    pages_df = spark.sql("""
        SELECT
            page_number,
            MIN(chunk_id) as first_chunk_id,
            CONCAT_WS('\n\n', COLLECT_LIST(text)) as page_text,
            COUNT(*) as num_chunks
        FROM chunks_temp
        GROUP BY page_number
        ORDER BY page_number
    """)

    # Convert to list of dicts
    pages = [
        {
            "page_number": row["page_number"],
            "first_chunk_id": row["first_chunk_id"],
            "page_text": row["page_text"],
            "num_chunks": row["num_chunks"]
        }
        for row in pages_df.collect()
    ]

    print(f"✓ Regrouped into {len(pages)} pages")

    return {
        **state,
        "pages": pages
    }


# ==============================================================================
# NODE 2: CREATE BATCHES (5 pages per batch)
# ==============================================================================

def create_batches_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    Group pages into batches of 5 pages each.

    This is IDENTICAL to summarization's create_batches_node.
    """
    pages = state["pages"]
    pages_per_batch = Config.PAGES_PER_BATCH

    print(f"Creating batches ({pages_per_batch} pages per batch)...")

    batches = []
    for i in range(0, len(pages), pages_per_batch):
        batch_pages = pages[i:i + pages_per_batch]

        batch_text = "\n\n".join([p["page_text"] for p in batch_pages])
        start_page = batch_pages[0]["page_number"]
        end_page = batch_pages[-1]["page_number"]

        batches.append({
            "batch_id": len(batches) + 1,
            "start_page": start_page,
            "end_page": end_page,
            "num_pages": len(batch_pages),
            "content": batch_text,
            "page_numbers": [p["page_number"] for p in batch_pages]
        })

    print(f"✓ Created {len(batches)} batches")

    return {
        **state,
        "batches": batches,
        "total_batches": len(batches)
    }


# ==============================================================================
# NODE 3: MAP PHASE - Generate questions from each batch
# ==============================================================================

def map_generate_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    MAP: Generate 5-7 questions from each batch using ai_query.

    Uses Spark SQL ai_query to process ALL batches in parallel.
    Each batch generates 5-7 multiple-choice questions.

    Output: List of JSON strings (one per batch)
    """
    batches = state["batches"]

    print(f"\n{'='*80}")
    print(f"MAP PHASE: Generating questions from {len(batches)} batches")
    print(f"Each batch → 5-7 questions (total ~{len(batches) * 6} questions)")
    print(f"{'='*80}\n")

    spark = get_spark()

    # Create temp table from batches
    batches_df = spark.createDataFrame(batches)
    batches_df.createOrReplaceTempView("batches_temp")

    # Prepare prompts (escape quotes for SQL)
    system_prompt = MAP_SYSTEM.replace("'", "\\'").replace('"', '\\"')

    # Use ai_query to generate questions for all batches in parallel
    questions_df = spark.sql(f"""
        SELECT
            batch_id,
            ai_query(
                '{Config.LLM_ENDPOINT}',
                concat(
                    '{system_prompt}',
                    '\\n\\nCONTENT (from pages ', CAST(start_page AS STRING), ' to ', CAST(end_page AS STRING), '):\\n\\n',
                    content,
                    '\\n\\nGenerate 5-7 multiple-choice training questions from this content.\\n\\n',
                    'Requirements:\\n',
                    '- Simple language (8th-grade reading level)\\n',
                    '- ONE correct answer, THREE plausible distractors\\n',
                    '- Mix difficulty: 2 easy, 3 medium, 1-2 hard\\n',
                    '- Topics: safety, operation, maintenance, troubleshooting\\n',
                    '- Include page references\\n',
                    '- Return as JSON array\\n\\n',
                    'ONLY use information from the content above.'
                ),
                modelParameters => named_struct(
                    'temperature', {Config.MAP_TEMPERATURE},
                    'max_tokens', {Config.MAP_MAX_TOKENS}
                )
            ) as questions
        FROM batches_temp
        ORDER BY batch_id
    """)

    # Collect results
    batch_questions = [row["questions"] for row in questions_df.collect()]

    print(f"✓ Generated questions for {len(batch_questions)} batches")
    print(f"{'='*80}\n")

    return {
        **state,
        "batch_questions": batch_questions
    }


# ==============================================================================
# NODE 4: REDUCE PHASE - Hierarchical 3-to-1 (STOPS AT LEVEL 2)
# ==============================================================================

def reduce_combine_node(state: QuestionGenerationState) -> QuestionGenerationState:
    """
    REDUCE: Hierarchical 3-to-1 combination, STOPS AT LEVEL 2.

    Combines question sets and removes duplicates.
    CRITICAL: Stops at level 2 to preserve variety.

    Example:
    - Level 0: 135 question sets (from MAP)
    - Level 1: 45 question sets (135 → 45, combine 3-to-1)
    - Level 2: 15 question sets (45 → 15, combine 3-to-1) → STOP

    Output: Array of 15 question chunks (JSON strings)
    """
    batch_questions = state["batch_questions"]

    print(f"\n{'='*80}")
    print(f"REDUCE PHASE: Hierarchical 3-to-1 combination")
    print(f"Starting with {len(batch_questions)} question sets")
    print(f"Target: Stop at level 2 (preserve variety)")
    print(f"{'='*80}\n")

    spark = get_spark()

    # Maximum levels to reduce (stop at level 2)
    MAX_REDUCE_LEVELS = Config.MAX_REDUCE_LEVELS

    # Track all levels
    reduce_levels = []
    current_level = batch_questions
    level_num = 1

    # Prepare prompts (escape quotes for SQL)
    system_prompt = REDUCE_SYSTEM.replace("'", "\\'").replace('"', '\\"')

    # Hierarchical reduction loop - STOP AT LEVEL 2
    while len(current_level) > 1 and level_num <= MAX_REDUCE_LEVELS:
        print(f"Level {level_num}: Combining {len(current_level)} items (3-to-1)")

        # Group items into sets of 3
        reduce_ratio = Config.REDUCE_RATIO
        groups = []

        for i in range(0, len(current_level), reduce_ratio):
            group = current_level[i:i + reduce_ratio]
            groups.append({
                "group_id": len(groups) + 1,
                "question_sets": "\n\n=== Question Set {} ===\n\n".format(1) +
                              "\n\n=== Question Set {} ===\n\n".join(
                                  [f"{j+1}\n\n{item}" for j, item in enumerate(group)]
                              ),
                "num_sets": len(group)
            })

        # Create temp table
        groups_df = spark.createDataFrame(groups)
        groups_df.createOrReplaceTempView(f"reduce_level_{level_num}_temp")

        # Use ai_query to combine groups
        combined_df = spark.sql(f"""
            SELECT
                group_id,
                ai_query(
                    '{Config.LLM_ENDPOINT}',
                    concat(
                        '{system_prompt}',
                        '\\n\\nYou have multiple question sets to combine:\\n\\n',
                        question_sets,
                        '\\n\\nTasks:\\n',
                        '1. Remove exact duplicates\\n',
                        '2. Merge similar questions (keep best version)\\n',
                        '3. Fix any formatting issues\\n',
                        '4. Ensure difficulty distribution (30% easy, 50% medium, 20% hard)\\n',
                        '5. Verify each question has ONE clear correct answer\\n\\n',
                        'Return combined and polished questions as single JSON array.\\n',
                        'KEEP ALL UNIQUE QUESTIONS - do not reduce quantity unnecessarily.'
                    ),
                    modelParameters => named_struct(
                        'temperature', {Config.REDUCE_TEMPERATURE},
                        'max_tokens', {Config.REDUCE_MAX_TOKENS}
                    )
                ) as combined_questions
            FROM reduce_level_{level_num}_temp
            ORDER BY group_id
        """)

        # Collect results
        next_level = [row["combined_questions"] for row in combined_df.collect()]

        reduce_levels.append(next_level)
        current_level = next_level

        print(f"✓ Level {level_num} complete: {len(next_level)} question sets")

        level_num += 1

    # current_level now contains 15-45 question chunks
    question_chunks = current_level
    num_chunks = len(question_chunks)

    # Count total questions by parsing JSON
    total_questions = 0
    for chunk in question_chunks:
        try:
            parsed = json.loads(chunk)
            if isinstance(parsed, list):
                total_questions += len(parsed)
            elif isinstance(parsed, dict) and "questions" in parsed:
                total_questions += len(parsed["questions"])
        except:
            pass

    # Create full text (concatenate all chunks)
    questions_full_text = "\n\n" + "=" * 80 + "\n\n"
    questions_full_text += ("\n\n" + "=" * 80 + "\n\n").join(question_chunks)

    print(f"\n{'='*80}")
    print(f"REDUCE COMPLETE")
    print(f"Levels: {len(reduce_levels)}")
    print(f"Final chunks: {num_chunks}")
    print(f"Total questions: {total_questions}")
    print(f"{'='*80}\n")

    return {
        **state,
        "reduce_levels": reduce_levels,
        "question_chunks": question_chunks,
        "num_question_chunks": num_chunks,
        "total_questions": total_questions,
        "questions_full_text": questions_full_text
    }
