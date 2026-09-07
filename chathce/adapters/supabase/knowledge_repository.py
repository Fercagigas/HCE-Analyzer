"""SupabaseKnowledgeRepository: port de conocimiento sobre el RAG existente (pgvector + HF).

Envuelve `ImprovedRAGService` (busqueda hibrida + reranker) y `DocumentManager`
(ingesta/listado/borrado con `public.clinical_documents`). El core solo ve
`KnowledgeHit`/`DocumentRecord`; el texto recuperado se delimita como no confiable
en el gateway, nunca aqui.
"""

from __future__ import annotations

import hashlib
import time
from typing import Any, Callable, Dict, List, Optional

from chathce.adapters.supabase._common import parse_dt, run_blocking, sanitize_error
from chathce.domain.clinical import ProviderHealth
from chathce.domain.context import RequestContext
from chathce.domain.errors import ProviderUnavailable
from chathce.domain.knowledge import DocumentRecord, KnowledgeHit, KnowledgeStats, UploadResult


def _default_rag_service():
    from services.rag.improved_rag_service import get_rag_service

    return get_rag_service()


def _default_document_manager():
    from services.unified_chat.document_manager import DocumentManager

    return DocumentManager()


def _to_int(value: Any) -> Optional[int]:
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _hit(raw: Dict[str, Any], rank: int) -> KnowledgeHit:
    metadata = dict(raw.get("metadata") or {})
    content = str(raw.get("content") or "")
    chunk_id = str(metadata.get("chunk_id") or raw.get("chunk_id") or hashlib.sha1(content[:200].encode("utf-8")).hexdigest()[:16])
    filename = str(metadata.get("filename") or raw.get("source") or "Documento desconocido")
    return KnowledgeHit(
        chunk_id=chunk_id, document_id=metadata.get("document_id"), filename=filename,
        page=_to_int(metadata.get("page")), specialty=metadata.get("specialty"), doc_type=metadata.get("document_type"),
        content=content, score=(float(raw["score"]) if raw.get("score") is not None else None),
        metadata={**metadata, "rank": rank},
    )


class SupabaseKnowledgeRepository:
    def __init__(
        self,
        rag_service_factory: Callable[[], Any] = _default_rag_service,
        document_manager_factory: Callable[[], Any] = _default_document_manager,
        *,
        timeout_s: float = 60.0,
    ):
        self._rag_factory = rag_service_factory
        self._dm_factory = document_manager_factory
        self._timeout = timeout_s
        self._rag: Any = None
        self._dm: Any = None

    def _rag_service(self) -> Any:
        if self._rag is None:
            self._rag = self._rag_factory()
        return self._rag

    def _document_manager(self) -> Any:
        if self._dm is None:
            self._dm = self._dm_factory()
        return self._dm

    async def _run(self, fn, what: str):
        try:
            return await run_blocking(fn, what=what, timeout_s=self._timeout)
        except ProviderUnavailable:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ProviderUnavailable(f"Base de conocimiento no disponible ({what}): {sanitize_error(exc)}") from exc

    # ------------------------------------------------------------------
    async def search(self, ctx: RequestContext, *, query: str, top_k: int = 5,
                     specialty: Optional[str] = None) -> List[KnowledgeHit]:
        def do():
            service = self._rag_service()
            if specialty:
                results = service.search_with_filter(query, {"specialty": specialty}, top_k=top_k)
            else:
                results = service.search(query, top_k=top_k, rerank=True)
            return [_hit(r, i + 1) for i, r in enumerate(results or [])][:top_k]

        return await self._run(do, "busqueda documental")

    async def add_document(self, ctx: RequestContext, *, file_path: str, metadata: Dict[str, str]) -> UploadResult:
        def do():
            result = self._document_manager().upload_document(file_path, dict(metadata))
            filename = metadata.get("original_filename") or str(result.get("file") or file_path).replace("\\", "/").rsplit("/", 1)[-1]
            return UploadResult(
                success=bool(result.get("success")), document_id=(result.get("metadata") or {}).get("document_id"),
                filename=filename, chunks_processed=int(result.get("chunks_processed") or 0),
                message=str(result.get("message") or ""), error=result.get("error"),
            )

        return await self._run(do, "ingesta de documento")

    async def list_documents(self, ctx: RequestContext) -> List[DocumentRecord]:
        def do():
            listing = self._document_manager().list_documents()
            if not listing.get("success"):
                raise ProviderUnavailable(str(listing.get("error") or "listado no disponible"))
            records: List[DocumentRecord] = []
            for doc in listing.get("documents", []):
                records.append(DocumentRecord(
                    document_id=str(doc.get("id") or doc.get("filename")), filename=str(doc.get("filename")),
                    title=doc.get("title"), doc_type=doc.get("document_type"), specialty=doc.get("specialty"),
                    uploaded_at=parse_dt(doc.get("upload_date")), metadata=dict(doc.get("metadata") or {}),
                ))
            return records

        return await self._run(do, "listado de documentos")

    async def delete_document(self, ctx: RequestContext, *, document_id: str) -> int:
        def do():
            result = self._document_manager().delete_document(document_id)
            return int(result.get("deleted_count") or 0) if result.get("success") else 0

        return await self._run(do, "borrado de documento")

    async def stats(self, ctx: RequestContext) -> KnowledgeStats:
        def do():
            raw = self._rag_service().get_collection_stats() or {}
            if "error" in raw:
                raise ProviderUnavailable(str(raw["error"]))
            sources = list(raw.get("sources", []))
            return KnowledgeStats(
                total_documents=int(raw.get("total_documents") or 0), unique_sources=len(sources),
                sources=sources, specialties=list(raw.get("specialties", [])),
            )

        return await self._run(do, "estadisticas del conocimiento")

    async def health(self) -> ProviderHealth:
        started = time.perf_counter()
        try:
            raw = await self._run(lambda: self._rag_service().get_collection_stats() or {}, "health")
        except Exception as exc:  # noqa: BLE001
            return ProviderHealth(ok=False, latency_ms=int((time.perf_counter() - started) * 1000), detail=str(exc)[:200])
        if isinstance(raw, dict) and "error" in raw:
            return ProviderHealth(ok=False, latency_ms=int((time.perf_counter() - started) * 1000), detail=str(raw["error"])[:200])
        return ProviderHealth(ok=True, latency_ms=int((time.perf_counter() - started) * 1000), detail="rag_chunks")
