"""
Prompts for question generation workflow.

Generates training questions from operator summaries for machine operators.
"""

# ==============================================================================
# QUESTION GENERATION PROMPTS
# ==============================================================================

GENERATE_SYSTEM = """You are generating training questions for machine operators.

GOAL: Create practical, scenario-based questions that test operator knowledge.

AUDIENCE: Machine operators (8th-grade reading level).

QUESTION TYPES:
1. **Safety Check Questions** - "What should you check before...?"
2. **Procedure Questions** - "What are the steps to...?"
3. **Troubleshooting Questions** - "If X happens, what should you do?"
4. **Understanding Questions** - "Why do we need to...?"

KEY RULES:
1. Use SIMPLE language (8th-grade level)
2. Base questions ONLY on content from operator summary
3. Include the correct answer for each question
4. Vary difficulty: Easy (40%), Medium (40%), Hard (20%)
5. Cover different topics from the summary
6. Make questions practical and scenario-based

OUTPUT FORMAT (JSON):
{
  "questions": [
    {
      "question": "What should you check before starting the machine?",
      "answer": "Check that the emergency stop is accessible, safety guards are in place, and the work area is clear.",
      "difficulty": "easy",
      "topic": "Safety Checks"
    },
    ...
  ]
}
"""

GENERATE_HUMAN = """OPERATOR SUMMARY:
{summary}

Generate {num_questions} training questions based on this operator summary.

Requirements:
- Simple language (8th-grade level)
- Practical scenarios operators will face
- Mix of safety, procedure, troubleshooting questions
- Vary difficulty: {easy_count} easy, {medium_count} medium, {hard_count} hard
- Return as JSON with question, answer, difficulty, topic

ONLY use information from the summary above.
"""


# ==============================================================================
# CRITIQUE PROMPTS (Quality check for questions)
# ==============================================================================

CRITIQUE_SYSTEM = """You are a quality auditor for training questions.

CRITICAL CHECKS:
1. Are questions based ONLY on the operator summary?
2. Is language simple (8th-grade level)?
3. Are answers complete and correct?
4. Do questions cover different topics?
5. Is difficulty distribution appropriate?

ACCEPT if 90%+ meets standards.

OUTPUT:
If acceptable: PASS

If issues:
FAIL
ISSUES:
- [Specific problem with example]
- [What needs fixing]
"""

CRITIQUE_HUMAN = """OPERATOR SUMMARY:
{summary}

GENERATED QUESTIONS:
{questions}

Quick audit:
- Are questions based only on summary content?
- Is language simple enough?
- Are answers complete?

If yes, say PASS. If major issues, list them.
"""
