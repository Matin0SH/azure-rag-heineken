"""
Summarization Agent Nodes - MAP-REDUCE with Hierarchical 3-to-1 Combination

Architecture:
1. Fetch chunks from Unity Catalog
2. Regroup chunks by pages
3. Create batches (5 pages per batch)
4. MAP: Extract from each batch (3 workers parallel)
5. REDUCE: Combine hierarchically (3-to-1) until 1 final
6. Extract topics from final summary

PHILOSOPHY: EXTRACTION over summarization - preserve ALL details.
"""

# State
from .state import SummarizationState

# Prompts
from .prompts import (
    TECH_MAP_SYSTEM, TECH_MAP_HUMAN,
    OPERATOR_MAP_SYSTEM, OPERATOR_MAP_HUMAN,
    INTERMEDIATE_REDUCE_SYSTEM, INTERMEDIATE_REDUCE_HUMAN,
    REDUCE_SYSTEM, REDUCE_HUMAN,
    TOPIC_EXTRACTION_SYSTEM, TOPIC_EXTRACTION_HUMAN
)

# LLM
from databricks_langchain import ChatDatabricks
import os
from dotenv import load_dotenv

# Utilities
from typing import List, Dict
import concurrent.futures


# ==============================================================================
# CONFIGURATION
# ==============================================================================

class Config:
    """
    Centralized configuration for summarization agent.
    All hyperparameters in one place for easy tuning.
    """

    # ====================
    # BATCHING
    # ====================
    PAGES_PER_BATCH = 5                # 5 pages per batch

    # ====================
    # HIERARCHICAL REDUCE
    # ====================
    REDUCE_RATIO = 3                   # Combine 3 items → 1 (3-to-1)

    # ====================
    # PARALLEL PROCESSING
    # ====================
    MAX_WORKERS = 3                    # Max 3 concurrent API calls (avoid rate limits)

    # ====================
    # LLM CONFIGURATION
    # ====================
    LLM_ENDPOINT = "databricks-llama-4-maverick"

    # For EXTRACTION (MAP phase)
    EXTRACTION_TEMPERATURE = 0.1       # Very low = deterministic, follows instructions
    EXTRACTION_MAX_TOKENS = 8000       # Room for complete extraction

    # For COMBINATION (REDUCE phase)
    COMBINATION_TEMPERATURE = 0.1      # Very low = deterministic
    COMBINATION_MAX_TOKENS = 8000      # More room for combining multiple extractions

    # For TOPICS (keyword extraction)
    TOPICS_TEMPERATURE = 0.2           # Slightly creative for keyword variety
    TOPICS_MAX_TOKENS = 2000            # Just keywords


# ==============================================================================
# LLM INITIALIZATION (Singleton Pattern)
# ==============================================================================

_extraction_llm = None
_combination_llm = None
_topics_llm = None


def get_extraction_llm() -> ChatDatabricks:
    """Get or create extraction LLM instance (for MAP phase)"""
    global _extraction_llm

    if _extraction_llm is None:
        if not os.getenv("DATABRICKS_HOST"):
            load_dotenv()

        _extraction_llm = ChatDatabricks(
            endpoint=Config.LLM_ENDPOINT,
            temperature=Config.EXTRACTION_TEMPERATURE,
            max_tokens=Config.EXTRACTION_MAX_TOKENS,
            streaming=False
        )

    return _extraction_llm


def get_combination_llm() -> ChatDatabricks:
    """Get or create combination LLM instance (for REDUCE phase)"""
    global _combination_llm

    if _combination_llm is None:
        if not os.getenv("DATABRICKS_HOST"):
            load_dotenv()

        _combination_llm = ChatDatabricks(
            endpoint=Config.LLM_ENDPOINT,
            temperature=Config.COMBINATION_TEMPERATURE,
            max_tokens=Config.COMBINATION_MAX_TOKENS,
            streaming=False
        )

    return _combination_llm


