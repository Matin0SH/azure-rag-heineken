# Summarization Agent Architecture

## Overview

This agent implements a **hierarchical MAP-REDUCE pattern with reflection** for extracting comprehensive information from large technical documents (e.g., 674-page manuals with 1403 chunks).

**Philosophy**: EXTRACTION over summarization - preserve ALL technical details, remove only exact duplicates.

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INPUT: PDF Document                          │
│              1403 chunks • 674 pages • Technical Manual             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: MAP (Batch Extraction)                  │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  Config:                                                            │
│    • Batch size: 7 chunks per batch (QUALITY FOCUSED)               │
│    • Context window: Last 3 batch summaries                         │
│    • Token budget: 8,000 input + 4,000 output                       │
│                                                                      │
│  Process:                                                           │
│    1403 chunks → 200 batches                                        │
│                                                                      │
│    [Batch 1: chunks 1-7]   ──→ LLM (with context) → Extract 1       │
│    [Batch 2: chunks 8-14]  ──→ LLM (+ Batch 1)   → Extract 2        │
│    [Batch 3: chunks 15-21] ──→ LLM (+ B1, B2)    → Extract 3        │
│    [Batch 4: chunks 22-28] ──→ LLM (+ B2, B3)    → Extract 4        │
│    ...                                                               │
│    [Batch 200: chunks 1397-1403] → Extract 200                      │
│                                                                      │
│  Output: 200 batch extractions (each ~4K tokens)                    │
│  API Calls: 200 × extraction_llm.invoke()                           │
│  Time: ~5-7 minutes                                                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│              PHASE 2: REDUCE (Hierarchical Combination)             │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  Strategy: Recursive grouping by 4s                                 │
│                                                                      │
│  STAGE 1: First-level reduction                                     │
│    200 batch extractions → 50 groups of 4                           │
│                                                                      │
│    [Extracts 1-4]     ──→ LLM → Intermediate 1                      │
│    [Extracts 5-8]     ──→ LLM → Intermediate 2                      │
│    [Extracts 9-12]    ──→ LLM → Intermediate 3                      │
│    ...                                                               │
│    [Extracts 197-200] ──→ LLM → Intermediate 50                     │
│                                                                      │
│    Output: 50 intermediate summaries                                │
│    API Calls: 50 × extraction_llm.invoke()                          │
│                                                                      │
│  STAGE 2: Second-level reduction                                    │
│    50 intermediates → 13 groups of 4 (12×4 + 1×2)                   │
│                                                                      │
│    [Intermediates 1-4]   ──→ LLM → Level2-1                         │
│    [Intermediates 5-8]   ──→ LLM → Level2-2                         │
│    ...                                                               │
│    [Intermediates 49-50] ──→ LLM → Level2-13                        │
│                                                                      │
│    Output: 13 level-2 summaries                                     │
│    API Calls: 13 × extraction_llm.invoke()                          │
│                                                                      │
│  STAGE 3: Third-level reduction                                     │
│    13 summaries → 4 groups (3×4 + 1×1)                              │
│                                                                      │
│    [Level2 1-4]   ──→ LLM → Level3-1                                │
│    [Level2 5-8]   ──→ LLM → Level3-2                                │
│    [Level2 9-12]  ──→ LLM → Level3-3                                │
│    [Level2 13]    ──→ (pass through) → Level3-4                     │
│                                                                      │
│    Output: 4 level-3 summaries                                      │
│    API Calls: 3 × extraction_llm.invoke()                           │
│                                                                      │
│  STAGE 4: Final reduction (≤4 summaries → direct combine)           │
│    4 level-3 summaries → 1 final                                    │
│                                                                      │
│    [Level3 1-4] ──→ LLM → Final Summary                             │
│                                                                      │
│    Output: 1 final summary                                          │
│    API Calls: 1 × extraction_llm.invoke()                           │
│                                                                      │
│  Total Reduce API Calls: 67                                         │
│  Time: ~2-3 minutes                                                 │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                PHASE 3: REFLECT (Critique & Revision)               │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  Purpose: Quality assurance check                                   │
│                                                                      │
│  Final Summary ──→ critique_llm ──→ Evaluation                      │
│                                                                      │
│  Checks:                                                            │
│    ✓ Are all procedures preserved and separated?                    │
│    ✓ Are technical values/specs intact?                             │
│    ✓ Is structure complete and logical?                             │
│                                                                      │
│  Decision:                                                          │
│    • PASS → Continue to Phase 4                                     │
│    • FAIL (iteration < 2) → Reset, re-run MAP-REDUCE               │
│    • FAIL (iteration ≥ 2) → Accept anyway (prevent infinite loop)   │
│                                                                      │
│  API Calls: 1 × critique_llm.invoke()                               │
│  Max Iterations: 2                                                  │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  PHASE 4: EXTRACT TOPICS (Indexing)                 │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  Purpose: Generate searchable keywords for document discovery       │
│                                                                      │
│  Final Summary ──→ extraction_llm ──→ 5-10 Key Topics               │
│                                                                      │
│  Examples:                                                          │
│    • "Hydraulic Systems"                                            │
│    • "Safety Procedures"                                            │
│    • "Preventive Maintenance"                                       │
│    • "Electrical Schematics"                                        │
│    • "Troubleshooting Guides"                                       │
│                                                                      │
│  API Calls: 1 × extraction_llm.invoke()                             │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                            OUTPUT RESULT                            │
│━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━│
│  {                                                                  │
│    "final_summary": "Comprehensive extraction...",                  │
│    "key_topics": ["topic1", "topic2", ...],                         │
│    "processing_time": 180.5,                                        │
│    "current_batch": 47,                                             │
│    "iteration": 1,                                                  │
│    "error_message": null                                            │
│  }                                                                  │
│                                                                      │
│  Total API Calls: ~269 (200 MAP + 67 REDUCE + 1 REFLECT + 1 TOPICS)│
│  Total Time: ~8-10 minutes for 674 pages (HIGH QUALITY)             │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Hyperparameters (Optimized)

