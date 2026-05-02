"""
Tests para componentes RAG mejorados.

Verifica: ParentChildChunker, SupabaseVectorStore, Reranker
"""
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestParentChildChunker:
    """Tests para ParentChildChunker."""

    def test_chunk_document_creates_hierarchy(self):
        """Verifica que se crean chunks padre e hijo correctamente."""
        from services.rag.parent_child_chunker import ParentChildChunker

        chunker = ParentChildChunker(parent_size=500, child_size=100)

        # Texto de prueba
        text = "Este es un documento de prueba. " * 50
        metadata = {'document_id': 'test_doc', 'filename': 'test.txt'}

        parents, children = chunker.chunk_document(text, metadata)

        assert len(parents) > 0, "Debe crear al menos un chunk padre"
        assert len(children) > 0, "Debe crear al menos un chunk hijo"

        # Verificar que los hijos tienen parent_id
        for child in children:
            assert child['metadata']['parent_id'] is not None

    def test_get_parent_for_child(self):
        """Verifica recuperación de padre desde hijo."""
        from services.rag.parent_child_chunker import ParentChildChunker

        chunker = ParentChildChunker()

        text = "Contenido de prueba para chunking. " * 100
        metadata = {'document_id': 'doc1', 'filename': 'test.txt'}

        parents, children = chunker.chunk_document(text, metadata)

        # Crear diccionario de padres
        parents_dict = {p['chunk_id']: p for p in parents}

        # Verificar que podemos recuperar el padre de cada hijo
        for child in children:
            parent = chunker.get_parent_for_child(child['chunk_id'], parents_dict)
            assert parent is not None


class TestSupabaseVectorStore:
    """Tests para SupabaseVectorStore."""

    @pytest.fixture
    def mock_store(self):
        """Crea instancia con mocks de Supabase y embeddings."""
        with patch('services.rag.supabase_vector_store.create_client') as mock_create:
            mock_client = MagicMock()
            mock_create.return_value = mock_client

            mock_embeddings = Mock()
            mock_embeddings.embed_documents.return_value = [[0.1] * 384]
            mock_embeddings.embed_query.return_value = [0.1] * 384

            from services.rag.supabase_vector_store import SupabaseVectorStore
            store = SupabaseVectorStore(embeddings=mock_embeddings)
            store.client = mock_client
            return store

    def test_hybrid_search_calls_rpc(self, mock_store):
        """Verifica que hybrid_search llama al RPC de Supabase."""
        mock_rpc_result = MagicMock()
        mock_rpc_result.execute.return_value = MagicMock(data=[
            {
                "content": "Protocolo de diabetes",
                "rrf_score": 0.85,
                "metadata": {"specialty": "endocrinologia"},
                "parent_id": "parent_1",
                "filename": "diabetes.pdf",
                "chunk_id": "chunk_1",
            }
        ])
        mock_store.client.rpc.return_value = mock_rpc_result

        results = mock_store.hybrid_search("diabetes tratamiento", top_k=5)

        assert len(results) == 1
        assert results[0]["content"] == "Protocolo de diabetes"
        assert results[0]["score"] == 0.85
        mock_store.client.rpc.assert_called_once_with(
            "hybrid_search",
            {
                "query_embedding": [0.1] * 384,
                "query_text": "diabetes tratamiento",
                "match_count": 5,
                "rrf_k": 60,
            },
        )

    def test_vector_search_calls_rpc(self, mock_store):
        """Verifica que vector_search llama al RPC correcto."""
        mock_rpc_result = MagicMock()
        mock_rpc_result.execute.return_value = MagicMock(data=[
            {
                "content": "Guía de hipertensión",
                "similarity": 0.92,
                "metadata": {},
                "parent_id": None,
                "filename": "hipertension.pdf",
                "chunk_id": "chunk_2",
            }
        ])
        mock_store.client.rpc.return_value = mock_rpc_result

        results = mock_store.vector_search("hipertensión arterial", top_k=3)

        assert len(results) == 1
        assert results[0]["score"] == 0.92
        mock_store.client.rpc.assert_called_once_with(
            "vector_search",
            {
                "query_embedding": [0.1] * 384,
                "match_count": 3,
            },
        )

    def test_get_collection_stats(self, mock_store):
        """Verifica obtención de estadísticas."""
        # Mock count query
        mock_count = MagicMock()
        mock_count.execute.return_value = MagicMock(count=42)
        mock_select_count = MagicMock()
        mock_select_count.eq.return_value = mock_count

        # Mock sources query
        mock_sources = MagicMock()
        mock_sources.execute.return_value = MagicMock(data=[
            {"filename": "doc1.pdf"},
            {"filename": "doc2.pdf"},
        ])
        mock_select_sources = MagicMock()
        mock_select_sources.eq.return_value = mock_sources

        # Mock specialty query
        mock_spec = MagicMock()
        mock_spec.execute.return_value = MagicMock(data=[
            {"specialty": "cardiologia"},
        ])
        mock_select_spec = MagicMock()
        mock_select_spec.eq.return_value = mock_spec

        # Mock document_type query
        mock_type = MagicMock()
        mock_type.execute.return_value = MagicMock(data=[
            {"document_type": "guia_clinica"},
        ])
        mock_select_type = MagicMock()
        mock_select_type.eq.return_value = mock_type

        # Chain table().select().eq() calls
        mock_table = MagicMock()
        mock_table.select.side_effect = [
            mock_select_count,
            mock_select_sources,
            mock_select_spec,
            mock_select_type,
        ]
        mock_store.client.table.return_value = mock_table

        stats = mock_store.get_collection_stats()

        assert stats["total_documents"] == 42
        assert "doc1.pdf" in stats["sources"]
        assert "doc2.pdf" in stats["sources"]
        assert stats["storage"] == "supabase"

    def test_delete_by_filename(self, mock_store):
        """Verifica eliminación por filename."""
        mock_delete = MagicMock()
        mock_eq = MagicMock()
        mock_eq.execute.return_value = MagicMock(data=[{"id": "1"}, {"id": "2"}])
        mock_delete.eq.return_value = mock_eq
        mock_store.client.table.return_value.delete.return_value = mock_delete

        result = mock_store.delete_by_filename("test.pdf")

        assert result["success"] is True
        assert result["deleted_count"] == 2


class TestReranker:
    """Tests para Reranker."""

    def test_rerank_returns_original_when_unavailable(self):
        """Verifica fallback cuando modelo no disponible."""
        from services.rag.reranker import Reranker

        with patch.object(Reranker, '_load_model'):
            reranker = Reranker()
            reranker._model_available = False

            docs = [{'content': 'Doc 1'}, {'content': 'Doc 2'}]
            result = reranker.rerank("query", docs, top_k=2)

            assert result == docs[:2]

    def test_rerank_respects_top_k(self):
        """Verifica que respeta el límite top_k."""
        from services.rag.reranker import Reranker

        with patch.object(Reranker, '_load_model'):
            reranker = Reranker()
            reranker._model_available = True
            reranker.model = Mock()
            reranker.model.predict.return_value = [0.9, 0.8, 0.7, 0.6]

            docs = [{'content': f'Doc {i}'} for i in range(4)]
            result = reranker.rerank("query", docs, top_k=2)

            assert len(result) == 2
