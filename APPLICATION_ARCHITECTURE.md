# NextLevel RAG Application - Complete Architecture

## Overview

A complete RAG (Retrieval-Augmented Generation) system for PDF document processing, deployed on Databricks.

---

## 🏗️ Application Structure

### 1. **API Layer** (`api/`)

FastAPI REST API with 3 main endpoints:

#### Endpoints:
- **POST /api/v1/ingest-pdf** - Upload and process PDFs
- **POST /api/v1/generate-summary** - Generate technical summaries
- **POST /api/v1/generate-questions** - Generate training questions
- **GET /api/v1/jobs/{job_run_id}/status** - Check job status

#### Components:
```
api/
├── app.yaml                    # Databricks Apps config ✅
├── requirements.txt            # Python dependencies
├── .env                        # Local development config
├── app/
│   ├── main.py                 # FastAPI application
│   ├── config/
│   │   └── settings.py         # Pydantic settings (reads .env)
│   ├── routers/
│   │   ├── ingest.py           # PDF upload & ingestion
│   │   ├── summarization.py    # Summary generation
│   │   ├── question_generation.py  # Question generation
│   │   └── status.py           # Job status checking
│   ├── services/
│   │   ├── databricks_client.py       # Databricks SDK wrapper
│   │   ├── pdf_service.py             # PDF processing logic
│   │   ├── summarization_service.py   # Summary business logic
│   │   └── question_generation_service.py  # Questions business logic
│   ├── models/
│   │   └── schemas.py          # Pydantic request/response models
│   └── utils/
│       └── auth.py             # API key authentication
```

#### Configuration (from `settings.py`):
- **DATABRICKS_HOST**: Workspace URL
- **DATABRICKS_TOKEN**: Authentication token (secret)
- **API_KEY**: API endpoint authentication (secret)
- **Job IDs**: INGEST_JOB_ID, SUMMARIZATION_JOB_ID, QUESTION_GENERATION_JOB_ID
- **Unity Catalog**: CATALOG_NAME, SCHEMA_NAME, SQL_WAREHOUSE_ID
- **Tables**: TABLE_CHUNKS, TABLE_REGISTRY, TABLE_SCREENSHOTS
- **Volumes**: VOLUME_RAW_PDFS, VOLUME_SCREENSHOTS
- **Vector Search**: VECTOR_SEARCH_ENDPOINT, VECTOR_INDEX_NAME
- **Models**: EMBEDDING_MODEL

---

### 2. **Agent Layer** (`agents/`)

LangGraph-based processing agents with MAP-REDUCE pattern:

#### A. Summarization Agent (`agents/summarization/`)

**Purpose**: Extract technical information from PDFs (NOT summarize)

**Architecture**:
```
summarization/
├── __init__.py
├── state.py           # State schema (TypedDict)
├── prompts.py         # MAP/REDUCE prompts
├── nodes.py           # Processing nodes
├── graph.py           # LangGraph workflow
└── utils.py           # Helper functions
```

**Workflow**:
1. **regroup_pages**: Combine chunks → pages (Spark SQL)
2. **create_batches**: Group pages → batches (5 pages each)
3. **map_extract**: Extract technical info (parallel, Spark ai_query)
4. **reduce_combine**: Hierarchical 3-to-1 (level 1 → level 2, STOP)

**Key Features**:
- Uses Spark SQL `ai_query` for parallel processing
- EXTRACTION philosophy (preserve completeness, not reduce)
- Outputs 15-45 summary chunks
- Model: `databricks-llama-4-maverick`

**Prompts** (`prompts.py`):
- **TECH_MAP_SYSTEM**: Extract technical specifications verbatim
- **TECH_REDUCE_SYSTEM**: Deduplicate and organize extractions
- Target audience: Engineers/maintenance staff
- Format: Markdown with sections, procedures, parameters, warnings

#### B. Question Generation Agent (`agents/question_generation/`)

