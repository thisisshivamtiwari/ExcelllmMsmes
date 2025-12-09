"""
Vector store integration using ChromaDB for semantic search.

Stores and manages embeddings for:
- Column metadata
- Relationships
- File schemas
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path
import json

logger = logging.getLogger(__name__)


class VectorStore:
    """ChromaDB-based vector store for semantic indexing."""
    
    def __init__(self, persist_directory: Optional[Path] = None, collection_name: str = "excel_data"):
        """
        Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Directory to persist ChromaDB data. If None, uses in-memory mode.
            collection_name: Name of the ChromaDB collection
        """
        self.collection_name = collection_name
        
        if persist_directory:
            persist_directory = Path(persist_directory)
            persist_directory.mkdir(parents=True, exist_ok=True)
            self.persist_path = str(persist_directory)
            logger.info(f"Initializing ChromaDB with persistence: {self.persist_path}")
        else:
            self.persist_path = None
            logger.info("Initializing ChromaDB in-memory mode")
        
        try:
            # Initialize ChromaDB client
            if self.persist_path:
                self.client = chromadb.PersistentClient(
                    path=self.persist_path,
                    settings=Settings(anonymized_telemetry=False)
                )
            else:
                self.client = chromadb.Client(
                    settings=Settings(anonymized_telemetry=False)
                )
            
            # Get or create collection
            try:
                self.collection = self.client.get_collection(name=collection_name)
                logger.info(f"Loaded existing collection: {collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=collection_name,
                    metadata={"description": "Excel data semantic index"}
                )
                logger.info(f"Created new collection: {collection_name}")
            
            logger.info("✓ Vector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise
    
    def add_column(
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
        
        # Prepare metadata
        doc_metadata = {
            "file_id": file_id,
            "file_name": file_name,
            "sheet_name": sheet_name,
            "column_name": column_name,
            "type": metadata.get("column_type", "unknown"),
            "description": metadata.get("description", ""),
            "user_definition": metadata.get("user_definition", ""),
        }
        
        # Add user_id for multi-tenant support (convert to string for ChromaDB compatibility)
        if user_id:
            # Convert ObjectId to string if needed (MongoDB ObjectId -> str)
            doc_metadata["user_id"] = str(user_id) if user_id else None
        
        # Add sample values if available
        if metadata.get("sample_values"):
            doc_metadata["sample_values"] = json.dumps(metadata["sample_values"][:5])
        
        # Create document text for search
        doc_text = f"Column: {column_name}"
        if doc_metadata["description"]:
            doc_text += f" - {doc_metadata['description']}"
        elif doc_metadata["user_definition"]:
            doc_text += f" - {doc_metadata['user_definition']}"
        
        try:
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[doc_text],
                metadatas=[doc_metadata]
            )
            logger.debug(f"Added column to vector store: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error adding column to vector store: {str(e)}")
            raise
    
    def add_relationship(
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
        
        # Prepare metadata
        doc_metadata = {
            "type": "relationship",
            "relationship_type": rel_type,
            "source_column": source_col,
            "target_column": target_col,
            "description": relationship.get("description", ""),
            "strength": relationship.get("strength", "medium"),
            "impact": relationship.get("impact", "informational"),
        }
        
        # Add user_id for multi-tenant support (convert to string for ChromaDB compatibility)
        if user_id:
            # Convert ObjectId to string if needed (MongoDB ObjectId -> str)
            doc_metadata["user_id"] = str(user_id) if user_id else None
        
        try:
            self.collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[doc_text],
                metadatas=[doc_metadata]
            )
            logger.debug(f"Added relationship to vector store: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error adding relationship to vector store: {str(e)}")
            raise
    
    def search(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        filter_metadata: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search for similar items in the vector store.
        
        Args:
            query_embedding: Embedding vector of the query
            n_results: Number of results to return
            filter_metadata: Optional metadata filters (e.g., {"file_id": "..."})
            user_id: User ID for multi-tenant filtering (required for SaaS)
            
        Returns:
            List of search results with metadata
        """
        try:
            # Always filter by user_id for multi-tenant support
            where = filter_metadata.copy() if filter_metadata else {}
            if user_id:
                # Convert ObjectId to string if needed (MongoDB ObjectId -> str)
                where["user_id"] = str(user_id) if user_id else None
            
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where
            )
            
            # Format results
            formatted_results = []
            if results["ids"] and len(results["ids"][0]) > 0:
                for i in range(len(results["ids"][0])):
                    formatted_results.append({
                        "id": results["ids"][0][i],
                        "document": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i] if "distances" in results else None
                    })
            
            return formatted_results
        except Exception as e:
            logger.error(f"Error searching vector store: {str(e)}")
            return []
    
    def delete_file(self, file_id: str, user_id: Optional[str] = None) -> bool:
        """
        Delete all entries for a specific file.
        
        Args:
            file_id: File ID to delete
            user_id: User ID for multi-tenant filtering (required for SaaS)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Build filter with user_id for multi-tenant support
            where = {"file_id": file_id}
            if user_id:
                # Convert ObjectId to string if needed (MongoDB ObjectId -> str)
                where["user_id"] = str(user_id) if user_id else None
            
            # Get all documents for this file (and user)
            results = self.collection.get(where=where)
            
            if results["ids"]:
                self.collection.delete(ids=results["ids"])
                logger.info(f"Deleted {len(results['ids'])} entries for file: {file_id}")
            
            return True
        except Exception as e:
            logger.error(f"Error deleting file from vector store: {str(e)}")
            return False
    
    def get_collection_stats(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get statistics about the vector store collection."""
        try:
            # Count all documents or filter by user_id
            if user_id:
                # Convert ObjectId to string if needed (MongoDB ObjectId -> str)
                results = self.collection.get(where={"user_id": str(user_id) if user_id else None})
                count = len(results["ids"]) if results["ids"] else 0
            else:
                count = self.collection.count()
            
            return {
                "collection_name": self.collection_name,
                "total_documents": count,
                "persist_path": self.persist_path,
                "user_specific": user_id is not None
            }
        except Exception as e:
            logger.error(f"Error getting collection stats: {str(e)}")
            return {
                "collection_name": self.collection_name,
                "total_documents": 0,
                "error": str(e)
            }




