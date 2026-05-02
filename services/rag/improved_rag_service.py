"""
Improved RAG Service - Supabase pgvector backend

Enhanced RAG service that integrates:
- Parent-Child Chunking for better context retrieval
- Hybrid Search (pgvector + tsvector) with RRF fusion in Supabase
- Cross-encoder Reranking for improved relevance

All vector and text search operations happen in PostgreSQL.
"""

import logging
import uuid
import json
import os
from typing import List, Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field

from langchain_huggingface import HuggingFaceEmbeddings

from services.rag.parent_child_chunker import ParentChildChunker
from services.rag.supabase_vector_store import SupabaseVectorStore
from services.rag.reranker import Reranker
from src.processors.document_processor import DocumentProcessor
from config.config import RAG_CONFIG, HUGGINGFACE_API_TOKEN

logger = logging.getLogger(__name__)


# ─── Module-level singleton ────────────────────────────────────────────────────
# Streamlit re-runs the script on every interaction. Re-creating HuggingFaceEmbeddings
# each time tries to move an already-loaded CUDA model to CUDA again, which triggers
# "Cannot copy out of meta tensor" in sentence-transformers 5.x.
# Keeping a single instance per Python process avoids the double-load.
_rag_service_instance: Optional["ImprovedRAGService"] = None


def get_rag_service(**kwargs) -> "ImprovedRAGService":
    """Return the module-level singleton ImprovedRAGService, creating it if needed."""
    global _rag_service_instance
    if _rag_service_instance is None:
        _rag_service_instance = ImprovedRAGService(**kwargs)
    return _rag_service_instance


@dataclass
class SearchResult:
    """
    Search result with parent context.
    """
    content: str
    score: float
    metadata: Dict[str, Any]
    source: str
    child_content: Optional[str] = None