def get_topics_llm() -> ChatDatabricks:
    """Get or create topics LLM instance (for keyword extraction)"""
    global _topics_llm

    if _topics_llm is None:
        if not os.getenv("DATABRICKS_HOST"):
            load_dotenv()

        _topics_llm = ChatDatabricks(
            endpoint=Config.LLM_ENDPOINT,
            temperature=Config.TOPICS_TEMPERATURE,
            max_tokens=Config.TOPICS_MAX_TOKENS,
            streaming=False
        )

    return _topics_llm


# ==============================================================================
# NODES START HERE
# ==============================================================================

def regroup_pages_node(state: SummarizationState) -> SummarizationState:
    """
    Regroup chunks by page_number using Spark.

    Input: state["chunks"] - List of chunk dicts from Unity Catalog
    Output: state["pages"] - List of page dicts with combined text

    Uses Spark for memory efficiency and parallel processing.
    """
    print("\n" + "=" * 80)
    print("🔄 NODE: regroup_pages_node - START")
    print("=" * 80)

    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, collect_list, concat_ws

    print("📊 Importing Spark dependencies... OK")
    print("=" * 80)
    print("REGROUP: Combining chunks by page using Spark")
    print("=" * 80)

    chunks = state.get("chunks", [])

    if not chunks:
        print("No chunks to regroup")
        return {**state, "pages": []}

    # Get Spark session
    spark = SparkSession.builder.getOrCreate()

    # Convert chunks list to Spark DataFrame
    chunks_df = spark.createDataFrame(chunks)

    # Group by page_number and concatenate all chunk texts (ordered by chunk_index)
    from pyspark.sql.functions import struct, sort_array, transform

    pages_df = chunks_df.groupBy("page_number").agg(
        sort_array(collect_list(struct(col("chunk_index"), col("text")))).alias("chunks_ordered")
    ).selectExpr(
        "page_number",
        "concat_ws('\\n\\n', transform(chunks_ordered, x -> x.text)) as text"
    ).orderBy("page_number")

    # Collect back to Python list
    pages = [
        {
            "page_number": row["page_number"],
            "text": row["text"]
        }
        for row in pages_df.collect()
    ]

    total_pages = len(pages)
    print(f"Regrouped {len(chunks)} chunks → {total_pages} pages")
    print("=" * 80)

    return {
        **state,
        "pages": pages,
        "total_pages": total_pages
    }