### Token Budgets
```python
PROMPT_BUDGET_TOKENS = 8000   # Max input tokens (balanced)
CONTEXT_TOKEN_LIMIT = 4000    # Max context window tokens
```

**Rationale**:
- Balanced between quality and context fit
- Allows 5-10 chunks + rolling context to fit comfortably
- Prevents token budget overflow errors

### Batch Configuration
```python
DEFAULT_BATCH_SIZE = 7        # Chunks per batch (QUALITY FOCUSED)
MIN_BATCH_SIZE = 1            # Minimum when splitting
CONTEXT_WINDOW_SIZE = 3       # Rolling context batches
REDUCE_GROUP_SIZE = 4         # Hierarchical grouping
```

**Rationale**:
- **7 chunks** = sweet spot for thorough extraction
  - Not too few (would need too many batches)
  - Not too many (LLM gets overwhelmed)
- LLM can carefully process 5-10 chunks without missing details
- Context window prevents duplication across batches
- Groups of 4 in REDUCE phase = logarithmic scaling

### LLM Configuration
```python
extraction_llm:
  endpoint: "databricks-llama-4-maverick"
  temperature: 0.1          # Low for deterministic extraction
  max_tokens: 4000          # Balanced for 7-chunk batches
  streaming: False

critique_llm:
  endpoint: "databricks-llama-4-maverick"
  temperature: 0.05         # Very low for consistent evaluation
  max_tokens: 2000          # Critiques are concise
  streaming: False
```

**Rationale**:
- Low temperature = deterministic, factual extraction
- 4000 tokens = enough for detailed extraction without bloat
- No streaming = simpler error handling
- Critique doesn't need long outputs

### Reduce Configuration
```python
REDUCE_GROUP_SIZE = 4         # Combine 4 summaries at a time
MAX_ITERATIONS = 2            # Critique revision limit
```

**Rationale**:
- Groups of 4 = logarithmic scaling (4 → 1, 16 → 4 → 1, etc.)
- Max 2 iterations prevents infinite revision loops
- Balances quality vs. processing time

---

## Performance Metrics

### Example: 674-page Technical Manual

| Metric | Value |
|--------|-------|
| **Input** | 1403 chunks, 674 pages |
| **MAP Phase** | 200 batches × 1 LLM call = 200 API calls |
| **REDUCE Phase** | 50 + 13 + 3 + 1 = 67 API calls |
| **REFLECT Phase** | 1 API call |
| **TOPICS Phase** | 1 API call |
| **Total API Calls** | ~269 calls |
| **Processing Time** | 8-10 minutes |
| **Output Size** | ~8K-12K tokens (comprehensive extraction) |
| **Quality** | **HIGH** - LLM processes only 7 chunks at a time |

### Why 7 Chunks is Optimal

| Batch Size | Pros | Cons | Quality |
|------------|------|------|---------|
| **3-5 chunks** | Very thorough, high quality | Too many API calls (280-467), slow | Excellent |
| **7 chunks** ✅ | Thorough, balanced speed | More calls than 10+ | **Very Good** |
| **10 chunks** | Faster (141 calls) | LLM starts missing details | Good |
| **20+ chunks** | Very fast (70 calls) | LLM overwhelmed, low quality | Poor |
| **30+ chunks** | Fastest (47 calls) | Significant information loss | Very Poor |

**Decision**: 7 chunks balances quality and performance

---

## Key Design Decisions

### 1. Why Hierarchical Instead of Iterative?

**Hierarchical** (current):
- ✅ Predictable structure
- ✅ Clear quality gates at each level
- ✅ Easy to debug/trace
- ✅ Parallelizable (future optimization)

**Iterative** (alternative):
- ❌ Unpredictable depth
- ❌ Harder to track quality
- ✅ Slightly more flexible

**Decision**: Hierarchical for production stability

### 2. Why Context Window in MAP Phase?

**Without context**:
```
Batch 1: "The hydraulic pump operates at 2000 PSI"
Batch 2: "The hydraulic pump operates at 2000 PSI" (DUPLICATE!)
```

**With context (last 3 batches)**:
```
Batch 1: "The hydraulic pump operates at 2000 PSI"
Batch 2: (sees Batch 1 context) "The pressure relief valve triggers at 2200 PSI" (NEW INFO!)
```