**Purpose**: Generate multiple-choice training questions

**Architecture**:
```
question_generation/
├── __init__.py
├── state.py           # State schema (TypedDict)
├── prompts.py         # MAP/REDUCE prompts
├── nodes.py           # Processing nodes (with JSON cleaning)
├── graph.py           # LangGraph workflow
└── nodes_new.py       # (backup/old version)
```

**Workflow**:
1. **regroup_pages**: Combine chunks → pages (Spark SQL)
2. **create_batches**: Group pages → batches (5 pages each)
3. **map_generate**: Generate 5-7 questions/batch (parallel, Spark ai_query)
4. **reduce_combine**: Hierarchical 3-to-1 (level 1 → level 2, STOP)

**Key Features**:
- Uses Spark SQL `ai_query` for parallel processing
- JSON cleaning with `JSONDecoder` (handles malformed LLM output)
- Outputs 15-45 question chunks
- Model: `databricks-llama-4-maverick`

**Prompts** (`prompts.py`):
- **MAP_SYSTEM**: Generate practical multiple-choice questions
- **REDUCE_SYSTEM**: Deduplicate, merge similar, balance difficulty
- Target audience: Machine operators (8th-grade reading level)
- Format: JSON with question_text, options, correct_answer, explanation, difficulty, topic, page_references

**JSON Cleaning** (`nodes.py`):
- `clean_llm_json_output()`: Extract valid JSON from LLM output
- Uses `json.JSONDecoder.raw_decode()` for robust parsing
- Handles `<|python_start|>` tokens and extra text
- Fallback: Keep original if cleaning fails

---

### 3. **Job Layer** (`jobs/`)

Databricks notebook jobs that orchestrate agents:

#### A. Ingestion Pipeline
- **Job ID**: 732673104250690
- **Notebook**: `jobs/ingest_pipeline.py`
- **Purpose**: Process PDF → chunks → embeddings → vector index
- **Steps**:
  1. Extract text and images from PDF
  2. Split into chunks with metadata
  3. Generate embeddings (databricks-gte-large-en)
  4. Store in Unity Catalog tables
  5. Index in Vector Search

#### B. Summarization Pipeline
- **Job ID**: 754789764730261
- **Notebook**: `jobs/summarization_pipeline.py`
- **Purpose**: Generate technical summaries
- **Steps**:
  1. Fetch chunks from Unity Catalog
  2. Run summarization agent (MAP-REDUCE)
  3. Save to `document_summaries` table
- **Output**: 15-45 summary chunks + full text

#### C. Question Generation Pipeline
- **Job ID**: 813011324430281
- **Notebook**: `jobs/question_generation_pipeline.py`
- **Purpose**: Generate training questions
- **Steps**:
  1. Fetch chunks from Unity Catalog
  2. Run question generation agent (MAP-REDUCE)
  3. Clean JSON outputs
  4. Save to `operator_questions` table
- **Output**: 15-45 question chunks (JSON arrays)

---

### 4. **Infrastructure Layer** (`terraform/`)

Infrastructure as Code for Databricks resources:

```
terraform/
├── main.tf                    # Main configuration
├── variables.tf               # Input variables
├── outputs.tf                 # Output values
├── terraform.tfvars          # Variable values
└── modules/
    ├── databricks_foundation/  # Catalog, schema, volumes
    ├── databricks_tables/      # Unity Catalog tables
    ├── databricks_jobs/        # Job definitions
    └── databricks_vector/      # Vector Search index
```

**Resources Created**:
- Unity Catalog: `heineken_test_workspace.nextlevel-rag`
- Tables: `pdf_registery`, `chunks_embedded`, `document_summaries`, `operator_questions`, `page_screenshots`
- Volumes: `raw_pdfs`, `screenshots`
- Jobs: Ingest, Summarization, Question Generation
- Vector Search: `chunks_embedded_index` on endpoint `heineken-vdb`

