"""
RAG Chat Service - Retrieval, Reranking, Answer Generation
"""
from typing import Dict, Any, List, Optional, Tuple
from fastapi import HTTPException
import json
import re

from databricks.sdk import WorkspaceClient
from databricks.sdk.service.serving import ChatMessage, ChatMessageRole

from app.config.settings import settings
from app.prompts.reranker_prompt import build_rerank_prompt
from app.prompts.answer_prompt import build_answer_prompt, parse_answer_response


class ChatService:
    """Service for RAG chat pipeline"""

    @staticmethod
    def retrieve_chunks(query: str, pdf_id: Optional[str] = None, top_k: int = 20) -> List[Dict[str, Any]]:
        """
        Step 1: Vector search to retrieve top K relevant chunks

        Args:
            query: User's question
            pdf_id: Optional filter by specific PDF
            top_k: Number of chunks to retrieve

        Returns:
            List of chunk dicts with keys: chunk_id, pdf_id, page_number, text, score
        """
        try:
            from databricks.sdk import WorkspaceClient
            import json

            w = WorkspaceClient(
                host=settings.DATABRICKS_HOST,
                token=settings.DATABRICKS_TOKEN
            )

            # Step 1: Generate embeddings using Foundation Model API
            print(f"[EMBEDDING] Generating embeddings for query: {query[:100]}...")

            # Call embedding endpoint using Foundation Model API format
            import requests

            embedding_url = f"{settings.DATABRICKS_HOST}/serving-endpoints/{settings.EMBEDDING_MODEL}/invocations"
            headers = {
                "Authorization": f"Bearer {settings.DATABRICKS_TOKEN}",
                "Content-Type": "application/json"
            }
            payload = {"input": [query]}

            response = requests.post(embedding_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()

            # Extract embedding vector
            result_json = response.json()
            query_vector = None

            # Try different response formats
            if "data" in result_json and len(result_json["data"]) > 0:
                query_vector = result_json["data"][0].get("embedding")
            elif "embeddings" in result_json:
                query_vector = result_json["embeddings"][0]
            elif "predictions" in result_json:
                query_vector = result_json["predictions"][0]

            if not query_vector:
                raise ValueError(f"Failed to extract embedding from response: {result_json}")

            print(f"[EMBEDDING] Generated embedding vector of length {len(query_vector)}")

            # Step 2: Query vector index with embedding
            full_index_name = f"{settings.CATALOG_NAME}.{settings.SCHEMA_NAME}.{settings.VECTOR_INDEX_NAME}"
            print(f"[RETRIEVAL] Searching vector index: {full_index_name}")

            # Build filters if pdf_id specified
            filters_json = None
            if pdf_id:
                filters_json = json.dumps({"pdf_id": pdf_id})

            # Execute similarity search with query vector
            results = w.vector_search_indexes.query_index(
                index_name=full_index_name,
                query_vector=query_vector,
                columns=["chunk_id", "pdf_id", "page_number", "text"],
                filters_json=filters_json,
                num_results=top_k
            )

            # Parse results
            chunks = []
            if hasattr(results, 'result') and hasattr(results.result, 'data_array'):
                for row in results.result.data_array:
                    chunks.append({
                        "chunk_id": row[0],
                        "pdf_id": row[1],
                        "page_number": int(row[2]),
                        "text": row[3],
                        "score": row[4] if len(row) > 4 else 0.0
                    })

            print(f"[RETRIEVAL] Retrieved {len(chunks)} chunks")
            return chunks

        except Exception as e:
            print(f"[ERROR] Vector search failed: {e}")
            import traceback
            traceback.print_exc()
            raise HTTPException(
                status_code=500,
                detail=f"Vector search failed: {str(e)}"
            )

    @staticmethod
    def group_chunks_by_page(chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 2: Group chunks by (pdf_id, page_number) and rebuild full page text

        Args:
            chunks: List of chunk dicts

        Returns:
            List of page dicts with keys: pdf_id, page_number, text, chunks
        """
        from collections import defaultdict

        print(f"[GROUPING] Grouping {len(chunks)} chunks by page...")

        # Group chunks by (pdf_id, page_number)
        page_groups = defaultdict(list)
        for chunk in chunks:
            key = (chunk["pdf_id"], chunk["page_number"])
            page_groups[key].append(chunk)

        # Rebuild full page text by concatenating chunks
        pages = []
        for (pdf_id, page_number), page_chunks in page_groups.items():
            # Sort chunks by chunk_id or order (assuming chunk_id has ordering info)
            page_chunks_sorted = sorted(page_chunks, key=lambda x: x["chunk_id"])

            # Concatenate text
            full_text = "\n\n".join([chunk["text"] for chunk in page_chunks_sorted])

            pages.append({
                "pdf_id": pdf_id,
                "page_number": page_number,
                "text": full_text,
                "chunks": page_chunks_sorted,
                "num_chunks": len(page_chunks_sorted)
            })

        # Sort pages by highest chunk score
        pages.sort(key=lambda p: max([c["score"] for c in p["chunks"]]), reverse=True)

        print(f"[GROUPING] Grouped into {len(pages)} unique pages")
        return pages

    @staticmethod
    def rerank_pages(query: str, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Step 3: Use LLM to rerank pages by relevance (0-10 scores)

        Args:
            query: User's question
            pages: List of page dicts

        Returns:
            List of pages sorted by rerank_score (highest first)
        """
        try:
            w = WorkspaceClient(
                host=settings.DATABRICKS_HOST,
                token=settings.DATABRICKS_TOKEN
            )

            # Build reranking prompt
            print(f"[RERANK] Reranking {len(pages)} pages...")
            rerank_prompt = build_rerank_prompt(query, pages)

            # Call LLM for scoring
            messages = [
                ChatMessage(role=ChatMessageRole.USER, content=rerank_prompt)
            ]

            response = w.serving_endpoints.query(
                name=settings.LLM_ENDPOINT,
                inputs={
                    "messages": [{"role": m.role.value, "content": m.content} for m in messages]
                }
            )

            # Parse scores from JSON response
            response_text = ""
            if hasattr(response, 'predictions') and response.predictions:
                if isinstance(response.predictions[0], dict):
                    response_text = response.predictions[0].get('choices', [{}])[0].get('message', {}).get('content', '')
                else:
                    response_text = str(response.predictions[0])

            print(f"[RERANK] LLM response: {response_text[:200]}")

            # Extract JSON array of scores
            scores = []
            try:
                # Try to find JSON array in response
                json_match = re.search(r'\[[\d\s,]+\]', response_text)
                if json_match:
                    scores = json.loads(json_match.group(0))
                else:
                    raise ValueError("No JSON array found in response")
            except Exception as e:
                print(f"[RERANK] Failed to parse scores: {e}. Using default scores.")
                scores = [5.0] * len(pages)  # Fallback to neutral scores

            # Assign scores to pages
            for i, page in enumerate(pages):
                if i < len(scores):
                    page["rerank_score"] = float(scores[i])
                else:
                    page["rerank_score"] = 0.0

            # Sort by rerank score
            pages.sort(key=lambda p: p["rerank_score"], reverse=True)

            print(f"[RERANK] Top 3 scores: {[p['rerank_score'] for p in pages[:3]]}")
            return pages

        except Exception as e:
            print(f"[ERROR] Reranking failed: {e}")
            # Fallback: return pages with default scores
            for page in pages:
                page["rerank_score"] = 5.0
            return pages

    @staticmethod
    def generate_answer(query: str, ranked_pages: List[Dict[str, Any]], top_n: int = 10) -> Dict[str, Any]:
        """
        Step 4: Generate answer using top N pages with Chain-of-Thought

        Args:
            query: User's question
            ranked_pages: Pages sorted by rerank_score
            top_n: Number of top pages to use for answer

        Returns:
            Dict with keys: answer, reasoning, citations, cited_pages
        """
        try:
            w = WorkspaceClient(
                host=settings.DATABRICKS_HOST,
                token=settings.DATABRICKS_TOKEN
            )

            # Take top N pages
            top_pages = ranked_pages[:top_n]
            print(f"[ANSWER] Generating answer using top {len(top_pages)} pages...")

            # Build answer prompt
            answer_prompt = build_answer_prompt(query, top_pages)

            # Call LLM
            messages = [
                ChatMessage(role=ChatMessageRole.USER, content=answer_prompt)
            ]

            response = w.serving_endpoints.query(
                name=settings.LLM_ENDPOINT,
                inputs={
                    "messages": [{"role": m.role.value, "content": m.content} for m in messages]
                }
            )

            # Parse response
            response_text = ""
            if hasattr(response, 'predictions') and response.predictions:
                if isinstance(response.predictions[0], dict):
                    response_text = response.predictions[0].get('choices', [{}])[0].get('message', {}).get('content', '')
                else:
                    response_text = str(response.predictions[0])

            print(f"[ANSWER] LLM response length: {len(response_text)} chars")

            # Parse structured response
            parsed = parse_answer_response(response_text, top_pages)

            return parsed

        except Exception as e:
            print(f"[ERROR] Answer generation failed: {e}")
            raise HTTPException(
                status_code=500,
                detail=f"Answer generation failed: {str(e)}"
            )

    @staticmethod
    def chat(query: str, pdf_id: Optional[str] = None, top_k: int = 20) -> Dict[str, Any]:
        """
        Main RAG pipeline: Retrieve -> Group -> Rerank -> Answer

        Args:
            query: User's question
            pdf_id: Optional PDF filter
            top_k: Number of chunks to retrieve

        Returns:
            Complete chat response dict
        """
        print(f"\n{'='*80}")
        print(f"[CHAT] Starting RAG pipeline for query: {query[:100]}")
        print(f"{'='*80}\n")

        # Step 1: Retrieve chunks
        chunks = ChatService.retrieve_chunks(query, pdf_id, top_k)

        if not chunks:
            return {
                "query": query,
                "answer": "No relevant information found in the knowledge base.",
                "reasoning": "Vector search returned no results.",
                "citations": [],
                "cited_pages": [],
                "num_chunks_retrieved": 0,
                "num_pages_ranked": 0,
                "top_reranked_pages": []
            }

        # Step 2: Group by page
        pages = ChatService.group_chunks_by_page(chunks)

        # Step 3: Rerank pages
        ranked_pages = ChatService.rerank_pages(query, pages)

        # Step 4: Generate answer
        answer_result = ChatService.generate_answer(query, ranked_pages, top_n=10)

        # Build response
        response = {
            "query": query,
            "answer": answer_result["answer"],
            "reasoning": answer_result["reasoning"],
            "citations": answer_result["citations"],
            "cited_pages": answer_result["cited_pages"],
            "num_chunks_retrieved": len(chunks),
            "num_pages_ranked": len(pages),
            "top_reranked_pages": [
                {
                    "pdf_id": p["pdf_id"],
                    "page_number": p["page_number"],
                    "rerank_score": p["rerank_score"],
                    "text_preview": p["text"][:200] + "..." if len(p["text"]) > 200 else p["text"]
                }
                for p in ranked_pages[:5]
            ]
        }

        print(f"\n{'='*80}")
        print(f"[CHAT] Pipeline complete. Answer length: {len(response['answer'])} chars")
        print(f"{'='*80}\n")

        return response


# Singleton instance
chat_service = ChatService()
