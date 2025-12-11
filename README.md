# Databricks RAG Infrastructure - Heineken Project

A production-ready **Retrieval-Augmented Generation (RAG)** system built on Azure Databricks with Unity Catalog, featuring intelligent document processing, vector search, and automated summarization pipelines.

---

## Overview

This infrastructure implements a sophisticated RAG system designed for processing technical PDF documents (manuals, specifications, training materials) and making them queryable through semantic search. The system automatically:

- Ingests and tracks PDF documents
- Extracts and chunks text with embeddings
- Generates page screenshots for visual reference
- Creates dual-purpose summaries (technical + operator-friendly)
- Produces training questions for operator onboarding

**Tech Stack:**
- **Infrastructure:** Terraform (IaC)
- **Platform:** Azure Databricks with Unity Catalog
- **Storage:** Delta Lake tables (managed)
- **Search:** Databricks Vector Search (1024-dim embeddings)
- **Processing:** MAP-REDUCE hierarchical summarization
- **Embedding Model:** `databricks-gte-large-en`

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AZURE DATABRICKS                             │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                  UNITY CATALOG STRUCTURE                       │ │
│  │                                                                 │ │
│  │  CATALOG: heineken_test_workspace                              │ │
│  │    └── SCHEMA: nextlevel-rag                                   │ │
│  │          ├── Volumes (Storage)                                 │ │
│  │          │     ├── raw_pdfs/                                   │ │
│  │          │     └── screenshots/                                │ │
│  │          │                                                      │ │
│  │          └── Tables (Delta Format)                             │ │
│  │                ├── pdf_registery                               │ │
│  │                ├── chunks_embedded [VECTOR INDEX ENABLED]      │ │
│  │                ├── page_screenshots                            │ │
│  │                ├── document_summaries                          │ │
│  │                └── operator_questions                          │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │                   PROCESSING PIPELINES                         │ │
│  │                                                                 │ │
│  │  Job 1: Ingestion Pipeline                                     │ │
│  │    → Extract PDF → Chunk Text → Generate Embeddings           │ │
│  │    → Capture Screenshots → Update Registry                     │ │
│  │                                                                 │ │
│  │  Job 2: Summarization Pipeline (MAP-REDUCE)                   │ │
│  │    → Technical Summary (expert-level)                          │ │
│  │    → Operator Summary (training-focused)                       │ │
│  │                                                                 │ │
│  │  Job 3: Question Generation Pipeline (MAP-REDUCE)             │ │
│  │    → Multiple-choice questions for operator training           │ │
│  └───────────────────────────────────────────────────────────────┘ │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐ │
│  │              VECTOR SEARCH INFRASTRUCTURE                      │ │
│  │                                                                 │ │
│  │  Endpoint: heineken-vdb                                        │ │
│  │    └── Index: chunks_vector_index                              │ │
│  │          └── Source: chunks_embedded.embedding                 │ │
│  │              (1024-dimensional vectors)                        │ │
│  └───────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Data Model - Unity Catalog Structure

### Complete Schema Visualization

