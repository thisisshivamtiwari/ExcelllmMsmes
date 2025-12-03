"""
Embedding generation for Excel data using sentence-transformers.

Generates embeddings for:
- Column names and descriptions
- User-provided column definitions
- Sample data rows (top 10-20 per column)
- Relationship descriptions
"""

from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import logging
import numpy as np

logger = logging.getLogger(__name__)


class Embedder:
    """Generate embeddings for Excel data using sentence-transformers."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize the embedder with a sentence transformer model.
        
        Args:
            model_name: Name of the sentence transformer model to use.
                       Default: "all-MiniLM-L6-v2" (lightweight, fast, good quality)
        """
        try:
            logger.info(f"Loading embedding model: {model_name}")
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
            logger.info(f"✓ Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {str(e)}")
            raise
    
    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.
        
        Args:
            text: Text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        if not text or not isinstance(text, str):
            text = str(text) if text else ""
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True, normalize_embeddings=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Error embedding text: {str(e)}")
            # Return zero vector as fallback
            return [0.0] * self.model.get_sentence_embedding_dimension()
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for a batch of texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts to process at once
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        # Filter out None/empty texts
        clean_texts = [str(t) if t else "" for t in texts]
        
        try:
            embeddings = self.model.encode(
                clean_texts,
                batch_size=batch_size,
                convert_to_numpy=True,
                normalize_embeddings=True,
                show_progress_bar=False
            )
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error embedding batch: {str(e)}")
            # Return zero vectors as fallback
            dim = self.model.get_sentence_embedding_dimension()
            return [[0.0] * dim] * len(texts)
    
    def embed_column_metadata(
        self,
        column_name: str,
        column_type: Optional[str] = None,
        description: Optional[str] = None,
        user_definition: Optional[str] = None,
        sample_values: Optional[List[str]] = None,
        max_samples: int = 10
    ) -> Dict[str, Any]:
        """
        Generate embeddings for column metadata.
        
        Args:
            column_name: Name of the column
            column_type: Detected or inferred type (date, numeric, categorical, etc.)
            description: AI-generated or user-provided description
            user_definition: User-provided definition/metadata
            sample_values: Sample data values from the column
            max_samples: Maximum number of sample values to include
            
        Returns:
            Dictionary with embeddings and metadata
        """
        # Build text representations for different aspects
        
        # 1. Column name and type
        name_text = f"Column: {column_name}"
        if column_type:
            name_text += f" (Type: {column_type})"
        
        # 2. Description text
        desc_text = ""
        if description:
            desc_text = f"Description: {description}"
        elif user_definition:
            desc_text = f"Definition: {user_definition}"
        
        # 3. Sample data text
        sample_text = ""
        if sample_values:
            samples = sample_values[:max_samples]
            sample_text = f"Sample values: {', '.join(str(v) for v in samples)}"
        
        # Combine all into a single context
        full_context = " ".join(filter(None, [name_text, desc_text, sample_text]))
        
        # Generate embeddings
        name_embedding = self.embed_text(name_text)
        context_embedding = self.embed_text(full_context)
        
        return {
            "column_name": column_name,
            "column_type": column_type,
            "description": description,
            "user_definition": user_definition,
            "name_embedding": name_embedding,
            "context_embedding": context_embedding,
            "sample_values": sample_values[:max_samples] if sample_values else [],
            "embedding_dimension": len(name_embedding)
        }
    
    def embed_relationship(
        self,
        relationship: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate embedding for a relationship description.
        
        Args:
            relationship: Relationship dictionary with type, description, etc.
            
        Returns:
            Dictionary with relationship embedding
        """
        # Build relationship text
        rel_type = relationship.get("type", "unknown")
        description = relationship.get("description", "")
        source_col = relationship.get("source_column", relationship.get("column", ""))
        target_col = relationship.get("target_column", "")
        
        rel_text = f"Relationship: {rel_type}"
        if description:
            rel_text += f" - {description}"
        if source_col and target_col:
            rel_text += f" ({source_col} → {target_col})"
        
        embedding = self.embed_text(rel_text)
        
        return {
            "relationship": relationship,
            "embedding": embedding,
            "text": rel_text
        }
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        return self.model.get_sentence_embedding_dimension()




