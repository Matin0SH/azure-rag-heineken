# Question Generation: Schema & Flow

## Database Table Schema

**Table:** `heineken_test_workspace.nextlevel-rag.operator_questions`

### Complete Schema

```sql
CREATE TABLE operator_questions (
  question_id STRING NOT NULL,           -- UUID for each question
  pdf_id STRING NOT NULL,                -- Link to PDF
  pdf_name STRING NOT NULL,              -- PDF filename
  question_number INT NOT NULL,          -- Order (1-70)

  -- Multiple Choice Question
  question_text STRING NOT NULL,         -- The question
  option_a STRING NOT NULL,              -- Choice A
  option_b STRING NOT NULL,              -- Choice B
  option_c STRING NOT NULL,              -- Choice C
  option_d STRING NOT NULL,              -- Choice D
  correct_answer STRING NOT NULL,        -- 'A', 'B', 'C', or 'D'
  explanation STRING NOT NULL,           -- Why the answer is correct

  -- Categorization
  difficulty_level STRING NOT NULL,      -- 'easy', 'medium', 'hard'
  topic_category STRING NOT NULL,        -- 'safety', 'operation', etc.

  -- Traceability
  page_references ARRAY<INT>,            -- Which pages [12, 13, 15]
  chunk_references ARRAY<STRING>,        -- Which chunks ["chunk-1", "chunk-2"]
  created_at TIMESTAMP NOT NULL          -- When generated
)
```

### Example Question Row

```json
{
  "question_id": "q-abc123-def456",
  "pdf_id": "CAS.pdf",
  "pdf_name": "CAS.pdf",
  "question_number": 15,

  "question_text": "What should you check before starting the machine?",
  "option_a": "All safety guards are in place",
  "option_b": "The weather outside",
  "option_c": "Your lunch break schedule",
  "option_d": "The machine's color",
  "correct_answer": "A",
  "explanation": "Safety guards prevent accidents and must always be verified before starting operations, as stated in Section 3.2 on page 12.",

  "difficulty_level": "easy",
  "topic_category": "safety",

  "page_references": [12, 13],
  "chunk_references": ["chunk-xyz-001", "chunk-xyz-002"],
  "created_at": "2025-11-30T10:00:00Z"
}
```

---

## MAP-REDUCE Flow

### Architecture Overview

```
1403 chunks (674 pages)
    ↓
[MAP PHASE] 50 chunks per batch → 12 questions per batch
    ↓
28 batches × 12 questions = ~336 questions generated
    ↓
[REDUCE PHASE] Deduplicate + Select best 70
    ↓
Distribution: 28 easy, 28 medium, 14 hard
    ↓
[REFLECT PHASE] Quality check
    ↓
70 final questions → Save to database
```

### Configuration

```python
# Batch Configuration
DEFAULT_BATCH_SIZE = 50              # Chunks per batch
QUESTIONS_PER_BATCH = 12             # Questions generated per batch
TOTAL_QUESTIONS_TARGET = 70          # Final questions saved

# Difficulty Distribution
EASY_RATIO = 0.40                    # 40% easy (28 questions)
MEDIUM_RATIO = 0.40                  # 40% medium (28 questions)
HARD_RATIO = 0.20                    # 20% hard (14 questions)

# Quality Control
MAX_ITERATIONS = 2                   # Reflection iterations
CONTEXT_WINDOW_SIZE = 2              # Avoid duplicates
```

---

## MAP PHASE: Batch Question Generation

### Process

For each batch of 50 chunks:

1. **Combine 50 chunks** into single text
2. **Include context** from last 2 batches (prevents duplicate questions)
3. **Call LLM** with generation prompt
4. **Parse JSON response** → Extract questions
5. **Add to batch_questions** list

### Output per Batch (12 questions)

```json
{
  "questions": [
    {
      "question_text": "What is the first step in starting the machine?",
      "option_a": "Turn on the power switch",
      "option_b": "Check safety guards",
      "option_c": "Start the conveyor",
      "option_d": "Load materials",
      "correct_answer": "B",
      "explanation": "Safety checks must be performed before powering on.",
      "difficulty_level": "easy",
      "topic_category": "startup"
    },
    ... (11 more questions)
  ]
}
```

### Tracer Output

```
================================================================================
MAP PHASE: Generating OPERATOR QUESTIONS
Total chunks: 1403 | Batch size: 50 | Estimated batches: 28
Questions per batch: 12 (5 easy, 5 medium, 2 hard)
================================================================================
[MAP 1/28] Generating questions from 50 chunks...
[MAP 1/28] ✓ Generated 12 questions
[MAP 2/28] Generating questions from 50 chunks...
[MAP 2/28] ✓ Generated 11 questions
...
```

---

## REDUCE PHASE: Deduplication & Selection

### Process

1. **Remove exact duplicates** (by question text)
2. **Separate by difficulty** (easy/medium/hard)
3. **Select top N from each category**:
   - 28 easy questions
   - 28 medium questions
   - 14 hard questions
4. **Assign question numbers** (1-70)

### Tracer Output