def create_batches_node(state: SummarizationState) -> SummarizationState:
    """
    Group pages into batches of 5 pages each using Spark.

    Input: state["pages"] - List of page dicts
    Output: state["batches"] - List of batch dicts

    Uses Spark for consistency and scalability.
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, collect_list, floor

    print("=" * 80)
    print("BATCH: Grouping pages into batches using Spark")
    print("=" * 80)

    pages = state.get("pages", [])

    if not pages:
        print("No pages to batch")
        return {**state, "batches": [], "total_batches": 0}

    batch_size = Config.PAGES_PER_BATCH  # 5

    # Get Spark session
    spark = SparkSession.builder.getOrCreate()

    # Convert pages to Spark DataFrame with batch_id
    pages_df = spark.createDataFrame(pages)

    # Add batch_id: (page_number - 1) // batch_size + 1
    pages_with_batch = pages_df.withColumn(
        "batch_id",
        (floor((col("page_number") - 1) / batch_size) + 1).cast("int")
    )

    # Group by batch_id and collect pages (ordered by page_number)
    from pyspark.sql.functions import struct, sort_array

    batches_df = pages_with_batch.groupBy("batch_id").agg(
        sort_array(collect_list(struct(col("page_number"), col("text")))).alias("pages_ordered")
    ).orderBy("batch_id")

    # Collect to Python list and reconstruct batch structure
    batches = []
    for row in batches_df.collect():
        batch_pages = [
            {"page_number": page["page_number"], "text": page["text"]}
            for page in row["pages_ordered"]
        ]
        batches.append({
            "batch_id": row["batch_id"],
            "pages": batch_pages
        })

    total_batches = len(batches)
    print(f"Grouped {len(pages)} pages → {total_batches} batches ({batch_size} pages/batch)")
    print("=" * 80)

    return {
        **state,
        "batches": batches,
        "total_batches": total_batches
    }


def map_extract_node(state: SummarizationState) -> SummarizationState:
    """
    MAP phase: Extract from each batch using ai_query (Spark SQL).

    Input: state["batches"] - List of batch dicts
    Output: state["batch_extractions"] - List of extractions (one per batch)

    Uses Spark SQL ai_query for native LLM calls - no Python API calls.
    Spark cluster handles parallelism and rate limiting automatically.
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, concat_ws, lit

    print("=" * 80)
    print("MAP: Extracting from batches using Spark SQL ai_query")
    print("=" * 80)

    batches = state.get("batches", [])
    summary_type = state.get("summary_type", "technical")

    if not batches:
        print("No batches to extract")
        return {**state, "batch_extractions": []}

    # Get Spark session
    spark = SparkSession.builder.getOrCreate()

    # Prepare batches for Spark: flatten pages into single text per batch
    batch_data = []
    for batch in batches:
        batch_text = "\n\n".join([page["text"] for page in batch["pages"]])
        batch_data.append({
            "batch_id": batch["batch_id"],
            "batch_text": batch_text
        })

    # Convert to Spark DataFrame
    batches_df = spark.createDataFrame(batch_data)

    # Select prompts based on summary_type
    if summary_type == "technical":
        system_prompt = TECH_MAP_SYSTEM
        human_template = TECH_MAP_HUMAN
    else:
        system_prompt = OPERATOR_MAP_SYSTEM
        human_template = OPERATOR_MAP_HUMAN

    # Create temp view
    batches_df.createOrReplaceTempView("batches_temp")

    # Build prompt with context (empty for first batch, previous for rest)
    total_batches = len(batches)

    # Use Spark SQL with ai_query to extract
    extractions_df = spark.sql(f"""
        SELECT
            batch_id,
            ai_query(
                '{Config.LLM_ENDPOINT}',
                concat(
                    '{system_prompt.replace("'", "''")}',
                    '\\n\\n',
                    'Batch ', CAST(batch_id AS STRING), '/{total_batches}',
                    '\\n\\nCONTENT:\\n',
                    batch_text,
                    '\\n\\nEXTRACT all information following the format. Use EXACT wording from source.'
                )
            ) as extraction
        FROM batches_temp
        ORDER BY batch_id
    """)

    # Collect extractions
    extractions = [row["extraction"] for row in extractions_df.collect()]

    print(f"Extracted from {len(extractions)} batches")
    print("=" * 80)

    # Clean up temp view
    spark.catalog.dropTempView("batches_temp")

    return {
        **state,
        "batch_extractions": extractions
    }


