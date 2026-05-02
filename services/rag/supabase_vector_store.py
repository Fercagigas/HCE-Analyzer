"""
Supabase Vector Store for RAG System

Provides vector similarity search, full-text search, and hybrid search
using PostgreSQL functions (pgvector + tsvector).

Uses the same embedding model (sentence-transformers/all-MiniLM-L6-v2, 384 dims)
and stores everything in Supabase rag_chunks table.
"""
import logging
from typing import Dict, Any, Optional, List, Tuple

from supabase import create_client, Client
from config.settings import settings

logger = logging.getLogger(__name__)


def _sanitize_text(text: str) -> str:
    """
    Remove null bytes and other characters that PostgreSQL rejects in text columns.

    PostgreSQL error 22P05: '\\u0000 cannot be converted to text' is raised when
    a string contains the null character (U+0000). This commonly happens with
    PDFs that embed binary data or form fields in their text layer.
    """
    if not isinstance(text, str):
        text = str(text) if text is not None else ""
    # Remove null bytes (U+0000) — the primary cause of error 22P05
    text = text.replace("\x00", "")
    # Also strip other non-printable control characters that can cause issues
    # (keep newlines \n, carriage returns \r, and tabs \t which are valid)
    import re
    text = re.sub(r"[\x01-\x08\x0b\x0c\x0e-\x1f\x7f]", "", text)
    return text


