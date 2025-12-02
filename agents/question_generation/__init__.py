"""
Question Generation Agent Module

Generates training questions from document chunks using batch-based processing.
Each batch: GENERATE → JUDGE → REFINE (max 2 iterations)
Uses max 3 workers to avoid API rate limits.

Main entry point: create_question_generation_graph() or run_question_generation()
"""

from .graph import create_question_generation_graph, run_question_generation

__all__ = ["create_question_generation_graph", "run_question_generation"]
