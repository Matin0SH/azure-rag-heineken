# Databricks notebook source
# MAGIC %md
# MAGIC # Question Generation Pipeline - LangGraph with Spark SQL ai_query
# MAGIC
# MAGIC This notebook processes document chunks through question generation workflow:
# MAGIC 1. **Fetch** - Load chunks from Unity Catalog
# MAGIC 2. **Regroup** - Combine chunks by pages using Spark
# MAGIC 3. **Batch** - Group pages into batches (5 pages per batch)
# MAGIC 4. **MAP** - Generate 5-7 questions using ai_query (parallel)
# MAGIC 5. **REDUCE** - Hierarchical 3-to-1 combination using ai_query (2 levels)
# MAGIC 6. **Store** - Save to operator_questions table

# COMMAND ----------

# MAGIC %md
# MAGIC ## Install Dependencies

# COMMAND ----------

# Install required packages
%pip install langgraph langgraph-checkpoint-sqlite langchain langchain-core databricks-langchain --quiet
dbutils.library.restartPython()

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Widget parameters (passed from API/job trigger)
dbutils.widgets.text("pdf_id", "", "PDF ID")

# Configuration widgets (set by Terraform)
dbutils.widgets.text("catalog", "databricks_rag_dev", "Catalog")
dbutils.widgets.text("schema", "nextlevel-rag", "Schema")
dbutils.widgets.text("llm_endpoint", "databricks-llama-4-maverick", "LLM Endpoint")
dbutils.widgets.text("table_chunks", "chunks_embedded", "Table: Chunks")
dbutils.widgets.text("table_questions", "operator_questions", "Table: Questions")

# Get values
pdf_id = dbutils.widgets.get("pdf_id")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
LLM_ENDPOINT = dbutils.widgets.get("llm_endpoint")
TABLE_CHUNKS_NAME = dbutils.widgets.get("table_chunks")
TABLE_QUESTIONS_NAME = dbutils.widgets.get("table_questions")

# Derived paths
TABLE_CHUNKS = f"`{CATALOG}`.`{SCHEMA}`.{TABLE_CHUNKS_NAME}"
TABLE_QUESTIONS = f"`{CATALOG}`.`{SCHEMA}`.{TABLE_QUESTIONS_NAME}"

print("=" * 80)
print(f"QUESTION GENERATION PIPELINE")
print("=" * 80)
print(f"PDF ID: {pdf_id}")
print(f"Catalog: {CATALOG}")
print(f"Schema: {SCHEMA}")
print(f"LLM Endpoint: {LLM_ENDPOINT}")
print("=" * 80)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

from datetime import datetime
import json

def log_checkpoint(step: str, status: str, message: str = ""):
    """Log checkpoint with timestamp and status"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"start": "▶", "done": "✓", "error": "✗"}
    icon = icons.get(status, "•")
    print(f"[{timestamp}] {icon} {step}: {message}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Fetch Chunks

# COMMAND ----------

log_checkpoint("Step 1: Fetch Chunks", "start", f"pdf_id={pdf_id}")

# Fetch chunks using Spark SQL
chunks_df = spark.sql(f"""
    SELECT
        chunk_id,
        text,
        page_number,
        chunk_index
    FROM {TABLE_CHUNKS}
    WHERE pdf_id = '{pdf_id}'
    ORDER BY page_number, chunk_index
""")

# Get PDF metadata (pdf_id IS the pdf_name in this system)
pdf_name = pdf_id

pdf_metadata = spark.sql(f"""
    SELECT
        COUNT(DISTINCT page_number) as total_pages,
        COUNT(*) as total_chunks
    FROM {TABLE_CHUNKS}
    WHERE pdf_id = '{pdf_id}'
