# Database Table Schemas

Complete schema definitions for all 5 Delta tables in the NextLevel RAG system.

---

## Catalog & Schema

```
Catalog: heineken_test_workspace
Schema: nextlevel-rag
```

---

## Table 1: pdf_registery

**Purpose:** Track PDF upload and processing status

**Full Name:** `heineken_test_workspace.nextlevel-rag.pdf_registery`

### Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `pdf_id` | STRING | No | Unique identifier for PDF (UUID) |
| `pdf_name` | STRING | No | Original filename of PDF |
| `file_path` | STRING | No | Path to PDF in volume |
| `upload_date` | TIMESTAMP | No | When PDF was uploaded |
| `processing_status` | STRING | No | Status: pending, processing, completed, failed |
| `processed_date` | TIMESTAMP | Yes | When processing completed |
| `error_message` | STRING | Yes | Error message if processing failed |

### Example Row

```json
{
  "pdf_id": "abc-123-def-456",
  "pdf_name": "machine_manual.pdf",
  "file_path": "/Volumes/heineken_test_workspace/nextlevel-rag/raw_pdfs/machine_manual.pdf",
  "upload_date": "2025-11-30T10:15:00Z",
  "processing_status": "completed",
  "processed_date": "2025-11-30T10:18:45Z",
  "error_message": null
}
```

### Usage Queries

```sql
-- Get all PDFs with failed status
SELECT * FROM heineken_test_workspace.`nextlevel-rag`.pdf_registery
WHERE processing_status = 'failed';

-- Get recently processed PDFs
SELECT * FROM heineken_test_workspace.`nextlevel-rag`.pdf_registery
WHERE processing_status = 'completed'
ORDER BY processed_date DESC
LIMIT 10;
```

---

## Table 2: chunks_embedded

**Purpose:** Text chunks with embeddings for vector search

**Full Name:** `heineken_test_workspace.nextlevel-rag.chunks_embedded`

**Critical:** This table is the source for the vector search index

### Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `chunk_id` | STRING | No | Unique identifier for chunk (UUID) |
| `pdf_id` | STRING | No | Link to pdf_registery |
| `page_number` | INT | No | Page number in PDF (1-indexed) |
| `chunk_index` | INT | No | Sequential index across entire document |
| `text` | STRING | No | Chunk text content (600-1600 chars) |
| `embedding` | ARRAY<FLOAT> | No | Embedding vector (1024 dimensions) |
| `created_at` | TIMESTAMP | No | When chunk was created |

### Key Constraints

- `chunk_id` = Primary key for vector search index
- `embedding` dimension = 1024 (databricks-gte-large-en model)
- Chunks never span multiple pages (respect page boundaries)

### Example Row

```json
{
  "chunk_id": "chunk-xyz-789",
  "pdf_id": "abc-123-def-456",
  "page_number": 5,
  "chunk_index": 12,
  "text": "Safety Procedures: Before starting the machine, ensure all safety guards are in place. Check that emergency stop buttons are functional...",
  "embedding": [0.123, 0.456, 0.789, ..., 0.321],  // 1024 floats
  "created_at": "2025-11-30T10:17:30Z"
}
```

### Usage Queries

```sql
-- Get all chunks from a specific page
SELECT chunk_id, text, page_number
FROM heineken_test_workspace.`nextlevel-rag`.chunks_embedded
WHERE pdf_id = 'abc-123-def-456' AND page_number = 5;

-- Count chunks per PDF
SELECT pdf_id, COUNT(*) as chunk_count
FROM heineken_test_workspace.`nextlevel-rag`.chunks_embedded
GROUP BY pdf_id;

-- Get chunks in document order
SELECT chunk_index, page_number, text
FROM heineken_test_workspace.`nextlevel-rag`.chunks_embedded
WHERE pdf_id = 'abc-123-def-456'
ORDER BY chunk_index;
```

---

## Table 3: page_screenshots

**Purpose:** Page screenshot metadata and file paths

**Full Name:** `heineken_test_workspace.nextlevel-rag.page_screenshots`

### Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `page_id` | STRING | No | Unique identifier for page (UUID) |
| `pdf_id` | STRING | No | Link to pdf_registery |
| `page_number` | INT | No | Page number in PDF |
| `screenshot_path` | STRING | No | Path to screenshot image in volume |
| `created_at` | TIMESTAMP | No | When screenshot was created |

### Example Row

```json
{
  "page_id": "page-aaa-111",
  "pdf_id": "abc-123-def-456",
  "page_number": 5,
  "screenshot_path": "/Volumes/heineken_test_workspace/nextlevel-rag/screenshots/abc-123-def-456/page_5.png",
  "created_at": "2025-11-30T10:17:15Z"
}
```

### Usage Queries

```sql
-- Get screenshot for specific page
SELECT screenshot_path
FROM heineken_test_workspace.`nextlevel-rag`.page_screenshots
WHERE pdf_id = 'abc-123-def-456' AND page_number = 5;

-- Get all screenshots for a PDF
SELECT page_number, screenshot_path
FROM heineken_test_workspace.`nextlevel-rag`.page_screenshots
WHERE pdf_id = 'abc-123-def-456'
ORDER BY page_number;
```

