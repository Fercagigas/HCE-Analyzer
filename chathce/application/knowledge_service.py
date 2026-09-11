"""KnowledgeService: ingesta, listado, borrado y estadisticas de documentos (sin Streamlit)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from chathce.application.audit_events import emit_safely, make_audit_event
from chathce.domain.audit import AuditAction
from chathce.domain.context import RequestContext
from chathce.application.knowledge_governance import ContextRoleKnowledgeApprovalAuthorizer, validate_upload
from chathce.domain.knowledge import DocumentRecord, KnowledgeHit, KnowledgeStats, UploadResult


class KnowledgeService:
    def __init__(self, repository: Any, audit: Any = None, approval_authorizer: Optional[Any] = None):
        self._repo = repository
        self._audit = audit
        self._approval_authorizer = approval_authorizer or ContextRoleKnowledgeApprovalAuthorizer()

    async def upload(self, ctx: RequestContext, *, file_path: str, metadata: Dict[str, str]) -> UploadResult:
        try:
            validation = validate_upload(file_path, metadata)
        except ValueError as exc:
            result = UploadResult(success=False, filename="documento", message="Documento rechazado en validacion", error=str(exc))
            await emit_safely(self._audit, make_audit_event(
                ctx, action=AuditAction.knowledge_document_drafted, outcome="refused", component="knowledge",
                operation="validate_document",
            ))
            return result
        if await self._repo.find_by_content_hash(ctx, content_hash=validation.content_hash):
            result = UploadResult(success=False, filename="documento", content_hash=validation.content_hash,
                                  message="Documento duplicado", error="contenido_duplicado")
            await emit_safely(self._audit, make_audit_event(
                ctx, action=AuditAction.knowledge_document_drafted, outcome="refused", component="knowledge",
                operation="duplicate_document",
            ))
            return result

        governed = dict(metadata)
        governed.update({
            "tenant_id": ctx.tenant_id,
            "content_hash": validation.content_hash,
            "status": "draft",
            "security_flags": ",".join(validation.flags),
        })
        result = await self._repo.create_draft(ctx, file_path=file_path, metadata=governed)
        result = result.model_copy(update={"content_hash": validation.content_hash, "security_flags": validation.flags})
        await emit_safely(self._audit, make_audit_event(
            ctx, action=AuditAction.knowledge_document_drafted, outcome="success" if result.success else "failure", component="knowledge",
            operation="create_draft", row_count=result.chunks_processed,
        ))
        return result

    async def approve(self, ctx: RequestContext, *, document_id: str) -> UploadResult:
        if not self._approval_authorizer.can_approve_documents(ctx):
            result = UploadResult(success=False, filename="documento", error="knowledge_manager_required", message="Aprobacion no autorizada")
            outcome = "refused"
        else:
            result = await self._repo.approve_document(ctx, document_id=document_id, approved_by=ctx.user_id)
            outcome = "success" if result.success else "refused"
        await emit_safely(self._audit, make_audit_event(
            ctx, action=AuditAction.knowledge_document_approved, outcome=outcome, component="knowledge",
            operation="approve_document", row_count=result.chunks_processed,
        ))
        return result

    async def retire(self, ctx: RequestContext, *, document_id: str) -> bool:
        if not self._approval_authorizer.can_approve_documents(ctx):
            await emit_safely(self._audit, make_audit_event(
                ctx, action=AuditAction.knowledge_document_retired, outcome="refused", component="knowledge",
                operation="retire_document",
            ))
            return False
        retired = await self._repo.retire_document(ctx, document_id=document_id)
        await emit_safely(self._audit, make_audit_event(
            ctx, action=AuditAction.knowledge_document_retired, outcome="success" if retired else "failure", component="knowledge",
            operation="retire_document", row_count=1 if retired else 0,
        ))
        return retired

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