class SupabaseVectorStore:
    """
    Vector store backed by Supabase pgvector.

    Handles:
    - Storing parent and child chunks with embeddings
    - Hybrid search (vector + full-text) via SQL RPC functions
    - Document CRUD operations
    - Collection statistics
    """

    TABLE_NAME = "rag_chunks"

    def __init__(self, embeddings=None):
        """
        Initialize the Supabase vector store.

        Args:
            embeddings: HuggingFaceEmbeddings instance for generating vectors
        """
        self.embeddings = embeddings
        self.client: Optional[Client] = None
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Create Supabase client."""
        try:
            self.client = create_client(
                settings.database.supabase_url,
                settings.database.supabase_key,
            )
            logger.info("SupabaseVectorStore: cliente inicializado")
        except Exception as e:
            logger.error(f"Error inicializando cliente Supabase: {e}")
            raise

    # ─── CRUD Operations ───────────────────────────────────────────────

    def add_chunks(
        self,
        parent_chunks: List[Dict[str, Any]],
        child_chunks: List[Dict[str, Any]],
        doc_metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Store parent and child chunks with embeddings in Supabase.

        Args:
            parent_chunks: List of parent chunk dicts from ParentChildChunker
            child_chunks: List of child chunk dicts from ParentChildChunker
            doc_metadata: Document-level metadata (filename, specialty, etc.)

        Returns:
            Dict with success status and counts
        """
        if not self.client or not self.embeddings:
            return {"success": False, "error": "Store not initialized"}

        try:
            filename = doc_metadata.get("filename", "unknown")
            specialty = doc_metadata.get("specialty")
            document_type = doc_metadata.get("document_type")
            document_id = doc_metadata.get("document_id", "unknown")

            # 1. Generate embeddings for child chunks
            child_texts = [_sanitize_text(c["content"]) for c in child_chunks]
            child_embeddings = self.embeddings.embed_documents(child_texts)

            # 2. Insert parent chunks (no embedding needed, used for context retrieval)
            parent_records = []
            for parent in parent_chunks:
                parent_records.append({
                    "document_id": document_id,
                    "chunk_id": parent["chunk_id"],
                    "parent_id": None,
                    "content": _sanitize_text(parent["content"]),
                    "embedding": None,
                    "metadata": parent.get("metadata", {}),
                    "is_parent": True,
                    "filename": filename,
                    "specialty": specialty,
                    "document_type": document_type,
                })

            if parent_records:
                self.client.table(self.TABLE_NAME).insert(parent_records).execute()

            # 3. Insert child chunks with embeddings
            child_records = []
            for child, emb in zip(child_chunks, child_embeddings):
                child_records.append({
                    "document_id": document_id,
                    "chunk_id": child["chunk_id"] if isinstance(child, dict) else child.get("chunk_id"),
                    "parent_id": child["metadata"]["parent_id"] if isinstance(child, dict) else None,
                    "content": _sanitize_text(child["content"]),
                    "embedding": emb,
                    "metadata": child.get("metadata", {}),
                    "is_parent": False,
                    "filename": filename,
                    "specialty": specialty,
                    "document_type": document_type,
                })

            # Insert in batches of 50 to avoid payload limits
            batch_size = 50
            for i in range(0, len(child_records), batch_size):
                batch = child_records[i : i + batch_size]
                self.client.table(self.TABLE_NAME).insert(batch).execute()

            logger.info(
                f"Stored {len(parent_records)} parent + {len(child_records)} child chunks "
                f"for document '{filename}'"
            )

            return {
                "success": True,
                "parent_chunks": len(parent_records),
                "child_chunks": len(child_records),
            }

        except Exception as e:
            logger.error(f"Error storing chunks: {e}")
            return {"success": False, "error": str(e)}

    def get_parent_chunk(self, parent_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a parent chunk by its chunk_id.

        Args:
            parent_id: The chunk_id of the parent chunk

        Returns:
            Dict with parent chunk data or None
        """
        if not self.client:
            return None
        try:
            result = (
                self.client.table(self.TABLE_NAME)
                .select("chunk_id, content, metadata, filename")
                .eq("chunk_id", parent_id)
                .eq("is_parent", True)
                .limit(1)
                .execute()
            )
            if result.data:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error retrieving parent chunk {parent_id}: {e}")
            return None

    def delete_by_document_id(self, document_id: str) -> Dict[str, Any]:
        """
        Delete all chunks for a document.

        Args:
            document_id: The document_id to delete

        Returns:
            Dict with deletion status
        """
        if not self.client:
            return {"success": False, "error": "Client not initialized"}
        try:
            result = (
                self.client.table(self.TABLE_NAME)
                .delete()
                .eq("document_id", document_id)
                .execute()
            )
            deleted = len(result.data) if result.data else 0
            logger.info(f"Deleted {deleted} chunks for document_id={document_id}")
            return {"success": True, "deleted_count": deleted}
        except Exception as e:
            logger.error(f"Error deleting by document_id: {e}")
            return {"success": False, "error": str(e), "deleted_count": 0}

    def delete_by_filename(self, filename: str) -> Dict[str, Any]:
        """
        Delete all chunks for a filename.

        Args:
            filename: The filename to delete

        Returns:
            Dict with deletion status
        """
        if not self.client:
            return {"success": False, "error": "Client not initialized"}
        try:
            result = (
                self.client.table(self.TABLE_NAME)
                .delete()
                .eq("filename", filename)
                .execute()
            )
            deleted = len(result.data) if result.data else 0
            logger.info(f"Deleted {deleted} chunks for filename={filename}")
            return {"success": True, "deleted_count": deleted}
        except Exception as e:
            logger.error(f"Error deleting by filename: {e}")
            return {"success": False, "error": str(e), "deleted_count": 0}

    def delete_by_filter(self, filter_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete chunks matching a metadata filter.

        Args:
            filter_dict: Filter dict (e.g., {'filename': 'doc.pdf'})

        Returns:
            Dict with deletion status
        """
        if not self.client:
            return {"success": False, "error": "Client not initialized"}
        try:
            # Try common filter keys directly on columns first
            query = self.client.table(self.TABLE_NAME).delete()
            for key, value in filter_dict.items():
                if key in ("filename", "document_id", "specialty", "document_type", "chunk_id"):
                    query = query.eq(key, value)
                elif key == "original_filename":
                    query = query.eq("filename", value)
                else:
                    # Filter on JSONB metadata
                    query = query.eq(f"metadata->>'{key}'", value)

            result = query.execute()
            deleted = len(result.data) if result.data else 0
            return {"success": True, "deleted_count": deleted}
        except Exception as e:
            logger.error(f"Error deleting by filter: {e}")
            return {"success": False, "error": str(e), "deleted_count": 0}

    # ─── Search Operations ─────────────────────────────────────────────

    def hybrid_search(
        self, query: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining vector similarity and full-text search
        using Supabase RPC function with RRF fusion.

        Args:
            query: Search query text
            top_k: Number of results to return

        Returns:
            List of dicts with 'content', 'score', 'metadata', 'parent_id'
        """
        if not self.client or not self.embeddings:
            logger.warning("Store not initialized for search")
            return []

        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)

            # Call hybrid_search RPC function
            result = self.client.rpc(
                "hybrid_search",
                {
                    "query_embedding": query_embedding,
                    "query_text": query,
                    "match_count": top_k,
                    "rrf_k": 60,
                },
            ).execute()

            if not result.data:
                # Fallback to vector-only search if hybrid returns nothing
                return self.vector_search(query, top_k)

            results = []
            for row in result.data:
                results.append({
                    "content": row["content"],
                    "score": float(row.get("rrf_score", 0.0)),
                    "metadata": row.get("metadata", {}),
                    "parent_id": row.get("parent_id"),
                    "filename": row.get("filename"),
                    "chunk_id": row.get("chunk_id"),
                })

            logger.info(f"Hybrid search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            # Fallback to vector-only
            try:
                return self.vector_search(query, top_k)
            except Exception:
                return []

    def vector_search(
        self, query: str, top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Perform vector-only similarity search.

        Args:
            query: Search query text
            top_k: Number of results to return

        Returns:
            List of dicts with 'content', 'score', 'metadata', 'parent_id'
        """
        if not self.client or not self.embeddings:
            return []

        try:
            query_embedding = self.embeddings.embed_query(query)

            result = self.client.rpc(
                "vector_search",
                {
                    "query_embedding": query_embedding,
                    "match_count": top_k,
                },
            ).execute()

            results = []
            for row in (result.data or []):
                results.append({
                    "content": row["content"],
                    "score": float(row.get("similarity", 0.0)),
                    "metadata": row.get("metadata", {}),
                    "parent_id": row.get("parent_id"),
                    "filename": row.get("filename"),
                    "chunk_id": row.get("chunk_id"),
                })

            logger.info(f"Vector search returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Error in vector search: {e}")
            return []

    # ─── Statistics ────────────────────────────────────────────────────

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the stored documents and chunks.

        Returns:
            Dict with total_documents, sources, specialties, etc.
        """
        if not self.client:
            return {"error": "Client not initialized"}

        try:
            # Count total child chunks
            count_result = (
                self.client.table(self.TABLE_NAME)
                .select("id", count="exact")
                .eq("is_parent", False)
                .execute()
            )
            total_chunks = count_result.count or 0

            # Get unique filenames (sources)
            sources_result = (
                self.client.table(self.TABLE_NAME)
                .select("filename")
                .eq("is_parent", True)
                .execute()
            )
            sources = list({
                row["filename"]
                for row in (sources_result.data or [])
                if row.get("filename")
            })

            # Get unique specialties
            spec_result = (
                self.client.table(self.TABLE_NAME)
                .select("specialty")
                .eq("is_parent", True)
                .execute()
            )
            specialties = list({
                row["specialty"]
                for row in (spec_result.data or [])
                if row.get("specialty")
            })

            # Get unique document types
            type_result = (
                self.client.table(self.TABLE_NAME)
                .select("document_type")
                .eq("is_parent", True)
                .execute()
            )
            document_types = list({
                row["document_type"]
                for row in (type_result.data or [])
                if row.get("document_type")
            })

            return {
                "total_documents": total_chunks,
                "sources": sources,
                "specialties": specialties,
                "document_types": document_types,
                "collection_name": "supabase_pgvector",
                "storage": "supabase",
            }

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

    def reset_collection(self) -> Dict[str, Any]:
        """Delete all chunks from the store."""
        if not self.client:
            return {"success": False, "error": "Client not initialized"}
        try:
            # Delete all rows (gt id filter to match all UUIDs)
            self.client.table(self.TABLE_NAME).delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
            logger.info("Collection reset: all chunks deleted")
            return {"success": True}
        except Exception as e:
            logger.error(f"Error resetting collection: {e}")
            return {"success": False, "error": str(e)}