**Decision**: Context window essential for avoiding duplication

### 3. Why Only 2 Reflection Iterations?

- Iteration 1: Usually catches major omissions
- Iteration 2: Fine-tuning
- Iteration 3+: Diminishing returns, possible oscillation
- Risk: Infinite loop if LLM critique is inconsistent

**Decision**: 2 iterations balances quality vs. runtime

### 4. Why Groups of 4 in REDUCE?

- **Powers of 4**: 4 → 1, 16 → 4 → 1, 64 → 16 → 4 → 1
- **Not too shallow**: Groups of 2 = too many stages
- **Not too deep**: Groups of 8 = risks exceeding token limit
- **Empirical sweet spot**: 4 summaries fit comfortably in prompt

**Decision**: 4 is the Goldilocks number

---

## Error Handling

### Token Budget Exceeded
- **Detection**: `_count_tokens()` monitors prompt size
- **Action**: Shrink current batch size by 1, retry
- **Minimum**: Falls back to `MIN_BATCH_SIZE = 1`

### LLM API Failure
- **Detection**: Try-catch around `llm.invoke()`
- **Action**: Return partial results with error message
- **State**: Preserves all progress in state dict

### Reflection Loop Prevention
- **Detection**: Iteration counter in state
- **Action**: Force accept after `MAX_ITERATIONS = 2`
- **Logging**: Warns user if quality check failed

---

## Prompt Engineering

### MAP Phase (Technical Summary)
```
SYSTEM: You are extracting technical information...
HUMAN: Previous batches: {context}
       Current batch (batch {N}/{total}): {content}

       Extract ALL technical details verbatim...
```

**Key**: "Extract" not "summarize" - preserves completeness

### REDUCE Phase (Intermediate)
```
SYSTEM: You are combining batch extractions...
HUMAN: Batches {start}-{end}:
       {batch_extractions}

       Combine and deduplicate...
```

**Key**: "Combine" not "reduce" - no loss of information

### REDUCE Phase (Final)
```
SYSTEM: You are creating the final comprehensive extraction...
HUMAN: All extractions: {extractions}

       Merge into single comprehensive document...
```

**Key**: "Merge" not "summarize" - completeness over brevity

### REFLECT Phase
```
SYSTEM: You are a quality assurance critic...
HUMAN: Summary: {summary}

       Evaluate:
       - Are all procedures preserved?
       - Are technical values intact?
       - Is structure complete?

       Reply: PASS or FAIL with reasons
```

**Key**: Strict criteria prevent information loss

---

## Future Optimizations

### 1. Parallel MAP Phase
- Current: Sequential batch processing
- Future: Process batches in parallel via ThreadPoolExecutor
- Speedup: ~5-10x for MAP phase

### 2. Dynamic Batch Sizing
- Current: Fixed 30 chunks
- Future: Adjust based on chunk token density
- Benefit: Maximize prompt utilization

### 3. Caching Intermediate Results
- Current: Regenerate on re-run
- Future: Cache batch extractions by content hash
- Benefit: Instant re-runs for same document

### 4. Streaming for Long Documents
- Current: Wait for final result
- Future: Stream batch summaries as they complete
- Benefit: Better UX for 1000+ page docs

---

## Usage Example

```python
from agents.summarization.graph import run_summarization

# Prepare inputs
chunks = [{"text": "...", "page_number": 1, "chunk_index": 0}, ...]

# Run agent
result = run_summarization(
    pdf_id="CAS.pdf",
    pdf_name="CAS.pdf",
    chunks=chunks,
    summary_type="technical",  # or "operator"
    total_pages=674,
    total_chunks=1403
)

# Access results
print(f"Processing time: {result['processing_time']:.2f}s")
print(f"Key topics: {result['key_topics']}")
print(f"Summary:\n{result['final_summary']}")
```

---

## Monitoring & Debugging

### State Inspection
```python
# LangGraph state at each node
state = {
    "chunks": [...],              # Input chunks
    "batch_summaries": [...],     # MAP output
    "context_window": [...],      # Rolling context
    "intermediate_summaries": [...],  # REDUCE stage outputs
    "final_summary": "...",       # REDUCE final output
    "critique": "PASS",           # REFLECT output
    "key_topics": [...],          # TOPICS output
    "current_batch": 47,          # Progress counter
    "iteration": 1,               # Reflection iteration
    "processing_time": 180.5,     # Cumulative time
    "error_message": null         # Error state
}
```

### Tracing with MLflow
```python
import mlflow

mlflow.autolog()  # Automatically trace LangGraph execution

# View trace in Databricks UI:
# ML → Experiments → [Your Experiment] → Traces
```

---

## References

- [LangChain Map-Reduce Pattern](https://python.langchain.com/docs/how_to/summarize_map_reduce/)
- [Databricks Foundation Model APIs](https://docs.databricks.com/machine-learning/foundation-model-apis/)
- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [MLflow Tracing for LangGraph](https://docs.databricks.com/mlflow3/genai/tracing/integrations/langgraph)
