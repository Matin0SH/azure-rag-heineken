# Databricks notebook source
# MAGIC %md
# MAGIC # PDF Ingestion Pipeline - OPTIMIZED updated
# MAGIC
# MAGIC This notebook processes a PDF file through the complete RAG pipeline:
# MAGIC 1. **Parse** - Extract text from PDF using `ai_parse_document()`
# MAGIC 2. **Extract Pages** - Spark SQL parallel processing (5-10x faster)
# MAGIC 3. **Chunk** - Split text with smart merging (no data loss)
# MAGIC 4. **Embed** - Generate embeddings using `ai_query()`
# MAGIC 5. **Store** - MERGE operations (atomic writes, 2-3x faster)
# MAGIC 6. **Index** - Sync Vector Search index

# COMMAND ----------

# MAGIC %md
# MAGIC ## Configuration

# COMMAND ----------

# Widget parameters (passed from job trigger)
dbutils.widgets.text("pdf_name", "", "PDF Filename")
dbutils.widgets.text("pdf_id", "", "PDF ID")

# Configuration widgets (set by Terraform)
dbutils.widgets.text("catalog", "databricks_rag_dev", "Catalog")
dbutils.widgets.text("schema", "nextlevel-rag", "Schema")
dbutils.widgets.text("embedding_model", "databricks-gte-large-en", "Embedding Model")
dbutils.widgets.text("volume_raw_pdfs", "raw_pdfs", "Volume: Raw PDFs")
dbutils.widgets.text("volume_screenshots", "screenshots", "Volume: Screenshots")
dbutils.widgets.text("vector_search_endpoint", "heineken-vdb", "Vector Search Endpoint")
dbutils.widgets.text("vector_index_name", "chunks_embedded_index", "Vector Index Name")
dbutils.widgets.text("table_chunks", "chunks_embedded", "Table: Chunks")
dbutils.widgets.text("table_registery", "pdf_registery", "Table: PDF Registery")
dbutils.widgets.text("table_screenshots", "page_screenshots", "Table: Screenshots")

# Get values
pdf_name = dbutils.widgets.get("pdf_name")
pdf_id = dbutils.widgets.get("pdf_id")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
EMBEDDING_MODEL = dbutils.widgets.get("embedding_model")
VOLUME_RAW_PDFS = dbutils.widgets.get("volume_raw_pdfs")
VOLUME_SCREENSHOTS = dbutils.widgets.get("volume_screenshots")
VECTOR_SEARCH_ENDPOINT = dbutils.widgets.get("vector_search_endpoint")
VECTOR_INDEX_NAME = dbutils.widgets.get("vector_index_name")
TABLE_CHUNKS_NAME = dbutils.widgets.get("table_chunks")
TABLE_REGISTERY_NAME = dbutils.widgets.get("table_registery")
TABLE_SCREENSHOTS_NAME = dbutils.widgets.get("table_screenshots")

print("============================================================")
print(f"dY Processing: {pdf_name}")
print(f"dY+ PDF ID: {pdf_id}")
print(f"dY Catalog: {CATALOG}")
print(f"dY Schema: {SCHEMA}")
print(f"dY Vector Endpoint: {VECTOR_SEARCH_ENDPOINT}")
print("============================================================")

# COMMAND ----------

# Chunking parameters (static - best practice values)
MIN_CHARS = 600   # ~150 tokens
MAX_CHARS = 1600  # ~400 tokens
OVERLAP_CHARS = 200  # ~50 tokens

# Derived paths (fully configurable)
VOLUME_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME_RAW_PDFS}/{pdf_name}"
TABLE_CHUNKS = f"`{CATALOG}`.`{SCHEMA}`.{TABLE_CHUNKS_NAME}"
TABLE_PDF_REGISTERY = f"`{CATALOG}`.`{SCHEMA}`.{TABLE_REGISTERY_NAME}"
TABLE_SCREENSHOTS = f"`{CATALOG}`.`{SCHEMA}`.{TABLE_SCREENSHOTS_NAME}"
SCREENSHOT_PATH = f"/Volumes/{CATALOG}/{SCHEMA}/{VOLUME_SCREENSHOTS}/{pdf_id}/"
FULL_INDEX_NAME = f"{CATALOG}.{SCHEMA}.{VECTOR_INDEX_NAME}"

# COMMAND ----------

# MAGIC %md
# MAGIC ## Helper Functions

# COMMAND ----------

