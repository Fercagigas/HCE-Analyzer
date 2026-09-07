"""Port de conocimiento documental (RAG)."""

from __future__ import annotations

from typing import Dict, List, Optional, Protocol, runtime_checkable

from chathce.domain.clinical import ProviderHealth
from chathce.domain.context import RequestContext
from chathce.domain.knowledge import DocumentRecord, KnowledgeHit, KnowledgeStats, UploadResult


@runtime_checkable
class KnowledgeRepository(Protocol):
    async def search(
        self,
        ctx: RequestContext,
        *,
        query: str,
        top_k: int = 5,
        specialty: Optional[str] = None,
    ) -> List[KnowledgeHit]: ...

    async def add_document(self, ctx: RequestContext, *, file_path: str, metadata: Dict[str, str]) -> UploadResult: ...

    async def list_documents(self, ctx: RequestContext) -> List[DocumentRecord]: ...

    async def delete_document(self, ctx: RequestContext, *, document_id: str) -> int: ...

    async def stats(self, ctx: RequestContext) -> KnowledgeStats: ...

    async def health(self) -> ProviderHealth: ...
