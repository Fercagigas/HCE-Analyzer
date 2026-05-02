"""
Reranker for RAG System

This module implements cross-encoder reranking to improve search result relevance.
Uses the cross-encoder/ms-marco-MiniLM-L-6-v2 model for computing query-document
relevance scores.
"""

import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class Reranker:
    """
    Cross-encoder reranker for improving search result relevance.
    
    Uses a cross-encoder model to compute relevance scores between
    query and document pairs, then reorders results by score.
    
    Requirements: 3.1, 3.2
    """
    
    DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
    
    def __init__(self, model_name: str = DEFAULT_MODEL):
        """
        Initialize the Reranker with a cross-encoder model.
        
        Args:
            model_name: Name of the cross-encoder model to use
                       (default: cross-encoder/ms-marco-MiniLM-L-6-v2)
                       
        Requirements: 3.1
        """
        self.model_name = model_name
        self.model = None
        self._model_available = False
        
        # Try to load the model
        self._load_model()
    
    def _load_model(self) -> None:
        """
        Load the cross-encoder model.

        Sets _model_available to False if loading fails.
        """
        try:
            from sentence_transformers import CrossEncoder

            logger.info(f"Loading cross-encoder model: {self.model_name}")

            # Try loading on CPU to avoid meta-tensor issues with CUDA
            self.model = CrossEncoder(self.model_name, device="cpu")
            self._model_available = True
            logger.info(f"Cross-encoder model loaded successfully: {self.model_name}")

        except ImportError as e:
            logger.warning(
                f"sentence-transformers not available, reranking disabled: {e}"
            )
            self._model_available = False

        except Exception as e:
            logger.warning(
                f"Failed to load cross-encoder model '{self.model_name}': {e}. "
                "Reranking will be disabled."
            )
            self._model_available = False

    
    @property
    def is_available(self) -> bool:
        """
        Check if the reranker model is available.
        
        Returns:
            True if model is loaded and ready, False otherwise
        """
        return self._model_available and self.model is not None
    
    def rerank(
        self, 
        query: str, 
        documents: List[Dict[str, Any]], 
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Rerank documents by relevance to the query using cross-encoder.
        
        If the model is unavailable, returns the original documents unchanged.
        
        Args:
            query: Search query to rank documents against
            documents: List of document dicts with 'content' key
            top_k: Maximum number of documents to return
            
        Returns:
            List of document dicts with added 'rerank_score' key,
            sorted by relevance score descending
            
        Requirements: 3.1, 3.2, 3.3, 3.4
        """
        if not documents:
            logger.debug("No documents provided for reranking")
            return []
        
        if not query or not query.strip():
            logger.warning("Empty query provided for reranking")
            return documents[:top_k]
        
        # If model is not available, return original results
        # Requirements: 3.3
        if not self.is_available:
            logger.warning(
                "Reranker model not available, returning original results without reranking"
            )
            return documents[:top_k]
        
        try:
            # Extract document contents for scoring
            doc_contents = []
            for doc in documents:
                content = doc.get('content', '')
                if isinstance(content, str):
                    doc_contents.append(content)
                else:
                    doc_contents.append(str(content))
            
            # Create query-document pairs for cross-encoder
            # Requirements: 3.2
            pairs = [(query, content) for content in doc_contents]
            
            # Compute relevance scores
            scores = self.model.predict(pairs)
            
            # Add scores to documents and sort
            scored_docs = []
            for doc, score in zip(documents, scores):
                doc_copy = doc.copy()
                doc_copy['rerank_score'] = float(score)
                scored_docs.append(doc_copy)
            
            # Sort by rerank_score descending
            # Requirements: 3.1, 3.4
            scored_docs.sort(key=lambda x: x['rerank_score'], reverse=True)
            
            # Return top_k results
            result = scored_docs[:top_k]
            
            logger.info(
                f"Reranked {len(documents)} documents, returning top {len(result)}. "
                f"Score range: [{result[-1]['rerank_score']:.4f}, {result[0]['rerank_score']:.4f}]"
                if result else "No results"
            )
            
            return result
            
        except Exception as e:
            # Requirements: 3.3 - Return original results on error
            logger.warning(
                f"Error during reranking: {e}. Returning original results."
            )
            return documents[:top_k]
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the reranker.
        
        Returns:
            Dict with reranker statistics
        """
        return {
            'model_name': self.model_name,
            'model_available': self._model_available,
            'model_loaded': self.model is not None
        }
