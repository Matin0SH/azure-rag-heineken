"""
Reranking Prompt for LLM-based Page Scoring
Based on LangChain RERANK_PROMPT_JSON pattern
"""

# Simple char-based token estimation (no tiktoken needed)
def count_tokens(text: str) -> int:
    return len(text) // 4

RERANKER_TOKEN_LIMIT = 2000

RERANK_PROMPT_TEMPLATE = """You are an expert relevance evaluator. Your task is to score the relevance of each document to the given query.

Query: {query}

Documents to score:
{documents}

Instructions:
1. Evaluate each document's relevance to the query on a scale of 0-10
2. Consider:
   - Direct answers to the query (score 8-10)
   - Relevant context or related information (score 5-7)
   - Tangentially related content (score 2-4)
   - Irrelevant content (score 0-1)
3. Respond with ONLY a JSON array of scores in the exact order documents were presented

Output format: [score1, score2, score3, ...]

Example: [9, 6, 3, 8, 2]

Scores:"""


def build_rerank_prompt(query: str, pages: list) -> str:
    """
    Build reranking prompt with query and full page contexts (up to 2000 tokens per page)

    Args:
        query: User's search query
        pages: List of dicts with keys: pdf_id, page_number, text, chunks

    Returns:
        str: Formatted prompt for LLM
    """
    documents_text = ""
    for idx, page in enumerate(pages, 1):
        pdf_name = page.get("pdf_id", "unknown")
        page_num = page.get("page_number", "?")
        text = page.get("text", "")

        # Truncate to configured token limit (not characters)
        token_count = count_tokens(text)
        if token_count > RERANKER_TOKEN_LIMIT:
            # Binary search to find approximate character limit for target tokens
            char_limit = int(len(text) * (RERANKER_TOKEN_LIMIT / token_count))
            preview = text[:char_limit]
            # Verify and adjust
            while count_tokens(preview) > RERANKER_TOKEN_LIMIT:
                char_limit = int(char_limit * 0.9)
                preview = text[:char_limit]
            preview += "..."
        else:
            preview = text

        documents_text += f"\n[Document {idx}] (Source: {pdf_name}, Page {page_num})\n{preview}\n"

    return RERANK_PROMPT_TEMPLATE.format(
        query=query,
        documents=documents_text.strip()
    )
