"""Contrato de SupabaseKnowledgeRepository con RAG y DocumentManager simulados."""

import pytest

from chathce.adapters.supabase.knowledge_repository import SupabaseKnowledgeRepository
from chathce.domain.context import Channel, RequestContext
from chathce.domain.errors import ProviderUnavailable
from chathce.ports import KnowledgeRepository

pytestmark = pytest.mark.contract


class FakeRag:
    def __init__(self):
        self.calls = []
        self.results = [
            {"content": "La sepsis se define como...", "score": 0.91, "source": "guia_sepsis.pdf",
             "metadata": {"filename": "guia_sepsis.pdf", "page": "12", "specialty": "Urgencias", "document_type": "guia_clinica", "document_id": "d1", "chunk_id": "c1"}},
            {"content": "Hipertension arterial...", "score": 0.4, "source": "protocolo_hta.pdf", "metadata": {"filename": "protocolo_hta.pdf", "page": 4}},
        ]

    def search(self, query, top_k=5, rerank=True):
        self.calls.append(("search", query, top_k, rerank))
        return self.results[:top_k]

    def search_with_filter(self, query, filter_dict, top_k=5):
        self.calls.append(("filter", query, filter_dict, top_k))
        return [r for r in self.results if r["metadata"].get("specialty") == filter_dict.get("specialty")][:top_k]

    def get_collection_stats(self):
        return {"total_documents": 42, "sources": ["guia_sepsis.pdf", "protocolo_hta.pdf"], "specialties": ["Urgencias"], "collection_name": "rag_chunks"}


class FakeDocumentManager:
    def __init__(self):
        self.deleted = []

    def upload_document(self, file_path, metadata):
        return {"success": True, "message": "ok", "file": file_path, "chunks_processed": 7, "metadata": {"document_id": "d9", **metadata}}

    def list_documents(self):
        return {"success": True, "documents": [{"filename": "guia_sepsis.pdf", "source": "guia_sepsis.pdf", "indexed": True, "id": "d1",
                                                "document_type": "guia_clinica", "specialty": "Urgencias", "upload_date": "2026-01-01T10:00:00"}],
                "summary": {"total_documents": 42}}

    def delete_document(self, document_id):
        self.deleted.append(document_id)
        return {"success": True, "deleted_count": 3, "document_id": document_id}


@pytest.fixture
def repo():
    rag, dm = FakeRag(), FakeDocumentManager()
    return SupabaseKnowledgeRepository(lambda: rag, lambda: dm), rag, dm


def _ctx():
    return RequestContext(user_id="u", channel=Channel.api)


async def test_search_maps_hits_and_respects_top_k(repo):
    repository, rag, _ = repo
    assert isinstance(repository, KnowledgeRepository)
    hits = await repository.search(_ctx(), query="sepsis", top_k=1)
    assert len(hits) == 1 and rag.calls[-1] == ("search", "sepsis", 1, True)
    hit = hits[0]
    assert hit.filename == "guia_sepsis.pdf" and hit.page == 12 and hit.specialty == "Urgencias" and hit.doc_type == "guia_clinica"
    assert hit.chunk_id == "c1" and hit.document_id == "d1" and hit.score == 0.91 and hit.metadata["rank"] == 1


async def test_search_with_specialty_uses_filter(repo):
    repository, rag, _ = repo
    hits = await repository.search(_ctx(), query="hta", top_k=5, specialty="Urgencias")
    assert rag.calls[-1][0] == "filter" and len(hits) == 1
    second = await repository.search(_ctx(), query="x", top_k=5)
    assert second[1].page == 4 and second[1].chunk_id  # chunk_id derivado del contenido


async def test_documents_lifecycle(repo):
    repository, _, dm = repo
    upload = await repository.add_document(_ctx(), file_path="C:/tmp/guia.pdf", metadata={"original_filename": "guia.pdf", "specialty": "Urgencias"})
    assert upload.success and upload.document_id == "d9" and upload.filename == "guia.pdf" and upload.chunks_processed == 7
    docs = await repository.list_documents(_ctx())
    assert docs[0].document_id == "d1" and docs[0].uploaded_at is not None
    assert await repository.delete_document(_ctx(), document_id="d1") == 3 and dm.deleted == ["d1"]
    stats = await repository.stats(_ctx())
    assert stats.total_documents == 42 and stats.unique_sources == 2
    assert (await repository.health()).ok is True


async def test_backend_errors_become_provider_unavailable():
    class Broken:
        def search(self, *a, **k):
            raise RuntimeError("pgvector down http://secret")

        def get_collection_stats(self):
            return {"error": "down"}

    repository = SupabaseKnowledgeRepository(lambda: Broken(), lambda: None)
    with pytest.raises(ProviderUnavailable) as exc:
        await repository.search(_ctx(), query="x")
    assert "http" not in exc.value.message
    assert (await repository.health()).ok is False