""").first()

total_pages = pdf_metadata["total_pages"] if pdf_metadata else 0
total_chunks = pdf_metadata["total_chunks"] if pdf_metadata else 0

# Convert to list of dicts for agent
chunks = [
    {
        "chunk_id": row["chunk_id"],
        "text": row["text"],
        "page_number": row["page_number"],
        "chunk_index": row["chunk_index"]
    }
    for row in chunks_df.collect()
]

log_checkpoint(
    "Step 1: Fetch Chunks",
    "done",
    f"Loaded {len(chunks)} chunks, {total_pages} pages"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Run LangGraph Workflow

# COMMAND ----------

log_checkpoint("Step 2: LangGraph Workflow", "start", "Initializing graph")

# Import LangGraph workflow
import sys
repo_path = "/Workspace/Repos/Production/azure-rag-heineken"
sys.path.append(repo_path)
print(f"Added to sys.path: {repo_path}")

print("Importing agents.question_generation...")
from agents.question_generation import create_question_generation_graph
print("✓ Import successful")

# Create graph
print("Creating question generation graph...")
graph = create_question_generation_graph()
print("✓ Graph created")

# Prepare initial state
initial_state = {
    "pdf_id": pdf_id,
    "pdf_name": pdf_name,
    "chunks": chunks,
    "total_chunks": total_chunks,
    "total_pages": total_pages,
    "pages": [],
    "batches": [],
    "total_batches": 0,
    "batch_questions": [],
    "reduce_levels": [],
    "question_chunks": [],
    "questions_full_text": "",
    "num_question_chunks": 0,
    "total_questions": 0,
    "processing_time": 0.0,
    "error_message": None
}

log_checkpoint("Step 2: LangGraph Workflow", "start", "Running workflow")

# Run workflow
import time
start_time = time.time()

try:
    final_state = graph.invoke(initial_state)
    processing_time = time.time() - start_time

    log_checkpoint(
        "Step 2: LangGraph Workflow",
        "done",
        f"Completed in {processing_time:.2f}s"
    )
except Exception as e:
    processing_time = time.time() - start_time
    log_checkpoint("Step 2: LangGraph Workflow", "error", str(e))
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Save Results

# COMMAND ----------

log_checkpoint("Step 3: Save Results", "start", "")

import uuid
from pyspark.sql.types import *

# Prepare question data
questions_id = str(uuid.uuid4())

# Get data from final state
question_chunks = final_state["question_chunks"]
questions_full_text = final_state["questions_full_text"]

question_data = [{
    "questions_id": questions_id,
    "pdf_id": pdf_id,
    "pdf_name": pdf_name,
    "question_chunks": question_chunks,
    "questions_full_text": questions_full_text,
    "num_question_chunks": final_state["num_question_chunks"],
    "total_questions": final_state["total_questions"],
    "total_pages": final_state["total_pages"],
    "total_chunks": final_state["total_chunks"],
    "total_batches": final_state["total_batches"],
    "reduce_levels": len(final_state["reduce_levels"]),
    "processing_model": LLM_ENDPOINT,
    "processing_time_seconds": processing_time,
    "created_at": datetime.now()
}]

# Define schema
schema = StructType([
    StructField("questions_id", StringType(), False),
    StructField("pdf_id", StringType(), False),
    StructField("pdf_name", StringType(), False),
    StructField("question_chunks", ArrayType(StringType()), False),
    StructField("questions_full_text", StringType(), False),
    StructField("num_question_chunks", IntegerType(), False),
    StructField("total_questions", IntegerType(), False),
    StructField("total_pages", IntegerType(), False),
    StructField("total_chunks", IntegerType(), False),
    StructField("total_batches", IntegerType(), False),
    StructField("reduce_levels", IntegerType(), False),
    StructField("processing_model", StringType(), False),
    StructField("processing_time_seconds", FloatType(), True),
    StructField("created_at", TimestampType(), False)
])

# Create DataFrame and save
questions_df = spark.createDataFrame(question_data, schema=schema)

# Delete existing questions for this pdf_id
spark.sql(f"""
    DELETE FROM {TABLE_QUESTIONS}
    WHERE pdf_id = '{pdf_id}'
""")

# Insert new questions
questions_df.write.format("delta").mode("append").saveAsTable(TABLE_QUESTIONS)

log_checkpoint("Step 3: Save Results", "done", f"Saved questions_id={questions_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Complete

# COMMAND ----------

print("")
print("=" * 80)
print("✓ QUESTION GENERATION COMPLETE")
print("=" * 80)
print(f"PDF: {pdf_name}")
print(f"Pages: {final_state['total_pages']}")
print(f"Batches: {final_state['total_batches']}")
print(f"Reduce Levels: {len(final_state['reduce_levels'])}")
print(f"Final Chunks: {final_state['num_question_chunks']}")
print(f"Total Questions: {final_state['total_questions']}")
print(f"Processing Time: {processing_time:.2f}s")
print("=" * 80)

# Return success
dbutils.notebook.exit(json.dumps({
    "status": "success",
    "questions_id": questions_id,
    "pdf_id": pdf_id,
    "num_question_chunks": final_state["num_question_chunks"],
    "total_questions": final_state["total_questions"],
    "reduce_levels": len(final_state["reduce_levels"]),
    "processing_time": processing_time
}))
