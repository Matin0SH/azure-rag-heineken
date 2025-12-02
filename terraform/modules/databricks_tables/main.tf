# ===========================
# DATABRICKS TABLES MODULE
# ===========================
# Purpose: Create all Delta tables with proper schemas
# Creates 5 tables for the RAG application

# ===========================
# TABLE 1: pdf_registery
# ===========================
# Tracks PDF upload and processing status
resource "databricks_sql_table" "pdf_registery" {
  catalog_name = var.catalog_name
  schema_name  = var.schema_name
  name         = "pdf_registery"
  table_type   = "MANAGED"
  data_source_format = "DELTA"
  storage_location   = ""  # Managed table, Databricks handles storage

  comment = "Tracks PDF upload and processing status"

  column {
    name     = "pdf_id"
    type     = "STRING"
    comment  = "Unique identifier for PDF"
  }

  column {
    name     = "pdf_name"
    type     = "STRING"
    comment  = "Original filename of PDF"
  }

  column {
    name     = "file_path"
    type     = "STRING"
    comment  = "Path to PDF in volume"
  }

  column {
    name     = "upload_date"
    type     = "TIMESTAMP"
    comment  = "When PDF was uploaded"
  }

  column {
    name     = "processing_status"
    type     = "STRING"
    comment  = "Status: pending, processing, completed, failed"
  }

  column {
    name     = "processed_date"
    type     = "TIMESTAMP"
    nullable = true
    comment  = "When processing completed"
  }

  column {
    name     = "error_message"
    type     = "STRING"
    nullable = true
    comment  = "Error message if processing failed"
  }
}

# ===========================
# TABLE 2: chunks_embedded
# ===========================
# Text chunks with embeddings for vector search
resource "databricks_sql_table" "chunks_embedded" {
  catalog_name = var.catalog_name
  schema_name  = var.schema_name
  name         = "chunks_embedded"
  table_type   = "MANAGED"
  data_source_format = "DELTA"
  storage_location   = ""

  comment = "Text chunks with embeddings for vector search"

  column {
    name     = "chunk_id"
    type     = "STRING"
    comment  = "Unique identifier for chunk"
  }

  column {
    name     = "pdf_id"
    type     = "STRING"
    comment  = "Link to pdf_registery"
  }

  column {
    name     = "page_number"
    type     = "INT"
    comment  = "Page number in PDF (1-indexed)"
  }

  column {
    name     = "chunk_index"
    type     = "INT"
    comment  = "Chunk index within page"
  }

  column {
    name     = "text"
    type     = "STRING"
    comment  = "Chunk text content"
  }

  column {
    name     = "embedding"
    type     = "ARRAY<FLOAT>"
    comment  = "Embedding vector (1024 dimensions for databricks-gte-large-en)"
  }

  column {
    name     = "created_at"
    type     = "TIMESTAMP"
    comment  = "When chunk was created"
  }
}

# ===========================
# TABLE 3: page_screenshots
# ===========================
# Page screenshot metadata
resource "databricks_sql_table" "page_screenshots" {
  catalog_name = var.catalog_name
  schema_name  = var.schema_name
  name         = "page_screenshots"
  table_type   = "MANAGED"
  data_source_format = "DELTA"
  storage_location   = ""

  comment = "Page screenshot metadata and file paths"

  column {
    name     = "page_id"
    type     = "STRING"
    comment  = "Unique identifier for page"
  }

  column {
    name     = "pdf_id"
    type     = "STRING"
    comment  = "Link to pdf_registery"
  }

  column {
    name     = "page_number"
    type     = "INT"
    comment  = "Page number in PDF"
  }

  column {
    name     = "screenshot_path"
    type     = "STRING"
    comment  = "Path to screenshot image in volume"
  }

  column {
    name     = "created_at"
    type     = "TIMESTAMP"
    comment  = "When screenshot was created"
  }
}