```
UNITY CATALOG: heineken_test_workspace
│
├── SCHEMA: nextlevel-rag
│   │   Properties: environment, managed_by=terraform, project=databricks-rag
│   │
│   ├── VOLUMES (Storage)
│   │   ├── raw_pdfs      → Stores uploaded PDF files
│   │   └── screenshots   → Stores PDF page screenshot images
│   │
│   └── TABLES (Delta Format - Managed)
│       │
│       ├── 1. pdf_registery (PDF Tracking & Status)
│       │   ├── pdf_id                STRING       [PRIMARY]
│       │   ├── pdf_name              STRING
│       │   ├── file_path             STRING       → Points to raw_pdfs volume
│       │   ├── upload_date           TIMESTAMP
│       │   ├── processing_status     STRING       (pending/processing/completed/failed)
│       │   ├── processed_date        TIMESTAMP    [NULLABLE]
│       │   └── error_message         STRING       [NULLABLE]
│       │
│       ├── 2. chunks_embedded (Text Chunks + Embeddings) [⚡ VECTOR INDEXED]
│       │   ├── chunk_id              STRING       [PRIMARY]
│       │   ├── pdf_id                STRING       [FOREIGN KEY → pdf_registery]
│       │   ├── page_number           INT
│       │   ├── chunk_index           INT
│       │   ├── text                  STRING
│       │   ├── embedding             ARRAY<FLOAT> (1024 dimensions)
│       │   └── created_at            TIMESTAMP
│       │       │
│       │       └─→ [VECTOR INDEX: chunks_vector_index - Enables semantic search]
│       │
│       ├── 3. page_screenshots (Visual References)
│       │   ├── page_id               STRING       [PRIMARY]
│       │   ├── pdf_id                STRING       [FOREIGN KEY → pdf_registery]
│       │   ├── page_number           INT
│       │   ├── screenshot_path       STRING       → Points to screenshots volume
│       │   └── created_at            TIMESTAMP
│       │
│       ├── 4. document_summaries (Technical & Operator Summaries)
│       │   ├── summary_id            STRING       [PRIMARY]
│       │   ├── pdf_id                STRING       [FOREIGN KEY → pdf_registery]
│       │   ├── pdf_name              STRING
│       │   ├── summary_type          STRING       ('technical' | 'operator')
│       │   ├── summary_chunks        ARRAY<STRING> (15-45 chunks via MAP-REDUCE)
│       │   ├── summary_text_full     STRING       (concatenated full text)
│       │   ├── num_chunks            INT
│       │   ├── total_pages           INT
│       │   ├── total_chunks          INT
│       │   ├── total_batches         INT
│       │   ├── reduce_levels         INT          (hierarchical level = 2)
│       │   ├── processing_model      STRING       (LLM model name)
│       │   ├── processing_time_seconds FLOAT      [NULLABLE]
│       │   └── created_at            TIMESTAMP
│       │
│       └── 5. operator_questions (Training Questions - MCQ Format)
│           ├── questions_id          STRING       [PRIMARY]
│           ├── pdf_id                STRING       [FOREIGN KEY → pdf_registery]
│           ├── pdf_name              STRING
│           ├── question_chunks       ARRAY<STRING> (15-45 chunks - JSON strings)
│           ├── questions_full_text   STRING       (concatenated full text)
│           ├── num_question_chunks   INT
│           ├── total_questions       INT
│           ├── total_pages           INT
│           ├── total_chunks          INT
│           ├── total_batches         INT
│           ├── reduce_levels         INT          (hierarchical level = 2)
│           ├── processing_model      STRING       (LLM model name)
│           ├── processing_time_seconds FLOAT      [NULLABLE]
│           └── created_at            TIMESTAMP
```

---

## Table Relationships & Data Flow

### Entity Relationship Diagram

```
pdf_registery (1:N relationships with all child tables)
    │
    ├──→ chunks_embedded       (1:N)  [One PDF → Many chunks]
    │      └─→ Vector Index (for semantic search)
    │
    ├──→ page_screenshots      (1:N)  [One PDF → Many pages]
    │
    ├──→ document_summaries    (1:2)  [One PDF → 2 summaries: technical + operator]
    │
    └──→ operator_questions    (1:1)  [One PDF → One question set]
```

### Data Processing Pipeline

```
1. PDF Upload
   └─→ pdf_registery (status: pending)
        │
        ├─→ Ingestion Job Triggered
        │    ├─→ Extract text → chunks_embedded
        │    ├─→ Generate embeddings (1024-dim)
        │    └─→ Capture screenshots → page_screenshots
        │
        ├─→ Summarization Job Triggered
        │    ├─→ MAP phase: Batch chunks
        │    ├─→ REDUCE phase: Hierarchical summarization (2 levels)
        │    ├─→ Generate technical summary → document_summaries
        │    └─→ Generate operator summary → document_summaries
        │
        └─→ Question Generation Job Triggered
             ├─→ MAP phase: Batch chunks
             ├─→ REDUCE phase: Hierarchical generation (2 levels)
             └─→ Generate MCQ questions → operator_questions

2. Vector Index Sync
   └─→ chunks_embedded changes trigger automatic index update
        └─→ chunks_vector_index (ready for similarity search)

3. Query Time (RAG)
   └─→ User query → Vector Search → Top-K chunks → LLM → Response
        └─→ Return with page_screenshots for visual context
```

---

## Detailed Component Breakdown

### 1. PDF Registry Table (`pdf_registery`)

**Purpose:** Central tracking system for all PDF documents and their processing lifecycle.

