"""Contrato de `SupabaseVectorStore` con el backend (RPC y tablas) usando mocks."""

from unittest.mock import MagicMock, Mock, patch

import pytest

pytestmark = pytest.mark.contract


@pytest.fixture
def mock_store():
    with patch("services.rag.supabase_vector_store.create_client") as mock_create:
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        mock_embeddings = Mock()
        mock_embeddings.embed_documents.return_value = [[0.1] * 384]
        mock_embeddings.embed_query.return_value = [0.1] * 384

        from services.rag.supabase_vector_store import SupabaseVectorStore

        store = SupabaseVectorStore(embeddings=mock_embeddings)
        store.client = mock_client
        return store


def test_hybrid_search_calls_rpc(mock_store):
    mock_rpc_result = MagicMock()
    mock_rpc_result.execute.return_value = MagicMock(data=[{
        "content": "Protocolo de diabetes", "rrf_score": 0.85, "metadata": {"specialty": "endocrinologia"},
        "parent_id": "parent_1", "filename": "diabetes.pdf", "chunk_id": "chunk_1",
    }])
    mock_store.client.rpc.return_value = mock_rpc_result

    results = mock_store.hybrid_search("diabetes tratamiento", top_k=5)

    assert len(results) == 1
    assert results[0]["content"] == "Protocolo de diabetes"
    assert results[0]["score"] == 0.85
    mock_store.client.rpc.assert_called_once_with(
        "hybrid_search",
        {"query_embedding": [0.1] * 384, "query_text": "diabetes tratamiento", "match_count": 5, "rrf_k": 60},
    )


def test_vector_search_calls_rpc(mock_store):
    mock_rpc_result = MagicMock()
    mock_rpc_result.execute.return_value = MagicMock(data=[{
        "content": "Guía de hipertensión", "similarity": 0.92, "metadata": {}, "parent_id": None,
        "filename": "hipertension.pdf", "chunk_id": "chunk_2",
    }])
    mock_store.client.rpc.return_value = mock_rpc_result

    results = mock_store.vector_search("hipertensión arterial", top_k=3)

    assert len(results) == 1
    assert results[0]["score"] == 0.92
    mock_store.client.rpc.assert_called_once_with("vector_search", {"query_embedding": [0.1] * 384, "match_count": 3})


def test_get_collection_stats(mock_store):
    mock_count = MagicMock()
    mock_count.execute.return_value = MagicMock(count=42)
    mock_select_count = MagicMock()
    mock_select_count.eq.return_value = mock_count

    mock_sources = MagicMock()
    mock_sources.execute.return_value = MagicMock(data=[{"filename": "doc1.pdf"}, {"filename": "doc2.pdf"}])
    mock_select_sources = MagicMock()
    mock_select_sources.eq.return_value = mock_sources

    mock_spec = MagicMock()
    mock_spec.execute.return_value = MagicMock(data=[{"specialty": "cardiologia"}])
    mock_select_spec = MagicMock()
    mock_select_spec.eq.return_value = mock_spec

    mock_type = MagicMock()
    mock_type.execute.return_value = MagicMock(data=[{"document_type": "guia_clinica"}])
    mock_select_type = MagicMock()
    mock_select_type.eq.return_value = mock_type

    mock_table = MagicMock()
    mock_table.select.side_effect = [mock_select_count, mock_select_sources, mock_select_spec, mock_select_type]
    mock_store.client.table.return_value = mock_table

    stats = mock_store.get_collection_stats()

    assert stats["total_documents"] == 42
    assert "doc1.pdf" in stats["sources"] and "doc2.pdf" in stats["sources"]
    assert stats["storage"] == "supabase"


def test_delete_by_filename(mock_store):
    mock_delete = MagicMock()
    mock_eq = MagicMock()
    mock_eq.execute.return_value = MagicMock(data=[{"id": "1"}, {"id": "2"}])
    mock_delete.eq.return_value = mock_eq
    mock_store.client.table.return_value.delete.return_value = mock_delete

    result = mock_store.delete_by_filename("test.pdf")

    assert result["success"] is True
    assert result["deleted_count"] == 2
