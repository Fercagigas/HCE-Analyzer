"""Tests unitarios de `Reranker` (modelo parcheado, sin descargas)."""

from unittest.mock import Mock, patch

import pytest

pytestmark = pytest.mark.unit


def test_rerank_returns_original_when_unavailable():
    from services.rag.reranker import Reranker

    with patch.object(Reranker, "_load_model"):
        reranker = Reranker()
        reranker._model_available = False
        docs = [{"content": "Doc 1"}, {"content": "Doc 2"}]
        assert reranker.rerank("query", docs, top_k=2) == docs[:2]


def test_rerank_respects_top_k():
    from services.rag.reranker import Reranker

    with patch.object(Reranker, "_load_model"):
        reranker = Reranker()
        reranker._model_available = True
        reranker.model = Mock()
        reranker.model.predict.return_value = [0.9, 0.8, 0.7, 0.6]
        docs = [{"content": f"Doc {i}"} for i in range(4)]
        assert len(reranker.rerank("query", docs, top_k=2)) == 2
