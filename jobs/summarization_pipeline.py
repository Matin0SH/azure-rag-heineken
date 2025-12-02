# Databricks notebook source
# MAGIC %md
# MAGIC # Summarization Pipeline - LangGraph with Spark SQL ai_query
# MAGIC
# MAGIC This notebook processes document chunks through summarization workflow:
# MAGIC 1. **Fetch** - Load chunks from Unity Catalog
# MAGIC 2. **Regroup** - Combine chunks by pages using Spark
# MAGIC 3. **Batch** - Group pages into batches (5 pages per batch)
# MAGIC 4. **MAP** - Extract information using ai_query (parallel)
# MAGIC 5. **REDUCE** - Hierarchical 3-to-1 combination using ai_query
# MAGIC 6. **Topics** - Extract keywords
# MAGIC 7. **Store** - Save to summaries table

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Widget parameters (passed from API/job trigger)
dbutils.widgets.text("pdf_id", "", "PDF ID")
dbutils.widgets.dropdown("summary_type", "technical", ["technical", "operator"], "Summary Type")

# Configuration widgets (set by Terraform)
dbutils.widgets.text("catalog", "heineken_test_workspace", "Catalog")
dbutils.widgets.text("schema", "nextlevel-rag", "Schema")
dbutils.widgets.text("llm_endpoint", "databricks-llama-4-maverick", "LLM Endpoint")
dbutils.widgets.text("table_chunks", "chunks_embedded", "Table: Chunks")
dbutils.widgets.text("table_summaries", "document_summaries", "Table: Summaries")

# Get values
pdf_id = dbutils.widgets.get("pdf_id")
summary_type = dbutils.widgets.get("summary_type")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
LLM_ENDPOINT = dbutils.widgets.get("llm_endpoint")
TABLE_CHUNKS_NAME = dbutils.widgets.get("table_chunks")
TABLE_SUMMARIES_NAME = dbutils.widgets.get("table_summaries")

# Derived paths
TABLE_CHUNKS = f"`{CATALOG}`.`{SCHEMA}`.{TABLE_CHUNKS_NAME}"
TABLE_SUMMARIES = f"`{CATALOG}`.`{SCHEMA}`.{TABLE_SUMMARIES_NAME}"

print("=" * 80)
print(f"SUMMARIZATION PIPELINE")
print("=" * 80)
print(f"PDF ID: {pdf_id}")
print(f"Summary Type: {summary_type}")
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
sys.path.append("/Workspace/Repos/matin_kh84/NextLevel")  # Adjust path to your repo

from agents.summarization import create_summarization_graph

# Create graph
graph = create_summarization_graph()

# Prepare initial state
initial_state = {
    "pdf_id": pdf_id,
    "pdf_name": pdf_name,
    "summary_type": summary_type,
    "chunks": chunks,
    "total_chunks": total_chunks,
    "total_pages": total_pages,
    "pages": [],
    "batches": [],
    "total_batches": 0,
    "batch_extractions": [],
    "reduce_levels": [],
    "final_summary": "",
    "key_topics": [],
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

# Prepare summary data
summary_id = str(uuid.uuid4())
summary_data = [{
    "summary_id": summary_id,
    "pdf_id": pdf_id,
    "pdf_name": pdf_name,
    "summary_type": summary_type,
    "summary_text": final_state["final_summary"],
    "total_pages": final_state["total_pages"],
    "total_chunks": final_state["total_chunks"],
    "total_batches": final_state["total_batches"],
    "key_topics": final_state["key_topics"],
    "processing_model": LLM_ENDPOINT,
    "processing_time_seconds": processing_time,
    "created_at": datetime.now()
}]

# Define schema
schema = StructType([
    StructField("summary_id", StringType(), False),
    StructField("pdf_id", StringType(), False),
    StructField("pdf_name", StringType(), False),
    StructField("summary_type", StringType(), False),
    StructField("summary_text", StringType(), False),
    StructField("total_pages", IntegerType(), False),
    StructField("total_chunks", IntegerType(), False),
    StructField("total_batches", IntegerType(), False),
    StructField("key_topics", ArrayType(StringType()), True),
    StructField("processing_model", StringType(), False),
    StructField("processing_time_seconds", FloatType(), True),
    StructField("created_at", TimestampType(), False)
])

# Create DataFrame and save
summary_df = spark.createDataFrame(summary_data, schema=schema)

# Delete existing summary for this pdf_id and summary_type
spark.sql(f"""
    DELETE FROM {TABLE_SUMMARIES}
    WHERE pdf_id = '{pdf_id}' AND summary_type = '{summary_type}'
""")

# Insert new summary
summary_df.write.format("delta").mode("append").saveAsTable(TABLE_SUMMARIES)

log_checkpoint("Step 3: Save Results", "done", f"Saved summary_id={summary_id}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Complete

# COMMAND ----------

print("")
print("=" * 80)
print("✓ SUMMARIZATION COMPLETE")
print("=" * 80)
print(f"PDF: {pdf_name}")
print(f"Type: {summary_type}")
print(f"Pages: {final_state['total_pages']}")
print(f"Batches: {final_state['total_batches']}")
print(f"Summary Length: {len(final_state['final_summary'])} chars")
print(f"Topics: {', '.join(final_state['key_topics'][:5])}")
print(f"Processing Time: {processing_time:.2f}s")
print("=" * 80)

# Return success
dbutils.notebook.exit(json.dumps({
    "status": "success",
    "summary_id": summary_id,
    "pdf_id": pdf_id,
    "summary_type": summary_type,
    "summary_length": len(final_state["final_summary"]),
    "topics_count": len(final_state["key_topics"]),
    "processing_time": processing_time
}))
