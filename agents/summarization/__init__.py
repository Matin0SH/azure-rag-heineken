"""
Summarization Agent Module

Extraction-based summarization using LangGraph for technical equipment manuals.
Generates two types of outputs:
- Technical: For engineers and maintenance staff
- Operator: For machine operators (8th-grade reading level)

Main entry point: create_summarization_graph()
"""

from .graph import create_summarization_graph

__all__ = ["create_summarization_graph"]
