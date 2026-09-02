"""Tool de busqueda documental (RAG) sobre KnowledgeRepository. El texto recuperado es dato no confiable."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from chathce.domain.context import RequestContext
from chathce.domain.evidence import Evidence, EvidenceType, Provenance
from chathce.domain.knowledge import Source
from chathce.domain.tools import AuditCategory, ToolArtifacts, ToolContract, ToolResult
from chathce.gateway.tool_registry import Tool

MAX_EXCERPT_CHARS = 1500


class KnowledgeSearchInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(description="Pregunta o tema clinico a buscar en las guias y protocolos indexados", min_length=3, max_length=500)
    specialty: Optional[str] = Field(None, description="Filtrar por especialidad (p. ej. 'Urgencias')", max_length=60)
    top_k: int = Field(5, ge=1, le=10, description="Numero maximo de fragmentos")


class KnowledgeOutput(BaseModel):
    model_config = ConfigDict(extra="allow")


def build_knowledge_tool(repository: Any) -> Tool:
    async def search(ctx: RequestContext, args: KnowledgeSearchInput) -> ToolResult:
        hits = await repository.search(ctx, query=args.query, top_k=args.top_k, specialty=args.specialty)
        now = datetime.now(timezone.utc)
        documents: List[Dict[str, Any]] = []
        sources: List[Source] = []
        evidence: List[Evidence] = []
        for rank, hit in enumerate(hits, start=1):
            excerpt = hit.content[:MAX_EXCERPT_CHARS]
            evidence_id = f"rag_chunks:chunk:{hit.chunk_id}"
            documents.append({
                "rank": rank, "filename": hit.filename, "page": hit.page, "specialty": hit.specialty,
                "doc_type": hit.doc_type, "score": hit.score, "content": excerpt, "evidence_id": evidence_id,
            })
            sources.append(Source(filename=hit.filename, page=hit.page, specialty=hit.specialty, doc_type=hit.doc_type,
                                  tool="search_clinical_documents", retrieved_content=excerpt, evidence_id=evidence_id, score=hit.score))
            evidence.append(Evidence(
                evidence_id=evidence_id, type=EvidenceType.guideline_document, source_system="rag_chunks", resource_type="chunk",
                resource_id=hit.chunk_id, excerpt=excerpt[:300], page=hit.page,
                provenance=Provenance(tool_name="search_clinical_documents", tool_use_id="", trace_id=ctx.trace_id,
                                      retrieved_at=now, provider="knowledge_repository"),
            ))
        data = {"found": bool(documents), "documents": documents,
                "message": None if documents else "No se encontraron documentos relevantes para la consulta."}
        return ToolResult(
            tool_name="", tool_use_id="", success=True, operation="search_documents", scope=ctx.scope(), data=data,
            count=len(documents), limit=args.top_k, truncated=False, evidence=evidence,
            artifacts=ToolArtifacts(sources=sources),
        )

    contract = ToolContract(
        name="search_clinical_documents",
        description="Busqueda semantica en las guias clinicas y protocolos indexados. Devuelve fragmentos con documento y pagina para citar. Usa esta herramienta para preguntas sobre protocolos, tratamientos, criterios o recomendaciones generales.",
        input_model=KnowledgeSearchInput, output_model=KnowledgeOutput, requires_patient_scope=False,
        audit_category=AuditCategory.knowledge, data_categories=("guidelines",), max_rows=10, timeout_s=45.0,
    )
    return Tool(contract, search)