---

## 🔄 Data Flow

### Complete Processing Pipeline:

```
1. PDF Upload (API)
   ↓
2. Ingestion Job (Databricks)
   - Extract text/images
   - Split into chunks
   - Generate embeddings
   - Store in Unity Catalog
   ↓
3A. Summarization Job (Parallel)        3B. Question Generation Job (Parallel)
    - Fetch chunks                           - Fetch chunks
    - MAP: Extract tech info (135 batches)  - MAP: Generate questions (135 batches)
    - REDUCE L1: 135 → 45                   - REDUCE L1: 135 → 45
    - REDUCE L2: 45 → 15 (STOP)            - REDUCE L2: 45 → 15 (STOP)
    - Save to document_summaries            - Save to operator_questions
    ↓                                        ↓
4. Results Available via API
   - GET status
   - Retrieve summaries/questions
```

---

## 📊 Data Models

### Unity Catalog Tables:

#### 1. `pdf_registery`
- pdf_id (STRING)
- pdf_name (STRING)
- file_size_mb (FLOAT)
- total_pages (INT)
- processing_status (STRING)
- uploaded_at (TIMESTAMP)
- processed_at (TIMESTAMP)

#### 2. `chunks_embedded`
- chunk_id (STRING)
- pdf_id (STRING)
- page_number (INT)
- chunk_index (INT)
- text (STRING)
- embedding (ARRAY<FLOAT>)
- created_at (TIMESTAMP)

#### 3. `document_summaries`
- summary_id (STRING)
- pdf_id (STRING)
- pdf_name (STRING)
- summary_type (STRING)
- summary_chunks (ARRAY<STRING>)  ← 15-45 chunks
- summary_text_full (STRING)
- num_chunks (INT)
- total_pages (INT)
- total_chunks (INT)
- total_batches (INT)
- reduce_levels (INT)
- processing_model (STRING)
- processing_time_seconds (FLOAT)
- created_at (TIMESTAMP)

#### 4. `operator_questions`
- questions_id (STRING)
- pdf_id (STRING)
- pdf_name (STRING)
- question_chunks (ARRAY<STRING>)  ← 15-45 chunks (JSON)
- questions_full_text (STRING)
- num_question_chunks (INT)
- total_questions (INT)
- total_pages (INT)
- total_chunks (INT)
- total_batches (INT)
- reduce_levels (INT)
- processing_model (STRING)
- processing_time_seconds (FLOAT)
- created_at (TIMESTAMP)

#### 5. `page_screenshots`
- screenshot_id (STRING)
- pdf_id (STRING)
- page_number (INT)
- screenshot_path (STRING)
- created_at (TIMESTAMP)

---

## 🔐 Security & Configuration

### Secrets Required:
1. **DATABRICKS_TOKEN** - Databricks API authentication
2. **API_KEY** - REST API endpoint authentication

### Environment Variables (23 total):

**Auto-injected by Databricks Apps:**
- DATABRICKS_HOST
- DATABRICKS_WORKSPACE_ID
- DATABRICKS_APP_PORT

**From Secrets:**
- DATABRICKS_TOKEN
- API_KEY

**Job IDs:**
- INGEST_JOB_ID
- SUMMARIZATION_JOB_ID
- QUESTION_GENERATION_JOB_ID

**Unity Catalog:**
- CATALOG_NAME
- SCHEMA_NAME
- SQL_WAREHOUSE_ID
- TABLE_CHUNKS
- TABLE_REGISTRY
- TABLE_SCREENSHOTS
- VOLUME_RAW_PDFS
- VOLUME_SCREENSHOTS

**Vector Search:**
- VECTOR_SEARCH_ENDPOINT
- VECTOR_INDEX_NAME

**Models:**
- EMBEDDING_MODEL

**App Settings:**
- ALLOWED_ORIGINS
- MAX_FILE_SIZE_MB
- ALLOWED_EXTENSIONS

