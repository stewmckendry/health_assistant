"""
Search module for Dr. OPA MCP tools.
Implements Vector → Rerank → Filter algorithm for semantic search.
"""

from .semantic_search import SemanticSearchEngine

__all__ = ['SemanticSearchEngine']