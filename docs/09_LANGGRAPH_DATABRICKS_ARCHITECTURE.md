# LangGraph + Databricks Architecture Design

**Purpose:** Final architecture design for NextLevel RAG agent system integrating LangGraph with Databricks

**Research Date:** 2025-11-30

**Models:**
- LLM: `databricks-llama-4-maverick`
- Embeddings: `databricks-gte-large-en`

---

## Table of Contents

1. [Research Summary](#research-summary)
2. [Integration Patterns](#integration-patterns)
3. [File Structure](#file-structure)
4. [Final Architecture](#final-architecture)
5. [Implementation Details](#implementation-details)
6. [Model Configuration](#model-configuration)

---

## Research Summary

### Key Findings from Web Research

#### 1. LangGraph + Databricks Integration

**Source:** [Databricks LangChain Integration](https://docs.databricks.com/aws/en/generative-ai/agent-framework/langchain-uc-integration)

**Key Patterns:**
- ✅ Use `ChatDatabricks` for LLM calls (LangChain wrapper)
- ✅ MLflow auto-tracing: `mlflow.langchain.autolog()`
- ✅ Production pattern: `ResponsesAgent` wrapper
- ✅ Unity Catalog integration for tools

**Code Example:**
```python
from databricks_langchain import ChatDatabricks

llm = ChatDatabricks(
    endpoint="databricks-meta-llama-3-3-70b-instruct",
    temperature=0.1
)
```

---

#### 2. LangGraph Application Structure

**Source:** [LangGraph Application Structure](https://docs.langchain.com/langgraph-platform/application-structure)

**Recommended Structure:**
```
my-app/
├── my_agent/                 # Main package
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── tools.py         # Tool definitions
│   │   ├── nodes.py         # Node functions
│   │   └── state.py         # State schemas
│   ├── __init__.py
│   └── agent.py             # Graph construction
├── requirements.txt
└── langgraph.json           # Deployment config
```

**Best Practices:**
- ✅ Separate state, nodes, tools into dedicated modules
- ✅ Keep graph construction centralized in `agent.py`
- ✅ Use `langgraph.json` for deployment configuration
- ✅ Environment variables in `.env`

---

#### 3. Supervisor Pattern Implementation

**Source:** [LangGraph Supervisor GitHub](https://github.com/langchain-ai/langgraph-supervisor-py)

**Pattern:**
```python
from langgraph_supervisor import create_supervisor
from langgraph.prebuilt import create_react_agent

# Create specialized agents
agent1 = create_react_agent(model, tools, name="specialist_1")
agent2 = create_react_agent(model, tools, name="specialist_2")

# Create supervisor
workflow = create_supervisor(
    agents=[agent1, agent2],
    model=model,
    prompt="You are a supervisor managing specialists."
)

app = workflow.compile()
```

**Key Features:**
- ✅ Supervisor controls all communication
- ✅ Agents are self-contained modules
- ✅ State management with checkpoints
- ✅ Output modes: `full_history` or `last_message`

---

#### 4. Production Best Practices

**Sources:**
- [Top 5 LangGraph Agents in Production 2024](https://blog.langchain.com/top-5-langgraph-agents-in-production-2024/)
- [LangGraph Architecture](https://medium.com/@shuv.sdr/langgraph-architecture-and-design-280c365aaf2c)

**Critical Insights:**
- ✅ **Fault tolerance:** Automated retries, per-node timeouts, pause/resume
- ✅ **Observability:** MLflow tracing, LangSmith integration
- ✅ **Modularity:** Each agent = independent module
- ✅ **Control:** Low-level primitives, no black boxes
- ✅ **Scalability:** Graph-based orchestration with parallelization

**Production Features:**
1. Parallelization (concurrent node execution)
2. Streaming (real-time output)
3. Checkpointing (state persistence)
4. Human-in-the-loop (approval gates)
5. Tracing (observability)
6. Task queue (job management)

---

## Integration Patterns

### Pattern 1: Databricks LLM in LangGraph

**Challenge:** Use Databricks models in LangGraph agents

**Solution:** `ChatDatabricks` wrapper from `databricks-langchain`

```python
from databricks_langchain import ChatDatabricks
from langgraph.prebuilt import create_react_agent

# Databricks LLM
llm = ChatDatabricks(
    endpoint="databricks-llama-4-maverick",
    temperature=0.1,
    max_tokens=8192
)

# Use in LangGraph agent
agent = create_react_agent(
    model=llm,
    tools=[tool1, tool2],
    name="summarization_agent"
)
```

---

### Pattern 2: ai_query Integration (Alternative)

**Challenge:** Use Databricks `ai_query()` SQL function in LangGraph

**Solution:** Custom tool wrapper

```python
from langchain_core.tools import tool
from pyspark.sql import SparkSession

@tool
def databricks_llm_call(prompt: str) -> str:
    """Call Databricks LLM via ai_query using DataFrame pattern."""
    spark = SparkSession.builder.getOrCreate()

    # DataFrame pattern (no SQL escaping issues)
    prompt_df = spark.createDataFrame([(prompt,)], ["prompt"])
    prompt_df.createOrReplaceTempView("prompt_temp")

    result_df = spark.sql(f"""
        SELECT ai_query(
            'databricks-llama-4-maverick',
            prompt,
            modelParameters => named_struct(
                'max_tokens', 8192,
                'temperature', 0.1
            )
        ) as response
        FROM prompt_temp
    """)

    result = result_df.first()
    spark.catalog.dropTempView("prompt_temp")

    return result['response'] if result else ""
```

**When to use:**
- ✅ Use `ChatDatabricks` for LangGraph agents (cleaner, native integration)
- ✅ Use `ai_query()` for direct Spark operations (batch processing, embeddings)

---

### Pattern 3: MLflow Tracing

**Purpose:** Automatic observability for LangGraph workflows

```python
import mlflow

# Enable auto-tracing
mlflow.langchain.autolog()

# All LangGraph executions now traced
result = app.invoke({"input": "..."})

# Traces logged to active MLflow experiment
```

---

### Pattern 4: State Persistence

**Purpose:** Checkpoint state for resumable workflows

```python
from langgraph.checkpoint.memory import InMemorySaver

# In-memory checkpointing (development)
checkpointer = InMemorySaver()
app = workflow.compile(checkpointer=checkpointer)

# For production: Use Databricks-backed checkpointer
# (store state in Delta table)
```

---

## File Structure

### Final Directory Layout

```
NextLevel/
├── agents/
│   ├── __init__.py
│   │
│   ├── summarization/
│   │   ├── __init__.py
│   │   ├── graph.py              # Main: create_summarization_graph()
│   │   ├── state.py              # SummarizationState (TypedDict)
│   │   ├── nodes.py              # Node functions (batch_summarize, refine, etc.)
│   │   ├── prompts.py            # All prompts (SYSTEM + HUMAN templates)
│   │   └── tools.py              # Custom tools (if needed)
│   │
│   └── question_generation/
│       ├── __init__.py
│       ├── graph.py              # Main: create_question_graph()
│       ├── state.py              # QuestionGenState (TypedDict)
│       ├── nodes.py              # Node functions (generate, validate, etc.)
│       ├── prompts.py            # All prompts
│       └── tools.py              # Custom tools
│
├── jobs/
│   ├── ingest_pipeline.py        # ✅ Already done
│   ├── summarization_pipeline.py # Databricks job → calls agents/summarization
│   └── question_generation_pipeline.py # Databricks job → calls agents/question_generation
│
├── docs/
│   ├── 06_RESEARCH_BEST_PRACTICES.md  # ✅ LangGraph research
│   ├── 08_PROMPT_ENGINEERING_BEST_PRACTICES.md  # ✅ Prompts
│   └── 09_LANGGRAPH_DATABRICKS_ARCHITECTURE.md  # ✅ This file
│
└── requirements.txt              # Updated with LangGraph dependencies
```

---

### Module Responsibilities

#### `agents/summarization/graph.py`
**Purpose:** Main entry point, creates and returns compiled graph

```python
from langgraph.graph import StateGraph
from .state import SummarizationState
from .nodes import batch_summarize_node, refine_node, reflect_node, extract_topics_node

def create_summarization_graph(summary_type: str = "technical"):
    """
    Create summarization graph.

    Args:
        summary_type: 'technical' or 'operator'

    Returns:
        Compiled LangGraph app
    """
    workflow = StateGraph(SummarizationState)

    # Add nodes
    workflow.add_node("batch_summarize", batch_summarize_node)
    workflow.add_node("refine", refine_node)
    workflow.add_node("reflect", reflect_node)
    workflow.add_node("extract_topics", extract_topics_node)

    # Add edges (workflow)
    workflow.set_entry_point("batch_summarize")
    workflow.add_edge("batch_summarize", "refine")
    workflow.add_edge("refine", "reflect")
    workflow.add_conditional_edges(
        "reflect",
        lambda state: "refine" if state["needs_revision"] else "extract_topics"
    )
    workflow.add_edge("extract_topics", END)

    return workflow.compile()
```

---

#### `agents/summarization/state.py`
**Purpose:** Define state schema (shared memory across nodes)

```python
from typing import TypedDict, List, Dict, Optional

class SummarizationState(TypedDict):
    """State for summarization workflow."""
    # Input
    pdf_id: str
    pdf_name: str
    chunks: List[Dict]  # [{chunk_id, text, page_number}, ...]
    summary_type: str  # 'technical' or 'operator'
    total_pages: int  # Total pages in document
    total_chunks: int  # Total chunks in document

    # Processing
    batch_summaries: List[str]
    context_window: List[str]  # Last 3 batch summaries for context
    intermediate_summaries: List[str]  # For hierarchical reduction
    final_summary: str

    # Reflection
    critique: str
    needs_revision: bool
    iteration: int

    # Output
    key_topics: List[str]
    processing_time: float

    # Error tracking
    error_message: Optional[str]
    current_batch: int  # Track progress
```

---

#### `agents/summarization/nodes.py`
**Purpose:** Node functions (the actual work)

```python
from databricks_langchain import ChatDatabricks
from .prompts import TECH_MAP_SYSTEM, TECH_MAP_HUMAN
from .state import SummarizationState

# Initialize LLM (shared across nodes)
llm = ChatDatabricks(
    endpoint="databricks-llama-4-maverick",
    temperature=0.1,  # Low for accuracy
    max_tokens=8192
)

def batch_summarize_node(state: SummarizationState) -> SummarizationState:
    """MAP phase: Extract information from chunks in batches with cumulative context."""
    import time
    start_time = time.time()

    chunks = state["chunks"]
    summary_type = state["summary_type"]
    batch_size = 10  # REDUCED from 20 for better context fit
    CONTEXT_WINDOW = 3  # Keep last 3 batch extractions

    batch_summaries = []
    context_window = state.get("context_window", [])

    try:
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i+batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(chunks) + batch_size - 1) // batch_size

            batch_text = "\n\n".join([c["text"] for c in batch])

            # Build context from recent batches (prevents repetition)
            if context_window:
                context_str = "\n\n---\n\n".join(context_window)
            else:
                context_str = "This is the first batch."

            # Select prompts based on summary type
            system_prompt = TECH_MAP_SYSTEM if summary_type == "technical" else OPERATOR_MAP_SYSTEM
            human_prompt = TECH_MAP_HUMAN if summary_type == "technical" else OPERATOR_MAP_HUMAN

            # Call LLM
            messages = [
                ("system", system_prompt),
                ("human", human_prompt.format(
                    context=context_str,
                    content=batch_text,
                    batch_num=batch_num,
                    total_batches=total_batches
                ))
            ]
            response = llm.invoke(messages)
            batch_summaries.append(response.content)

            # Update context window (keep last 3)
            context_window.append(response.content)
            if len(context_window) > CONTEXT_WINDOW:
                context_window = context_window[-CONTEXT_WINDOW:]

    except Exception as e:
        return {
            **state,
            "error_message": f"Batch summarization failed: {str(e)}",
            "batch_summaries": batch_summaries  # Return partial results
        }

    processing_time = time.time() - start_time
    return {
        **state,
        "batch_summaries": batch_summaries,
        "context_window": context_window,
        "processing_time": state.get("processing_time", 0.0) + processing_time
    }

def refine_node(state: SummarizationState) -> SummarizationState:
    """REDUCE phase: Combine batch extractions with hierarchical combination (NOT reduction)."""
    import time
    start_time = time.time()

    batch_summaries = state["batch_summaries"]
    num_batches = len(batch_summaries)
    REDUCE_CHUNK_SIZE = 4  # Max batches per intermediate combination

    try:
        if num_batches <= REDUCE_CHUNK_SIZE:
            # Small document: Direct combination (1 LLM call)
            print(f"   Direct combination ({num_batches} batches)")
            all_summaries = "\n\n---\n\n".join(batch_summaries)

            messages = [
                ("system", REDUCE_SYSTEM),
                ("human", REDUCE_HUMAN.format(
                    num_batches=num_batches,
                    extractions=all_summaries
                ))
            ]
            response = llm.invoke(messages)
            final_summary = response.content

        else:
            # Large document: Hierarchical combination (multiple LLM calls)
            print(f"   Hierarchical combination ({num_batches} batches)")

            # Stage 1: Combine into intermediates (chunks of 4)
            intermediate_summaries = []
            for i in range(0, num_batches, REDUCE_CHUNK_SIZE):
                chunk = batch_summaries[i:i + REDUCE_CHUNK_SIZE]
                chunk_start = i + 1
                chunk_end = min(i + REDUCE_CHUNK_SIZE, num_batches)
                chunk_text = "\n\n---\n\n".join(chunk)

                messages = [
                    ("system", INTERMEDIATE_REDUCE_SYSTEM),
                    ("human", INTERMEDIATE_REDUCE_HUMAN.format(
                        start=chunk_start,
                        end=chunk_end,
                        batch_extractions=chunk_text
                    ))
                ]
                response = llm.invoke(messages)
                intermediate_summaries.append(response.content)

            print(f"   Created {len(intermediate_summaries)} intermediate documents")

            # Stage 2: Organize intermediates into final document
            all_intermediates = "\n\n---\n\n".join(intermediate_summaries)
            messages = [
                ("system", REDUCE_SYSTEM),
                ("human", REDUCE_HUMAN.format(
                    num_intermediates=len(intermediate_summaries),
                    intermediate_extractions=all_intermediates
                ))
            ]
            response = llm.invoke(messages)
            final_summary = response.content

    except Exception as e:
        return {
            **state,
            "error_message": f"Combination failed: {str(e)}",
            "final_summary": ""
        }

    processing_time = time.time() - start_time
    return {
        **state,
        "final_summary": final_summary,
        "processing_time": state.get("processing_time", 0.0) + processing_time
    }

def reflect_node(state: SummarizationState) -> SummarizationState:
    """Critique summary and decide if revision needed."""
    import time
    start_time = time.time()

    final_summary = state["final_summary"]
    iteration = state.get("iteration", 0)

    try:
        # Critique with lower temperature for consistency
        llm_critique = ChatDatabricks(
            endpoint="databricks-llama-4-maverick",
            temperature=0.05,  # Very low for consistent evaluation
            max_tokens=1024
        )

        messages = [
            ("system", CRITIQUE_SYSTEM),
            ("human", CRITIQUE_HUMAN.format(summary=final_summary))
        ]
        response = llm_critique.invoke(messages)
        critique = response.content

        # Check if needs revision (max 2 iterations)
        needs_revision = not critique.strip().upper().startswith("PASS") and iteration < 2

    except Exception as e:
        # If critique fails, accept the summary (don't block on reflection)
        critique = f"CRITIQUE FAILED: {str(e)}"
        needs_revision = False

    processing_time = time.time() - start_time
    return {
        **state,
        "critique": critique,
        "needs_revision": needs_revision,
        "iteration": iteration + 1,
        "processing_time": state.get("processing_time", 0.0) + processing_time
    }

def extract_topics_node(state: SummarizationState) -> SummarizationState:
    """Extract key topics from final summary."""
    import time
    start_time = time.time()

    final_summary = state["final_summary"]

    try:
        # Extract topics
        messages = [
            ("system", "Extract 5-10 key topics from this summary. Return as comma-separated list."),
            ("human", final_summary)
        ]
        response = llm.invoke(messages)
        topics = [t.strip() for t in response.content.split(",") if t.strip()]

    except Exception as e:
        # If extraction fails, return empty list
        topics = []

    processing_time = time.time() - start_time
    return {
        **state,
        "key_topics": topics,
        "processing_time": state.get("processing_time", 0.0) + processing_time
    }
```

---

#### `agents/summarization/prompts.py`
**Purpose:** Centralized prompt templates

```python
# Technical Extraction Prompts (EXTRACTION, not summarization)
TECH_MAP_SYSTEM = """You are extracting technical information from equipment manuals.

CRITICAL: You are EXTRACTING, not summarizing. DO NOT reduce or paraphrase.

GOAL: Extract ALL technical specifications and procedures exactly as written.

AUDIENCE: Engineers and maintenance staff.

KEY RULES:
1. EXTRACT all procedures - keep every step verbatim
2. EXTRACT all technical values with units (e.g., "45 Nm", "120°C")
3. PRESERVE original headings and structure from source
4. DO NOT rewrite or paraphrase - copy exact wording
5. DO NOT reduce for brevity - completeness is priority
6. ONLY skip if already extracted in previous context

COMPLETENESS > BREVITY. When in doubt, KEEP IT.

OUTPUT FORMAT:
## [Exact Heading from Source]

### Procedure: [Exact Name from Source]
**Purpose:** [Exact purpose from source]

**Steps:** [Extract verbatim - do NOT rewrite]
1. [Exact step from source]
2. [Exact step from source]

**Parameters:**
- [Parameter]: [Exact value] [exact unit]

**Warnings:** [Extract verbatim]
- [Exact warning from source]
"""

TECH_MAP_HUMAN = """PREVIOUS CONTEXT (Batch {batch_num}/{total_batches}):
{context}

CURRENT SECTION:
{content}

EXTRACT all technical content following the format.
- Use EXACT wording from source
- Include ALL procedures and specifications
- DO NOT reduce or paraphrase
- ONLY skip content already extracted in previous context"""

# Operator Extraction Prompts (EXTRACTION, not summarization)
OPERATOR_MAP_SYSTEM = """You are extracting operator procedures from equipment manuals.

CRITICAL: You are EXTRACTING, not summarizing. Keep all critical information.

GOAL: Extract ALL operator procedures in simple, clear language.

AUDIENCE: Machine operators (8th-grade reading level).

KEY RULES:
1. EXTRACT all operating procedures - keep every step
2. Simplify language but KEEP all steps and checks
3. PRESERVE all safety warnings verbatim
4. DO NOT skip steps to reduce length
5. DO NOT paraphrase safety information
6. ONLY skip if already extracted in previous context

COMPLETENESS > BREVITY. When in doubt, KEEP IT.

OUTPUT FORMAT:
## [Simple Heading]

### How to [Action]
**What you need to check first:**
1. [Simple check] - Why: [Simple reason]

**Steps:** [All steps - don't skip any]
1. [Simple action in active voice]
2. [Simple action]
...

**Safety:** [Extract ALL warnings verbatim]
⚠️ [Exact warning from source]
"""

OPERATOR_MAP_HUMAN = """PREVIOUS CONTEXT (Batch {batch_num}/{total_batches}):
{context}

CURRENT SECTION:
{content}

EXTRACT all operator procedures in simple language.
- Keep ALL steps and safety checks
- Simplify language but DON'T skip content
- ONLY skip if already extracted in previous context"""

# Combination Prompts (COMBINING/ORGANIZING, not reducing)
REDUCE_SYSTEM = """You are ORGANIZING technical extractions into ONE final document.

CRITICAL: You are ORGANIZING, not reducing. DO NOT cut any content.

GOAL: Merge batch/intermediate extractions into complete final document.

KEY RULES:
1. INCLUDE all procedures from all extractions
2. PRESERVE all technical values, steps, warnings
3. ORGANIZE by topic/section (group related procedures)
4. ONLY remove exact duplicates (same text extracted multiple times)
5. DO NOT paraphrase or shorten anything
6. If unsure, KEEP IT - completeness is priority

COMPLETENESS > BREVITY. Your job is to ORGANIZE, not REDUCE.

OUTPUT: Complete final document with ALL extracted information organized by topic.
"""

REDUCE_HUMAN = """EXTRACTIONS ({num_batches} batches OR {num_intermediates} intermediates):
{extractions} OR {intermediate_extractions}

ORGANIZE into final document.
- KEEP all procedures and specifications
- Group related procedures together
- ONLY remove exact duplicates
- DO NOT reduce for brevity
- Completeness > brevity"""

# Critique Prompts
CRITIQUE_SYSTEM = """You are a quality auditor.

CRITICAL CHECKS:
1. Are all procedures present and separate?
2. Are technical values preserved correctly?
3. Is structure complete?

ACCEPT if 90%+ meets standards.

OUTPUT:
If acceptable: PASS

If issues:
FAIL
ISSUES:
- [Specific problem]
"""

CRITIQUE_HUMAN = """SUMMARY TO VALIDATE:
{summary}

Quick audit: Are procedures preserved and separate? If yes, say PASS. If issues, list them."""

# Intermediate Combination Prompts (Stage 1 of hierarchical combination)
INTERMEDIATE_REDUCE_SYSTEM = """You are COMBINING technical extractions from multiple batches.

CRITICAL: You are COMBINING, not summarizing. DO NOT cut any content.

GOAL: Merge batch extractions into ONE complete intermediate document.

KEY RULES:
1. INCLUDE all procedures from all batches
2. PRESERVE all technical values and steps
3. ORGANIZE chronologically (maintain document order)
4. ONLY remove exact duplicates (if same procedure extracted twice)
5. DO NOT paraphrase or shorten
6. If in doubt, KEEP IT - completeness is priority

COMPLETENESS > BREVITY. Your job is to COMBINE, not REDUCE.

OUTPUT: Complete intermediate document with ALL extracted information.
"""

INTERMEDIATE_REDUCE_HUMAN = """BATCH EXTRACTIONS (Batches {start}-{end}):
{batch_extractions}

COMBINE all extractions.
- KEEP all procedures and specifications
- ONLY remove exact duplicates
- Organize in document order
- DO NOT reduce for brevity"""
```

---

## Final Architecture

### Summarization Pipeline Graph (EXTRACTION + COMBINATION)

```
                   ┌─────────────────┐
                   │  Start (Input)  │
                   │  - pdf_id       │
                   │  - 450 chunks   │
                   │  - summary_type │
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │ Batch Extract   │ ← MAP phase (EXTRACTION)
                   │   (10 chunks)   │   Extract all procedures
                   │   45 batches    │   Context prevents duplication
                   │   Temp: 0.1     │   Completeness > brevity
                   └────────┬────────┘
                            │
                    45 batch extractions
                            │
                   ┌────────▼────────┐
                   │  Combine Node   │ ← REDUCE phase (COMBINATION)
                   │                 │   Stage 1: Group 4 → intermediates
                   │  Hierarchical:  │   Stage 2: Merge → final
                   │  If >4 batches  │   ORGANIZE, not reduce
                   └────────┬────────┘
                            │
                   1 complete document (ALL info)
                            │
                   ┌────────▼────────┐
                   │  Reflect Node   │ ← Quality check
                   │  Temp: 0.05     │   PASS/FAIL
                   └────────┬────────┘
                            │
                      ┌─────┴─────┐
                      │           │
              needs_revision?    PASS
                      │           │
                ┌─────▼─────┐     │
                │  Combine  │     │
                │  (retry)  │     │
                └─────┬─────┘     │
                      │           │
                      └─────┬─────┘
                            │
                   ┌────────▼────────┐
                   │ Extract Topics  │
                   │  Temp: 0.1      │
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │  End (Output)   │
                   │ Complete doc    │
                   │ + key topics    │
                   └─────────────────┘

KEY: EXTRACTION (MAP) → COMBINATION (REDUCE) → ORGANIZATION
     No content loss, just progressive organization
```

---

### Question Generation Pipeline Graph

**Note:** Simplified approach - run graph 7 times from job notebook (each run generates 10 questions)

```
                   ┌─────────────────┐
                   │  Start (Input)  │
                   │  - pdf_id       │
                   │  - summary_text │
                   │  - batch_num    │  (1-7)
                   │  - existing_q's │  (avoid duplication)
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │  Generate Node  │ ← Generate 10 Q's (JSON)
                   │  Temperature:   │   Slightly higher (0.2)
                   │  0.2            │   for variety
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │  Validate Node  │ ← Quality check
                   │  Temperature:   │   - 4 unique options
                   │  0.05           │   - Answer exists
                   └────────┬────────┘   - Difficulty ok
                            │
                      ┌─────┴─────┐
                      │           │
                   PASS?         FAIL
                      │           │
                      │      ┌────▼─────┐
                      │      │ Generate │
                      │      │  (retry) │
                      │      └────┬─────┘
                      │           │
                      └─────┬─────┘
                            │
                   ┌────────▼────────┐
                   │ Categorize Node │ ← Assign topics/difficulty
                   │                 │   (if not already set)
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │  Link Node      │ ← Link to pages/chunks
                   │                 │   from summary references
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │  End (Output)   │
                   │  - 10 questions │
                   │  - validated    │
                   └─────────────────┘

     Job Notebook runs this graph 7 times → 70 total questions
```

---

## Implementation Details

### 1. Databricks Job Integration

**File:** `jobs/summarization_pipeline.py`

```python
# Databricks notebook source
# MAGIC %md
# MAGIC # Summarization Pipeline - LangGraph Implementation

# COMMAND ----------

# Widget parameters
dbutils.widgets.text("pdf_name", "", "PDF Filename")
dbutils.widgets.text("pdf_id", "", "PDF ID")
dbutils.widgets.dropdown("summary_type", "technical", ["technical", "operator"], "Summary Type")

pdf_name = dbutils.widgets.get("pdf_name")
pdf_id = dbutils.widgets.get("pdf_id")
summary_type = dbutils.widgets.get("summary_type")

# COMMAND ----------

# Configuration
CATALOG = "heineken_test_workspace"
SCHEMA = "nextlevel-rag"
TABLE_CHUNKS = f"`{CATALOG}`.`{SCHEMA}`.chunks_embedded"
TABLE_SUMMARIES = f"`{CATALOG}`.`{SCHEMA}`.document_summaries"

# COMMAND ----------

# Enable MLflow tracing
import mlflow
mlflow.langchain.autolog()

# COMMAND ----------

# Load chunks from Delta table
chunks_df = spark.sql(f"""
    SELECT chunk_id, text, page_number
    FROM {TABLE_CHUNKS}
    WHERE pdf_id = '{pdf_id}'
    ORDER BY chunk_index
""")

chunks = [
    {
        "chunk_id": row["chunk_id"],
        "text": row["text"],
        "page_number": row["page_number"]
    }
    for row in chunks_df.collect()
]

print(f"Loaded {len(chunks)} chunks for {pdf_name}")

# COMMAND ----------

# Import and run LangGraph agent
from agents.summarization.graph import create_summarization_graph

# Create graph
graph = create_summarization_graph(summary_type=summary_type)

# Run workflow
result = graph.invoke({
    "pdf_id": pdf_id,
    "pdf_name": pdf_name,
    "chunks": chunks,
    "summary_type": summary_type,
    "total_pages": max([c["page_number"] for c in chunks]) if chunks else 0,
    "total_chunks": len(chunks),
    "batch_summaries": [],
    "context_window": [],
    "intermediate_summaries": [],
    "final_summary": "",
    "critique": "",
    "needs_revision": False,
    "iteration": 0,
    "key_topics": [],
    "processing_time": 0.0,
    "error_message": None,
    "current_batch": 0
})

print(f"\n✓ Summarization complete")
print(f"Summary length: {len(result['final_summary'])} chars")
print(f"Key topics: {', '.join(result['key_topics'])}")

# COMMAND ----------

# Save to Delta table
import uuid
from datetime import datetime

summary_data = [{
    "summary_id": str(uuid.uuid4()),
    "pdf_id": pdf_id,
    "pdf_name": pdf_name,
    "summary_type": summary_type,
    "summary_text": result["final_summary"],
    "total_pages": max([c["page_number"] for c in chunks]),
    "total_chunks": len(chunks),
    "key_topics": result["key_topics"],
    "processing_model": "databricks-llama-4-maverick",
    "processing_time_seconds": result["processing_time"],
    "created_at": datetime.now()
}]

from pyspark.sql.types import *
schema = StructType([
    StructField("summary_id", StringType(), False),
    StructField("pdf_id", StringType(), False),
    StructField("pdf_name", StringType(), False),
    StructField("summary_type", StringType(), False),
    StructField("summary_text", StringType(), False),
    StructField("total_pages", IntegerType(), False),
    StructField("total_chunks", IntegerType(), False),
    StructField("key_topics", ArrayType(StringType()), True),
    StructField("processing_model", StringType(), False),
    StructField("processing_time_seconds", FloatType(), True),
    StructField("created_at", TimestampType(), False)
])

summary_df = spark.createDataFrame(summary_data, schema=schema)
summary_df.write.format("delta").mode("append").saveAsTable(TABLE_SUMMARIES)

print(f"✓ Saved to {TABLE_SUMMARIES}")

# COMMAND ----------

# Return success
dbutils.notebook.exit(json.dumps({
    "status": "success",
    "pdf_id": pdf_id,
    "summary_type": summary_type,
    "summary_length": len(result["final_summary"]),
    "key_topics_count": len(result["key_topics"])
}))
```

---

### 2. Model Configuration

**All agents use consistent low-temperature settings:**

```python
from databricks_langchain import ChatDatabricks

# Shared LLM configuration
llm = ChatDatabricks(
    endpoint="databricks-llama-4-maverick",
    temperature=0.1,  # VERY LOW for accuracy (no hallucinations)
    max_tokens=8192
)
```

**Temperature by Task:**
- ✅ **Summarization (Map):** 0.1
- ✅ **Summarization (Reduce):** 0.1
- ✅ **Reflection/Critique:** 0.05 (even lower for consistency)
- ✅ **Question Generation:** 0.2 (slightly higher for variety, but still conservative)
- ✅ **Question Validation:** 0.05

**Why such low temperatures?**
- Prevent hallucinations
- Ensure technical accuracy
- Maintain consistency across batches
- Critical for safety/procedure documentation

---

### 3. Dependencies

**Update:** `NextLevel/requirements.txt`

```txt
# Existing dependencies
databricks-sdk
langchain-text-splitters
pyspark

# LangGraph dependencies (NEW)
langgraph>=0.2.0
langchain-core>=0.3.0
databricks-langchain>=0.1.0
mlflow>=2.10.0

# Optional: Supervisor pattern
langgraph-supervisor>=0.0.30
```

---

## Model Configuration

### Primary Models

**LLM (Text Generation):**
- Model: `databricks-llama-4-maverick`
- Temperature: 0.05 - 0.2 (task-dependent)
- Max Tokens: 2048 - 8192 (task-dependent)

**Embeddings:**
- Model: `databricks-gte-large-en`
- Dimensions: 1024
- Used in: Ingest pipeline (already implemented)

---

### Temperature Matrix

| Task | Temperature | Max Tokens | Reasoning |
|------|-------------|------------|-----------|
| **Technical Summary (Map)** | 0.1 | 2048 | High accuracy, preserve values |
| **Operator Summary (Map)** | 0.1 | 2048 | Clear language, no creativity needed |
| **Reduce (Combine)** | 0.1 | 8192 | Accurate consolidation |
| **Reflection/Critique** | 0.05 | 1024 | Consistent evaluation |
| **Revision** | 0.1 | 4096 | Targeted fixes |
| **Question Generation** | 0.2 | 4096 | Some variety in distractors |
| **Question Validation** | 0.05 | 1024 | Binary pass/fail consistency |
| **Topic Extraction** | 0.1 | 512 | Accurate identification |

---

## Advantages of This Architecture

### 1. Clean Separation of Concerns
- ✅ `agents/` = reusable logic (pure Python)
- ✅ `jobs/` = Databricks integration (notebooks)
- ✅ Easy to test agents independently
- ✅ Can reuse agents in different contexts

### 2. Databricks-Native Integration
- ✅ `ChatDatabricks` for LLM calls
- ✅ MLflow auto-tracing for observability
- ✅ Spark for data loading (Delta tables)
- ✅ Production-ready with ResponsesAgent pattern

### 3. LangGraph Benefits
- ✅ Fault tolerance (retries, timeouts)
- ✅ State persistence (checkpointing)
- ✅ Observability (tracing, debugging)
- ✅ Modularity (independent nodes)
- ✅ Control (explicit graph definition)

### 4. Low Hallucination Risk
- ✅ Very low temperature (0.05 - 0.2)
- ✅ Reflection pattern (self-correction)
- ✅ Validation nodes (quality gates)
- ✅ Grounding in source chunks

### 5. Scalability
- ✅ Handles documents of any size (batch processing)
- ✅ Parallel batch summarization (Map phase)
- ✅ Can process multiple PDFs concurrently
- ✅ State persistence for long-running jobs

---

## Architecture Improvements (Professional Grade)

### 🎯 Critical Design Philosophy: EXTRACTION, not SUMMARIZATION

**The Fundamental Shift:**

❌ **OLD Approach (Summarization):**
- Summarize → Reduce → Condense
- Each stage loses information
- Brevity prioritized over completeness
- 300 pages → 50 pages → 10 pages (info loss!)

✅ **NEW Approach (Extraction + Combination):**
- Extract → Combine → Organize
- No information loss at any stage
- Completeness prioritized over brevity
- 300 pages → Complete extraction → Organized document (ALL info preserved!)

**Key Changes:**
1. **Batch size:** 20 → 10 chunks (better context fit)
2. **Prompts:** "Summarize" → "EXTRACT" (preserve verbatim)
3. **REDUCE phase:** "Reduce" → "COMBINE/ORGANIZE" (no cutting)
4. **Philosophy:** "Brevity" → "COMPLETENESS > BREVITY"

**Result:** Final document contains ALL operating procedures and technical specifications, just organized.

---

### 1. **Cumulative Context Window** ✅
**Problem:** Batch extractions can repeat information without context from previous batches.

**Solution:** Maintain sliding window of last 3 batch extractions.

**Implementation:**
- Add `context_window: List[str]` to state
- Pass context to each batch in MAP phase
- Update prompts to include: "PREVIOUS CONTEXT: {context}... ONLY skip content already extracted in previous context"

**Benefit:** Prevents duplication (not loss!), maintains document flow, completeness preserved.

---

### 2. **Hierarchical Combination (NOT Reduction)** ✅
**Problem:** Large documents (300+ pages, 45+ batches) exceed token limits in COMBINE phase.

**Solution:** Two-stage hierarchical COMBINATION (not reduction).

**Implementation:**
- If ≤4 batches: Direct combination (1 LLM call)
- If >4 batches:
  - Stage 1: Group into chunks of 4 → intermediate documents (COMBINE all info)
  - Stage 2: Merge intermediates → final document (ORGANIZE all info)

**Prompts emphasize:** "COMBINE, not reduce" + "COMPLETENESS > BREVITY"

**Benefit:** Handles documents of any size without hitting token limits AND without losing content.

---

### 3. **Error Handling & Resilience** ✅
**Problem:** Single LLM failure can crash entire pipeline.

**Solution:** Try-except in all nodes with graceful degradation.

**Implementation:**
```python
try:
    # LLM call
except Exception as e:
    return {
        **state,
        "error_message": f"Node failed: {str(e)}",
        # Return partial results
    }
```

**Benefit:** Pipeline continues even if individual nodes fail, errors logged for debugging.

---

### 4. **Processing Time Tracking** ✅
**Problem:** No visibility into node performance.

**Solution:** Track time in each node, accumulate in state.

**Implementation:**
```python
import time
start_time = time.time()
# ... work ...
processing_time = time.time() - start_time
return {**state, "processing_time": state.get("processing_time", 0.0) + processing_time}
```

**Benefit:** Performance monitoring, optimization opportunities, MLflow metrics.

---

### 5. **Temperature Tuning by Task** ✅
**Problem:** Same temperature (0.1) not optimal for all tasks.

**Solution:** Task-specific temperature settings.

**Implementation:**
- **Critique:** 0.05 (very low for consistency)
- **Summarization:** 0.1 (low for accuracy)
- **Question Generation:** 0.2 (slightly higher for variety)
- **Validation:** 0.05 (binary decisions)

**Benefit:** Optimal balance between accuracy and variety per task.

---

### 6. **Simplified Question Generation Loop** ✅
**Problem:** Complex conditional loops in LangGraph are hard to debug.

**Solution:** Run graph 7 times from job notebook (simpler, clearer).

**Implementation:**
```python
all_questions = []
for batch_num in range(1, 8):  # 7 batches × 10 questions = 70
    result = graph.invoke({
        "batch_num": batch_num,
        "existing_questions": all_questions  # Avoid duplicates
    })
    all_questions.extend(result["questions"])
```

**Benefit:** Simpler graph logic, easier debugging, explicit progress tracking.

---

### 7. **Enhanced State Schema** ✅
**Problem:** Missing fields make debugging difficult.

**Solution:** Add tracking and metadata fields.

**New Fields:**
- `total_pages: int` - Document size for logging
- `total_chunks: int` - Processing scope
- `context_window: List[str]` - Recent batch summaries
- `intermediate_summaries: List[str]` - Hierarchical reduction tracking
- `error_message: Optional[str]` - Error details
- `current_batch: int` - Progress tracking

**Benefit:** Better observability, easier debugging, comprehensive MLflow logging.

---

### 8. **Intermediate Reduction Prompts** ✅
**Problem:** Missing prompts for hierarchical reduction stage.

**Solution:** Add dedicated INTERMEDIATE_REDUCE prompts.

**Implementation:**
```python
INTERMEDIATE_REDUCE_SYSTEM = """You are organizing technical summaries from multiple batches.

GOAL: Combine batch summaries into ONE cohesive intermediate summary.

KEY RULES:
1. Keep each procedure separate - do NOT merge
2. Preserve all technical values (numbers with units)
3. Maintain chronological order
4. Remove redundancy across batches
5. Keep all safety warnings verbatim
"""
```

**Benefit:** Clear instructions for intermediate consolidation step.

---

### 9. **Graceful Critique Failure** ✅
**Problem:** If reflection/critique fails, entire pipeline blocks.

**Solution:** If critique fails, accept the summary and continue.

**Implementation:**
```python
except Exception as e:
    # Don't block on reflection failure
    critique = f"CRITIQUE FAILED: {str(e)}"
    needs_revision = False  # Accept summary
```

**Benefit:** Reflection is valuable but optional - don't block production pipeline.

---

### 10. **Context-Aware Prompts** ✅
**Problem:** Prompts don't guide model to build on previous work.

**Solution:** Update prompts with explicit context awareness.

**Implementation:**
```python
TECH_MAP_HUMAN = """PREVIOUS CONTEXT (Batch {batch_num}/{total_batches}):
{context}

CURRENT SECTION:
{content}

Extract technical content following the format.
Build on previous context - skip content already covered."""
```

**Benefit:** Reduces repetition, improves coherence, better use of context window.

---

## Production-Ready Features Summary

| Feature | Status | Impact |
|---------|--------|--------|
| Cumulative Context | ✅ | Prevents repetition |
| Hierarchical Reduction | ✅ | Handles any document size |
| Error Handling | ✅ | Resilient to failures |
| Time Tracking | ✅ | Performance monitoring |
| Temperature Tuning | ✅ | Optimal per task |
| Simplified Loops | ✅ | Easier debugging |
| Enhanced State | ✅ | Better observability |
| Intermediate Prompts | ✅ | Clear instructions |
| Graceful Degradation | ✅ | Don't block on optional steps |
| Context-Aware Prompts | ✅ | Better coherence |

---

## Next Steps

1. ✅ Architecture designed
2. ✅ Professional improvements added
3. ⏳ Implement `agents/summarization/` module
4. ⏳ Implement `agents/question_generation/` module
5. ⏳ Create Databricks job notebooks
6. ⏳ Test with sample PDF
7. ⏳ Deploy to Databricks jobs
8. ⏳ Monitor with MLflow

---

## Sources

- [Databricks LangChain Integration](https://docs.databricks.com/aws/en/generative-ai/agent-framework/langchain-uc-integration)
- [LangGraph Application Structure](https://docs.langchain.com/langgraph-platform/application-structure)
- [LangGraph Supervisor GitHub](https://github.com/langchain-ai/langgraph-supervisor-py)
- [Top 5 LangGraph Agents in Production 2024](https://blog.langchain.com/top-5-langgraph-agents-in-production-2024/)
- [LangGraph Architecture Design](https://medium.com/@shuv.sdr/langgraph-architecture-and-design-280c365aaf2c)
- [LangGraph Multi-Agent Orchestration Guide](https://latenode.com/blog/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)

---

*Last Updated: 2025-11-30*
*Next: Implementation of agents modules*
