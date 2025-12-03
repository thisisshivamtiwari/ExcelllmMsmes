"""
Semantic Indexing & RAG Module for ExcelLLM

This module provides:
- Embedding generation for Excel data (columns, descriptions, sample rows)
- Vector store integration (ChromaDB)
- Semantic search and retrieval
"""

from .embedder import Embedder
from .vector_store import VectorStore
from .retriever import Retriever

__all__ = ["Embedder", "VectorStore", "Retriever"]



