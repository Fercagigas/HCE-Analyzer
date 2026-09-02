"""KnowledgeService: ingesta, listado, borrado y estadisticas de documentos (sin Streamlit)."""

from __future__ import annotations

from typing import Any, Dict, List

from chathce.application.audit_events import emit_safely, make_audit_event
from chathce.domain.audit import AuditAction
from chathce.domain.context import RequestContext
from chathce.domain.knowledge import DocumentRecord, KnowledgeHit, KnowledgeStats, UploadResult


class KnowledgeService:
    def __init__(self, repository: Any, audit: Any = None):
        self._repo = repository
        self._audit = audit

    async def upload(self, ctx: RequestContext, *, file_path: str, metadata: Dict[str, str]) -> UploadResult:
        result = await self._repo.add_document(ctx, file_path=file_path, metadata=metadata)
        await emit_safely(self._audit, make_audit_event(
            ctx, action=AuditAction.knowledge_query, outcome="success" if result.success else "failure", component="knowledge",
            operation="upload_document", row_count=result.chunks_processed,
        ))
        return result

    async def list_documents(self, ctx: RequestContext) -> List[DocumentRecord]:
        return await self._repo.list_documents(ctx)

    async def delete(self, ctx: RequestContext, *, document_id: str) -> int:
        deleted = await self._repo.delete_document(ctx, document_id=document_id)
        await emit_safely(self._audit, make_audit_event(
            ctx, action=AuditAction.knowledge_query, outcome="success", component="knowledge",
            operation="delete_document", row_count=deleted,
        ))
        return deleted

    async def search(self, ctx: RequestContext, *, query: str, top_k: int = 5) -> List[KnowledgeHit]:
        return await self._repo.search(ctx, query=query, top_k=top_k)

    async def stats(self, ctx: RequestContext) -> KnowledgeStats:
        return await self._repo.stats(ctx)