| Column | Type | Description | Notes |
|--------|------|-------------|-------|
| `pdf_id` | STRING | Unique identifier | Primary key, UUID format |
| `pdf_name` | STRING | Original filename | User-visible name |
| `file_path` | STRING | Storage path | References `raw_pdfs` volume |
| `upload_date` | TIMESTAMP | Upload timestamp | Auto-generated |
| `processing_status` | STRING | Current status | Values: pending, processing, completed, failed |
| `processed_date` | TIMESTAMP | Completion timestamp | Nullable, set on completion |
| `error_message` | STRING | Error details | Nullable, populated on failure |

**Key Features:**
- Acts as the parent table for all relationships
- Enables status tracking and error handling
- Supports retry logic for failed processing

---

### 2. Chunks Embedded Table (`chunks_embedded`)

**Purpose:** Stores text chunks with vector embeddings for semantic search (core RAG component).

| Column | Type | Description | Dimensions |
|--------|------|-------------|------------|
| `chunk_id` | STRING | Unique chunk identifier | UUID |
| `pdf_id` | STRING | Parent PDF reference | FK to pdf_registery |
| `page_number` | INT | Source page (1-indexed) | - |
| `chunk_index` | INT | Position within page | - |
| `text` | STRING | Chunk content | Variable length |
| `embedding` | ARRAY<FLOAT> | Vector representation | **1024 dimensions** |
| `created_at` | TIMESTAMP | Creation timestamp | - |

**Key Features:**
- **Vector Index Enabled:** `chunks_vector_index` on `embedding` column
- **Embedding Model:** `databricks-gte-large-en` (1024-dimensional)
- **Search Capability:** Supports similarity search for RAG queries
- **Optimized for:** Semantic retrieval with low latency

---

### 3. Page Screenshots Table (`page_screenshots`)

**Purpose:** Stores visual references for each PDF page to provide context alongside text results.

| Column | Type | Description |
|--------|------|-------------|
| `page_id` | STRING | Unique page identifier |
| `pdf_id` | STRING | Parent PDF reference |
| `page_number` | INT | Page number |
| `screenshot_path` | STRING | Image file path in `screenshots` volume |
| `created_at` | TIMESTAMP | Creation timestamp |

**Key Features:**
- Enables visual context in RAG responses
- Useful for technical diagrams, charts, and schematics
- Stored as image files in dedicated volume

---

### 4. Document Summaries Table (`document_summaries`)

**Purpose:** Hierarchical MAP-REDUCE summaries for different audiences (technical experts vs operators).

| Column | Type | Description |
|--------|------|-------------|
| `summary_id` | STRING | Unique summary identifier |
| `pdf_id` | STRING | Parent PDF reference |
| `pdf_name` | STRING | PDF filename (denormalized) |
| `summary_type` | STRING | Audience type: `'technical'` or `'operator'` |
| `summary_chunks` | ARRAY<STRING> | 15-45 hierarchical summary chunks |
| `summary_text_full` | STRING | Concatenated full summary |
| `num_chunks` | INT | Number of summary chunks |
| `total_pages` | INT | Source PDF page count |
| `total_chunks` | INT | Total chunks processed |
| `total_batches` | INT | MAP phase batches |
| `reduce_levels` | INT | Reduction depth (always 2) |
| `processing_model` | STRING | LLM model used |
| `processing_time_seconds` | FLOAT | Generation time |
| `created_at` | TIMESTAMP | Creation timestamp |

**Summary Types:**
1. **Technical Summary:** Expert-level, detailed technical content
2. **Operator Summary:** Simplified, training-focused content for machine operators

**MAP-REDUCE Process:**
- **MAP Phase:** Split document into batches
- **REDUCE Phase 1:** Summarize each batch
- **REDUCE Phase 2:** Combine batch summaries into final chunks (15-45 chunks)

---

### 5. Operator Questions Table (`operator_questions`)

**Purpose:** Multiple-choice questions for operator training and assessment, generated via MAP-REDUCE.

| Column | Type | Description |
|--------|------|-------------|
| `questions_id` | STRING | Unique question set identifier |
| `pdf_id` | STRING | Parent PDF reference |
| `pdf_name` | STRING | PDF filename (denormalized) |
| `question_chunks` | ARRAY<STRING> | 15-45 question chunks (JSON format) |
| `questions_full_text` | STRING | Concatenated full question text |
| `num_question_chunks` | INT | Number of question chunks |
| `total_questions` | INT | Total count of all questions |
| `total_pages` | INT | Source PDF page count |
| `total_chunks` | INT | Total chunks processed |
| `total_batches` | INT | MAP phase batches |
| `reduce_levels` | INT | Reduction depth (always 2) |
| `processing_model` | STRING | LLM model used |
| `processing_time_seconds` | FLOAT | Generation time |
| `created_at` | TIMESTAMP | Creation timestamp |

