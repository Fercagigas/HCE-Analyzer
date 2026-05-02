"""
RAG (Retrieval-Augmented Generation) improvement components.

This package contains improved RAG components including:
- ParentChildChunker: Hierarchical chunking for better context
- SupabaseVectorStore: Vector store backed by Supabase pgvector
- Reranker: Cross-encoder reranking for relevance
- ImprovedRAGService: Integrated service combining all components
"""

from services.rag.parent_child_chunker import ParentChildChunker
from services.rag.supabase_vector_store import SupabaseVectorStore
from services.rag.reranker import Reranker
from services.rag.improved_rag_service import ImprovedRAGService

__all__ = [
    'ParentChildChunker',
    'SupabaseVectorStore',
    'Reranker',
    'ImprovedRAGService',
]