---

## Table 4: document_summaries

**Purpose:** Store technical and operator summaries (2 per PDF)

**Full Name:** `heineken_test_workspace.nextlevel-rag.document_summaries`

### Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `summary_id` | STRING | No | Unique identifier for summary (UUID) |
| `pdf_id` | STRING | No | Link to pdf_registery |
| `pdf_name` | STRING | No | PDF filename for reference |
| `summary_type` | STRING | No | Type: 'technical' or 'operator' |
| `summary_text` | STRING | No | The full summary text |
| `total_pages` | INT | No | Total pages in PDF |
| `total_chunks` | INT | No | Total chunks processed |
| `key_topics` | ARRAY<STRING> | Yes | Extracted key topics |
| `processing_model` | STRING | No | LLM model used for summarization |
| `processing_time_seconds` | FLOAT | Yes | Time taken to generate summary |
| `created_at` | TIMESTAMP | No | When summary was created |

### Summary Types

#### Technical Summary
- **Audience:** Engineers, technicians, maintenance staff
- **Focus:** Specifications, technical procedures, troubleshooting, system architecture
- **Language:** Technical terminology, detailed explanations

#### Operator Summary
- **Audience:** Machine operators, end users
- **Focus:** Basic operation steps, safety procedures, common tasks, do's and don'ts
- **Language:** Simple, clear, 8th-grade reading level

### Example Rows

```json
// Row 1: Technical Summary
{
  "summary_id": "sum-tech-001",
  "pdf_id": "abc-123-def-456",
  "pdf_name": "machine_manual.pdf",
  "summary_type": "technical",
  "summary_text": "This hydraulic press operates at 500 PSI with a 10-ton capacity. The system uses a dual-circuit hydraulic design with independent safety valves...",
  "total_pages": 150,
  "total_chunks": 450,
  "key_topics": ["hydraulic systems", "safety valves", "maintenance schedules", "troubleshooting"],
  "processing_model": "databricks-meta-llama-3-1-70b-instruct",
  "processing_time_seconds": 45.3,
  "created_at": "2025-11-30T10:20:00Z"
}

// Row 2: Operator Summary
{
  "summary_id": "sum-oper-001",
  "pdf_id": "abc-123-def-456",
  "pdf_name": "machine_manual.pdf",
  "summary_type": "operator",
  "summary_text": "To start the machine: 1) Check all safety guards are closed. 2) Press the green start button. 3) Wait for the ready light...",
  "total_pages": 150,
  "total_chunks": 450,
  "key_topics": ["startup procedure", "safety checks", "basic operation", "shutdown steps"],
  "processing_model": "databricks-meta-llama-3-1-70b-instruct",
  "processing_time_seconds": 42.7,
  "created_at": "2025-11-30T10:20:50Z"
}
```

### Usage Queries

```sql
-- Get technical summary for a PDF
SELECT summary_text, key_topics
FROM heineken_test_workspace.`nextlevel-rag`.document_summaries
WHERE pdf_id = 'abc-123-def-456' AND summary_type = 'technical';

-- Get both summaries for a PDF
SELECT summary_type, summary_text, key_topics
FROM heineken_test_workspace.`nextlevel-rag`.document_summaries
WHERE pdf_id = 'abc-123-def-456'
ORDER BY summary_type;

-- List all PDFs with summaries
SELECT DISTINCT pdf_name, pdf_id
FROM heineken_test_workspace.`nextlevel-rag`.document_summaries;
```

---

## Table 5: operator_questions

**Purpose:** Multiple choice questions for operator training (60-80 per PDF)

**Full Name:** `heineken_test_workspace.nextlevel-rag.operator_questions`

### Schema

| Column | Type | Nullable | Description |
|--------|------|----------|-------------|
| `question_id` | STRING | No | Unique identifier for question (UUID) |
| `pdf_id` | STRING | No | Link to pdf_registery |
| `pdf_name` | STRING | No | PDF filename for reference |
| `question_number` | INT | No | Question number (1-70) for ordering |
| `question_text` | STRING | No | The question text |
| `option_a` | STRING | No | Choice A text |
| `option_b` | STRING | No | Choice B text |
| `option_c` | STRING | No | Choice C text |
| `option_d` | STRING | No | Choice D text |
| `correct_answer` | STRING | No | Correct answer: 'A', 'B', 'C', or 'D' |
| `explanation` | STRING | No | Explanation/reason for correct answer |
| `difficulty_level` | STRING | No | Difficulty: 'easy', 'medium', 'hard' |
| `topic_category` | STRING | No | Category: safety, operation, maintenance, etc. |
| `page_references` | ARRAY<INT> | Yes | Page numbers this question relates to |
| `chunk_references` | ARRAY<STRING> | Yes | Chunk IDs used to generate this question |
| `created_at` | TIMESTAMP | No | When question was created |

### Topic Categories

- `safety` - Safety procedures and protocols
- `startup` - Machine startup procedures
- `shutdown` - Machine shutdown procedures
- `operation` - Normal operation tasks
- `maintenance` - Routine maintenance
- `troubleshooting` - Problem identification and resolution
- `emergency` - Emergency procedures
- `quality` - Quality control and checks

