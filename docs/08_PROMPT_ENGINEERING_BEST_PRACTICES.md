# Prompt Engineering Best Practices

**Purpose:** Comprehensive guide for crafting effective prompts for the NextLevel RAG system's summarization and question generation pipelines.

**Based on:** Analysis of existing graph_summarization_pipeline.py prompts + established LLM research

**Last Updated:** 2025-11-30

---

## Table of Contents

1. [Core Principles](#core-principles)
2. [Connection Syntax Patterns](#connection-syntax-patterns)
3. [Summarization Prompts](#summarization-prompts)
4. [Question Generation Prompts](#question-generation-prompts)
5. [Reflection/Critique Prompts](#reflectioncritique-prompts)
6. [Model Parameters](#model-parameters)
7. [Databricks-Specific Patterns](#databricks-specific-patterns)
8. [Prompt Templates](#prompt-templates)

---

## Core Principles

### 1. Role Definition (Persona)

**Best Practice:** Define a clear, specific role with expertise context.

**Good Examples:**
```
"You are an expert technical writer extracting operator procedures from equipment manuals."
"You are a quality auditor for technical procedures."
"You are organizing technical procedures from multiple batch summaries."
```

**Why it works:**
- Sets context and expectations
- Activates relevant knowledge in the model
- Improves consistency and tone

**Bad Example:**
```
"You are a helpful assistant."  # Too generic
```

---

### 2. Goal Clarity

**Best Practice:** State the goal explicitly in one sentence.

**Pattern:**
```
GOAL: [Specific, measurable outcome]
```

**Examples from existing code:**
```
GOAL: Extract procedures while preserving their original structure and exact technical values.
```

**Why it works:**
- Focuses model attention
- Provides success criteria
- Reduces hallucination

---

### 3. Key Rules (Constraints)

**Best Practice:** Use numbered, specific rules. Limit to 5-7 rules per prompt.

**Pattern:**
```
KEY RULES:
1. [Specific constraint with example]
2. [Specific constraint with example]
3. [Specific constraint with example]
```

**Example from existing code:**
```
KEY RULES:
1. Keep each procedure separate - do NOT merge multiple procedures together
2. Copy all numbers exactly with their units (e.g., "45 Nm", "120°C", "2.5 bar")
3. Use original headings from the source
4. Build on previous context - skip content already covered
5. Focus on operator actions only - remove background theory
```

**Why it works:**
- Numbered lists improve compliance
- Specific examples reduce ambiguity
- Negative constraints ("do NOT") prevent common errors

---

### 4. Output Format Specification

**Best Practice:** Provide exact output structure with markdown templates.

**Pattern:**
```
OUTPUT FORMAT:
## [Heading]

### [Subheading]
**Label:** [Content]

**Steps:**
1. [Item]
2. [Item]
```

**Why it works:**
- Ensures consistent structure
- Easier to parse programmatically
- Reduces model uncertainty

---

### 5. Few-Shot Examples vs Zero-Shot

**When to use Few-Shot:**
- Complex formatting requirements
- Domain-specific terminology
- Quality is critical

**When to use Zero-Shot:**
- Simple, well-defined tasks
- Models already trained on similar patterns
- Speed is priority

**Our approach:** Zero-shot with detailed structure (faster, scales better)

---

## Connection Syntax Patterns

### Pattern 1: Widget Parameters (Job Inputs)

**From existing code:**
```python
# Widget parameters (passed from job trigger)
dbutils.widgets.text("pdf_name", "", "PDF Filename")
dbutils.widgets.text("pdf_id", "", "PDF ID")

pdf_name = dbutils.widgets.get("pdf_name")
pdf_id = dbutils.widgets.get("pdf_id")
```

**Best Practice:**
- Always provide default values (empty string)
- Use descriptive label (3rd parameter)
- Validate inputs after retrieval

---

### Pattern 2: Configuration Constants

**From existing code:**
```python
CATALOG = "heineken_test_workspace"
SCHEMA = "nextlevel-rag"
LLM_MODEL = "databricks-meta-llama-3-1-70b-instruct"

# Model parameters
TEMPERATURE = 0.2
MAX_TOKENS = 8192
BATCH_SIZE = 2
```

**Best Practice:**
- Use UPPER_CASE for constants
- Group related configs together
- Comment non-obvious values

---

### Pattern 3: LLM Call via ai_query (DataFrame Method)

**CRITICAL PATTERN from graph_summarization_pipeline.py:**

```python
def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    Call Databricks LLM via ai_query using DataFrame approach (no SQL escaping!)

    This follows the ingest_pipeline.py pattern:
    - Create temp view with prompt as column
    - Query via ai_query referencing column
    - Avoids all SQL escaping issues
    """
    # Combine prompts (model understands this convention)
    full_prompt = f"{system_prompt}\n\n{user_prompt}"

    # Create DataFrame with prompt as column (avoids SQL escaping!)
    prompt_df = spark.createDataFrame([(full_prompt,)], ["prompt"])
    prompt_df.createOrReplaceTempView("prompt_temp")

    try:
        # Query with column reference (no escaping needed!)
        result_df = spark.sql(f"""
            SELECT ai_query(
                '{LLM_MODEL}',
                prompt,
                modelParameters => named_struct(
                    'max_tokens', {MAX_TOKENS},
                    'temperature', {TEMPERATURE}
                )
            ) as response
            FROM prompt_temp
        """)

        result = result_df.first()
        return result['response'] if result else ""

    finally:
        # Clean up temp view
        try:
            spark.catalog.dropTempView("prompt_temp")
        except:
            pass
```

**Why this pattern:**
- **Avoids SQL escaping issues** (quotes, newlines, special chars)
- Uses DataFrame column reference (safe)
- Follows existing ingest_pipeline.py pattern
- Clean temp view cleanup

**Alternative (direct SQL - NOT RECOMMENDED):**
```python
# AVOID: Causes escaping issues with quotes/newlines
spark.sql(f"SELECT ai_query('{LLM_MODEL}', '{prompt}')")
```

---

### Pattern 4: Databricks SDK for Job Triggering

**From graph_community_pipeline.py:**

```python
import requests
import os

# Get config from environment variables
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST", "https://adb-xxx.azuredatabricks.net")
DATABRICKS_TOKEN = os.getenv("DATABRICKS_TOKEN", "dapi...")
JOB_ID = os.getenv("SUMMARIZATION_JOB_ID", "12345")

url = f"{DATABRICKS_HOST}/api/2.1/jobs/run-now"
headers = {
    "Authorization": f"Bearer {DATABRICKS_TOKEN}",
    "Content-Type": "application/json"
}

payload = {
    "job_id": int(JOB_ID),
    "notebook_params": {
        "pdf_name": pdf_name,
        "pdf_id": pdf_id
    }
}

response = requests.post(url, headers=headers, json=payload, timeout=30)

if response.status_code == 200:
    data = response.json()
    run_id = data.get("run_id")
    print(f"Triggered job: Run ID {run_id}")
```

**Best Practice:**
- Use environment variables for secrets
- Provide fallback defaults for development
- Set timeout (30s recommended)
- Check response status code

---

## Summarization Prompts

### Dual Audience Approach

**Challenge:** Generate 2 summaries per PDF
1. **Technical:** For engineers, maintenance staff
2. **Operator:** For machine operators, end users

---

### Technical Summary Prompt Template

```python
TECHNICAL_SUMMARY_SYSTEM = """You are a technical documentation specialist creating comprehensive summaries for engineers and maintenance staff.

GOAL: Create a detailed technical summary preserving specifications, procedures, and troubleshooting information.

AUDIENCE: Engineers, technicians, maintenance personnel with technical background.

KEY RULES:
1. Preserve all technical specifications (values, units, tolerances)
2. Include system architecture and component relationships
3. Maintain technical terminology and precision
4. Focus on: specifications, procedures, troubleshooting, maintenance schedules
5. Organize by technical systems/subsystems

OUTPUT FORMAT:
# Technical Summary: {document_name}

## 1. SYSTEM OVERVIEW
**Equipment Type:** [Type]
**Model:** [Model number]
**Specifications:** [Key specs with values and units]

## 2. TECHNICAL SPECIFICATIONS
### 2.1 [Subsystem Name]
- **Parameter:** Value ± Tolerance [unit]
- **Operating Range:** Min-Max [unit]

## 3. MAINTENANCE PROCEDURES
### 3.1 [Procedure Name]
**Frequency:** [Schedule]
**Steps:**
1. [Technical step with exact values]
2. [Technical step]

**Critical Parameters:**
- [Parameter]: [Value] [unit]

## 4. TROUBLESHOOTING
**Symptom:** [Issue description]
**Possible Causes:**
1. [Cause] → [Diagnostic test]
2. [Cause] → [Diagnostic test]

**Resolution:**
- [Technical solution with exact steps]

## 5. SAFETY & WARNINGS
- [Critical safety information with technical context]

## 6. DIAGRAMS & REFERENCES
- [List of referenced diagrams/sections]
"""

TECHNICAL_SUMMARY_HUMAN = """DOCUMENT: {pdf_name}
TOTAL PAGES: {total_pages}
CHUNKS: {total_chunks}

CONTENT (Batch {batch_num}/{total_batches}):
{chunk_text}

Create the technical summary following the format above. Preserve all technical details."""
```

**Key Design Decisions:**
- **Temperature:** 0.2 (low for accuracy)
- **Max Tokens:** 8192 (allow detailed output)
- **Batch Processing:** 20 chunks at a time
- **Context Preservation:** Include previous batch summary in next batch

---

### Operator Summary Prompt Template

```python
OPERATOR_SUMMARY_SYSTEM = """You are creating an operator manual for machine operators and end users.

GOAL: Create a clear, simple summary focused on safe operation and basic procedures.

AUDIENCE: Machine operators, end users with basic training (8th-grade reading level).

KEY RULES:
1. Use simple, clear language - avoid technical jargon
2. Focus on: startup, operation, shutdown, safety
3. Use active voice and imperative mood ("Press the button" not "The button should be pressed")
4. Include safety warnings prominently
5. Use numbered steps for all procedures
6. Explain what to check and why, but keep it simple

OUTPUT FORMAT:
# Operator Manual: {document_name}

## 1. SAFETY FIRST
**Before You Start:**
- [Safety check in simple language]
- [Safety check]

**WARNING Signs to Watch For:**
- [Warning condition] → [What to do]

**Personal Protection:**
- [Required PPE in simple terms]

## 2. STARTING THE MACHINE
**Pre-Start Checks:**
1. [Simple check] - Why: [Simple reason]
2. [Check]

**Startup Steps:**
1. [Simple action]
2. [Simple action]
3. Wait for [indicator] - this means [simple explanation]

## 3. NORMAL OPERATION
**What You'll Do:**
1. [Regular task in simple language]
2. [Regular task]

**What's Normal:**
- [Normal indicator] - this is good
- [Normal sound/behavior]

**What's NOT Normal:**
- [Problem sign] → Stop and call maintenance

## 4. SHUTTING DOWN
**Shutdown Steps:**
1. [Simple step]
2. [Simple step]

**Final Checks:**
- [End-of-shift check]

## 5. COMMON PROBLEMS & FIXES
**Problem:** [Simple description]
**What to try:**
1. [Simple fix] - If this doesn't work, stop and call maintenance
2. [Simple fix]

**Never Try To:**
- [Dangerous action to avoid]

## 6. WHO TO CALL
**Call Maintenance If:**
- [Problem condition]
- [Problem condition]
"""

OPERATOR_SUMMARY_HUMAN = """DOCUMENT: {pdf_name}
TOTAL PAGES: {total_pages}

CONTENT (Batch {batch_num}/{total_batches}):
{chunk_text}

Create the operator manual following the format above. Keep language simple and focus on safe operation."""
```

**Key Design Decisions:**
- **Reading Level:** 8th grade (Flesch-Kincaid 60-70)
- **Temperature:** 0.3 (slightly higher for natural language)
- **Focus:** Safety, basic operation, when to get help
- **Tone:** Supportive, clear, imperative

---

### Map-Reduce Strategy for Long Documents

**Pattern from existing code (PROVEN EFFECTIVE):**

```python
# MAP PHASE: Process batches with context
batch_summaries = []
cumulative_context = ""

for batch_idx in range(0, num_chunks, BATCH_SIZE):
    batch_chunks = chunks[batch_idx:batch_idx + BATCH_SIZE]

    # Build context from recent batches (sliding window)
    context_str = cumulative_context if cumulative_context else "This is the first batch."

    # Draft summary for this batch
    draft_summary = call_llm(
        MAP_DRAFT_SYSTEM,
        MAP_DRAFT_HUMAN.format(
            context=context_str,
            chunks=batch_chunks
        )
    )

    batch_summaries.append(draft_summary)

    # Update cumulative context (keep last 3 batches)
    recent_summaries = batch_summaries[-3:]
    cumulative_context = "\n\n---\n\n".join(recent_summaries)

# REDUCE PHASE: Combine batch summaries
all_summaries_text = "\n\n---\n\n".join(batch_summaries)
final_summary = call_llm(
    REDUCE_DRAFT_SYSTEM,
    REDUCE_DRAFT_HUMAN.format(
        title=pdf_name,
        total_batches=len(batch_summaries),
        summaries=all_summaries_text
    )
)
```

**Why this works:**
- Context window prevents repetition
- Batch summaries stay under token limits
- Reduce phase consolidates without losing details

---

## Question Generation Prompts

### Multiple Choice Question Generation

**Best Practice:** Generate in small batches (10 questions at a time) with validation.

```python
QUESTION_GENERATION_SYSTEM = """You are an instructional designer creating multiple choice questions for operator training.

GOAL: Generate high-quality multiple choice questions that test understanding of the operator manual.

AUDIENCE: Machine operators completing training assessments.

QUESTION QUALITY STANDARDS:
1. **Clear and Specific:** Each question tests one concept
2. **Realistic Distractors:** Wrong answers should be plausible but clearly incorrect
3. **No Tricks:** Questions should be fair and straightforward
4. **Practical Focus:** Test real-world operator knowledge

DIFFICULTY DISTRIBUTION (for each batch of 10):
- Easy (4 questions): Direct recall from manual
- Medium (4 questions): Understanding and application
- Hard (2 questions): Analysis or multi-step reasoning

TOPIC COVERAGE:
- Safety procedures
- Startup/shutdown sequences
- Normal operation
- Problem identification
- When to call for help

OUTPUT FORMAT (JSON):
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "[Clear question based on manual]",
      "option_a": "[First option]",
      "option_b": "[Second option]",
      "option_c": "[Third option]",
      "option_d": "[Fourth option]",
      "correct_answer": "B",
      "explanation": "[Why B is correct and why others are wrong]",
      "difficulty_level": "easy",
      "topic_category": "safety",
      "page_references": [12, 13]
    }},
    ... (9 more questions)
  ]
}}

DISTRACTOR QUALITY:
- Use common misconceptions
- Include values that are close but wrong
- Reference related but incorrect procedures
- Avoid obviously silly options
"""

QUESTION_GENERATION_HUMAN = """OPERATOR MANUAL SUMMARY:
{operator_summary}

SPECIFIC CONTENT FOR THIS BATCH (Pages {page_start}-{page_end}):
{focused_content}

Generate 10 multiple choice questions following the format above. Ensure 4 easy, 4 medium, 2 hard. Return valid JSON only."""
```

**Best Practice Implementation:**

```python
# Generate questions in batches of 10
questions = []

for batch_idx in range(0, target_questions, 10):
    # Get focused content for this batch
    focused_content = get_content_for_batch(batch_idx)

    # Generate 10 questions
    response = call_llm(
        QUESTION_GENERATION_SYSTEM,
        QUESTION_GENERATION_HUMAN.format(
            operator_summary=operator_summary,
            focused_content=focused_content,
            page_start=batch_start_page,
            page_end=batch_end_page
        )
    )

    # Parse JSON response
    import json
    batch_questions = json.loads(response)

    # Validate batch
    if validate_question_batch(batch_questions):
        questions.extend(batch_questions['questions'])
    else:
        # Regenerate if validation fails
        print(f"Batch {batch_idx//10 + 1} failed validation, regenerating...")
```

**Key Parameters:**
- **Temperature:** 0.7 (higher for creative distractors)
- **Max Tokens:** 4096 (enough for 10 questions)
- **Batch Size:** 10 questions (proven optimal)

---

### Question Validation Prompt

```python
QUESTION_VALIDATION_SYSTEM = """You are a quality reviewer for training assessments.

GOAL: Validate that multiple choice questions meet quality standards.

QUALITY CHECKS:
1. **Question Clarity:** Is the question clear and unambiguous?
2. **Distractor Quality:** Are wrong answers plausible but clearly incorrect?
3. **Answer Correctness:** Is the correct answer actually correct per the source?
4. **Explanation Quality:** Does the explanation justify the answer?
5. **No Tricks:** Is the question fair and straightforward?

ACCEPT if 8/10 or better meet standards.

OUTPUT:
If batch is acceptable:
PASS

If batch has issues:
FAIL
ISSUES:
- Question [number]: [Specific problem]
- Question [number]: [Specific problem]
"""

QUESTION_VALIDATION_HUMAN = """SOURCE MANUAL:
{operator_summary}

QUESTIONS TO VALIDATE:
{questions_json}

Validate these questions. Accept if 8/10 or better are high quality."""
```

---

## Reflection/Critique Prompts

### Pattern from Existing Code (PROVEN)

**The reflection pattern from graph_summarization_pipeline.py:**

```
1. DRAFT → 2. CRITIQUE → 3. REVISE (if needed)
```

This pattern appears in both MAP and REDUCE phases.

---

### Critique Prompt Template

```python
CRITIQUE_SYSTEM = """You are a quality auditor for [specific task: technical procedures/summaries/questions].

CRITICAL CHECKS (must pass):
1. [Specific check with measurable criterion]
2. [Specific check]
3. [Specific check]

ACCEPT if [threshold]% meets standards. Minor issues are acceptable.

OUTPUT:
If good enough, respond:
PASS

If major issues exist, respond:
ISSUES:
- [Specific problem with example from source]
- [What needs to be fixed]
"""

CRITIQUE_HUMAN = """SOURCE MATERIAL:
{source}

OUTPUT TO CHECK:
{draft}

Quick audit: [Specific validation questions]. If yes, say PASS. If major issues, list them."""
```

**Key Design Decisions:**
- **Binary Decision:** PASS or list ISSUES (no ambiguity)
- **Specific Checks:** Measurable criteria
- **Accept Threshold:** 85-90% (avoid perfectionism)
- **Temperature:** 0.1 (very low for consistency)

---

### Revision Prompt Template

```python
REVISE_SYSTEM = """Revise the [output type] to fix the issues identified in the critique.

RULES:
1. Fix only what the critique mentions
2. Check source material for correct information
3. Keep everything else the same
4. Maintain the same output format
"""

REVISE_HUMAN = """SOURCE MATERIAL:
{source}

CURRENT DRAFT:
{draft}

ISSUES TO FIX:
{critique}

Revise the draft to fix these issues. Keep the same format."""
```

**Key Design Decisions:**
- **Focused Changes:** Only fix what's broken
- **Temperature:** 0.2 (low but not zero for natural language)
- **Max Iterations:** 1-2 (diminishing returns after that)

---

### Implementation Pattern

```python
def generate_with_reflection(source_material, draft_system, draft_human,
                              critique_system, critique_human,
                              revise_system, revise_human,
                              max_iterations=1):
    """
    Generate output with reflection pattern.

    Args:
        max_iterations: Max revision attempts (1-2 recommended)

    Returns:
        Final output after critique and optional revision
    """
    # Draft
    draft = call_llm(draft_system, draft_human.format(source=source_material))

    # Critique
    critique = call_llm(
        critique_system,
        critique_human.format(source=source_material, draft=draft)
    )

    # Revise if needed
    iterations = 0
    while not critique.strip().upper().startswith("PASS") and iterations < max_iterations:
        draft = call_llm(
            revise_system,
            revise_human.format(source=source_material, draft=draft, critique=critique)
        )

        # Re-critique
        critique = call_llm(
            critique_system,
            critique_human.format(source=source_material, draft=draft)
        )

        iterations += 1

    return draft
```

---

## Model Parameters

### Temperature Settings

**Purpose:** Controls randomness in output.

| Task | Temperature | Reasoning |
|------|-------------|-----------|
| Technical Summary | 0.2 | Need accuracy, precision with technical values |
| Operator Summary | 0.3 | Slightly higher for natural, friendly language |
| Question Generation | 0.7 | Higher for creative, plausible distractors |
| Critique/Validation | 0.1 | Very low for consistent, objective evaluation |
| Revision | 0.2 | Low but not zero for natural language fixes |

**General Rules:**
- **0.0-0.3:** Factual, deterministic tasks
- **0.3-0.7:** Creative but grounded tasks
- **0.7-1.0:** Highly creative tasks (not used in our system)

---

### Max Tokens Settings

| Task | Max Tokens | Reasoning |
|------|------------|-----------|
| Batch Summary (Map) | 2048 | Enough for ~500 words per batch |
| Final Summary (Reduce) | 8192 | Comprehensive final document |
| Question Batch (10 Q's) | 4096 | ~400 tokens per question |
| Critique | 1024 | Short PASS/FAIL response |
| Revision | 4096 | Same as original draft |

**General Rules:**
- Leave 20% headroom (don't use full context window)
- Monitor actual usage and adjust
- Truncation = quality loss

---

### Context Window Optimization

**Pattern from existing code:**

```python
# Sliding window context (keep last 3 batches)
CONTEXT_WINDOW = 3

cumulative_context = ""
for batch in batches:
    # Use recent context
    context_str = cumulative_context if cumulative_context else "This is the first batch."

    # Process batch
    summary = process_batch(batch, context_str)
    batch_summaries.append(summary)

    # Update context (keep last 3)
    recent_summaries = batch_summaries[-CONTEXT_WINDOW:]
    cumulative_context = "\n\n---\n\n".join(recent_summaries)
```

**Why this works:**
- Prevents repetition across batches
- Maintains narrative flow
- Stays under token limits

---

## Databricks-Specific Patterns

### 1. ai_query Named Struct Parameters

```python
result_df = spark.sql(f"""
    SELECT ai_query(
        '{LLM_MODEL}',
        prompt,
        modelParameters => named_struct(
            'max_tokens', {MAX_TOKENS},
            'temperature', {TEMPERATURE}
        )
    ) as response
    FROM prompt_temp
""")
```

**Available Parameters:**
- `max_tokens`: Maximum output length
- `temperature`: Randomness (0.0-1.0)
- `top_p`: Nucleus sampling (alternative to temperature)
- `stop`: Stop sequences (array of strings)

---

### 2. Batch Embedding Generation

**From ingest_pipeline.py:**

```python
# Generate embeddings for all chunks at once (parallel)
embedded_df = spark.sql(f"""
    SELECT
        chunk_id,
        text,
        ai_query('{EMBEDDING_MODEL}', text) as embedding
    FROM chunks_temp
""")
```

**Key:** Spark parallelizes this across cluster, much faster than loop.

---

### 3. Hierarchical Reduction for Token Limits

**Pattern from graph_summarization_pipeline.py:**

```python
def hierarchical_reduce_to_sop(batch_summaries, section_title, current_date):
    """
    Reduce batch summaries to SOP with hierarchical reduction.

    Strategy:
    - If ≤4 batches: Direct reduction (fits in token limit)
    - If >4 batches: Two-stage reduction
        Stage 1: Group batches into chunks of 4, create intermediate summaries
        Stage 2: Merge intermediate summaries into final SOP
    """
    num_batches = len(batch_summaries)
    REDUCE_CHUNK_SIZE = 4

    if num_batches <= REDUCE_CHUNK_SIZE:
        # Direct reduction
        all_summaries_text = "\n\n---\n\n".join(batch_summaries)
        return call_llm(REDUCE_SYSTEM, REDUCE_HUMAN.format(summaries=all_summaries_text))

    # Stage 1: Create intermediate summaries
    intermediate_summaries = []
    for i in range(0, num_batches, REDUCE_CHUNK_SIZE):
        chunk = batch_summaries[i:i + REDUCE_CHUNK_SIZE]
        chunk_text = "\n\n---\n\n".join(chunk)
        intermediate = call_llm(INTERMEDIATE_REDUCE_SYSTEM,
                                INTERMEDIATE_REDUCE_HUMAN.format(summaries=chunk_text))
        intermediate_summaries.append(intermediate)

    # Stage 2: Merge intermediates
    all_intermediates = "\n\n---\n\n".join(intermediate_summaries)
    return call_llm(REDUCE_SYSTEM, REDUCE_HUMAN.format(summaries=all_intermediates))
```

**Why this works:**
- Avoids hitting token limits on large documents
- Maintains quality through two-stage consolidation
- Scales to documents of any size

---

## Prompt Templates

### Template 1: Technical Summary (Map Phase)

```python
TECH_MAP_SYSTEM = """You are a technical documentation specialist.

GOAL: Extract technical specifications and procedures from this section of the manual.

AUDIENCE: Engineers and maintenance staff.

KEY RULES:
1. Preserve all technical values with units (e.g., "45 Nm", "120°C")
2. Keep procedures separate - do NOT merge
3. Use original headings from source
4. Build on previous context - skip content already covered
5. Focus on specifications, procedures, troubleshooting

OUTPUT FORMAT:
## [Original Heading]

### [Subsystem/Component]
**Specifications:**
- [Parameter]: [Value] [unit] (±[tolerance])

### Procedure: [Name]
**Steps:**
1. [Action with exact values]
2. [Action]

**Critical Parameters:**
- [Param]: [Value] [unit]

**Warnings:**
- [Safety warning]
"""

TECH_MAP_HUMAN = """PREVIOUS CONTEXT:
{context}

CURRENT SECTION (Pages {page_start}-{page_end}):
{content}

Extract technical content following the format. Preserve exact values."""
```

---

### Template 2: Operator Summary (Map Phase)

```python
OPERATOR_MAP_SYSTEM = """You are creating an operator guide in simple language.

GOAL: Extract operator procedures in clear, simple terms.

AUDIENCE: Machine operators (8th-grade reading level).

KEY RULES:
1. Use simple language - no jargon
2. Keep each procedure separate
3. Use active voice ("Press button" not "Button should be pressed")
4. Include safety prominently
5. Explain what to check and why, simply

OUTPUT FORMAT:
## [Simple Heading]

### How to [Action]
**What you need to check first:**
1. [Simple check] - Why: [Simple reason]

**Steps:**
1. [Simple action in active voice]
2. [Simple action]
3. Wait for [indicator] - this means [simple explanation]

**Safety:**
⚠️ [Warning in simple language]

**If something goes wrong:**
- [Problem] → [Simple fix or "Call maintenance"]
"""

OPERATOR_MAP_HUMAN = """PREVIOUS CONTEXT:
{context}

CURRENT SECTION (Pages {page_start}-{page_end}):
{content}

Extract operator procedures in simple language following the format."""
```

---

### Template 3: Question Generation (10 at a time)

```python
QUESTION_GEN_SYSTEM = """You are an instructional designer creating operator training questions.

GOAL: Generate 10 high-quality multiple choice questions.

DIFFICULTY MIX (per batch of 10):
- Easy (4): Direct recall - "What should you check before starting?"
- Medium (4): Understanding - "Why do you wait for the green light?"
- Hard (2): Application - "If X happens, what should you do first?"

TOPIC MIX:
- Safety procedures (2-3 questions)
- Startup/shutdown (2-3 questions)
- Normal operation (2-3 questions)
- Problem identification (2-3 questions)

QUESTION QUALITY:
- Clear and specific (one concept per question)
- Realistic distractors (plausible but wrong)
- Fair and straightforward (no tricks)
- Based directly on manual content

OUTPUT (JSON):
{{
  "questions": [
    {{
      "question_number": 1,
      "question_text": "[Clear question]",
      "option_a": "[Plausible option]",
      "option_b": "[Plausible option]",
      "option_c": "[Plausible option]",
      "option_d": "[Plausible option]",
      "correct_answer": "B",
      "explanation": "[Why B is correct; why others are wrong]",
      "difficulty_level": "easy",
      "topic_category": "safety",
      "page_references": [12]
    }},
    ... (9 more)
  ]
}}
"""

QUESTION_GEN_HUMAN = """OPERATOR MANUAL:
{operator_summary}

FOCUS CONTENT (Pages {page_start}-{page_end}):
{focused_content}

Generate 10 questions: 4 easy, 4 medium, 2 hard. Mix topics. Return valid JSON."""
```

---

### Template 4: Critique (Binary Pass/Fail)

```python
CRITIQUE_SYSTEM = """You are a quality auditor for {output_type}.

CRITICAL CHECKS:
1. {check_1}
2. {check_2}
3. {check_3}

ACCEPT if {threshold}% meets standards. Minor issues OK.

OUTPUT:
If acceptable:
PASS

If major issues:
FAIL
ISSUES:
- [Specific problem with example]
- [What needs fixing]
"""

CRITIQUE_HUMAN = """SOURCE:
{source}

OUTPUT TO VALIDATE:
{output}

Quick audit: {validation_questions}. If acceptable, say PASS. If issues, list them."""
```

---

### Template 5: Revision (Targeted Fixes)

```python
REVISE_SYSTEM = """Revise the {output_type} to fix identified issues.

RULES:
1. Fix only what critique mentions
2. Check source for correct information
3. Keep everything else unchanged
4. Maintain same format
"""

REVISE_HUMAN = """SOURCE:
{source}

CURRENT DRAFT:
{draft}

ISSUES:
{critique}

Fix the issues. Keep same format."""
```

---

## Implementation Checklist

### For Summarization Pipeline

- [ ] Define CATALOG, SCHEMA constants
- [ ] Set LLM_MODEL (databricks-meta-llama-3-1-70b-instruct)
- [ ] Set TEMPERATURE (0.2 technical, 0.3 operator)
- [ ] Set MAX_TOKENS (2048 map, 8192 reduce)
- [ ] Set BATCH_SIZE (20 chunks recommended)
- [ ] Set CONTEXT_WINDOW (3 batches)
- [ ] Implement call_llm() with DataFrame pattern
- [ ] Implement hierarchical_reduce_to_sop() for token limits
- [ ] Create technical summary prompts (system + human)
- [ ] Create operator summary prompts (system + human)
- [ ] Create critique prompts for both
- [ ] Create revision prompts for both
- [ ] Implement Map-Reduce pattern with context
- [ ] Implement reflection pattern (draft → critique → revise)
- [ ] Save to document_summaries table (2 rows per PDF)

### For Question Generation Pipeline

- [ ] Set TEMPERATURE (0.7 for creative distractors)
- [ ] Set MAX_TOKENS (4096 for 10 questions)
- [ ] Set BATCH_SIZE (10 questions)
- [ ] Create question generation prompt (JSON output)
- [ ] Create validation prompt (pass/fail)
- [ ] Implement JSON parsing and validation
- [ ] Implement batch generation loop (60-80 questions total)
- [ ] Add difficulty distribution (40% easy, 40% medium, 20% hard)
- [ ] Add topic distribution (safety, operation, maintenance, troubleshooting)
- [ ] Link to page_references and chunk_references
- [ ] Save to operator_questions table

---

## Key Takeaways

1. **Role + Goal + Rules + Format** = Effective prompt structure
2. **DataFrame pattern for ai_query** avoids SQL escaping issues
3. **Reflection pattern** (draft → critique → revise) improves quality
4. **Hierarchical reduction** handles documents of any size
5. **Context windows** prevent repetition across batches
6. **Temperature tuning** matters: low for facts, higher for creativity
7. **Batch processing** (10-20 items) optimal for quality and speed
8. **Binary critique** (PASS/FAIL) clearer than subjective scoring
9. **Dual summaries** (technical + operator) serve different audiences
10. **Question batches of 10** proven optimal for MCQ generation

---

## Sources

- Existing codebase: `databricks/jobs/graph_summarization_pipeline.py`
- Existing codebase: `databricks/jobs/graph_community_pipeline.py`
- Existing codebase: `NextLevel/jobs/ingest_pipeline.py`
- Previous research: `NextLevel/docs/06_RESEARCH_BEST_PRACTICES.md`
- Previous research: `NextLevel/docs/07_OPTIMAL_CHUNKING_STRATEGY.md`

---

*Last Updated: 2025-11-30*
*Next: Implement these patterns in summarization_pipeline.py and question_generation_pipeline.py*
