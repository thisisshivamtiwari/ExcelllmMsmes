"""
Semantic Indexing & RAG Module for ExcelLLM

This module provides:
- Embedding generation for Excel data (columns, descriptions, sample rows)
- Vector store integration (ChromaDB)
- Semantic search and retrieval
"""

from .embedder import Embedder
from .vector_store import VectorStore  # Legacy ChromaDB implementation
from .mongodb_vector_store import MongoDBVectorStore  # New MongoDB implementation
from .retriever import Retriever

__all__ = ["Embedder", "VectorStore", "MongoDBVectorStore", "Retriever"]




