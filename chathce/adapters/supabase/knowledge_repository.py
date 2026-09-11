"""SupabaseKnowledgeRepository: port de conocimiento sobre el RAG existente (pgvector + HF).

Envuelve `ImprovedRAGService` (busqueda hibrida + reranker) y `DocumentManager`
(ingesta/listado/borrado con `public.clinical_documents`). El core solo ve
`KnowledgeHit`/`DocumentRecord`; el texto recuperado se delimita como no confiable
en el gateway, nunca aqui.
"""

from __future__ import annotations

import hashlib
import time
from datetime import date
from typing import Any, Callable, Dict, List, Optional

from chathce.adapters.supabase._common import parse_dt, run_blocking, sanitize_error
from chathce.domain.clinical import ProviderHealth
from chathce.domain.context import RequestContext
from chathce.domain.errors import ProviderUnavailable
from chathce.domain.knowledge import DocumentRecord, DocumentStatus, KnowledgeHit, KnowledgeStats, UploadResult


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


def _to_date(value: Any, default: Optional[date] = None) -> Optional[date]:
    if value in (None, ""):
        return default
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return default


def _status(value: Any) -> Optional[DocumentStatus]:
    try:
        return DocumentStatus(str(value))
    except ValueError:
        return None


def _hit(raw: Dict[str, Any], rank: int) -> KnowledgeHit:
    metadata = dict(raw.get("metadata") or {})
    content = str(raw.get("content") or "")
    chunk_id = str(metadata.get("chunk_id") or raw.get("chunk_id") or hashlib.sha1(content[:200].encode("utf-8")).hexdigest()[:16])
    filename = str(metadata.get("filename") or raw.get("source") or "Documento desconocido")
    status = _status(metadata.get("status") or raw.get("status"))
    return KnowledgeHit(
        chunk_id=chunk_id, document_id=metadata.get("document_id"), filename=filename,
        page=_to_int(metadata.get("page")), specialty=metadata.get("specialty"), doc_type=metadata.get("document_type"),
        content=content, score=(float(raw["score"]) if raw.get("score") is not None else None),
        tenant_id=str(metadata.get("tenant_id") or raw.get("tenant_id") or ""),
        document_key=metadata.get("document_key") or raw.get("document_key"),
        version=str(metadata.get("version") or raw.get("version") or ""),
        effective_from=_to_date(metadata.get("effective_from") or raw.get("effective_from"), date.max),
        effective_to=_to_date(metadata.get("effective_to") or raw.get("effective_to")),
        status=status or DocumentStatus.draft,
        approved_by=metadata.get("approved_by") or raw.get("approved_by"),
        approved_at=parse_dt(metadata.get("approved_at") or raw.get("approved_at")),
        content_hash=str(metadata.get("content_hash") or raw.get("content_hash") or ""),
        metadata={**metadata, "rank": rank},
    )


def _is_retrievable(hit: KnowledgeHit, ctx: RequestContext) -> bool:
    today = ctx.created_at.date()
    return (
        hit.tenant_id == ctx.tenant_id
        and hit.status == DocumentStatus.approved
        and bool(hit.version)
        and bool(hit.content_hash)
        and hit.effective_from <= today
        and (hit.effective_to is None or hit.effective_to >= today)
    )


def _version_key(hit: KnowledgeHit) -> tuple:
    tokens = tuple((1, int(part)) if part.isdigit() else (0, part.lower()) for part in hit.version.replace("-", ".").split("."))
    return hit.effective_from, tokens


def _resolve_versions(hits: List[KnowledgeHit]) -> List[KnowledgeHit]:
    selected: Dict[str, KnowledgeHit] = {}
    for hit in hits:
        key = hit.document_key or hit.filename
        previous = selected.get(key)
        if previous is None or _version_key(hit) > _version_key(previous):
            selected[key] = hit
    return [hit for hit in hits if selected[hit.document_key or hit.filename].version == hit.version]


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
                results = service.search_with_filter(
                    query, {"specialty": specialty}, top_k=top_k * 3,
                    tenant_id=ctx.tenant_id, as_of=ctx.created_at.date(),
                )
            else:
                results = service.search(query, top_k=top_k * 3, rerank=True, tenant_id=ctx.tenant_id, as_of=ctx.created_at.date())
            hits = [_hit(r, i + 1) for i, r in enumerate(results or [])]
            return _resolve_versions([hit for hit in hits if _is_retrievable(hit, ctx)])[:top_k]

        return await self._run(do, "busqueda documental")

    async def find_by_content_hash(self, ctx: RequestContext, *, content_hash: str) -> bool:
        return await self._run(lambda: bool(self._document_manager().find_governed_document_by_hash(ctx.tenant_id, content_hash)), "comprobacion de duplicado")

    async def create_draft(self, ctx: RequestContext, *, file_path: str, metadata: Dict[str, str]) -> UploadResult:
        def do():
            result = self._document_manager().create_governed_draft(file_path, dict(metadata))
            filename = metadata.get("original_filename") or str(result.get("file") or file_path).replace("\\", "/").rsplit("/", 1)[-1]
            return UploadResult(
                success=bool(result.get("success")), document_id=(result.get("metadata") or {}).get("document_id"),
                filename=filename, chunks_processed=int(result.get("chunks_processed") or 0),
                message=str(result.get("message") or ""), error=result.get("error"), status=DocumentStatus.draft,
            )

        return await self._run(do, "carga de borrador documental")

    async def approve_document(self, ctx: RequestContext, *, document_id: str, approved_by: str) -> UploadResult:
        def do():
            result = self._document_manager().approve_governed_document(document_id, ctx.tenant_id, approved_by)
            return UploadResult(success=bool(result.get("success")), document_id=document_id,
                                filename=str(result.get("filename") or "documento"), chunks_processed=int(result.get("chunks_processed") or 0),
                                message=str(result.get("message") or ""), error=result.get("error"), status=DocumentStatus.approved)
        return await self._run(do, "aprobacion documental")

    async def retire_document(self, ctx: RequestContext, *, document_id: str) -> bool:
        return await self._run(lambda: bool(self._document_manager().retire_governed_document(document_id, ctx.tenant_id).get("success")), "retirada documental")

    async def list_documents(self, ctx: RequestContext) -> List[DocumentRecord]:
        def do():
            listing = self._document_manager().list_governed_documents(ctx.tenant_id)
            if not listing.get("success"):
                raise ProviderUnavailable(str(listing.get("error") or "listado no disponible"))
            records: List[DocumentRecord] = []
            for doc in listing.get("documents", []):
                records.append(DocumentRecord(
                    document_id=str(doc.get("id") or doc.get("filename")), filename=str(doc.get("filename")),
                    title=doc.get("title"), doc_type=doc.get("document_type"), specialty=doc.get("specialty"),
                    uploaded_at=parse_dt(doc.get("upload_date")), tenant_id=str(doc.get("tenant_id") or ""),
                    document_key=doc.get("document_key"), version=str(doc.get("version") or ""),
                    effective_from=_to_date(doc.get("effective_from"), date.max), effective_to=_to_date(doc.get("effective_to")),
                    status=_status(doc.get("status")) or DocumentStatus.draft, approved_by=doc.get("approved_by"),
                    approved_at=parse_dt(doc.get("approved_at")), content_hash=str(doc.get("content_hash") or ""),
                    metadata=dict(doc.get("metadata") or {}),
                ))
            return [record for record in records if record.tenant_id == ctx.tenant_id and record.status == DocumentStatus.approved
                    and record.effective_from <= ctx.created_at.date() and (record.effective_to is None or record.effective_to >= ctx.created_at.date())]

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