**Question Format:**
- Multiple-choice questions (MCQ)
- Stored as JSON strings within chunks
- Covers key concepts from technical documentation
- Designed for operator onboarding and certification

---

## Processing Architecture

### MAP-REDUCE Hierarchical Processing

Both summarization and question generation use a **two-level hierarchical MAP-REDUCE** pattern:

```
Level 0: Source Document (chunks_embedded)
         ├─ chunk_1
         ├─ chunk_2
         ├─ ...
         └─ chunk_N

         ↓ MAP Phase (Batch grouping)

Level 1: Batch Summaries (10-20 batches)
         ├─ batch_summary_1 (chunks 1-50)
         ├─ batch_summary_2 (chunks 51-100)
         ├─ ...
         └─ batch_summary_M

         ↓ REDUCE Phase 1

Level 2: Final Output (15-45 chunks)
         ├─ final_chunk_1
         ├─ final_chunk_2
         ├─ ...
         └─ final_chunk_K

         ↓ Concatenation

Full Text: summary_text_full / questions_full_text
```

**Benefits:**
- Handles arbitrarily large documents
- Preserves hierarchical structure
- Maintains context across chunks
- Enables parallel processing

---

## Vector Search Infrastructure

### Endpoint Configuration

| Property | Value |
|----------|-------|
| **Endpoint Name** | `heineken-vdb` |
| **Index Name** | `chunks_vector_index` |
| **Source Table** | `heineken_test_workspace.nextlevel-rag.chunks_embedded` |
| **Embedding Column** | `embedding` |
| **Dimension** | 1024 |
| **Model** | `databricks-gte-large-en` |

### Search Capabilities

```python
# Example: Semantic similarity search
query = "How to calibrate the filling valve?"
results = vector_search(
    query=query,
    endpoint="heineken-vdb",
    index="chunks_vector_index",
    top_k=5
)

# Returns:
# - Top 5 most relevant chunks
# - Similarity scores
# - Associated metadata (pdf_id, page_number, etc.)
# - Can be enriched with screenshots for visual context
```

---

## Databricks Jobs (Processing Pipelines)

### Job 1: Ingestion Pipeline
- **Notebook Path:** `/Repos/Production/azure-rag-heineken/jobs/ingest_pipeline.py`
- **Purpose:** Extract text, generate embeddings, capture screenshots
- **Triggers:** Manual or event-driven (new PDF upload)
- **Outputs:** `chunks_embedded`, `page_screenshots`

### Job 2: Summarization Pipeline
- **Notebook Path:** `/Repos/Production/azure-rag-heineken/jobs/summarization_pipeline.py`
- **Purpose:** Generate technical and operator summaries (MAP-REDUCE)
- **Triggers:** After ingestion completes
- **Outputs:** `document_summaries` (2 rows per PDF)

### Job 3: Question Generation Pipeline
- **Notebook Path:** `/Repos/Production/azure-rag-heineken/jobs/question_generation_pipeline.py`
- **Purpose:** Generate training questions (MAP-REDUCE)
- **Triggers:** After ingestion completes
- **Outputs:** `operator_questions` (1 row per PDF)

---

## Infrastructure Components

### Terraform Modules

| Module | Purpose | Resources Created |
|--------|---------|-------------------|
| **databricks_foundation** | Core Unity Catalog setup | Schema, Volumes (raw_pdfs, screenshots) |
| **databricks_tables** | Delta table creation | 5 managed Delta tables |
| **databricks_vector** | Vector search setup | Vector endpoint, index configuration |
| **databricks_jobs** | Processing pipelines | 3 Databricks jobs |

### Azure Resources (Bootstrap)

| Resource | Name | Purpose |
|----------|------|---------|
| **Resource Group** | `rg-databricks-rag-dev` | Container for all resources |
| **Storage Account** | `stdatabricksragnew24` | Terraform state backend |
| **Storage Container** | `tfstate` | State file storage |
| **Key Vault** | `kv-databricks-rag-dev` | Secrets management |

---

## Technical Specifications

### Storage
- **Format:** Delta Lake (ACID transactions, time travel, schema evolution)
- **Management:** Fully managed by Databricks (automatic optimization)
- **Location:** Unity Catalog managed storage

