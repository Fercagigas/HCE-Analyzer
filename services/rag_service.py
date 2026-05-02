"""
RAG Service - Thin facade over ImprovedRAGService

This module provides backward-compatible access to RAG functionality
by delegating all operations to ImprovedRAGService.

ImprovedRAGService is the single source of truth for:
- Document indexing (parent-child chunking + Supabase pgvector)
- Hybrid search (pgvector + tsvector) with RRF fusion
- Cross-encoder reranking
- Collection management
"""
import logging
from typing import List, Dict, Any, Optional

from services.rag.improved_rag_service import ImprovedRAGService, get_rag_service

logger = logging.getLogger(__name__)


class RAGService:
    """Backward-compatible facade for RAG functionality."""
    
    def __init__(self):
        """Use singleton ImprovedRAGService to avoid re-loading CUDA models."""
        self._service = get_rag_service()
        logger.info("RAGService initialized (delegating to ImprovedRAGService)")

    @property
    def vectorstore(self):
        """Access the underlying vectorstore for backward compatibility."""
        return self._service.vectorstore

    def add_documents(
        self, file_paths: List[str], metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Add documents to the RAG index."""
        return self._service.add_documents(file_paths, metadata)

    def search_clinical_guidelines(
        self, query: str, specialty: str = None, top_k: int = None
    ) -> List[Dict[str, Any]]:
        """Search clinical guidelines."""
        return self._service.search_clinical_guidelines(query, specialty, top_k)

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        return self._service.get_collection_stats()

    def delete_documents(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Delete documents matching a filter."""
        return self._service.delete_documents(filter_dict)

    def rebuild_index(self) -> Dict[str, Any]:
        """Rebuild all indexes."""
        return self._service.rebuild_indexes()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return self._service.get_cache_stats()

    def clear_cache(self, cache_type: str = "all") -> Dict[str, Any]:
        """Clear caches."""
        return self._service.clear_cache(cache_type)

    def export_collection(self, output_path: str) -> Dict[str, Any]:
        """Export the collection to a JSON file."""
        return self._service.export_collection(output_path)

    def reset_collection(self) -> Dict[str, Any]:
        """Reset the entire collection."""
        return self._service.reset_collection()
