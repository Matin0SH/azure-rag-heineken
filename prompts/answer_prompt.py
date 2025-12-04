"""
Answer Generation Prompt Templates
Based on LangChain ANSWER_COT_PROMPT with Chain-of-Thought reasoning
"""

ANSWER_COT_TEMPLATE = """You are a technical documentation assistant. The context below contains individual document PAGES that were rebuilt from multiple text chunks. Treat each [Doc X] block as a single page; do not merge unrelated instructions across pages unless the page itself does so.

Context (Ordered Pages):
{context}

User Question: {query}

Instructions:
1. Understand what the user is trying to accomplish, even if the wording does not exactly match the manuals. Map the request to similar procedures already described in the pages.
2. Review every page in the order provided. Keep procedures, steps, warnings, and troubleshooting flows intact for each page. Never combine different issues into one blended procedure.
3. Extract all information that is relevant to the task while keeping the original structure (steps remain steps, warnings remain warnings). If multiple procedures are relevant, output them as clearly separated sections.
4. If the pages lack the required details, explicitly state what is missing.
5. **CITATION FORMAT**: Cite sources using [Doc X] format where X is the document number (e.g., [Doc 1], [Doc 2]). You can cite multiple documents like [Doc 1, Doc 3]. Place citations immediately after the claim. Citations must reference only the documents that actually supply the information.

Response Format (use these exact tags):
<reasoning>
- Bullet list of how each document supports (or does not support) the requested task. Use [Doc X] format for references.
</reasoning>

<final_answer>
[Direct answer with numbered steps or bullet sections. Keep the order found in the documents and do not invent steps. Cite using [Doc X] format immediately after each claim.]
</final_answer>

<citations>
[Doc 1], [Doc 2], [Doc 3]
(List all documents you cited in the answer, comma-separated)
</citations>

Answer:"""


def build_answer_prompt(query: str, pages: list) -> str:
    """
    Build answer generation prompt with context and structured document indexing

    Args:
        query: User's question
        pages: List of ranked page dicts with keys: pdf_id, page_number, text, rerank_score

    Returns:
        str: Formatted prompt for LLM
    """
    context_text = ""
    for idx, page in enumerate(pages, 1):
        pdf_name = page.get("pdf_id", "unknown")
        page_num = page.get("page_number", "?")
        text = page.get("text", "")
        score = page.get("rerank_score", 0)

        context_text += f"\n[Doc {idx}] (Source: {pdf_name}, Page {page_num}, Relevance: {score}/10)\n{text}\n"
        context_text += "-" * 80 + "\n"

    return ANSWER_COT_TEMPLATE.format(
        query=query,
        context=context_text.strip()
    )


def parse_answer_response(response_text: str, pages: list) -> dict:
    """
    Parse LLM response to extract reasoning, answer, and citations
    Maps [Doc X] references to actual (pdf_id, page_number) pairs

    Args:
        response_text: Raw LLM response with tags
        pages: Original pages list used in prompt (for mapping Doc index to pdf_id/page)

    Returns:
        dict: {
            "reasoning": str,
            "answer": str,
            "citations": list of dict [{"doc_num": int, "pdf_id": str, "page_number": int}],
            "cited_pages": list of (pdf_id, page_number) tuples for screenshot lookup
        }
    """
    import re

    result = {
        "reasoning": "",
        "answer": "",
        "citations": [],
        "cited_pages": []
    }

    # Extract reasoning
    reasoning_match = re.search(r'<reasoning>(.*?)</reasoning>', response_text, re.DOTALL | re.IGNORECASE)
    if reasoning_match:
        result["reasoning"] = reasoning_match.group(1).strip()

    # Extract final answer
    answer_match = re.search(r'<final_answer>(.*?)</final_answer>', response_text, re.DOTALL | re.IGNORECASE)
    if answer_match:
        result["answer"] = answer_match.group(1).strip()

    # Extract citations block
    citations_match = re.search(r'<citations>(.*?)</citations>', response_text, re.DOTALL | re.IGNORECASE)
    citations_text = citations_match.group(1).strip() if citations_match else ""

    # Find all [Doc X] references in answer and citations
    doc_pattern = re.compile(r'\[Doc\s+(\d+)\]', re.IGNORECASE)
    cited_doc_nums = set()

    # Extract from answer
    for match in doc_pattern.finditer(result["answer"]):
        cited_doc_nums.add(int(match.group(1)))

    # Extract from citations block
    for match in doc_pattern.finditer(citations_text):
        cited_doc_nums.add(int(match.group(1)))

    # Map Doc numbers to (pdf_id, page_number) using pages array
    for doc_num in sorted(cited_doc_nums):
        # Doc numbers are 1-indexed
        if 1 <= doc_num <= len(pages):
            page = pages[doc_num - 1]
            pdf_id = page.get("pdf_id", "unknown")
            page_number = page.get("page_number", 0)

            result["citations"].append({
                "doc_num": doc_num,
                "pdf_id": pdf_id,
                "page_number": page_number
            })
            result["cited_pages"].append((pdf_id, page_number))

    # Fallback: if no tags found, use entire response as answer
    if not result["answer"]:
        result["answer"] = response_text.strip()

    return result
