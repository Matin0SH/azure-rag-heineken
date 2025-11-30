"""
Question Generation Agent Module

Generates training questions from operator summaries for assessment and training.
Uses LangGraph for orchestration with reflection pattern.

Main entry point: create_question_generation_graph()
"""

from .graph import create_question_generation_graph

__all__ = ["create_question_generation_graph"]
