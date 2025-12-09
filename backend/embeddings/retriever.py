"""
Semantic retrieval system for Excel data.

Provides context-aware retrieval using relationships and metadata.
"""

from typing import List, Dict, Any, Optional
import logging
from .embedder import Embedder

logger = logging.getLogger(__name__)

# Support both ChromaDB and MongoDB vector stores
try:
    from .mongodb_vector_store import MongoDBVectorStore
    MongoDBVectorStoreType = MongoDBVectorStore
except ImportError:
    MongoDBVectorStoreType = None

try:
    from .vector_store import VectorStore
    VectorStoreType = VectorStore
except ImportError:
    VectorStoreType = None


class Retriever:
    """Semantic retriever for Excel data using embeddings."""
    
    def __init__(self, embedder: Embedder, vector_store):
        """
        Initialize the retriever.
        
        Args:
            embedder: Embedder instance for generating query embeddings
            vector_store: VectorStore instance for searching
        """
        self.embedder = embedder
        self.vector_store = vector_store
    
    async def retrieve_columns(
        self,
        query: str,
        n_results: int = 10,
        file_filter: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant columns based on a natural language query.
        
        Args:
            query: Natural language query
            n_results: Number of results to return
            file_filter: Optional file_id to filter results
            user_id: User ID for multi-tenant filtering (required for SaaS)
            
        Returns:
            List of relevant columns with metadata
        """
        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_text(query)
            
            # Build filter if needed
            filter_metadata = None
            if file_filter:
                filter_metadata = {"file_id": file_filter}
            
            # Search vector store (with user_id filtering) - async for MongoDB
            import inspect
            if inspect.iscoroutinefunction(self.vector_store.search):
                results = await self.vector_store.search(
                    query_embedding=query_embedding,
                    n_results=n_results,
                    filter_metadata=filter_metadata,
                    user_id=user_id
                )
            else:
                results = self.vector_store.search(
                    query_embedding=query_embedding,
                    n_results=n_results,
                    filter_metadata=filter_metadata,
                    user_id=user_id
                )
            
            # Filter to only column results (not relationships)
            column_results = []
            for result in results:
                metadata = result.get("metadata", {})
                if metadata.get("type") != "relationship":
                    # ChromaDB uses cosine distance (0-2), convert to similarity (0-1)
                    distance = result.get("distance", 2.0)
                    # Normalize: distance 0 = similarity 1, distance 2 = similarity 0
                    relevance_score = max(0.0, 1.0 - (distance / 2.0))
                    
                    column_results.append({
                        "file_id": metadata.get("file_id"),
                        "file_name": metadata.get("file_name"),
                        "sheet_name": metadata.get("sheet_name"),
                        "column_name": metadata.get("column_name"),
                        "column_type": metadata.get("type"),
                        "description": metadata.get("description"),
                        "user_definition": metadata.get("user_definition"),
                        "relevance_score": relevance_score,
                        "document": result.get("document")
                    })
            
            return column_results
        except Exception as e:
            logger.error(f"Error retrieving columns: {str(e)}")
            return []
    
    async def retrieve_relationships(
        self,
        query: str,
        n_results: int = 5,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve relevant relationships based on a query.
        
        Args:
            query: Natural language query
            n_results: Number of results to return
            user_id: User ID for multi-tenant filtering (required for SaaS)
            
        Returns:
            List of relevant relationships
        """
        try:
            # Generate query embedding
            query_embedding = self.embedder.embed_text(query)
            
            # Search for relationships only (with user_id filtering) - async for MongoDB
            filter_metadata = {"type": "relationship"}
            
            import inspect
            if inspect.iscoroutinefunction(self.vector_store.search):
                results = await self.vector_store.search(
                    query_embedding=query_embedding,
                    n_results=n_results,
                    filter_metadata=filter_metadata,
                    user_id=user_id
                )
            else:
                results = self.vector_store.search(
                    query_embedding=query_embedding,
                    n_results=n_results,
                    filter_metadata=filter_metadata,
                    user_id=user_id
                )
            
            # Format results
            relationship_results = []
            for result in results:
                metadata = result.get("metadata", {})
                # ChromaDB uses cosine distance (0-2), convert to similarity (0-1)
                distance = result.get("distance", 2.0)
                relevance_score = max(0.0, 1.0 - (distance / 2.0))
                
                relationship_results.append({
                    "type": metadata.get("relationship_type"),
                    "source_column": metadata.get("source_column"),
                    "target_column": metadata.get("target_column"),
                    "description": metadata.get("description"),
                    "strength": metadata.get("strength"),
                    "impact": metadata.get("impact"),
                    "relevance_score": relevance_score,
                    "document": result.get("document")
                })
            
            return relationship_results
        except Exception as e:
            logger.error(f"Error retrieving relationships: {str(e)}")
            return []
    
    async def retrieve_context(
        self,
        query: str,
        n_columns: int = 10,
        n_relationships: int = 5,
        file_filter: Optional[str] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve comprehensive context (columns + relationships) for a query.
        
        Args:
            query: Natural language query
            n_columns: Number of relevant columns to retrieve
            n_relationships: Number of relevant relationships to retrieve
            file_filter: Optional file_id to filter results
            user_id: User ID for multi-tenant filtering (required for SaaS)
            
        Returns:
            Dictionary with columns and relationships
        """
        columns = await self.retrieve_columns(
            query=query,
            n_results=n_columns,
            file_filter=file_filter,
            user_id=user_id
        )
        
        relationships = await self.retrieve_relationships(
            query=query,
            n_results=n_relationships,
            user_id=user_id
        )
        
        return {
            "query": query,
            "columns": columns,
            "relationships": relationships,
            "total_results": len(columns) + len(relationships)
        }

