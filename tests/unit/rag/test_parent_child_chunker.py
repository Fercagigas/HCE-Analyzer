"""Tests unitarios de `ParentChildChunker`."""

import pytest

pytestmark = pytest.mark.unit


def test_chunk_document_creates_hierarchy():
    from services.rag.parent_child_chunker import ParentChildChunker

    chunker = ParentChildChunker(parent_size=500, child_size=100)
    text = "Este es un documento de prueba. " * 50
    metadata = {"document_id": "test_doc", "filename": "test.txt"}

    parents, children = chunker.chunk_document(text, metadata)

    assert len(parents) > 0
    assert len(children) > 0
    for child in children:
        assert child["metadata"]["parent_id"] is not None


def test_get_parent_for_child():
    from services.rag.parent_child_chunker import ParentChildChunker

    chunker = ParentChildChunker()
    text = "Contenido de prueba para chunking. " * 100
    parents, children = chunker.chunk_document(text, {"document_id": "doc1", "filename": "test.txt"})
    parents_dict = {p["chunk_id"]: p for p in parents}

    for child in children:
        assert chunker.get_parent_for_child(child["chunk_id"], parents_dict) is not None