# ===========================
# TABLE 4: document_summaries
# ===========================
# Technical and Operator summaries (2 per PDF)
resource "databricks_sql_table" "document_summaries" {
  catalog_name = var.catalog_name
  schema_name  = var.schema_name
  name         = "document_summaries"
  table_type   = "MANAGED"
  data_source_format = "DELTA"
  storage_location   = ""

  comment = "Document summaries (technical and operator versions)"

  column {
    name     = "summary_id"
    type     = "STRING"
    comment  = "Unique identifier for summary"
  }

  column {
    name     = "pdf_id"
    type     = "STRING"
    comment  = "Link to pdf_registery"
  }

  column {
    name     = "pdf_name"
    type     = "STRING"
    comment  = "PDF filename for reference"
  }

  column {
    name     = "summary_type"
    type     = "STRING"
    comment  = "Type: 'technical' or 'operator'"
  }

  column {
    name     = "summary_chunks"
    type     = "ARRAY<STRING>"
    comment  = "Array of 15-45 detailed summary chunks (hierarchical MAP-REDUCE level 2)"
  }

  column {
    name     = "num_chunks"
    type     = "INT"
    comment  = "Number of summary chunks"
  }

  column {
    name     = "total_pages"
    type     = "INT"
    comment  = "Total pages in PDF"
  }

  column {
    name     = "total_chunks"
    type     = "INT"
    comment  = "Total chunks processed"
  }

  column {
    name     = "total_batches"
    type     = "INT"
    comment  = "Total batches in MAP phase"
  }

  column {
    name     = "reduce_levels"
    type     = "INT"
    comment  = "Number of reduction levels (always 2)"
  }

  column {
    name     = "processing_model"
    type     = "STRING"
    comment  = "LLM model used for summarization"
  }

  column {
    name     = "processing_time_seconds"
    type     = "FLOAT"
    nullable = true
    comment  = "Time taken to generate summary"
  }

  column {
    name     = "created_at"
    type     = "TIMESTAMP"
    comment  = "When summary was created"
  }
}

# ===========================
# TABLE 5: operator_questions
# ===========================
# Multiple choice questions for operator training (60-80 per PDF)
resource "databricks_sql_table" "operator_questions" {
  catalog_name = var.catalog_name
  schema_name  = var.schema_name
  name         = "operator_questions"
  table_type   = "MANAGED"
  data_source_format = "DELTA"
  storage_location   = ""

  comment = "Multiple choice questions for operator training"

  column {
    name     = "question_id"
    type     = "STRING"
    comment  = "Unique identifier for question"
  }

  column {
    name     = "pdf_id"
    type     = "STRING"
    comment  = "Link to pdf_registery"
  }

  column {
    name     = "pdf_name"
    type     = "STRING"
    comment  = "PDF filename for reference"
  }

  column {
    name     = "question_number"
    type     = "INT"
    comment  = "Question number (1-70) for ordering"
  }

  column {
    name     = "question_text"
    type     = "STRING"
    comment  = "The question text"
  }

  column {
    name     = "option_a"
    type     = "STRING"
    comment  = "Choice A text"
  }

  column {
    name     = "option_b"
    type     = "STRING"
    comment  = "Choice B text"
  }

  column {
    name     = "option_c"
    type     = "STRING"
    comment  = "Choice C text"
  }

  column {
    name     = "option_d"
    type     = "STRING"
    comment  = "Choice D text"
  }

  column {
    name     = "correct_answer"
    type     = "STRING"
    comment  = "Correct answer: A, B, C, or D"
  }

  column {
    name     = "explanation"
    type     = "STRING"
    comment  = "Explanation/reason for the correct answer"
  }

  column {
    name     = "difficulty_level"
    type     = "STRING"
    comment  = "Difficulty: easy, medium, hard"
  }

  column {
    name     = "topic_category"
    type     = "STRING"
    comment  = "Category: safety, operation, maintenance, troubleshooting, etc."
  }

  column {
    name     = "page_references"
    type     = "ARRAY<INT>"
    nullable = true
    comment  = "Page numbers this question relates to"
  }

  column {
    name     = "chunk_references"
    type     = "ARRAY<STRING>"
    nullable = true
    comment  = "Chunk IDs used to generate this question"
  }

  column {
    name     = "created_at"
    type     = "TIMESTAMP"
    comment  = "When question was created"
  }
}