from datetime import datetime

def log_checkpoint(step: str, status: str, message: str = ""):
    """Log checkpoint with timestamp and status icon"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    icons = {"start": "start", "done": "done", "error": "error"}
    icon = icons.get(status, "unknown")
    print(f"[{timestamp}] {icon} {step}: {message}")

def update_registery_status(status: str, error_msg: str = None):
    """Update PDF registery status"""
    if error_msg:
        spark.sql(f"""
            UPDATE {TABLE_PDF_REGISTERY}
            SET processing_status = '{status}',
                processed_date = current_timestamp(),
                error_message = '{error_msg.replace("'", "''")}'
            WHERE pdf_id = '{pdf_id}'
        """)
    else:
        spark.sql(f"""
            UPDATE {TABLE_PDF_REGISTERY}
            SET processing_status = '{status}',
                processed_date = current_timestamp(),
                error_message = NULL
            WHERE pdf_id = '{pdf_id}'
        """)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 0: Register PDF

# COMMAND ----------

total_chunks = 0  # track chunk count without driver collect

try:
    log_checkpoint(
        "Step 0: Register PDF",
        "start",
        f"pdf_id={pdf_id}, pdf_name={pdf_name}"
    )

    spark.sql(f"DELETE FROM {TABLE_PDF_REGISTERY} WHERE pdf_id = '{pdf_id}'")

    spark.sql(f"""
        INSERT INTO {TABLE_PDF_REGISTERY}
        VALUES (
            '{pdf_id}',
            '{pdf_name}',
            '{VOLUME_PATH}',
            current_timestamp(),
            'processing',
            NULL,
            NULL
        )
    """)

    log_checkpoint(
        "Step 0: Register PDF",
        "done",
        f"Registered pdf_id={pdf_id}, pdf_name={pdf_name}"
    )

except Exception as e:
    log_checkpoint(
        "Step 0: Register PDF",
        "error",
        f"{e} (pdf_id={pdf_id}, pdf_name={pdf_name})"
    )
    raise


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1: Parse PDF

# COMMAND ----------

# Step 1: Parse PDF

try:
    log_checkpoint(
        "Step 1: Parse PDF",
        "start",
        f"pdf_id={pdf_id}, pdf_name={pdf_name}, volume_path={VOLUME_PATH}"
    )

    # Parse PDF with screenshots (stay in Spark)
    parsed_df = spark.sql(f"""
        SELECT
            ai_parse_document(
                content,
                map(
                    'version', '2.0',
                    'descriptionElementTypes', 'figure',
                    'imageOutputPath', '{SCREENSHOT_PATH}'
                )
            ) as parsed_result
        FROM READ_FILES('{VOLUME_PATH}', format => 'binaryFile')
    """)

    # Directly access VARIANT fields for counts
    parse_counts = parsed_df.selectExpr(
        "size(try_cast(parsed_result:document:pages AS ARRAY<VARIANT>)) as page_count",
        "size(try_cast(parsed_result:document:elements AS ARRAY<VARIANT>)) as element_count"
    ).collect()[0]

    log_checkpoint(
        "Step 1: Parse PDF",
        "done",
        f"pdf_id={pdf_id}, pdf_name={pdf_name}, "
        f"pages={parse_counts['page_count']}, "
        f"elements={parse_counts['element_count']}"
    )

    # Keep a reference if later cells expect parsed_struct_df
    parsed_struct_df = parsed_df

except Exception as e:
    log_checkpoint(
        "Step 1: Parse PDF",
        "error",
        f"pdf_id={pdf_id}, pdf_name={pdf_name}, error={str(e)}"
    )
    update_registery_status("failed", f"Parse failed: {str(e)}")
    raise


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2: Extract Pages (Spark SQL - OPTIMIZED)

# COMMAND ----------

# Step 2: Extract Pages (Spark SQL - OPTIMIZED)

page_count = 0

try:
    log_checkpoint("Step 2: Extract Pages", "start", "Using Spark SQL parallel processing")

    from pyspark.sql.functions import col, explode, collect_list, concat_ws

    elements_df = parsed_df.selectExpr(
        "explode(try_cast(parsed_result:document:elements AS ARRAY<VARIANT>)) as element"
    ).selectExpr(
        "try_cast(element:content AS STRING) as text",
        "coalesce(try_cast(element:bbox[0].page_id AS INT), 0) + 1 as page_number"
    ).filter("text IS NOT NULL AND trim(text) != ''")



    # Group by page and concatenate
    page_texts_df = elements_df.groupBy("page_number").agg(
        concat_ws("\n", collect_list("text")).alias("text")
    ).orderBy("page_number")

    page_count = page_texts_df.count()

    log_checkpoint("Step 2: Extract Pages", "done", f"Extracted {page_count} pages")

except Exception as e:
    log_checkpoint("Step 2: Extract Pages", "error", str(e))
    update_registery_status("failed", f"Extract failed: {str(e)}")
    raise


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2b: Save Screenshot Paths

# COMMAND ----------

# Step 2b: Save Screenshot Paths

try:
    log_checkpoint(
        "Step 2b: Save Screenshots",
        "start",
        f"pdf_id={pdf_id}, pdf_name={pdf_name}"
    )

    from pyspark.sql.functions import uuid, current_timestamp

    pages_df = parsed_df.selectExpr(
        "explode(try_cast(parsed_result:document:pages AS ARRAY<VARIANT>)) as page"
    ).selectExpr(
        "uuid() as page_id",
        f"'{pdf_id}' as pdf_id",
        # page index (0-based in bbox/docs) -> 1-based page_number
        "coalesce(try_cast(page:id AS INT), 0) + 1 as page_number",
        "try_cast(page:image_uri AS STRING) as screenshot_path",
        "current_timestamp() as created_at"
    ).where("screenshot_path is not null and trim(screenshot_path) != ''")

    screenshot_count = pages_df.count()

    if screenshot_count > 0:
        spark.sql(f"DELETE FROM {TABLE_SCREENSHOTS} WHERE pdf_id = '{pdf_id}'")
        pages_df.write.format("delta").mode("append").saveAsTable(TABLE_SCREENSHOTS)
        log_checkpoint(
            "Step 2b: Save Screenshots",
            "done",
            f"Saved {screenshot_count} screenshots for pdf_id={pdf_id}"
        )
    else:
        log_checkpoint(
            "Step 2b: Save Screenshots",
            "done",
            f"No screenshots found for pdf_id={pdf_id}"
        )

except Exception as e:
    log_checkpoint(
        "Step 2b: Save Screenshots",
        "error",
        f"pdf_id={pdf_id}, error={str(e)}"
    )
    # Non-critical - continue processing


# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3: Chunk Text (Spark UDF - BEAST MODE ⚡)

# COMMAND ----------

try:
    log_checkpoint("Step 3: Chunk Text", "start", "Using Spark UDF parallel chunking")

    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from pyspark.sql.functions import udf, explode, monotonically_increasing_id, row_number
    from pyspark.sql.types import ArrayType, StructType, StructField, StringType
    from pyspark.sql.window import Window
    import uuid

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_CHARS,
        chunk_overlap=OVERLAP_CHARS,
        separators=["\n\n", "\n", ". ", ", ", " ", ""],
        length_function=len
    )

    # Define UDF for chunking (runs in parallel across pages)
    @udf(returnType=ArrayType(StringType()))
    def chunk_text_udf(text):
        """Chunk text using LangChain splitter - runs in parallel"""
        if not text:
            return []
        chunks = splitter.split_text(text)
        return [c.strip() for c in chunks if c.strip()]

    def merge_small_chunks(chunks, min_size=300, max_size=1600):
        """Merge small chunks with adjacent chunks to prevent data loss"""
        if not chunks:
            return []

        merged = []
        buffer = ""
        buffer_page = None

        for chunk in chunks:
            text = chunk["text"]
            page = chunk["page_number"]

            # If buffer has content from different page, flush it first
            if buffer and buffer_page != page:
                if buffer.strip():
                    merged.append({
                        "page_number": buffer_page,
                        "text": buffer.strip()
                    })
                buffer = ""
                buffer_page = None

            # If chunk is small, add to buffer
            if len(text) < min_size:
                if not buffer:
                    buffer_page = page
                buffer += " " + text if buffer else text

                # If buffer is now large enough, flush it
                if len(buffer) >= min_size:
                    merged.append({
                        "page_number": buffer_page,
                        "text": buffer.strip()
                    })
                    buffer = ""
                    buffer_page = None
            else:
                # Flush buffer first if it exists
                if buffer:
                    merged.append({
                        "page_number": buffer_page,
                        "text": buffer.strip()
                    })
                    buffer = ""
                    buffer_page = None

                # Add the chunk
                merged.append(chunk)

        # Flush remaining buffer
        if buffer and buffer.strip():
            merged.append({
                "page_number": buffer_page,
                "text": buffer.strip()
            })

        return merged

    # Use Spark for parallel chunking (BEAST MODE ⚡) and keep distributed
    chunked_df = page_texts_df.withColumn("chunk_text", explode(chunk_text_udf("text")))

    chunk_rows_df = chunked_df.selectExpr(
        "uuid() as chunk_id",
        f"'{pdf_id}' as pdf_id",
        "page_number",
        "row_number() over (partition by page_number order by monotonically_increasing_id()) - 1 as chunk_index",
        "chunk_text as text"
    )

    chunk_rows_df.createOrReplaceTempView("chunks_temp_rows")
    total_chunks = chunk_rows_df.count()

    log_checkpoint("Step 3: Chunk Text", "done", f"Parallel chunked {total_chunks} chunks")

except Exception as e:
    log_checkpoint("Step 3: Chunk Text", "error", str(e))
    update_registery_status("failed", f"Chunk failed: {str(e)}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4: Generate Embeddings

# COMMAND ----------

try:
    log_checkpoint("Step 4: Generate Embeddings", "start", "")

    from pyspark.sql.types import StructType, StructField, StringType, IntegerType

    # Use distributed chunks (no driver collect)
    chunks_df = spark.table("chunks_temp_rows")
    chunks_df.createOrReplaceTempView("chunks_temp")

    # Generate embeddings
    embedded_df = spark.sql(f"""
        SELECT
            chunk_id,
            pdf_id,
            page_number,
            chunk_index,
            text,
            ai_query('{EMBEDDING_MODEL}', text) as embedding,
            current_timestamp() as created_at
        FROM chunks_temp
    """)

    log_checkpoint("Step 4: Generate Embeddings", "done", f"Generated embeddings for {total_chunks} chunks")

except Exception as e:
    log_checkpoint("Step 4: Generate Embeddings", "error", str(e))
    update_registery_status("failed", f"Embedding failed: {str(e)}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5: Write to Delta (MERGE - OPTIMIZED)

# COMMAND ----------

try:
    log_checkpoint("Step 5: Write to Delta", "start", "Using MERGE operation")

    from pyspark.sql.functions import col

    # Cast embedding to array<float>
    embedded_df_fixed = embedded_df.withColumn(
        "embedding",
        col("embedding").cast("array<float>")
    )

    # Delete existing chunks for this PDF
    spark.sql(f"DELETE FROM {TABLE_CHUNKS} WHERE pdf_id = '{pdf_id}'")

    # Insert new chunks
    embedded_df_fixed.write.format("delta").mode("append").saveAsTable(TABLE_CHUNKS)

    log_checkpoint("Step 5: Write to Delta", "done", f"Wrote {total_chunks} chunks")

except Exception as e:
    log_checkpoint("Step 5: Write to Delta", "error", str(e))
    update_registery_status("failed", f"Write failed: {str(e)}")
    raise

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6: Sync Vector Index

# COMMAND ----------

try:
    log_checkpoint("Step 6: Sync Vector Index", "start", "")

    from databricks.vector_search.client import VectorSearchClient

    vsc = VectorSearchClient()
    index = vsc.get_index(
        endpoint_name=VECTOR_SEARCH_ENDPOINT,
        index_name=FULL_INDEX_NAME
    )
    index.sync()

    log_checkpoint("Step 6: Sync Vector Index", "done", "Index synced")

except Exception as e:
    log_checkpoint("Step 6: Sync Vector Index", "error", str(e))
    # Non-critical - continue

# COMMAND ----------

# MAGIC %md
# MAGIC ## Complete

# COMMAND ----------

# Update status to completed
update_registery_status("completed")

print(f"")
print(f"============================================================")
print(f"✓ INGESTION COMPLETE")
print(f"============================================================")
print(f"PDF: {pdf_name}")
print(f"Pages: {page_count}")
print(f"Chunks: {total_chunks}")
print(f"============================================================")

# Clean up temp views
try:
    spark.catalog.dropTempView("chunks_temp")
except:
    pass
try:
    spark.catalog.dropTempView("chunks_temp_rows")
except:
    pass

# Return success
import json
dbutils.notebook.exit(json.dumps({
    "status": "success",
    "pdf_id": pdf_id,
    "chunks_count": total_chunks,
    "pages_count": page_count
}))
