"""
Question Generation Agent Module

Generates training questions from document chunks using MAP-REDUCE pattern.
Uses hierarchical 3-to-1 reduction with Spark SQL ai_query for parallel processing.

Main entry point: create_question_generation_graph()
"""

from .graph import create_question_generation_graph

__all__ = ["create_question_generation_graph"]
