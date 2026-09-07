"""Integracion (lectura) del KnowledgeRepository sobre el RAG real (carga embeddings locales; lento)."""

import pytest

from chathce.adapters.supabase.knowledge_repository import SupabaseKnowledgeRepository
from chathce.domain.context import Channel, RequestContext

pytestmark = pytest.mark.slow


async def test_search_and_stats_live(integration_settings):
    repo = SupabaseKnowledgeRepository()
    ctx = RequestContext(user_id="it", channel=Channel.cli)
    stats = await repo.stats(ctx)
    assert stats.total_documents >= 0
    if stats.total_documents == 0:
        pytest.skip("Coleccion RAG vacia")
    hits = await repo.search(ctx, query="sepsis", top_k=3)
    assert len(hits) <= 3
    for hit in hits:
        assert hit.filename and hit.content
