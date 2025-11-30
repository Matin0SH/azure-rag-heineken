"""
Prompts for summarization workflow.

All prompts follow EXTRACTION philosophy: preserve completeness, not reduce.
"""

# ==============================================================================
# TECHNICAL EXTRACTION PROMPTS (for engineers/maintenance staff)
# ==============================================================================

TECH_MAP_SYSTEM = """You are extracting technical information from equipment manuals.

CRITICAL: You are EXTRACTING, not summarizing. DO NOT reduce or paraphrase.

GOAL: Extract ALL technical specifications and procedures exactly as written.

AUDIENCE: Engineers and maintenance staff.

KEY RULES:
1. EXTRACT all procedures - keep every step verbatim
2. EXTRACT all technical values with units (e.g., "45 Nm", "120°C", "2.5 bar")
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


# ==============================================================================
# OPERATOR EXTRACTION PROMPTS (for machine operators)
# ==============================================================================

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


# ==============================================================================
# COMBINATION PROMPTS (REDUCE phase - ORGANIZING, not reducing)
# ==============================================================================

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

REDUCE_HUMAN = """EXTRACTIONS TO ORGANIZE:
{extractions}

ORGANIZE into final document.
- KEEP all procedures and specifications
- Group related procedures together
- ONLY remove exact duplicates
- DO NOT reduce for brevity
- Completeness > brevity"""


# ==============================================================================
# CRITIQUE PROMPTS (Quality check)
# ==============================================================================

CRITIQUE_SYSTEM = """You are a quality auditor for technical documentation.

CRITICAL CHECKS:
1. Are all procedures present and separate?
2. Are technical values preserved correctly?
3. Is structure complete?

ACCEPT if 90%+ meets standards. Minor formatting issues OK.

OUTPUT:
If acceptable: PASS

If issues:
FAIL
ISSUES:
- [Specific problem with example]
- [What needs fixing]"""

CRITIQUE_HUMAN = """DOCUMENT TO VALIDATE:
{summary}

Quick audit: Are procedures preserved and separate? Are values present?
If yes, say PASS. If major issues, list them."""


# ==============================================================================
# TOPIC EXTRACTION PROMPT
# ==============================================================================

TOPIC_EXTRACTION_SYSTEM = """Extract 5-10 key topics from this technical document.

Return as comma-separated list.

Focus on: major systems, procedures, safety topics, technical domains."""

TOPIC_EXTRACTION_HUMAN = """DOCUMENT:
{summary}

Extract key topics. Return as comma-separated list only."""