### Difficulty Distribution (Target)

- **Easy (40%):** Direct recall, clearly stated in manual
- **Medium (40%):** Understanding, applying knowledge
- **Hard (20%):** Analysis, multi-step reasoning

### Example Row

```json
{
  "question_id": "q-001",
  "pdf_id": "abc-123-def-456",
  "pdf_name": "machine_manual.pdf",
  "question_number": 1,
  "question_text": "What must you check before starting the machine?",
  "option_a": "The weather outside",
  "option_b": "All safety guards are in place",
  "option_c": "Your lunch break schedule",
  "option_d": "The color of the machine",
  "correct_answer": "B",
  "explanation": "Safety guards prevent accidents and must always be verified before starting operations, as stated in Section 3.2 on page 12.",
  "difficulty_level": "easy",
  "topic_category": "safety",
  "page_references": [12],
  "chunk_references": ["chunk-xyz-789", "chunk-xyz-790"],
  "created_at": "2025-11-30T10:25:00Z"
}
```

### Usage Queries

```sql
-- Get all questions for a PDF
SELECT question_number, question_text, correct_answer
FROM heineken_test_workspace.`nextlevel-rag`.operator_questions
WHERE pdf_id = 'abc-123-def-456'
ORDER BY question_number;

-- Get questions by topic
SELECT question_text, option_a, option_b, option_c, option_d, correct_answer
FROM heineken_test_workspace.`nextlevel-rag`.operator_questions
WHERE pdf_id = 'abc-123-def-456' AND topic_category = 'safety';

-- Get questions by difficulty
SELECT question_number, question_text, difficulty_level
FROM heineken_test_workspace.`nextlevel-rag`.operator_questions
WHERE pdf_id = 'abc-123-def-456' AND difficulty_level = 'easy';

-- Count questions by category
SELECT topic_category, COUNT(*) as question_count
FROM heineken_test_workspace.`nextlevel-rag`.operator_questions
WHERE pdf_id = 'abc-123-def-456'
GROUP BY topic_category;

-- Get random 10 questions for quiz
SELECT question_number, question_text, option_a, option_b, option_c, option_d, correct_answer, explanation
FROM heineken_test_workspace.`nextlevel-rag`.operator_questions
WHERE pdf_id = 'abc-123-def-456'
ORDER BY RAND()
LIMIT 10;
```

---

## Table Relationships

```
pdf_registery (1)
    ↓
    ├─→ chunks_embedded (many)          → Vector Search Index
    ├─→ page_screenshots (many)
    ├─→ document_summaries (2)          [technical + operator]
    └─→ operator_questions (60-80)

chunks_embedded.page_number ←→ page_screenshots.page_number
operator_questions.page_references ←→ page_screenshots.page_number
operator_questions.chunk_references ←→ chunks_embedded.chunk_id
```

---

## Storage Volumes

### Volume 1: raw_pdfs
- **Path:** `/Volumes/heineken_test_workspace/nextlevel-rag/raw_pdfs/`
- **Purpose:** Store uploaded PDF files
- **Referenced By:** `pdf_registery.file_path`

### Volume 2: screenshots
- **Path:** `/Volumes/heineken_test_workspace/nextlevel-rag/screenshots/`
- **Purpose:** Store page screenshot images
- **Structure:** `screenshots/{pdf_id}/page_{number}.png`
- **Referenced By:** `page_screenshots.screenshot_path`

---

## Data Flow

```
1. PDF Upload
   → Stored in raw_pdfs volume
   → Registered in pdf_registery (status: pending)

2. Ingestion Job
   → Parse PDF
   → Extract pages + screenshots (save to screenshots volume)
   → Chunk text
   → Generate embeddings
   → Store in chunks_embedded + page_screenshots
   → Update pdf_registery (status: completed)

3. Vector Index
   → Auto-syncs from chunks_embedded (DELTA_SYNC mode)

4. Summarization Job
   → Read chunks from chunks_embedded
   → Generate technical summary
   → Generate operator summary
   → Store 2 rows in document_summaries

5. Question Generation Job
   → Read operator summary from document_summaries
   → Generate 60-80 multiple choice questions
   → Store in operator_questions
```

---

## Index Information

### Primary Keys
- `pdf_registery`: `pdf_id`
- `chunks_embedded`: `chunk_id` (used by vector search)
- `page_screenshots`: `page_id`
- `document_summaries`: `summary_id`
- `operator_questions`: `question_id`

### Foreign Keys (Logical)
- All tables link to `pdf_registery.pdf_id`
- `operator_questions.chunk_references` → `chunks_embedded.chunk_id`

### Vector Search Index
- **Name:** `heineken_test_workspace.nextlevel-rag.chunks_embedded_index`
- **Source:** `chunks_embedded` table
- **Primary Key:** `chunk_id`
- **Embedding Column:** `embedding`
- **Sync Mode:** DELTA_SYNC (automatic)

---

*Last Updated: 2025-11-30*