### Compute
- **Runtime:** Databricks Runtime (with ML libraries)
- **Cluster:** Configurable (existing or new cluster for jobs)
- **Autoscaling:** Supported for cost optimization

### Security
- **Authentication:** Databricks Personal Access Token
- **Secrets:** Azure Key Vault integration
- **Access Control:** Unity Catalog permissions (catalog/schema/table level)

### Monitoring
- **Job Tracking:** Databricks Jobs UI
- **Table History:** Delta Lake time travel
- **Vector Index:** Sync status monitoring

---

## Key Design Decisions

### Why Unity Catalog?
- Centralized governance and access control
- Cross-workspace data sharing
- Audit logging and lineage tracking

### Why Delta Lake?
- ACID transactions for data reliability
- Time travel for debugging and rollback
- Schema evolution without downtime

### Why MAP-REDUCE for Summaries?
- Scalable to arbitrarily large documents
- Preserves hierarchical context
- Enables parallel processing for speed

### Why Dual Summaries?
- **Technical:** For engineers, maintenance teams (detailed, precise)
- **Operator:** For production floor staff (simplified, action-focused)

### Why Vector Search?
- Semantic understanding (not just keyword matching)
- Low-latency retrieval for real-time queries
- Integrates seamlessly with LLMs for RAG

---

## Data Lifecycle

```
┌─────────────┐
│ PDF Upload  │
└──────┬──────┘
       │
       ↓
┌──────────────────────┐
│  pdf_registery       │ ← Status: pending
│  (tracking starts)   │
└──────┬───────────────┘
       │
       ↓
┌──────────────────────┐
│  Ingestion Job       │ ← Status: processing
│  - Text extraction   │
│  - Chunking          │
│  - Embedding gen     │
│  - Screenshot capture│
└──────┬───────────────┘
       │
       ├─→ chunks_embedded (with vectors)
       └─→ page_screenshots
       │
       ↓
┌──────────────────────┐
│  Summarization Job   │
│  - Technical summary │
│  - Operator summary  │
└──────┬───────────────┘
       │
       └─→ document_summaries (2 rows)
       │
       ↓
┌──────────────────────┐
│  Question Gen Job    │
│  - MCQ generation    │
└──────┬───────────────┘
       │
       └─→ operator_questions (1 row)
       │
       ↓
┌──────────────────────┐
│  pdf_registery       │ ← Status: completed
│  (tracking complete) │
└──────────────────────┘
       │
       ↓
┌──────────────────────┐
│  Vector Index Sync   │
│  (automatic)         │
└──────────────────────┘
       │
       ↓
    ✅ Ready for RAG Queries
```

---

## Project Structure

```
heineken/
├── bootstrap/                    # Azure infrastructure foundation
│   ├── main.tf                   # Resource group, storage, key vault
│   ├── variables.tf
│   ├── outputs.tf
│   └── backend.tf
│
├── terraform/                    # Databricks resources
│   ├── main.tf                   # Root module orchestration
│   ├── variables.tf
│   ├── outputs.tf
│   │
│   └── modules/
│       ├── databricks_foundation/    # Unity Catalog + Volumes
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       │
│       ├── databricks_tables/        # Delta tables (5 tables)
│       │   ├── main.tf              # ← Detailed table schemas
│       │   ├── variables.tf
│       │   └── outputs.tf
│       │
│       ├── databricks_vector/        # Vector search setup
│       │   ├── main.tf
│       │   ├── variables.tf
│       │   └── outputs.tf
│       │
│       └── databricks_jobs/          # Processing pipelines (3 jobs)
│           ├── main.tf
│           ├── variables.tf
│           └── outputs.tf
│
└── README.md                     # ← You are here
```

---

## Repository Information

**Environment:** Development
**Region:** East US
**Databricks Workspace:** https://adb-420728015502334.14.azuredatabricks.net
**Azure Subscription:** Azure subscription 1 (`a51ac199-5e57-484e-b4ed-194abc9fa5f8`)

**Infrastructure as Code:**
- Terraform >= 1.6.0
- Databricks Provider ~> 1.40
- State Backend: Azure Storage (remote state)

---

## Future Enhancements

- **Multi-language support** for document ingestion
- **Advanced chunking strategies** (semantic, recursive)
- **Hybrid search** (vector + keyword)
- **Real-time streaming ingestion** (Event Hub integration)
- **API layer** for external RAG queries
- **Feedback loop** for answer quality improvement

---

**Built with Terraform | Powered by Azure Databricks | Engineered for Production**
