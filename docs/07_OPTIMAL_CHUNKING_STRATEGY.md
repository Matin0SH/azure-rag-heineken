# Optimal Chunking Strategy for Map-Reduce Summarization

**Research Date:** 2025-11-30
**Focus:** Finding the best chunk size and window context strategy for high-quality summarization

---

## Table of Contents
1. [Optimal Chunk Sizes (2024 Research)](#optimal-chunk-sizes-2024-research)
2. [Context Overlap Strategies](#context-overlap-strategies)
3. [Semantic Chunking](#semantic-chunking)
4. [Hierarchical & Adaptive Approaches](#hierarchical--adaptive-approaches)
5. [Recommended Strategy for NextLevel](#recommended-strategy-for-nextlevel)

---

## 1. Optimal Chunk Sizes (2024 Research)

### 1.1 Research-Backed Chunk Sizes

**Source:** [Optimal Chunk-Size for Large Document Summarization](https://bestofai.com/article/optimal-chunk-size-for-large-document-summarization)

**Key Finding:**
> "Across all three document types, chunk sizes **512 or 1024** consistently outperform other chunk sizes for both models in RAG applications."

**Token to Word Conversion:**
- 512 tokens ≈ 384 words ≈ 0.5-0.75 pages
- 1024 tokens ≈ 768 words ≈ 1-1.5 pages

---

### 1.2 Trade-offs in Chunk Size

**Source:** [How to Optimize Context Window Usage for Long Documents](https://markaicode.com/optimize-context-window-long-documents/)

**Balance Required:**
> "An optimal chunk size balances the trade-off between providing sufficient context and minimizing irrelevant information."

**Key Principle:**
- **Too small** (<300 tokens): Loses context, fragmented meaning
- **Too large** (>2000 tokens): Includes irrelevant info, slower processing
- **Sweet spot**: 512-1024 tokens for RAG, 1024-2048 for summarization

---

### 1.3 Avoiding Biased Summaries

**Source:** [Introducing a new hyper-parameter for RAG: Context Window Utilization](https://arxiv.org/html/2407.19794v2)

**Critical Finding:**
> "Unequal chunk sizes can lead to biased summaries."

**Solution: Equal Distribution Algorithm**
```python
def distribute_chunks_equally(total_tokens, target_chunk_size):
    """
    Ensures all chunks are approximately equal size
    Maximum difference: ±1 token
    """
    num_chunks = ceil(total_tokens / target_chunk_size)
    avg_chunk_size = total_tokens // num_chunks
    remainder = total_tokens % num_chunks

    # Distribute remainder across first chunks
    chunk_sizes = [avg_chunk_size + 1 if i < remainder
                   else avg_chunk_size
                   for i in range(num_chunks)]

    return chunk_sizes

# Example: 10,000 tokens with target 1024
# Result: 10 chunks of [1000, 1000, 1000, ..., 1000]
# Instead of: [1024, 1024, ..., 1024, 736] ← Last chunk smaller = BIAS
```

**Research Quote:**
> "An optimal approach involves calculating the average chunk size and redistributing tokens from preceding chunks to the last chunk until it reaches the average chunk size, resulting in a maximum chunk size difference of 1."

---

## 2. Context Overlap Strategies

### 2.1 Why Overlap Matters

**Sources:**
- [Understanding Chunking Algorithms and Overlapping Techniques](https://medium.com/@jagadeesan.ganesh/understanding-chunking-algorithms-and-overlapping-techniques-in-natural-language-processing-df7b2c7183b2)
- [Chunking Strategies for LLM Applications | Pinecone](https://www.pinecone.io/learn/chunking-strategies/)

**Purpose:**
> "Chunk overlap involves repeating some tokens from the end of one chunk at the beginning of the next, which preserves context that might otherwise be lost at chunk boundaries."

**For Summarization:**
> "Overlapping chunks help maintain coherence by linking related ideas together."

---

### 2.2 Recommended Overlap Percentages

**Sources:**
- [Chunking Strategies to Improve Your RAG Performance | Weaviate](https://weaviate.io/blog/chunking-strategies-for-rag)
- [Chunk size and overlap | Unstract Documentation](https://docs.unstract.com/unstract/unstract_platform/user_guides/chunking/)

**Standard Recommendations:**
- **Typical:** 10-20% of chunk size
- **Recommended:** 20-30% for summarization
- **Conservative:** 15% as baseline

**Examples:**
```python
# Chunk size: 1024 tokens
overlap_10_percent = 102 tokens   # Minimum
overlap_20_percent = 205 tokens   # Standard
overlap_30_percent = 307 tokens   # Maximum (for critical context)

# Chunk size: 2048 tokens
overlap_15_percent = 307 tokens   # Recommended baseline
overlap_20_percent = 410 tokens   # Better context preservation
```

---

### 2.3 Benefits for Summarization

**Source:** [7 Chunking Strategies in RAG You Need To Know](https://www.f22labs.com/blogs/7-chunking-strategies-in-rag-you-need-to-know/)

**Key Benefits:**
1. **Prevents information loss** at chunk boundaries
2. **Ensures seamless transitions** between chunks
3. **Preserves semantic connections** across boundaries
4. **Critical for dialogue and summarization** tasks

**Research Quote:**
> "Overlapping chunks ensure that no critical information is lost between segments, which is particularly important for tasks requiring seamless transitions, like dialogue generation or summarization."

---

## 3. Semantic Chunking

### 3.1 Structure-Aware Chunking

**Sources:**
- [Semantic Chunking for RAG: Better Context, Better Results](https://www.multimodal.dev/post/semantic-chunking-for-rag)
- [Chunk and vectorize by document layout - Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-how-to-semantic-chunking)

**Concept:**
> "Semantic chunking leverages text embeddings to group semantically related content, with adaptive breakpoints determined by evaluating the similarity between consecutive sentences or text segments."

**Natural Boundaries:**
- Paragraph breaks
- Section headings
- Sentence endings
- Logical topic shifts

---

### 3.2 Max-Min Semantic Chunking Algorithm

**Source:** [Max–Min semantic chunking of documents for RAG application](https://link.springer.com/article/10.1007/s10791-025-09638-7)

**Approach:**
> "The Max–Min semantic chunking algorithm frames the chunking task as a dynamic clustering problem, where the goal is to group consecutive sentences based on their semantic similarity while respecting the linear structure of the document."

**How It Works:**
```python
def semantic_chunking(sentences, embeddings, threshold=0.75):
    """
    Group sentences by semantic similarity
    """
    chunks = []
    current_chunk = [sentences[0]]

    for i in range(1, len(sentences)):
        similarity = cosine_similarity(
            embeddings[i-1],
            embeddings[i]
        )

        if similarity >= threshold:
            # Similar enough: add to current chunk
            current_chunk.append(sentences[i])
        else:
            # Different topic: start new chunk
            chunks.append(current_chunk)
            current_chunk = [sentences[i]]

    chunks.append(current_chunk)  # Add last chunk
    return chunks
```

---

### 3.3 Document Structure Awareness

**Source:** [S2 Chunking: A Hybrid Framework for Document Segmentation](https://arxiv.org/html/2501.05485v1)

**Best Practice:**
> "The Document Layout skill enables chunking content based on document structure, capturing headings and chunking the content body based on semantic coherence, such as paragraphs and sentences."

**Strategies:**
1. **Sentence-based:** Preserves complete thoughts
2. **Paragraph-based:** Maintains topic coherence
3. **Hierarchical:** Respects document structure (sections, subsections)

**Problem with Fixed-Size:**
> "Fixed-size chunking often fails to preserve the semantic meaning of the text, as it does not consider the natural boundaries of sentences or paragraphs."

---

## 4. Hierarchical & Adaptive Approaches

### 4.1 HiChunk: Hierarchical Chunking (2025)

**Source:** [HiChunk: Evaluating and Enhancing Retrieval-Augmented Generation](https://arxiv.org/html/2509.11552v2)

**Innovation:**
> "HiChunk employs fine-tuned LLMs for hierarchical document structuring and incorporates iterative reasoning to address the challenge of adapting to extremely long documents."

**Auto-Merge Algorithm:**
> "For hierarchically structured documents, it introduces the Auto-Merge retrieval algorithm, which **adaptively adjusts the granularity of retrieval chunks based on the query**."

**Key Insight:**
- **Small chunks:** For specific, detailed queries
- **Large chunks:** For broad, conceptual queries
- **Adaptive:** Changes granularity dynamically

---

### 4.2 MacRAG: Multi-Scale Adaptive Context (2025)

**Source:** [MacRAG: Compress, Slice, and Scale-up for Multi-Scale Adaptive Context RAG](https://arxiv.org/html/2505.06569v1)

**Two-Phase Approach:**

#### Phase 1: Top-Down Hierarchical Indexing
```
Document
  ↓ (chunk with overlap)
Chunks
  ↓ (compress via summarization)
Summaries
  ↓ (slice into finer pieces)
Slices
```

#### Phase 2: Bottom-Up Multi-Scale Retrieval
> "The framework consists of bottom-up multi-scale adaptive retrieval on the constructed hierarchy of document-chunk-summary-slice."

**Benefit:**
- Start with high-level summaries
- Drill down to details only when needed
- Reduces processing time for long documents

---

### 4.3 Context Utilization in Summarization (2024)

**Source:** [On Context Utilization in Summarization with Large Language Models](https://arxiv.org/html/2310.10570v3)

**Position Bias Problem:**
- LLMs may favor information at beginning or end of context
- Middle content often under-represented

**Solutions:**

1. **Hierarchical Summarization**
   - Summarize sections independently
   - Combine section summaries
   - Reduces position bias

2. **Incremental Summarization**
   - Process document sequentially
   - Update summary with each new chunk
   - Maintains running context

**Research Benchmark:**
> "Research introduced a new evaluation benchmark called MiddleSum to benchmark two alternative inference methods to alleviate position bias."

---

### 4.4 Semantic Compression (2023)

**Source:** [Extending Context Window of Large Language Models via Semantic Compression](https://arxiv.org/html/2312.09571v1)

**Breakthrough:**
> "A proposed method of semantic compression can effectively extend the context window by up to **7-8 times** without modifying the parameters of the pre-trained models."

**How:**
- Compress chunks by extracting key information
- Store compressed representations
- Fit more content in same context window

**Implication for Summarization:**
- Can process 7-8x more content per pass
- 300-page doc = process as if 40-page doc
- Maintains quality with larger "effective" window

---

### 4.5 Dynamic Chunking (2024)

**Source:** [Dynamic Chunking and Selection for Reading Comprehension](https://arxiv.org/html/2506.00773v2)

**Adaptive Chunk Sizing:**
- Dense, technical content → Smaller chunks
- Narrative, simple content → Larger chunks
- Adjust dynamically based on complexity

**Benefit:**
- Optimizes processing time
- Maintains quality across varying content types

---

## 5. Recommended Strategy for NextLevel

Based on all research, here's the optimal chunking strategy:

---

### 5.1 Adaptive Chunk Size Selection

```python
def determine_chunk_size(document_metadata):
    """
    Adaptive chunk size based on document characteristics
    """
    # Base size from research: 1024 tokens optimal
    base_chunk_size = 1024

    # Adjust based on document complexity
    if is_technical_manual(document_metadata):
        # Technical content: smaller chunks for precision
        return 768  # ~576 words

    elif is_narrative_document(document_metadata):
        # Narrative content: larger chunks for context
        return 1536  # ~1152 words

    else:
        # Standard procedural manual
        return base_chunk_size  # ~768 words
```

---

### 5.2 Context Overlap Strategy

**Recommended: 20% overlap**

```python
def calculate_overlap(chunk_size):
    """
    20% overlap as baseline
    Adjust up to 30% for critical context preservation
    """
    return int(chunk_size * 0.20)

# Examples:
# 768 tokens → 154 token overlap
# 1024 tokens → 205 token overlap
# 1536 tokens → 307 token overlap
```

---

### 5.3 Equal Distribution Algorithm

**Prevent bias from unequal chunks:**

```python
def create_equal_chunks(text_tokens, target_chunk_size, overlap):
    """
    Create chunks of equal size with overlap
    Maximum size difference: ±1 token
    """
    total_tokens = len(text_tokens)
    effective_chunk_size = target_chunk_size - overlap

    # Calculate number of chunks needed
    num_chunks = ceil((total_tokens - overlap) / effective_chunk_size)

    # Calculate actual chunk size for equal distribution
    actual_chunk_size = (total_tokens + (num_chunks - 1) * overlap) // num_chunks

    chunks = []
    start = 0

    for i in range(num_chunks):
        end = start + actual_chunk_size

        # Last chunk: take remaining tokens
        if i == num_chunks - 1:
            end = total_tokens

        chunks.append(text_tokens[start:end])
        start = end - overlap  # Overlap with next chunk

    return chunks
```

**Result:**
- All chunks approximately same size
- No small "leftover" chunks
- Prevents bias toward beginning/end

---

### 5.4 Semantic Boundary Preservation

**Combine fixed-size with semantic awareness:**

```python
def create_semantic_chunks(text, target_chunk_size, overlap):
    """
    Hybrid approach: Fixed size + semantic boundaries
    """
    # 1. Split into sentences
    sentences = split_sentences(text)

    # 2. Calculate embeddings for sentences
    embeddings = embed_sentences(sentences)

    # 3. Group into chunks near target size
    chunks = []
    current_chunk = []
    current_size = 0

    for i, sentence in enumerate(sentences):
        sentence_tokens = count_tokens(sentence)

        # Check if adding sentence exceeds target
        if current_size + sentence_tokens > target_chunk_size:
            # Check semantic similarity with next sentence
            if i < len(sentences) - 1:
                similarity = cosine_similarity(
                    embeddings[i],
                    embeddings[i+1]
                )

                # High similarity: add sentence anyway (preserve context)
                # Low similarity: natural break point
                if similarity < 0.75:  # Threshold
                    chunks.append(current_chunk)
                    current_chunk = [sentence]
                    current_size = sentence_tokens
                    continue

        current_chunk.append(sentence)
        current_size += sentence_tokens

    if current_chunk:
        chunks.append(current_chunk)

    # 4. Add overlap between chunks
    return add_overlap_to_chunks(chunks, overlap)
```

---

### 5.5 Hierarchical Chunking for Large Documents

**For documents >100 pages:**

```python
def hierarchical_chunking_strategy(total_pages):
    """
    Multi-level chunking based on document size
    """
    if total_pages <= 50:
        # Single-level: Chunk → Summarize
        return {
            "levels": 1,
            "chunk_size": 1024,
            "overlap": 205,
            "method": "map_reduce"
        }

    elif total_pages <= 200:
        # Two-level: Chunk → Section → Document
        return {
            "levels": 2,
            "chunk_size": 1024,
            "section_size": 20,  # 20 chunks per section
            "overlap": 205,
            "method": "hierarchical"
        }

    else:  # > 200 pages
        # Three-level: Chunk → Section → Chapter → Document
        return {
            "levels": 3,
            "chunk_size": 1024,
            "section_size": 20,
            "chapter_size": 5,  # 5 sections per chapter
            "overlap": 205,
            "method": "hierarchical_adaptive"
        }
```

**Example for 300-page document:**
```
Level 1 (Chunks):
  - 900 chunks × 1024 tokens = ~692K tokens

Level 2 (Sections):
  - 45 sections × 20 chunks each
  - Summarize each section independently (parallel)

Level 3 (Chapters):
  - 9 chapters × 5 sections each
  - Refine summaries with context

Level 4 (Document):
  - Combine 9 chapter summaries
  - Final summary
```

---

### 5.6 Complete Chunking Pipeline

```python
def optimal_chunking_pipeline(document, metadata):
    """
    Complete pipeline with all best practices
    """
    # 1. Determine optimal chunk size
    chunk_size = determine_chunk_size(metadata)
    overlap = int(chunk_size * 0.20)  # 20% overlap

    # 2. Parse document structure
    sections = parse_document_structure(document)

    # 3. For each section:
    all_chunks = []
    for section in sections:
        # a. Extract text and sentences
        sentences = extract_sentences(section.text)

        # b. Generate sentence embeddings
        embeddings = generate_embeddings(sentences)

        # c. Create semantic chunks
        chunks = create_semantic_chunks(
            sentences,
            embeddings,
            chunk_size,
            overlap
        )

        # d. Ensure equal distribution
        chunks = redistribute_for_equality(chunks)

        all_chunks.extend(chunks)

    # 4. Validate chunk sizes
    validate_chunk_distribution(all_chunks)

    return all_chunks
```

---

### 5.7 Summary of Best Practices

| Aspect | Recommendation | Source |
|--------|----------------|--------|
| **Base chunk size** | 1024 tokens (768 words) | [Optimal Chunk-Size Research](https://bestofai.com/article/optimal-chunk-size-for-large-document-summarization) |
| **Context overlap** | 20-30% (205-307 tokens) | [Weaviate](https://weaviate.io/blog/chunking-strategies-for-rag) |
| **Chunk equality** | Max difference ±1 token | [Context Window Utilization](https://arxiv.org/html/2407.19794v2) |
| **Boundary respect** | Use semantic similarity | [Semantic Chunking](https://www.multimodal.dev/post/semantic-chunking-for-rag) |
| **Large docs** | Hierarchical 3-level | [HiChunk](https://arxiv.org/html/2509.11552v2) |
| **Position bias** | Hierarchical summarization | [Context Utilization](https://arxiv.org/html/2310.10570v3) |

---

### 5.8 Quality vs Performance Trade-offs

**For NextLevel RAG System:**

#### Option A: Maximum Quality (Recommended)
```python
config = {
    "chunk_size": 1024,
    "overlap": 307,  # 30%
    "method": "semantic_hierarchical",
    "equal_distribution": True,
    "levels": "adaptive"  # Based on doc size
}
# Time: ~12-15 minutes for 300-page doc
# Quality: Excellent
```

#### Option B: Balanced
```python
config = {
    "chunk_size": 1024,
    "overlap": 205,  # 20%
    "method": "hierarchical",
    "equal_distribution": True,
    "levels": 2
}
# Time: ~8-10 minutes for 300-page doc
# Quality: Very Good
```

#### Option C: Fast
```python
config = {
    "chunk_size": 1536,
    "overlap": 205,  # ~13%
    "method": "map_reduce",
    "equal_distribution": False,
    "levels": 1
}
# Time: ~5-6 minutes for 300-page doc
# Quality: Good
```

---

## Sources

### Optimal Chunk Sizes
- [Optimal Chunk-Size for Large Document Summarization](https://bestofai.com/article/optimal-chunk-size-for-large-document-summarization)
- [How to Optimize Context Window Usage for Long Documents](https://markaicode.com/optimize-context-window-long-documents/)
- [Introducing a new hyper-parameter for RAG: Context Window Utilization](https://arxiv.org/html/2407.19794v2)
- [Chunking Strategies for LLM Applications | Pinecone](https://www.pinecone.io/learn/chunking-strategies/)

### Context Overlap
- [Understanding Chunking Algorithms and Overlapping Techniques](https://medium.com/@jagadeesan.ganesh/understanding-chunking-algorithms-and-overlapping-techniques-in-natural-language-processing-df7b2c7183b2)
- [Chunking Strategies to Improve Your RAG Performance | Weaviate](https://weaviate.io/blog/chunking-strategies-for-rag)
- [Chunk size and overlap | Unstract Documentation](https://docs.unstract.com/unstract/unstract_platform/user_guides/chunking/)
- [7 Chunking Strategies in RAG You Need To Know](https://www.f22labs.com/blogs/7-chunking-strategies-in-rag-you-need-to-know/)

### Semantic Chunking
- [Semantic Chunking for RAG: Better Context, Better Results](https://www.multimodal.dev/post/semantic-chunking-for-rag)
- [Max–Min semantic chunking of documents for RAG application](https://link.springer.com/article/10.1007/s10791-025-09638-7)
- [Chunk and vectorize by document layout - Azure AI Search](https://learn.microsoft.com/en-us/azure/search/search-how-to-semantic-chunking)
- [S2 Chunking: A Hybrid Framework for Document Segmentation](https://arxiv.org/html/2501.05485v1)
- [15 Chunking Techniques to Build Exceptional RAGs Systems](https://www.analyticsvidhya.com/blog/2024/10/chunking-techniques-to-build-exceptional-rag-systems/)

### Hierarchical & Adaptive
- [HiChunk: Evaluating and Enhancing Retrieval-Augmented Generation](https://arxiv.org/html/2509.11552v2)
- [MacRAG: Compress, Slice, and Scale-up for Multi-Scale Adaptive Context RAG](https://arxiv.org/html/2505.06569v1)
- [On Context Utilization in Summarization with Large Language Models](https://arxiv.org/html/2310.10570v3)
- [Extending Context Window of Large Language Models via Semantic Compression](https://arxiv.org/html/2312.09571v1)
- [Dynamic Chunking and Selection for Reading Comprehension](https://arxiv.org/html/2506.00773v2)

---

*Last Updated: 2025-11-30*
*Recommendation: Use Maximum Quality config for production NextLevel system*