class ImprovedRAGService:
    """
    Enhanced RAG service backed by Supabase pgvector.

    Pipeline:
    1. ParentChildChunker splits documents into hierarchical chunks
    2. HuggingFace embeddings (all-MiniLM-L6-v2, 384 dims) generated locally
    3. Chunks + embeddings stored in Supabase rag_chunks table
    4. Hybrid search via pgvector (cosine) + tsvector (full-text) with RRF fusion
    5. Cross-encoder reranking for final relevance ordering
    """

    def __init__(
        self,
        parent_chunk_size: int = 3000,
        child_chunk_size: int = 800,
    ):
        self.config = RAG_CONFIG
        self.collection_name = self.config.get(
            "collection_name", "clinical_guidelines"
        )

        # Component instances
        self.chunker: Optional[ParentChildChunker] = None
        self.reranker: Optional[Reranker] = None
        self.embeddings = None
        self.store: Optional[SupabaseVectorStore] = None
        self.document_processor = None

        # Chunk size configuration
        self.parent_chunk_size = parent_chunk_size
        self.child_chunk_size = child_chunk_size

        self._initialize_components()

        logger.info(
            f"ImprovedRAGService initialized with Supabase pgvector "
            f"(collection '{self.collection_name}')"
        )

    # ─── Initialization ────────────────────────────────────────────────

    def _initialize_components(self) -> None:
        """Initialize all RAG components."""
        try:
            # 1. ParentChildChunker
            self.chunker = ParentChildChunker(
                parent_size=self.parent_chunk_size,
                child_size=self.child_chunk_size,
            )
            logger.info("ParentChildChunker initialized")

            # 2. Embeddings — try CUDA first, fall back to CPU on any error
            device = "cpu"
            try:
                import torch
                if torch.cuda.is_available():
                    device = "cuda"
            except ImportError:
                pass

            model_kwargs = {"device": device}
            if HUGGINGFACE_API_TOKEN:
                model_kwargs["token"] = HUGGINGFACE_API_TOKEN

            try:
                self.embeddings = HuggingFaceEmbeddings(
                    model_name=self.config.get(
                        "embedding_model",
                        "sentence-transformers/all-MiniLM-L6-v2",
                    ),
                    model_kwargs=model_kwargs,
                    encode_kwargs={"normalize_embeddings": True},
                )
                logger.info(f"Embeddings initialized (device={device})")
            except Exception as emb_err:
                if device == "cuda":
                    logger.warning(
                        f"Failed to load embeddings on CUDA ({emb_err}), "
                        "retrying on CPU..."
                    )
                    model_kwargs["device"] = "cpu"
                    self.embeddings = HuggingFaceEmbeddings(
                        model_name=self.config.get(
                            "embedding_model",
                            "sentence-transformers/all-MiniLM-L6-v2",
                        ),
                        model_kwargs=model_kwargs,
                        encode_kwargs={"normalize_embeddings": True},
                    )
                    logger.info("Embeddings initialized (device=cpu, CUDA fallback)")
                else:
                    raise

            # 3. Supabase Vector Store
            self.store = SupabaseVectorStore(embeddings=self.embeddings)
            logger.info("SupabaseVectorStore initialized")

            # 4. Reranker — failure is non-fatal, reranking simply gets disabled
            try:
                self.reranker = Reranker()
                logger.info(f"Reranker initialized (available: {self.reranker.is_available})")
            except Exception as rerank_err:
                logger.warning(f"Reranker initialization failed ({rerank_err}), reranking disabled")
                self.reranker = Reranker.__new__(Reranker)
                self.reranker.model_name = Reranker.DEFAULT_MODEL
                self.reranker.model = None
                self.reranker._model_available = False

            # 5. Document processor
            self.document_processor = DocumentProcessor()
            logger.info("DocumentProcessor initialized")

        except Exception as e:
            logger.error(f"Error initializing ImprovedRAGService: {e}")
            raise

    # ─── Document Indexing ─────────────────────────────────────────────

    def add_documents(
        self,
        file_paths: List[str],
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Process and index documents with parent-child chunking.

        Args:
            file_paths: List of file paths to process
            metadata: Optional metadata to attach to documents

        Returns:
            Dict with processing results
        """
        results = {
            "success": True,
            "processed_files": [],
            "failed_files": [],
            "total_parent_chunks": 0,
            "total_child_chunks": 0,
        }

        if not file_paths:
            return results

        for file_path in file_paths:
            try:
                logger.info(f"Processing document: {file_path}")

                doc_chunks = self.document_processor.process_document(
                    file_path, metadata or {}
                )

                if not doc_chunks:
                    results["failed_files"].append(
                        {"file": file_path, "error": "No content extracted"}
                    )
                    continue

                full_text = "\n\n".join([c.page_content for c in doc_chunks])
                document_id = str(uuid.uuid4())
                filename = Path(file_path).name

                doc_metadata = {
                    "document_id": document_id,
                    "filename": filename,
                    "original_path": str(file_path),
                    **(metadata or {}),
                }

                parent_chunks, child_chunks = self.chunker.chunk_document(
                    full_text, doc_metadata
                )

                if not parent_chunks or not child_chunks:
                    results["failed_files"].append(
                        {"file": file_path, "error": "No chunks created"}
                    )
                    continue

                # Store in Supabase
                store_result = self.store.add_chunks(
                    parent_chunks, child_chunks, doc_metadata
                )

                if store_result.get("success"):
                    results["processed_files"].append({
                        "file": file_path,
                        "document_id": document_id,
                        "parent_chunks": len(parent_chunks),
                        "child_chunks": len(child_chunks),
                    })
                    results["total_parent_chunks"] += len(parent_chunks)
                    results["total_child_chunks"] += len(child_chunks)
                else:
                    results["failed_files"].append(
                        {"file": file_path, "error": store_result.get("error")}
                    )

            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                results["failed_files"].append({"file": file_path, "error": str(e)})

        if results["failed_files"]:
            results["success"] = len(results["processed_files"]) > 0

        return results

    def add_text(
        self,
        text: str,
        metadata: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        Add raw text directly to the index.

        Args:
            text: Text content to index
            metadata: Optional metadata for the document

        Returns:
            Dict with processing results
        """
        if not text or not text.strip():
            return {"success": False, "error": "Empty text provided"}

        try:
            document_id = str(uuid.uuid4())
            doc_metadata = {
                "document_id": document_id,
                "filename": metadata.get("filename", "direct_text") if metadata else "direct_text",
                **(metadata or {}),
            }

            parent_chunks, child_chunks = self.chunker.chunk_document(
                text, doc_metadata
            )

            if not parent_chunks or not child_chunks:
                return {"success": False, "error": "No chunks created from text"}

            store_result = self.store.add_chunks(
                parent_chunks, child_chunks, doc_metadata
            )

            if store_result.get("success"):
                return {
                    "success": True,
                    "document_id": document_id,
                    "parent_chunks": store_result["parent_chunks"],
                    "child_chunks": store_result["child_chunks"],
                }
            else:
                return {"success": False, "error": store_result.get("error")}

        except Exception as e:
            logger.error(f"Error adding text: {e}")
            return {"success": False, "error": str(e)}

    # ─── Search ────────────────────────────────────────────────────────

    def search(
        self,
        query: str,
        top_k: int = 5,
        rerank: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search for relevant documents using hybrid search and reranking.

        Pipeline:
        1. Hybrid search (pgvector + tsvector) on child chunks
        2. Rerank with cross-encoder (if enabled)
        3. Retrieve parent chunks for full context

        Args:
            query: Search query string
            top_k: Number of results to return
            rerank: Whether to apply reranking

        Returns:
            List of search results with parent context
        """
        if not query or not query.strip():
            return []

        try:
            # Step 1: Hybrid search on child chunks
            fetch_k = top_k * 4 if rerank else top_k
            hybrid_results = self.store.hybrid_search(query, top_k=fetch_k)

            if not hybrid_results:
                return []

            # Step 2: Rerank if enabled
            if rerank and self.reranker.is_available:
                reranked = self.reranker.rerank(
                    query=query, documents=hybrid_results, top_k=top_k
                )
            else:
                reranked = hybrid_results[:top_k]

            # Step 3: Retrieve parent chunks for context
            final_results = []
            seen_parents = set()

            for result in reranked:
                parent_id = result.get("parent_id")

                if parent_id and parent_id not in seen_parents:
                    seen_parents.add(parent_id)
                    parent = self.store.get_parent_chunk(parent_id)

                    if parent:
                        final_results.append({
                            "content": parent["content"],
                            "score": result.get("rerank_score", result.get("score", 0.0)),
                            "metadata": parent.get("metadata", {}),
                            "source": parent.get("filename", "Unknown"),
                            "child_content": result["content"],
                        })
                    else:
                        final_results.append({
                            "content": result["content"],
                            "score": result.get("rerank_score", result.get("score", 0.0)),
                            "metadata": result.get("metadata", {}),
                            "source": result.get("filename", "Unknown"),
                            "child_content": result["content"],
                        })
                elif not parent_id:
                    final_results.append({
                        "content": result["content"],
                        "score": result.get("rerank_score", result.get("score", 0.0)),
                        "metadata": result.get("metadata", {}),
                        "source": result.get("filename", "Unknown"),
                        "child_content": result["content"],
                    })

                if len(final_results) >= top_k:
                    break

            logger.info(f"Search completed: {len(final_results)} results")
            return final_results

        except Exception as e:
            logger.error(f"Error in search: {e}")
            return []

    def search_with_filter(
        self,
        query: str,
        filter_dict: Dict[str, Any],
        top_k: int = 5,
    ) -> List[Dict[str, Any]]:
        """Search with metadata filters (post-filter on search results)."""
        results = self.search(query, top_k=top_k * 2)

        filtered = []
        for r in results:
            matches = all(
                r["metadata"].get(k) == v for k, v in filter_dict.items()
            )
            if matches:
                filtered.append(r)
            if len(filtered) >= top_k:
                break

        return filtered

    def search_clinical_guidelines(
        self,
        query: str,
        specialty: str = None,
        top_k: int = None,
    ) -> List[Dict[str, Any]]:
        """Search clinical guidelines (backward-compatible interface)."""
        k = top_k or self.config.get("top_k", 5)

        if specialty:
            results = self.search_with_filter(
                query=query, filter_dict={"specialty": specialty}, top_k=k
            )
        else:
            results = self.search(query=query, top_k=k, rerank=True)

        return [
            {
                "content": r.get("content", ""),
                "metadata": r.get("metadata", {}),
                "source": r.get("source", "Desconocido"),
                "score": r.get("score", 0.0),
            }
            for r in results
        ]

    # ─── Delete Operations ─────────────────────────────────────────────

    def delete_document(self, document_id: str) -> Dict[str, Any]:
        """Delete a document and all its chunks."""
        try:
            result = self.store.delete_by_document_id(document_id)
            return {
                "success": result.get("success", False),
                "deleted_parent_chunks": result.get("deleted_count", 0),
                "document_id": document_id,
            }
        except Exception as e:
            logger.error(f"Error deleting document {document_id}: {e}")
            return {"success": False, "error": str(e)}

    def delete_documents(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Delete documents matching a metadata filter."""
        try:
            result = self.store.delete_by_filter(filter_dict)
            return {
                "success": result.get("success", False),
                "deleted_count": result.get("deleted_count", 0),
                "parents_removed": 0,
            }
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")
            return {"success": False, "error": str(e), "deleted_count": 0}

    # ─── Statistics & Management ───────────────────────────────────────

    def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        try:
            stats = self.store.get_collection_stats()
            if "error" in stats:
                return stats
            return stats
        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        try:
            collection_stats = self.store.get_collection_stats()
            return {
                "parent_chunks_count": len(collection_stats.get("sources", [])),
                "child_chunks_count": collection_stats.get("total_documents", 0),
                "reranker_stats": self.reranker.get_stats(),
                "collection_name": self.collection_name,
                "storage": "supabase_pgvector",
                "parent_chunk_size": self.parent_chunk_size,
                "child_chunk_size": self.child_chunk_size,
            }
        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            return {"error": str(e)}

    def get_document_ids(self) -> List[str]:
        """Get all unique document IDs."""
        try:
            result = (
                self.store.client.table(SupabaseVectorStore.TABLE_NAME)
                .select("document_id")
                .eq("is_parent", True)
                .execute()
            )
            return list({row["document_id"] for row in (result.data or [])})
        except Exception as e:
            logger.error(f"Error getting document IDs: {e}")
            return []

    def rebuild_indexes(self) -> Dict[str, Any]:
        """Clear and rebuild all indexes."""
        try:
            result = self.store.reset_collection()
            return {
                "success": result.get("success", False),
                "message": "Supabase collection reset" if result.get("success") else result.get("error"),
            }
        except Exception as e:
            logger.error(f"Error rebuilding indexes: {e}")
            return {"success": False, "message": str(e)}

    def rebuild_index(self) -> Dict[str, Any]:
        """Alias for rebuild_indexes."""
        return self.rebuild_indexes()

    def reset_collection(self) -> Dict[str, Any]:
        """Reset the entire collection."""
        return self.rebuild_indexes()

    def export_collection(self, output_path: str) -> Dict[str, Any]:
        """Export the collection to a JSON file."""
        try:
            from datetime import datetime

            result = (
                self.store.client.table(SupabaseVectorStore.TABLE_NAME)
                .select("chunk_id, content, metadata, is_parent, filename, document_id")
                .execute()
            )

            export_data = {
                "collection_name": self.collection_name,
                "storage": "supabase_pgvector",
                "export_timestamp": datetime.now().isoformat(),
                "total_documents": len(result.data or []),
                "documents": result.data or [],
            }

            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            return {
                "success": True,
                "exported_documents": len(result.data or []),
                "output_path": output_path,
            }
        except Exception as e:
            logger.error(f"Error exporting collection: {e}")
            return {"success": False, "error": str(e)}

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        try:
            from services.cache_manager import cache_manager
            stats = cache_manager.get_cache_stats("all")
            return {
                "embeddings": stats.get("by_cache_type", {}).get("embeddings", {}),
                "llm_responses": stats.get("by_cache_type", {}).get("llm_responses", {}),
                "query_results": stats.get("by_cache_type", {}).get("query_results", {}),
                "total_cache_size_mb": stats.get("total", {}).get("total_size_mb", 0),
                "overall_hit_rate": stats.get("total", {}).get("hit_rate", 0),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {}

    def clear_cache(self, cache_type: str = "all") -> Dict[str, Any]:
        """Clear caches."""
        try:
            from services.cache_manager import cache_manager
            return cache_manager.clear_cache(cache_type)
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return {"error": str(e)}
