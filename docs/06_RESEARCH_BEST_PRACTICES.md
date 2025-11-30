# Research: Best Practices for LangGraph Agents & Document Summarization

**Research Date:** 2025-11-30
**Purpose:** Identify best practices for building LangGraph multi-agent systems for document summarization and question generation

---

## Table of Contents
1. [LangGraph Multi-Agent Best Practices](#langgraph-multi-agent-best-practices)
2. [Document Summarization Techniques](#document-summarization-techniques)
3. [Question Generation Best Practices](#question-generation-best-practices)
4. [Reflection Pattern for Quality](#reflection-pattern-for-quality)
5. [Recommended Architecture for NextLevel](#recommended-architecture-for-nextlevel)

---

## 1. LangGraph Multi-Agent Best Practices

### 1.1 Architecture Patterns (2024-2025)

#### Supervisor Pattern ⭐ RECOMMENDED
**Source:** [LangGraph: Multi-Agent Workflows](https://blog.langchain.com/langgraph-multi-agent-workflows/)

**How it works:**
- Single supervisor agent receives user input
- Supervisor delegates work to specialized sub-agents
- When sub-agents respond, control returns to supervisor
- Only supervisor can respond to users

**Why recommended:**
- Places minimal assumptions on sub-agents
- Feasible for all multi-agent scenarios
- Clear separation of concerns

#### Tool/Responsibility Grouping
**Source:** [Advanced Multi-Agent Development with Langgraph](https://medium.com/@kacperwlodarczyk/advanced-multi-agent-development-with-langgraph-expert-guide-best-practices-2025-4067b9cec634)

**Best practice:**
- Group tools/responsibilities by focus area
- Agent more likely to succeed on focused task
- Avoid giving agents dozens of tools

**Research finding:**
> "Grouping tools/responsibilities can give better results, as an agent is more likely to succeed on a focused task than if it has to select from dozens of tools."

---

### 1.2 Scaling & Performance

#### Start Small, Scale Based on Data
**Sources:**
- [Top 5 LangGraph Agents in Production 2024](https://blog.langchain.com/top-5-langgraph-agents-in-production-2024/)
- [How and when to build multi-agent systems](https://blog.langchain.com/how-and-when-to-build-multi-agent-systems/)

**Recommendations:**
- ✅ Start with 2 agents
- ✅ Add monitoring from day one
- ✅ Scale based on real usage data
- ⚠️ Over 75% of systems become difficult to manage with >5 agents

**Research finding:**
> "Research shows that over 75% of multi-agent systems become increasingly difficult to manage once they exceed five agents."

---

### 1.3 Context Engineering

#### #1 Job of AI Engineers
**Source:** [LangGraph Multi-Agent Orchestration Guide](https://latenode.com/blog/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)

**Critical success factor:**
> "Context engineering is effectively the #1 job of engineers building AI agents and is critical to making agentic systems work reliably."

**Best practices:**
- Full control over what gets passed into LLM
- No hidden prompts (LangGraph advantage)
- No enforced cognitive architectures
- Clean, focused context windows

#### Context Window Optimization
**Source:** [How to Continuously Improve Your LangGraph Multi-Agent System](https://galileo.ai/blog/evaluate-langgraph-multi-agent-telecom)

**Techniques:**
1. **Remove handoff messages** from sub-agent state
   - Assigned agents don't view supervisor routing logic
   - De-clutters context window
   - Even recent models: clutter impacts reliability

2. **Forward_message tool** for supervisor
   - Forwards sub-agent responses directly to users
   - No re-generation = fewer errors
   - Reduces supervisor paraphrasing mistakes

---

### 1.4 Production Deployment

#### Fault Tolerance
**Source:** [Benchmarking Multi-Agent Architectures](https://blog.langchain.com/benchmarking-multi-agent-architectures/)

**Required features:**
- ✅ Automated retries
- ✅ Per-node timeouts
- ✅ Pause and resume workflows at specific nodes
- ✅ Custom error recovery

**LangGraph advantages:**
- Stateful abstractions
- Time-travel debugging
- Human-in-the-loop interrupts
- Robust fault tolerance
- LangSmith integration for observability

---

### 1.5 Modularity & Independence

**Source:** [Building Multi-Agent Systems with LangGraph](https://medium.com/cwan-engineering/building-multi-agent-systems-with-langgraph-04f90f312b8e)

**Key benefit:**
> "Each agent can be developed, tested, and improved independently - when billing logic changes, you don't touch technical support code."

**Design principle:**
- Each agent = independent module
- Changes localized to single agent
- Easier testing and debugging
- Parallel development possible

---

## 2. Document Summarization Techniques

### 2.1 Comparison of Methods

**Sources:**
- [Google Cloud: Summarization techniques](https://cloud.google.com/blog/products/ai-machine-learning/long-document-summarization-with-workflows-and-gemini-models)
- [LangChain Summarization: Map-Reduce vs. Refine Methods](https://www.toolify.ai/ai-news/langchain-summarization-mapreduce-vs-refine-methods-3395910)
- [Different Text Summarization Techniques Using Langchain](https://www.baeldung.com/cs/langchain-text-summarize)

---

### 2.2 Method 1: Map-Reduce ⚡ FAST

#### How It Works
```
1. MAP Phase (Parallel):
   Document → Split into chunks
   Each chunk → Summarize independently (parallel)

2. REDUCE Phase:
   Combine summaries → Generate final summary
   If still too long → Repeat reduce step
```

#### Advantages ✅
- **Parallel processing** - Chunks summarized simultaneously
- **Handles extreme length** - No practical limit
- **Fast execution** - 15-30 seconds for large docs
- **Scalable** - Works with any document size

#### Disadvantages ❌
- **Context loss** - Chunks summarized independently
- **Coherence issues** - May lack narrative flow
- **Temporal dependencies** - Struggles with chronological info
- **Cost** - Uses all tokens + intermediate summaries

#### Best For:
- ✅ 300+ page documents
- ✅ Independent sections (manuals, encyclopedias)
- ✅ Speed is priority
- ✅ Parallel processing available

**Research quote:**
> "Parallelizing Map/Reduce speeds up execution time. Summarization can take 15-30 seconds to execute, depending on the size of the input text."

---

### 2.3 Method 2: Refine 🔄 COHERENT

#### How It Works
```
1. Summarize chunk 1
2. Combine summary + chunk 2 → Refine summary
3. Combine refined summary + chunk 3 → Refine again
4. Repeat until all chunks processed
```

#### Advantages ✅
- **Context retention** - Each step uses previous summary
- **Better coherence** - Maintains narrative flow
- **Document relations** - Understands connections
- **Simpler implementation** - Sequential process

#### Disadvantages ❌
- **Sequential processing** - Can't parallelize
- **Slower** - Must wait for each step
- **Recency bias** - Later chunks may have more weight
- **Order dependent** - Chunk sequence matters

#### Best For:
- ✅ Narrative documents (stories, reports)
- ✅ Sequential information (procedures)
- ✅ Context/flow is critical
- ✅ <100 pages (speed acceptable)

**Research quote:**
> "The refine chain technique retains context across document chunks, often generating a more coherent summary than map-reduce, with better handling of document relations and narrative flow."

---

### 2.4 Method 3: Hybrid Map-Reduce-Refine ⭐ RECOMMENDED

#### How It Works
```
1. Split document into logical sections (e.g., chapters)
2. Within each section:
   - Map-Reduce: Parallel summarize chunks
3. Across sections:
   - Refine: Sequential refinement with context
4. Final summary: Reduce all section summaries
```

#### Advantages ✅
- **Best of both** - Speed + coherence
- **Balanced** - Parallel within sections, sequential across
- **Scalable** - Handles any size
- **Quality** - Maintains context where needed

#### Best For:
- ✅ **300-page manuals** ← OUR USE CASE
- ✅ Structured documents (chapters/sections)
- ✅ Need both speed AND quality

---

### 2.5 Chunking Strategy

**Source:** [Chunking Strategies for LLM Applications | Pinecone](https://www.pinecone.io/learn/chunking-strategies/)

#### Context Window Considerations
**Modern LLMs:**
- 8k tokens = ~12 pages (6,000 words)
- 16k tokens = ~24 pages (12,000 words)
- 32k tokens = ~48 pages (24,000 words)
- 128k tokens = ~192 pages (96,000 words)

**Rule of thumb:**
> "100 tokens ≈ 75 words"

#### Chunk Size Trade-offs

**Smaller chunks (500-1000 tokens):**
- ✅ More detailed outcomes
- ✅ Better for rich, detailed content
- ❌ Slower (more LLM requests)
- ❌ Higher cost

**Larger chunks (2000-4000 tokens):**
- ✅ Faster processing
- ✅ Lower cost
- ✅ Better context retention
- ❌ May lose fine details

**Recommendation for 300-page docs:**
- Chunk size: **2000-3000 tokens** (~1500-2250 words)
- Overlap: **200-400 tokens** (~150-300 words)
- Balance speed and detail

---

### 2.6 2024 Innovation: Contextual Retrieval

**Source:** [How to Summarize Huge Documents with LLMs](https://dev.to/dmitrybaraishuk/how-to-summarize-huge-documents-with-llms-beyond-token-limits-and-basic-prompts-57ao)

**Anthropic's approach:**
1. Prompt Claude with entire document + specific chunk
2. Generate contextualized description for chunk
3. Append description to chunk before embedding
4. Result: Chunks have document-level context

**Benefit:**
- Chunks understand their place in larger document
- Better retrieval relevance
- Reduces "orphaned chunk" problem

---

## 3. Question Generation Best Practices

### 3.1 Multiple-Choice Question Generation (2024)

**Sources:**
- [Multiple-Choice Question Generation Using LLMs](https://dl.acm.org/doi/10.1145/3631700.3665233)
- [Automatic Multiple-Choice Question Generation](https://aclanthology.org/2025.coling-main.154.pdf)

---

### 3.2 Model Comparison (2024 Research)

**Study:** Comparative analysis of Llama 2, Mistral, and GPT-3.5

**Results:**
> "GPT-3.5 generating the most effective MCQs across several known metrics."

**Recommendation:**
- For production: **GPT-3.5 or newer**
- For cost: **Llama 3.1 70B** (good balance)
- For speed: **Mistral 7B** (acceptable quality)

---

### 3.3 Prompt Engineering Best Practices

**Source:** [Analysis of LLMs for educational question classification](https://www.sciencedirect.com/science/article/pii/S2666920X24001012)

#### Critical Techniques:

1. **Knowledge Injection**
   > "Inject knowledge into the prompt rather than relying on the LLM's knowledge, to contrast hallucinations"

   **Implementation:**
   ```
   Instead of: "Generate questions about this topic"
   Use: "Based on this text: [DOCUMENT CONTEXT], generate questions"
   ```

2. **Bloom's Taxonomy Integration**
   > "Incorporate the target level of Bloom's taxonomy in the prompt"

   **Levels for operators:**
   - Remember (easy): Recall facts
   - Understand (medium): Explain concepts
   - Apply (hard): Use procedures in new situations

3. **Difficulty Distribution**
   **Target:**
   - 40% Easy (Recall/Remember)
   - 40% Medium (Understand/Apply)
   - 20% Hard (Analyze/Evaluate)

---

### 3.4 Quality Assurance

**Source:** [Docimological Quality Analysis of LLM-Generated MCQs](https://link.springer.com/article/10.1007/s42979-024-02963-6)

#### Required Validation:

1. **Docimological Evaluation**
   - Question structure correctness
   - Key (correct answer) validity
   - Distractor (wrong answers) plausibility
   - No "all of the above" / "none of the above"

2. **Human-Based Evaluation**
   > "Human-based evaluation is still needed to ensure the semantic correctness and determine the relevance of generated questions"

3. **Hallucination Prevention**
   > "LLMs may use knowledge from outside the source text when generating questions, which can introduce hallucination effects."

   **Solution:**
   - Explicitly instruct: "Only use information from provided text"
   - Validate answers against source chunks
   - Track chunk references for each question

---

### 3.5 System Design Pattern

**Source:** [Optimizing Automated Question Generation](https://etasr.com/index.php/ETASR/article/view/10662)

**Multi-Module Pipeline:**
```
1. Preprocessing Module
   - Clean document
   - Extract key concepts

2. Glossary Generation Module
   - Identify important terms
   - Create definitions

3. Preliminary Question Module
   - Generate questions
   - Create options (A, B, C, D)

4. Question Review Module
   - Validate correctness
   - Check distractor quality
   - Ensure difficulty distribution
```

---

### 3.6 Challenges & Mitigations

**Source:** [An LLM-Guided Method for Controllable Question Generation](https://aclanthology.org/2024.findings-acl.280.pdf)

**Challenge 1: Quality Degradation**
> "The accuracy of question types generated by LLMs decreases as the sequence of generated questions progresses"

**Mitigation:**
- Generate in small batches (10-15 questions)
- Reset context between batches
- Validate each batch before continuing

**Challenge 2: Distractor Quality**
- Wrong answers must be plausible (not obviously wrong)
- Should reflect common misconceptions
- Must be unambiguously incorrect

**Mitigation:**
- Prompt for "plausible but incorrect" options
- Validate distractors against source text
- Human review of sample questions

---

## 4. Reflection Pattern for Quality

**Sources:**
- [What is Agentic AI Reflection Pattern?](https://www.analyticsvidhya.com/blog/2024/10/agentic-ai-reflection-pattern/)
- [Agent Reflection Pattern](https://aiengineering.academy/Agents/patterns/reflection_pattern/)
- [Reflection Pattern: When Agents think twice](https://theneuralmaze.substack.com/p/reflection-pattern-agents-that-think)

---

### 4.1 What is Reflection?

**Definition:**
> "The Reflection Pattern is a powerful approach in AI where an iterative process of generation and self-assessment improves the output quality."

**Core cycle:**
```
Generate → Critique → Refine → Repeat
```

---

### 4.2 How It Works

**Three Components:**

1. **Generation**
   - Model generates initial response
   - Evaluates output for quality
   - Then refines based on feedback

2. **Self-Reflection/Critique**
   - Evaluates own work
   - Checks for errors, inconsistencies
   - Identifies enhancement areas

3. **Iterative Refinement**
   - Cycle repeats multiple times
   - Each iteration improves quality
   - Mimics human revision process

---

### 4.3 Benefits

**Quality Improvement:**
> "Although the Reflection Pattern is the simplest of all the patterns, it provides surprising performance gains for the LLM response."

**Applications:**
- ✅ Text generation (summaries)
- ✅ Code development (validation)
- ✅ Complex problem solving
- ✅ Question generation (quality check)

**Example for our use case:**
```
1. Generate summary
2. Critique: "Is this clear for operators? Any jargon?"
3. Refine: Simplify language
4. Critique: "Does it cover safety? Complete procedures?"
5. Refine: Add missing elements
6. Final summary
```

---

### 4.4 Implementation Considerations

**Stopping Criteria:**
- Fixed iterations (e.g., 2-3 cycles)
- Quality threshold (scoring metric)
- No significant changes between iterations
- Time/cost limits

**Best practices:**
> "Defined stopping criteria prevent endless loops in the reflection process."

---

## 5. Recommended Architecture for NextLevel

Based on all research, here's the optimal architecture:

---

### 5.1 Summarization Pipeline Architecture

#### LangGraph State
```python
class SummarizationState(TypedDict):
    pdf_id: str
    pdf_name: str
    chunks: List[Dict]
    summary_type: str  # 'technical' or 'operator'
    batch_summaries: List[str]
    intermediate_summary: str
    final_summary: str
    key_topics: List[str]
    critique: str
    iteration: int
```

#### Agent Graph (Supervisor Pattern)
```
┌─────────────────┐
│   Supervisor    │ ← Orchestrates workflow
└────────┬────────┘
         │
    ┌────┴───────────────────────┐
    │                            │
┌───▼────┐                  ┌────▼────┐
│ Batch  │                  │ Section │
│ Agent  │ (Map)            │ Agent   │ (Reduce)
└───┬────┘                  └────┬────┘
    │                            │
    │  Parallel summarize   │   │ Sequential refine
    │  20-chunk batches     │   │ with context
    │                            │
    └────────────┬───────────────┘
                 │
            ┌────▼─────┐
            │ Reflect  │ ← Critique & refine
            │ Agent    │
            └────┬─────┘
                 │
            ┌────▼─────┐
            │ Extract  │ ← Pull key topics
            │ Agent    │
            └──────────┘
```

**Agents (5 total - within safe limit):**
1. **Supervisor** - Orchestrates workflow
2. **Batch Summarizer** - Parallel chunk summarization (Map)
3. **Section Refiner** - Sequential context refinement (Reduce)
4. **Reflection Agent** - Critique and improve quality
5. **Topic Extractor** - Extract key topics

---

### 5.2 Question Generation Pipeline Architecture

#### LangGraph State
```python
class QuestionGenState(TypedDict):
    pdf_id: str
    summary_text: str
    target_count: int  # 70
    questions: List[Dict]
    validated_questions: List[Dict]
    difficulty_distribution: Dict[str, int]
    topic_distribution: Dict[str, int]
    critique: str
    iteration: int
```

#### Agent Graph
```
┌─────────────────┐
│   Supervisor    │
└────────┬────────┘
         │
    ┌────┴───────────────────────┐
    │                            │
┌───▼────────┐            ┌──────▼──────┐
│ Generator  │            │ Validator   │
│ Agent      │            │ Agent       │
└───┬────────┘            └──────┬──────┘
    │                            │
    │ Generate 10 questions │    │ Check quality
    │ per batch (7 batches) │    │ - 4 unique options
    │                            │ - Answer in source
    │                            │ - Difficulty ok
    │                            │
    └────────────┬───────────────┘
                 │
            ┌────▼───────┐
            │ Categorizer│ ← Assign topics
            │ Agent      │
            └────┬───────┘
                 │
            ┌────▼────┐
            │ Linker  │ ← Link to pages/chunks
            │ Agent   │
            └─────────┘
```

**Agents (5 total):**
1. **Supervisor** - Orchestrates batches
2. **Generator Agent** - Create questions (batches of 10)
3. **Validator Agent** - Quality checks
4. **Categorizer Agent** - Assign topics & difficulty
5. **Linker Agent** - Link to source pages/chunks

---

### 5.3 Key Design Decisions

#### Chunking Strategy
- **Size:** 2000-3000 tokens (~1500-2250 words)
- **Overlap:** 200-400 tokens
- **Grouping:** 20 chunks per batch for summarization

#### Summarization Method
- **Hybrid Map-Reduce-Refine**
- Map: Parallel within batches (speed)
- Refine: Sequential across sections (context)
- Reflection: 2-3 critique-improve cycles

#### Question Generation
- **Batch size:** 10 questions per batch
- **Total batches:** 7 (for 70 questions)
- **Validation:** After each batch
- **Source grounding:** Explicit chunk references

#### Quality Controls
- **Reflection pattern:** 2-3 iterations for summaries
- **Human-in-the-loop:** Approval gates at key steps
- **Validation agents:** Dedicated quality checkers
- **Metrics tracking:** LangSmith observability

---

### 5.4 Context Optimization

**Apply research findings:**

1. **Clean context windows**
   - Remove routing logic from sub-agent views
   - Use forward_message to avoid paraphrasing

2. **Focused tools**
   - Each agent: 3-5 tools maximum
   - No overlapping responsibilities

3. **State management**
   - Minimal state passed between nodes
   - Clear separation of concerns

4. **Fault tolerance**
   - Retries on failed nodes
   - Timeouts per agent
   - Pause/resume capability

---

### 5.5 Performance Estimates

**For 300-page document:**

#### Summarization (Technical + Operator):
- Chunking: 5 seconds
- Map phase (20-chunk batches): 30-45 seconds (parallel)
- Reduce phase: 15-20 seconds
- Reflection: 20-30 seconds (2 iterations)
- **Total: ~2-3 minutes per summary**
- **Both summaries: ~5 minutes**

#### Question Generation (70 questions):
- 7 batches × 10 questions
- Per batch: 15-20 seconds (generation + validation)
- Categorization: 10 seconds
- Linking: 5 seconds
- **Total: ~3-4 minutes**

**End-to-end (Ingest + Summarize + Questions):**
- Ingestion: 40-110 seconds
- Summarization: ~300 seconds
- Questions: ~200 seconds
- **Total: ~10-12 minutes for complete processing**

---

## Sources

### LangGraph & Multi-Agent Systems
- [LangGraph: Multi-Agent Workflows](https://blog.langchain.com/langgraph-multi-agent-workflows/)
- [Advanced Multi-Agent Development with Langgraph](https://medium.com/@kacperwlodarczyk/advanced-multi-agent-development-with-langgraph-expert-guide-best-practices-2025-4067b9cec634)
- [Top 5 LangGraph Agents in Production 2024](https://blog.langchain.com/top-5-langgraph-agents-in-production-2024/)
- [How to Continuously Improve Your LangGraph Multi-Agent System](https://galileo.ai/blog/evaluate-langgraph-multi-agent-telecom)
- [Benchmarking Multi-Agent Architectures](https://blog.langchain.com/benchmarking-multi-agent-architectures/)
- [Building Multi-Agent Systems with LangGraph](https://medium.com/cwan-engineering/building-multi-agent-systems-with-langgraph-04f90f312b8e)
- [LangGraph Multi-Agent Orchestration Guide](https://latenode.com/blog/langgraph-multi-agent-orchestration-complete-framework-guide-architecture-analysis-2025)
- [How and when to build multi-agent systems](https://blog.langchain.com/how-and-when-to-build-multi-agent-systems/)

### Document Summarization
- [Google Cloud: Summarization techniques](https://cloud.google.com/blog/products/ai-machine-learning/long-document-summarization-with-workflows-and-gemini-models)
- [Iteratively Summarize Long Documents with an LLM](https://blog.metrostar.com/iteratively-summarize-long-documents-llm)
- [Chunking Strategies for LLM Applications | Pinecone](https://www.pinecone.io/learn/chunking-strategies/)
- [How to Summarize Huge Documents with LLMs](https://dev.to/dmitrybaraishuk/how-to-summarize-huge-documents-with-llms-beyond-token-limits-and-basic-prompts-57ao)
- [LangChain Summarization: Map-Reduce vs. Refine Methods](https://www.toolify.ai/ai-news/langchain-summarization-mapreduce-vs-refine-methods-3395910)
- [Different Text Summarization Techniques Using Langchain](https://www.baeldung.com/cs/langchain-text-summarize)
- [Summarize Text | LangChain](https://python.langchain.com/v0.2/docs/tutorials/summarization/)

### Question Generation
- [Multiple-Choice Question Generation Using LLMs](https://dl.acm.org/doi/10.1145/3631700.3665233)
- [Automatic Multiple-Choice Question Generation](https://aclanthology.org/2025.coling-main.154.pdf)
- [An LLM-Guided Method for Controllable Question Generation](https://aclanthology.org/2024.findings-acl.280.pdf)
- [Analysis of LLMs for educational question classification](https://www.sciencedirect.com/science/article/pii/S2666920X24001012)
- [Docimological Quality Analysis of LLM-Generated MCQs](https://link.springer.com/article/10.1007/s42979-024-02963-6)
- [Optimizing Automated Question Generation](https://etasr.com/index.php/ETASR/article/view/10662)

### Reflection Pattern
- [What is Agentic AI Reflection Pattern?](https://www.analyticsvidhya.com/blog/2024/10/agentic-ai-reflection-pattern/)
- [Agent Reflection Pattern](https://aiengineering.academy/Agents/patterns/reflection_pattern/)
- [Reflection Pattern: When Agents think twice](https://theneuralmaze.substack.com/p/reflection-pattern-agents-that-think)
- [Agentic Design Patterns](https://medium.com/@rsadaphule/agentic-design-patterns-7f8e921cace4)

---

*Last Updated: 2025-11-30*
*Next Step: Implement LangGraph agents based on these findings*