def reduce_combine_node(state: SummarizationState) -> SummarizationState:
    """
    REDUCE phase: Hierarchical 3-to-1 combination using ai_query.

    Input: state["batch_extractions"] - List of extractions from MAP phase
    Output: state["reduce_levels"], state["final_summary"]

    Uses Spark SQL ai_query for hierarchical reduction.
    Continues combining until 1 final summary remains.
    """
    from pyspark.sql import SparkSession
    from pyspark.sql.functions import col, monotonically_increasing_id, floor, concat_ws, collect_list, lit

    print("=" * 80)
    print("REDUCE: Hierarchical 3-to-1 combination using Spark SQL ai_query")
    print("=" * 80)

    batch_extractions = state.get("batch_extractions", [])
    summary_type = state.get("summary_type", "technical")

    if not batch_extractions:
        print("No extractions to reduce")
        return {**state, "reduce_levels": [], "final_summary": ""}

    if len(batch_extractions) == 1:
        print("Only 1 extraction - using as final summary")
        return {
            **state,
            "reduce_levels": [],
            "final_summary": batch_extractions[0]
        }

    # Get Spark session
    spark = SparkSession.builder.getOrCreate()

    # Prepare combination prompt
    system_prompt = INTERMEDIATE_REDUCE_SYSTEM.replace("'", "''")

    # Track all levels
    reduce_levels = []
    current_level = batch_extractions
    level_num = 1

    # Hierarchical reduction loop
    while len(current_level) > 1:
        print(f"Level {level_num}: Combining {len(current_level)} items (3-to-1)")

        # Create DataFrame from current level
        level_data = [{"idx": i, "text": text} for i, text in enumerate(current_level)]
        level_df = spark.createDataFrame(level_data)

        # Add group_id: group every 3 items
        level_df = level_df.withColumn(
            "group_id",
            floor(col("idx") / lit(Config.REDUCE_RATIO))
        )

        # Create temp view
        level_df.createOrReplaceTempView(f"reduce_level_{level_num}")

        # Use Spark SQL to combine groups with ai_query
        combined_df = spark.sql(f"""
            SELECT
                group_id,
                ai_query(
                    '{Config.LLM_ENDPOINT}',
                    concat(
                        '{system_prompt}',
                        '\\n\\nCOMBINE the following extractions:\\n\\n',
                        concat_ws('\\n\\n---\\n\\n', collect_list(text)),
                        '\\n\\nKEEP all information. ORGANIZE chronologically. ONLY remove exact duplicates.'
                    ),
                    modelParameters => named_struct(
                        'temperature', {Config.COMBINATION_TEMPERATURE},
                        'max_tokens', {Config.COMBINATION_MAX_TOKENS}
                    )
                ) as combined_text
            FROM reduce_level_{level_num}
            GROUP BY group_id
            ORDER BY group_id
        """)

        # Collect results for next level
        current_level = [row["combined_text"] for row in combined_df.collect()]
        reduce_levels.append(current_level)

        print(f"Level {level_num}: → {len(current_level)} combined items")

        # Clean up temp view
        spark.catalog.dropTempView(f"reduce_level_{level_num}")

        level_num += 1

    # Final summary is the last item
    final_summary = current_level[0] if current_level else ""

    print(f"REDUCE complete: {len(batch_extractions)} extractions → 1 final summary ({level_num - 1} levels)")
    print("=" * 80)

    return {
        **state,
        "reduce_levels": reduce_levels,
        "final_summary": final_summary
    }


def extract_topics_node(state: SummarizationState) -> SummarizationState:
    """
    Extract key topics/keywords from final summary using ai_query.

    Input: state["final_summary"]
    Output: state["key_topics"] - List of keywords

    Uses Spark SQL ai_query for topic extraction.
    """
    from pyspark.sql import SparkSession

    print("=" * 80)
    print("TOPICS: Extracting keywords using Spark SQL ai_query")
    print("=" * 80)

    final_summary = state.get("final_summary", "")

    if not final_summary:
        print("No final summary - skipping topic extraction")
        return {**state, "key_topics": []}

    # Get Spark session
    spark = SparkSession.builder.getOrCreate()

    # Prepare prompts
    system_prompt = TOPIC_EXTRACTION_SYSTEM.replace("'", "''")
    human_prompt = TOPIC_EXTRACTION_HUMAN.replace("'", "''")

    # Create single-row DataFrame with summary
    summary_df = spark.createDataFrame([{"summary": final_summary}])
    summary_df.createOrReplaceTempView("summary_temp")

    # Use ai_query to extract topics
    topics_df = spark.sql(f"""
        SELECT
            ai_query(
                '{Config.LLM_ENDPOINT}',
                concat(
                    '{system_prompt}',
                    '\\n\\n',
                    replace('{human_prompt}', '{{summary}}', summary)
                ),
                modelParameters => named_struct(
                    'temperature', {Config.TOPICS_TEMPERATURE},
                    'max_tokens', {Config.TOPICS_MAX_TOKENS}
                )
            ) as topics_text
        FROM summary_temp
    """)

    # Get topics string
    topics_text = topics_df.collect()[0]["topics_text"]

    # Parse comma-separated topics
    key_topics = [t.strip() for t in topics_text.split(",") if t.strip()]

    print(f"Extracted {len(key_topics)} topics: {', '.join(key_topics[:5])}...")
    print("=" * 80)

    # Clean up temp view
    spark.catalog.dropTempView("summary_temp")

    return {
        **state,
        "key_topics": key_topics
    }