```
================================================================================
REDUCE PHASE: Deduplication & Selection
Total questions generated: 336
================================================================================
[REDUCE] After deduplication: 298 unique questions
[REDUCE] Distribution: 145 easy, 118 medium, 35 hard
[REDUCE] ✓ Selected 70 final questions
```

---

## REFLECT PHASE: Quality Check

### Quality Criteria

- ✅ Questions based on content (not hallucinated)
- ✅ Language is simple (8th grade level)
- ✅ Answers are complete and correct
- ✅ Explanations are clear
- ✅ Topics are diverse

### Decision Logic

```
If PASS → Accept 70 questions
If FAIL + iteration < 2 → Re-run MAP phase
If FAIL + iteration ≥ 2 → Accept anyway (prevent infinite loop)
```

### Tracer Output

```
[REFLECT] Iteration 1/2 - Critiquing 70 questions...
[REFLECT] ✓ PASS - Questions accepted
```

---

## Saving to Database

### Method 1: Bulk Insert (Recommended)

```python
from databricks import sql
import uuid
from datetime import datetime

# After agent completes
final_questions = result['final_questions']
pdf_id = "CAS.pdf"
pdf_name = "CAS.pdf"

# Prepare rows for bulk insert
rows = []
for q in final_questions:
    row = {
        "question_id": str(uuid.uuid4()),
        "pdf_id": pdf_id,
        "pdf_name": pdf_name,
        "question_number": q["question_number"],
        "question_text": q["question_text"],
        "option_a": q["option_a"],
        "option_b": q["option_b"],
        "option_c": q["option_c"],
        "option_d": q["option_d"],
        "correct_answer": q["correct_answer"],
        "explanation": q["explanation"],
        "difficulty_level": q["difficulty_level"],
        "topic_category": q["topic_category"],
        "page_references": q.get("page_references", []),
        "chunk_references": q.get("chunk_references", []),
        "created_at": datetime.utcnow()
    }
    rows.append(row)

# Bulk insert
with sql.connect(...) as conn:
    with conn.cursor() as cursor:
        cursor.executemany("""
            INSERT INTO heineken_test_workspace.`nextlevel-rag`.operator_questions
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [tuple(r.values()) for r in rows])
```

### Method 2: Individual Inserts (Slower)

```python
for q in final_questions:
    cursor.execute("""
        INSERT INTO heineken_test_workspace.`nextlevel-rag`.operator_questions
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
    """, (
        str(uuid.uuid4()),
        pdf_id,
        pdf_name,
        q["question_number"],
        q["question_text"],
        q["option_a"],
        q["option_b"],
        q["option_c"],
        q["option_d"],
        q["correct_answer"],
        q["explanation"],
        q["difficulty_level"],
        q["topic_category"],
        q.get("page_references", []),
        q.get("chunk_references", []),
        datetime.utcnow()
    ))
```

---

## Topic Categories

| Category | Description | Example Questions |
|----------|-------------|-------------------|
| `safety` | Safety procedures and protocols | "What PPE is required?" |
| `startup` | Machine startup procedures | "First step to start machine?" |
| `shutdown` | Machine shutdown procedures | "How to safely shut down?" |
| `operation` | Normal operation tasks | "How to adjust speed?" |
| `maintenance` | Routine maintenance | "How often to lubricate?" |
| `troubleshooting` | Problem identification | "If alarm sounds, do what?" |
| `emergency` | Emergency procedures | "Emergency stop procedure?" |
| `quality` | Quality control and checks | "How to verify quality?" |

---

## Difficulty Levels

### Easy (40% = 28 questions)
- Direct recall from manual
- Clearly stated information
- One-step reasoning
- Example: "What color is the emergency stop button?"

### Medium (40% = 28 questions)
- Understanding and application
- Multi-step procedures
- Cause-and-effect
- Example: "Why must you check safety guards before starting?"

### Hard (20% = 14 questions)
- Analysis and troubleshooting
- Multi-step reasoning
- Scenario-based
- Example: "If the machine stops and alarm X sounds, what is the likely cause and solution?"

---

## Complete Flow Summary

1. **MAP PHASE** (5-8 minutes)
   - 28 batches × 50 chunks
   - 336 questions generated
   - Adaptive batch sizing if needed
   - Context window prevents duplicates

2. **REDUCE PHASE** (1 minute)
   - Deduplicate by question text
   - Separate by difficulty
   - Select 70 best questions
   - Assign question numbers

3. **REFLECT PHASE** (30 seconds)
   - Critique quality
   - Check language simplicity
   - Verify answer correctness
   - Accept or retry

4. **SAVE TO DATABASE** (5 seconds)
   - Add UUID per question
   - Add page/chunk references
   - Bulk insert 70 rows
   - Return success

**Total Time:** ~10-12 minutes for 674-page PDF
**Total API Calls:** ~30 (28 MAP + 1 REDUCE + 1 REFLECT)
**Output:** 70 high-quality multiple-choice questions

---

## Next Steps

1. ✅ Schema defined
2. ✅ MAP-REDUCE flow created
3. ✅ Nodes implemented (`nodes_new.py`)
4. ⏳ Update `graph.py` to use new nodes
5. ⏳ Create test script
6. ⏳ Test with real PDF
7. ⏳ Integrate database save logic
