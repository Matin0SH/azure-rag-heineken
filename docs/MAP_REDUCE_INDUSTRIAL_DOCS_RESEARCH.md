# MAP-REDUCE for Industrial Documents - Research Evidence

**Date:** 2025-12-02
**Purpose:** Best practices for MAP-REDUCE on industrial/technical documents with procedures, diagrams, and troubleshooting guides

---

## Table of Contents
1. [Key Findings from NextLevel Docs](#key-findings-from-nextlevel-docs)
2. [MAP-REDUCE Best Practices (2024-2025)](#map-reduce-best-practices-2024-2025)
3. [Hierarchical Reduction Strategies](#hierarchical-reduction-strategies)
4. [Industrial Procedural Document Extraction](#industrial-procedural-document-extraction)
5. [Critical Design Recommendations](#critical-design-recommendations)

---

## 1. Key Findings from NextLevel Docs

### From `06_RESEARCH_BEST_PRACTICES.md`:

#### ✅ Method 3: Hybrid Map-Reduce-Refine ⭐ RECOMMENDED

**How It Works:**
```
1. Split document into logical sections (e.g., pages)
2. Within each section:
   - Map-Reduce: Parallel summarize chunks
3. Across sections:
   - Refine: Sequential refinement with context
4. Final summary: Reduce all section summaries
```

**Advantages:**
- ✅ Best of both - Speed + coherence
- ✅ Balanced - Parallel within sections, sequential across
- ✅ Scalable - Handles any size
- ✅ Quality - Maintains context where needed

**Best For:**
- ✅ **300-page manuals** ← OUR USE CASE
- ✅ Structured documents (chapters/sections)
- ✅ Need both speed AND quality

**Performance Estimates (300-page document):**
- Chunking: 5 seconds
- Map phase (20-chunk batches): 30-45 seconds (parallel)
- Reduce phase: 15-20 seconds
- Reflection: 20-30 seconds (2 iterations)
- **Total: ~2-3 minutes per summary**

---

### From `11_EXTRACTION_VS_SUMMARIZATION.md`:

#### 🎯 Critical Philosophy: EXTRACTION > SUMMARIZATION

**The Problem with Summarization:**
```
450 chunks (300 pages)
    ↓ MAP: Summarize
23 summaries (reduce from 450)
    ↓ REDUCE: Summarize again
1 summary (~10 pages) ← LOST ~290 pages of info!
```

**Problems:**
- ❌ Information loss at each stage
- ❌ Technical values might be dropped
- ❌ Safety procedures might be omitted
- ❌ "Brevity" prioritized over "Completeness"

**The Solution: EXTRACTION + COMBINATION**
```
450 chunks (300 pages)
    ↓ MAP: EXTRACT
45 extractions (ALL procedures preserved)
    ↓ REDUCE: COMBINE
12 intermediates (ALL info combined)
    ↓ ORGANIZE
1 complete document (~280 pages organized) ← ALL info preserved!
```

**Benefits:**
- ✅ ZERO information loss
- ✅ ALL technical values preserved verbatim
- ✅ ALL safety procedures included
- ✅ "Completeness" prioritized over "Brevity"

**Critical Prompt Changes:**
```
BEFORE: "Summarize this section..."
AFTER:  "EXTRACT all technical specifications..."
        "PRESERVE exact wording from source..."
        "DO NOT reduce or paraphrase..."
        "COMPLETENESS > BREVITY"
```

---

## 2. MAP-REDUCE Best Practices (2024-2025)

### From Web Research:

#### Google Cloud Workflow Approach (2024)

**Source:** [Google Cloud: Summarization techniques](https://cloud.google.com/blog/products/ai-machine-learning/long-document-summarization-with-workflows-and-gemini-models)

**Key Findings:**
> "With map/reduce, you can create a summary for each section in parallel (the 'map' operation), with a final summarization in the last step (the 'reduce' operation)."

**Advantages:**
- ✅ Map/reduce creates summaries in parallel = faster than sequential
- ✅ LLMs generally reason better on smaller chunks of data
- ✅ Scalable for large volumes of text

**Chunk Sizing:**
- 64,000 characters chosen as chunk size
- Fits in LLM context window
- Stays within memory limits

---

#### LangChain Implementation Patterns

**Source:** [Master LLM Summarization Strategies](https://galileo.ai/blog/llm-summarization-strategies)

**For Large Documents:**
> "For large documents, the map_reduce and refine techniques are recommended due to their ability to handle chunk-wise summarization efficiently."

**Optimization with Tools:**
> "Tools like Galileo can help optimize map-reduce pipelines by analyzing information preservation across chunks and identifying where critical information gets lost."

**Multi-Level Strategies:**
> "Multi-level summarization methodologies incorporate a series of steps, combining both extractive and abstractive techniques, which are advantageous when dealing with text with tokens longer than the limit of an LLM."

---

#### Advanced Framework: LLMxMapReduce-V2 (2025)

**Source:** [GitHub - thunlp/LLMxMapReduce](https://github.com/thunlp/LLMxMapReduce)

**Innovation:**
> "LLMxMapReduce-V2 is a novel test-time scaling strategy designed to enhance the ability of LLMs to process extremely long inputs."

**Key Feature:**
- Entropy-driven convolutional test-time scaling mechanism
- Improves integration of extremely large volumes of information
- Designed for production enterprise use cases

---

## 3. Hierarchical Reduction Strategies

### CoTHSSum Framework (2024-2025)

**Source:** [CoTHSSum: Structured long-document summarization](https://link.springer.com/article/10.1007/s44443-025-00041-2)

**Key Innovation:**
> "A novel framework integrates hierarchical input segmentation with Chain-of-Thought (CoT) prompting, decomposing long documents into semantically coherent segments and applying CoT-based prompting for intermediate summary reasoning to compose high-quality final summaries."

**Benefits:**
- ✅ Summaries with higher factual consistency
- ✅ Better preservation of important content
- ✅ Improved structural coherence

**Implementation Approach:**
```
1. Hierarchical input segmentation (semantically coherent)
2. Chain-of-Thought prompting for each segment
3. Intermediate summary reasoning
4. Compose high-quality final summaries
```

---

### Recursive/Multi-Stage Approaches

**Source:** [Master LLM Summarization Strategies](https://galileo.ai/blog/llm-summarization-strategies)

**Concept:**
> "Recursive summarization extends hierarchical concepts by applying multiple reduction steps for extremely long documents, gradually condensing information through multiple summarization layers while preserving key insights."

**Critical Finding:**
> "Incremental updating yields lower scores but higher level of detail than hierarchical merging, a trade-off sometimes preferred by annotators."

**For Book-Length Documents:**
> "For documents exceeding maximum context size, the length necessitates first dividing into smaller chunks and then repeatedly merging, updating, and/or compressing chunk-level partial summaries."

---

### Information Preservation Techniques

**Source:** [CoTHSSum Framework](https://www.researchgate.net/publication/391905673_CoTHSSum_Structured_long-document_summarization_via_chain-of-thought_reasoning_and_hierarchical_segmentation)

**Challenge:**
> "As text length grows, models risk semantic drift and struggle to preserve crucial content, requiring handling information at multiple levels of granularity and preserving the document's logical flow."

**Solution:**
> "CoT-driven summarization shows promising results in preserving key details, improving information completeness, and reducing factual inaccuracies in generated summaries."

---

## 4. Industrial Procedural Document Extraction

### Annotation and Extraction Research (2024)

**Source:** [Annotation and Extraction of Industrial Procedural Knowledge](https://dl.acm.org/doi/fullHtml/10.1145/3587259.3627570)

**Critical Finding:**
> "Research has been conducted specifically on extracting and representing procedural knowledge from documents, with methodologies tailored to user requirements in industrial settings."

**Manufacturing Context:**
> "Manufacturing companies particularly face challenges managing procedural knowledge found in documents like user manuals, troubleshooting instructions, guidelines, and internal processes."

**Key Challenge:**
> "Industrial documents may contain lengthy and detailed procedures with instructions in very different textual forms, making it difficult for knowledge extraction algorithms to accurately identify and structure the relevant information."

---

### Industrial Operation & Maintenance Manuals

**Source:** [From Documents to Database: Failure Modes for Industrial Assets](https://arxiv.org/pdf/2509.17834)

**Content Types:**
> "Industrial operation and maintenance manuals typically include information about installation, operation, inspection, and maintenance of equipment, containing considerable amounts of relevant information."

**LLM Application:**
> "LLM-generated content can be added for installation and troubleshooting sections."

---

### Technical Extraction Approaches

**Source:** [LLM-Powered Parsing and Analysis of Semi-Structured Documents](https://towardsdatascience.com/llm-powered-parsing-and-analysis-of-semi-structured-structured-documents-f03ac92f063e/)

**NLP Techniques:**
> "There is a growing need for approaches and tools to extract procedural knowledge from unstructured information encoded in documents such as PDF or text files, using advanced Natural Language Processing (NLP) techniques."

**Multi-Modal Processing:**
> "Documents can be converted to images and provided to multi-modal models, which use their vision capabilities to understand the document and extract text accordingly."

**Challenge with PDFs:**
> "Document processing, particularly for PDFs, presents challenges in the form of noisy text extraction and semantic interpretation of tables."

---

### Production Tools & Platforms

**Source:** [LLMs for Structured Data Extraction from PDF](https://unstract.com/blog/comparing-approaches-for-using-llms-for-structured-data-extraction-from-pdfs/)

**Unstract's Prompt Studio:**
> "Platforms like Unstract's Prompt Studio allow users to develop generic prompts for specific document types, which can be reused to extract structured data, then deployed as ETL pipelines, API endpoints, or manual review queues."

---

## 5. Critical Design Recommendations

### For NextLevel Industrial Document Processing:

#### 1. **Architecture: Hybrid MAP-REDUCE**

**Recommended Flow:**
```
1. FETCH: Get chunks from Unity Catalog
2. REGROUP: Combine chunks by pages
3. BATCH: Group 5 pages per batch
4. MAP: EXTRACT from each batch (3 workers parallel)
   - Extract ALL procedures
   - Extract ALL technical specs
   - Extract ALL safety warnings
   - Preserve exact wording
5. REDUCE: COMBINE hierarchically (3-to-1)
   - Level 1: Combine 3 batches → intermediate
   - Level 2: Combine 3 intermediates → next level
   - Continue until → 1 final organized document
6. ORGANIZE: Structure by categories
```

---

#### 2. **Prompt Strategy: EXTRACTION not SUMMARIZATION**

**Critical Instructions:**
```
"CRITICAL: You are EXTRACTING, not summarizing"
"PRESERVE exact wording from source"
"DO NOT reduce or paraphrase"
"COMPLETENESS > BREVITY"
"When in doubt, KEEP IT"

For procedures:
- Extract ALL steps verbatim
- Include exact technical values
- Preserve safety warnings word-for-word
- Maintain sequential order

For troubleshooting:
- Extract ALL symptoms
- Extract ALL diagnostic steps
- Extract ALL solutions
- Include conditional logic (if/then)
```

---

#### 3. **Context Management**

**From Research:**
- Use Chain-of-Thought prompting for complex procedures
- Maintain semantic coherence in segments
- Pass context between reduce levels to avoid information loss
- Use low temperature (0.1) for deterministic extraction

**Context Window Strategy:**
- Pass previous extraction summaries as context
- Prevents duplication (not information loss)
- Helps maintain narrative flow in procedures

---

#### 4. **Handling Diagrams & Visual Content**

**From Research:**
- Convert diagrams to images
- Use multi-modal LLMs (vision capabilities)
- Extract relationships described in diagrams
- Link diagram references to text procedures

**For Our Case:**
- During chunking, preserve page_number metadata
- Extract references like "See Figure 5.2"
- Maintain links between text and visual elements

---

#### 5. **Batch Sizing for Industrial Documents**

**Recommendations:**
- **5 pages per batch** (not 5-7 chunks)
- Rationale: Industrial procedures often span multiple pages
- Maintains procedure completeness
- Fits within LLM context windows

**From Research:**
- 64,000 characters = good chunk size for context fit
- ~5 pages ≈ 12,500 words ≈ 16,000 tokens
- Leaves room for prompts and output

---

#### 6. **Hierarchical Reduce: 3-to-1 Pattern**

**Why 3-to-1:**
- ✅ Manageable context per reduce step
- ✅ Balanced tree depth (100 batches → 34 → 12 → 4 → 1)
- ✅ Reduces risk of information loss compared to larger ratios
- ✅ Allows thorough combination at each level

**Combine vs. Summarize:**
```
WRONG: "Combine these 3 summaries into 1 shorter summary"
RIGHT:  "ORGANIZE these 3 extractions into 1 complete document.
         PRESERVE all procedures, specs, and warnings.
         Group by category (Safety, Operation, Maintenance).
         DO NOT reduce or omit any information."
```

---

#### 7. **Quality Assurance for Industrial Content**

**Critical Checks:**
1. **Completeness Validation**
   - All procedures have all steps
   - All technical values preserved with units
   - All safety warnings present

2. **Accuracy Validation**
   - No hallucinated steps
   - No changed technical values
   - No paraphrased safety instructions

3. **Structure Validation**
   - Procedures maintain sequential order
   - Conditional logic preserved (if/then)
   - Cross-references maintained (See page X)

---

#### 8. **Performance Optimization**

**Parallel Processing:**
- Map phase: 3 workers max (avoid API rate limits)
- Process batches in chunks of 3
- Sequential reduce to maintain context

**Expected Performance (500 pages):**
```
1. Fetch chunks: 2-3 seconds
2. Regroup by pages: 1 second
3. Create batches: <1 second
4. MAP (100 batches, 3 workers): ~5-7 minutes
5. REDUCE (hierarchical): ~2-3 minutes
6. Total: ~8-12 minutes
```

---

## 6. Final Architecture Recommendation

### State Schema (Already Implemented):
```python
class SummarizationState(TypedDict):
    # Input
    pdf_id: str
    pdf_name: str
    summary_type: str  # 'technical' or 'operator'

    # Fetched data
    chunks: List[Dict]
    total_chunks: int
    total_pages: int

    # Regrouped by pages
    pages: List[Dict]

    # Batched (5 pages per batch)
    batches: List[Dict]
    total_batches: int

    # MAP phase results
    batch_extractions: List[str]  # ALL info preserved

    # REDUCE phase results (hierarchical 3-to-1)
    reduce_levels: List[List[str]]  # Each level maintains ALL info
    final_summary: str  # Complete organized document

    # Output
    key_topics: List[str]

    # Metadata
    processing_time: float
    error_message: Optional[str]
```

### Node Flow:
1. **fetch_chunks_node** → fills `chunks`
2. **regroup_pages_node** → fills `pages`
3. **create_batches_node** → fills `batches` (5 pages each)
4. **map_extract_node** → fills `batch_extractions` (3 workers parallel)
5. **reduce_combine_node** → fills `reduce_levels` + `final_summary` (3-to-1)
6. **extract_topics_node** → fills `key_topics`

---

## 7. Key Takeaways for Implementation

### ✅ DO:
1. **EXTRACT** not summarize
2. **PRESERVE** all technical details verbatim
3. **GROUP** by pages (5 per batch) not chunks
4. **REDUCE** hierarchically (3-to-1) with full information
5. **USE** Chain-of-Thought prompting for complex procedures
6. **MAINTAIN** low temperature (0.1) for deterministic extraction
7. **LIMIT** parallel workers (max 3) to avoid API rate limits
8. **VALIDATE** completeness at each stage

### ❌ DON'T:
1. **DON'T** use "summarize" in prompts
2. **DON'T** reduce or condense information
3. **DON'T** paraphrase technical specifications
4. **DON'T** lose safety warnings
5. **DON'T** spawn unlimited parallel workers
6. **DON'T** process chunks individually (group by pages)
7. **DON'T** skip hierarchical reduce (prevents info loss)
8. **DON'T** prioritize brevity over completeness

---

## Sources

### NextLevel Docs:
- `docs/06_RESEARCH_BEST_PRACTICES.md`
- `docs/11_EXTRACTION_VS_SUMMARIZATION.md`

### External Research (2024-2025):
- [Google Cloud: Summarization techniques](https://cloud.google.com/blog/products/ai-machine-learning/long-document-summarization-with-workflows-and-gemini-models)
- [Master LLM Summarization Strategies](https://galileo.ai/blog/llm-summarization-strategies)
- [Summarization with LangChain](https://medium.com/@abonia/summarization-with-langchain-b3d83c030889)
- [GitHub - thunlp/LLMxMapReduce](https://github.com/thunlp/LLMxMapReduce)
- [CoTHSSum: Structured long-document summarization](https://link.springer.com/article/10.1007/s44443-025-00041-2)
- [Annotation and Extraction of Industrial Procedural Knowledge](https://dl.acm.org/doi/fullHtml/10.1145/3587259.3627570)
- [From Documents to Database: Failure Modes](https://arxiv.org/pdf/2509.17834)
- [LLM-Powered Parsing and Analysis](https://towardsdatascience.com/llm-powered-parsing-and-analysis-of-semi-structured-structured-documents-f03ac92f063e/)
- [LLMs for Structured Data Extraction from PDF](https://unstract.com/blog/comparing-approaches-for-using-llms-for-structured-data-extraction-from-pdfs/)

---

*Research compiled: 2025-12-02*
*Purpose: Guide implementation of MAP-REDUCE for NextLevel industrial document processing*