---

## 🎯 Key Technologies

- **Framework**: FastAPI (Python 3.11+)
- **LLM Orchestration**: LangGraph
- **Data Processing**: Apache Spark SQL (Databricks)
- **LLM**: databricks-llama-4-maverick (via ai_query)
- **Embeddings**: databricks-gte-large-en
- **Vector DB**: Databricks Vector Search
- **Storage**: Unity Catalog (Delta Lake)
- **Infrastructure**: Terraform
- **Deployment**: Databricks Apps (serverless)
- **SDK**: databricks-sdk-py

---

## 📈 Processing Scale

Example: 674-page PDF

### Ingestion:
- Pages: 674
- Chunks: ~1,400 (chunk size: 1000 chars, overlap: 200)
- Processing time: ~10-15 minutes

### Summarization:
- Input: 1,400 chunks → 674 pages
- Batches: 135 (5 pages each)
- MAP: 135 extractions (parallel)
- REDUCE L1: 135 → 45 (3-to-1)
- REDUCE L2: 45 → 15 (3-to-1) → STOP
- Output: 15 summary chunks
- Processing time: ~20-30 minutes

### Question Generation:
- Input: 1,400 chunks → 674 pages
- Batches: 135 (5 pages each)
- MAP: 135 batches × 6 questions = ~800 questions (parallel)
- REDUCE L1: 135 → 45 (deduplicate, merge)
- REDUCE L2: 45 → 15 → STOP
- Output: 15 question chunks (~750-900 total questions)
- Processing time: ~20-30 minutes

---

## 🚀 Deployment Strategy

### Current Status: ✅ Ready for Databricks Apps

**Phase 1**: Local Development (✅ Complete)
- FastAPI app working locally
- All 3 endpoints functional
- Terraform infrastructure deployed
- All jobs operational

**Phase 2**: Databricks Apps Setup (🔄 In Progress)
- [✅] Step 1: Created app.yaml
- [🔄] Step 2: Move secrets to Databricks
- [⏳] Step 3: Update main.py for Databricks Apps
- [⏳] Step 4: Test locally with Databricks env vars
- [⏳] Step 5: Deploy to development workspace
- [⏳] Step 6: Set up CI/CD (GitHub Actions)
- [⏳] Step 7: Deploy to production

**Phase 3**: UI Development (⏳ Planned)
- Frontend application (discussed later)
- User interface for PDF upload
- View summaries and questions
- Job monitoring dashboard

---

## 💡 Design Decisions

### Why MAP-REDUCE?
- Parallel processing (135 batches processed simultaneously)
- Better quality (each batch focused on 5 pages)
- Scalable (handles documents of any size)
- Cost-effective (Spark SQL ai_query optimized for Databricks)

### Why Stop at Level 2?
- Preserves detail and variety
- 15-45 chunks perfect for chunked retrieval
- Avoids over-reduction (single summary loses context)
- Better for RAG (more specific chunks to retrieve)

### Why Spark SQL ai_query?
- Native Databricks function (no external API calls)
- Optimized for parallel processing
- Handles large-scale workloads
- Built-in retry and error handling

### Why JSON Cleaning?
- LLM (llama-4-maverick) adds extra text after JSON
- `JSONDecoder.raw_decode()` extracts valid JSON portion
- Fallback to original prevents data loss
- Ensures database integrity

---

## 🎓 Next Steps

1. **Complete Databricks Apps Deployment** (Current)
   - Set up secret scopes
   - Update main.py
   - Deploy to dev workspace

2. **UI Development** (Future)
   - Framework selection (React/Streamlit/Gradio)
   - Integration with FastAPI backend
   - User-friendly interface

3. **Production Hardening** (Future)
   - Monitoring and alerting
   - Cost optimization
   - Performance tuning
   - Error handling improvements

---

**Status**: Production-ready backend, ready for Databricks Apps deployment and UI development.
