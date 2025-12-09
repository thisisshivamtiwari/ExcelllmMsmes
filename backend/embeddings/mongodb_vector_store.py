"""
MongoDB-based vector store for semantic search.
Stores embeddings directly in MongoDB collections.

Stores and manages embeddings for:
- Column metadata
- Relationships
- File schemas
"""

import numpy as np
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
from bson import ObjectId

logger = logging.getLogger(__name__)


class MongoDBVectorStore:
    """MongoDB-based vector store for semantic indexing."""
    
    def __init__(self, database=None, collection_name: str = "embeddings"):
        """
        Initialize MongoDB vector store.
        
        Args:
            database: MongoDB database instance (from database.get_database())
            collection_name: Name of the MongoDB collection for embeddings
        """
        self.collection_name = collection_name
        
        if database is None:
            from database import get_database
            self.database = get_database()
        else:
            self.database = database
        
        self.collection = self.database[collection_name]
        logger.info(f"Initialized MongoDB vector store: {collection_name}")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        vec1 = np.array(vec1)
        vec2 = np.array(vec2)
        
        dot_product = np.dot(vec1, vec2)
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    async def add_column(
        self,
        file_id: str,
        file_name: str,
        sheet_name: str,
        column_name: str,
        embedding: List[float],
        metadata: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> str:
        """
        Add a column to the vector store.
        
        Args:
            file_id: Unique identifier for the file
            file_name: Original filename
            sheet_name: Name of the sheet
            column_name: Name of the column
            embedding: Embedding vector for the column
            metadata: Additional metadata (type, description, etc.)
            user_id: User ID for multi-tenant support (required for SaaS)
            
        Returns:
            ID of the added document
        """
        doc_id = f"{file_id}::{sheet_name}::{column_name}"
        
        # Create document text for search
        doc_text = f"Column: {column_name}"
        description = metadata.get("description", "")
        user_definition = metadata.get("user_definition", "")
        
        if description:
            doc_text += f" - {description}"
        elif user_definition:
            doc_text += f" - {user_definition}"
        
        # Prepare document
        doc = {
            "_id": doc_id,
            "type": "column",
            "file_id": file_id,
            "file_name": file_name,
            "sheet_name": sheet_name,
            "column_name": column_name,
            "embedding": embedding,
            "document": doc_text,
            "column_type": metadata.get("column_type", "unknown"),
            "description": description,
            "user_definition": user_definition,
            "created_at": datetime.utcnow(),
        }
        
        # Add user_id for multi-tenant support
        if user_id:
            doc["user_id"] = str(user_id) if isinstance(user_id, ObjectId) else user_id
        
        # Add sample values if available
        if metadata.get("sample_values"):
            doc["sample_values"] = metadata["sample_values"][:5]
        
        try:
            # Use replace_one with upsert to handle duplicates
            self.collection.replace_one(
                {"_id": doc_id},
                doc,
                upsert=True
            )
            logger.debug(f"Added column to MongoDB vector store: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error adding column to MongoDB vector store: {str(e)}")
            raise
    
    async def add_relationship(
        self,
        relationship: Dict[str, Any],
        embedding: List[float],
        user_id: Optional[str] = None
    ) -> str:
        """
        Add a relationship to the vector store.
        
        Args:
            relationship: Relationship dictionary
            embedding: Embedding vector for the relationship
            user_id: User ID for multi-tenant support (required for SaaS)
            
        Returns:
            ID of the added document
        """
        rel_type = relationship.get("type", "unknown")
        source_col = relationship.get("source_column", relationship.get("column", ""))
        target_col = relationship.get("target_column", "")
        
        doc_id = f"relationship::{rel_type}::{source_col}::{target_col}"
        
        # Create document text
        doc_text = f"Relationship: {rel_type}"
        if relationship.get("description"):
            doc_text += f" - {relationship['description']}"
        
        # Prepare document
        doc = {
            "_id": doc_id,
            "type": "relationship",
            "relationship_type": rel_type,
            "source_column": source_col,
            "target_column": target_col,
            "embedding": embedding,
            "document": doc_text,
            "description": relationship.get("description", ""),
            "strength": relationship.get("strength", "medium"),
            "impact": relationship.get("impact", "informational"),
            "created_at": datetime.utcnow(),
        }
        
        # Add user_id for multi-tenant support
        if user_id:
            doc["user_id"] = str(user_id) if isinstance(user_id, ObjectId) else user_id
        
        try:
            # Use replace_one with upsert to handle duplicates (async Motor)
            await self.collection.replace_one(
                {"_id": doc_id},
                doc,
                upsert=True
            )
            logger.debug(f"Added relationship to MongoDB vector store: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error adding relationship to MongoDB vector store: {str(e)}")
            raise
    
    async def search(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar items in the vector store using cosine similarity.
        
        Args:
            query_embedding: Embedding vector of the query
            n_results: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"file_id": "..."})
            user_id: User ID for multi-tenant filtering (required for SaaS)
            
        Returns:
            List of search results with metadata
        """
        try:
            # Build MongoDB query filter
            query_filter = {}
            
            # Always filter by user_id for multi-tenant support
            if user_id:
                query_filter["user_id"] = str(user_id) if isinstance(user_id, ObjectId) else user_id
            
            # Add additional filters
            if filter_metadata:
                query_filter.update(filter_metadata)
            
            # Fetch all matching documents
            cursor = self.collection.find(query_filter)
            documents = await cursor.to_list(length=None)
            
            # Calculate cosine similarity for each document
            results_with_similarity = []
            for doc in documents:
                if "embedding" not in doc:
                    continue
                
                similarity = self._cosine_similarity(query_embedding, doc["embedding"])
                
                # Convert distance to similarity (cosine similarity is already 0-1)
                distance = 1.0 - similarity  # Convert similarity to distance
                
                results_with_similarity.append({
                    "id": doc["_id"],
                    "document": doc.get("document", ""),
                    "metadata": {k: v for k, v in doc.items() if k not in ["embedding", "_id"]},
                    "distance": distance,
                    "similarity": similarity
                })
            
            # Sort by similarity (descending) and take top n_results
            results_with_similarity.sort(key=lambda x: x["similarity"], reverse=True)
            results = results_with_similarity[:n_results]
            
            return results
        except Exception as e:
            logger.error(f"Error searching MongoDB vector store: {str(e)}")
            return []
    
    async def delete_file(self, file_id: str, user_id: Optional[str] = None) -> bool:
        """
        Delete all entries for a specific file.
        
        Args:
            file_id: File ID to delete
            user_id: User ID for multi-tenant filtering (required for SaaS)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build filter
            query_filter = {"file_id": file_id}
            if user_id:
                query_filter["user_id"] = str(user_id) if isinstance(user_id, ObjectId) else user_id
            
            # Delete all matching documents
            result = await self.collection.delete_many(query_filter)
            logger.info(f"Deleted {result.deleted_count} entries for file: {file_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting file from MongoDB vector store: {str(e)}")
            return False
    
    async def get_collection_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about the vector store collection."""
        try:
            # Build filter
            query_filter = {}
            if user_id:
                query_filter["user_id"] = str(user_id) if isinstance(user_id, ObjectId) else user_id
            
            # Count documents
            count = await self.collection.count_documents(query_filter)
            
            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "user_specific": user_id is not None
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {
                "collection_name": self.collection_name,
                "total_documents": 0,
                "error": str(e)
            }

