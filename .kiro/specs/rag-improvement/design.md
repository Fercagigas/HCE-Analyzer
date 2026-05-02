# Design Document: RAG System Improvement

## Overview

Este documento describe el diseno para mejorar el sistema RAG de ChatHCE implementando tres mejoras principales:

1. **Parent-Child Chunking**: Estrategia de chunking jerarquico donde chunks pequenos (children) se usan para busqueda precisa y chunks grandes (parents) se retornan para contexto completo.

2. **Hybrid Search**: Combinacion de BM25 (busqueda por keywords) y Vector Search (busqueda semantica) usando Reciprocal Rank Fusion (RRF).

3. **Reranking**: Uso de cross-encoder para reordenar resultados por relevancia despues de la busqueda inicial.

## Architecture

```
Document Input
      |
      v
+------------------+
| Parent-Child     |
| Chunker          |
+------------------+
      |
      v
+------------------+     +------------------+
| BM25 Index       |     | ChromaDB         |
| (rank_bm25)      |     | (embeddings)     |
+------------------+     +------------------+
      |                         |
      v                         v
+----------------------------------------+
|         Hybrid Search                   |
|   (Reciprocal Rank Fusion)             |
+----------------------------------------+
      |
      v
+------------------+
| Reranker         |
| (cross-encoder)  |
+------------------+
      |
      v
+------------------+
| Parent Chunk     |
| Retrieval        |
+------------------+
      |
      v
Final Results
```

## Components and Interfaces

### 1. ParentChildChunker

Responsable de crear chunks jerarquicos.

```python
class ParentChildChunker:
    def __init__(self, parent_size: int = 1500, child_size: int = 400):
        pass
    
    def chunk_document(self, text: str, metadata: dict) -> tuple[list[dict], list[dict]]:
        """Returns (parent_chunks, child_chunks) with linked metadata"""
        pass
    
    def get_parent_for_child(self, child_id: str, parents: dict) -> dict:
        """Retrieve parent chunk for a given child"""
        pass
    
    def pretty_print_hierarchy(self, parents: list, children: list) -> str:
        """Generate readable representation of chunk hierarchy"""
        pass
    
    def parse_hierarchy(self, hierarchy_str: str) -> tuple[list, list]:
        """Parse pretty-printed hierarchy back to chunks"""
        pass
```

### 2. HybridSearcher

Combina BM25 y Vector Search.

```python
class HybridSearcher:
    def __init__(self, vectorstore, bm25_index_path: str):
        pass
    
    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """Perform hybrid search with RRF fusion"""
        pass
    
    def _bm25_search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """BM25 keyword search"""
        pass
    
    def _vector_search(self, query: str, top_k: int) -> list[tuple[str, float]]:
        """Semantic vector search"""
        pass
    
    def _rrf_fusion(self, bm25_results: list, vector_results: list, k: int = 60) -> list:
        """Reciprocal Rank Fusion"""
        pass
```

### 3. Reranker

Reordena resultados usando cross-encoder.

```python
class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        pass
    
    def rerank(self, query: str, documents: list[dict], top_k: int = 5) -> list[dict]:
        """Rerank documents by relevance to query"""
        pass
```

### 4. ImprovedRAGService

Servicio principal que integra todos los componentes.

```python
class ImprovedRAGService:
    def __init__(self):
        pass
    
    def add_documents(self, file_paths: list[str], metadata: dict = None) -> dict:
        """Process and index documents"""
        pass
    
    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Search with hybrid search + reranking + parent retrieval"""
        pass
    
    def rebuild_indexes(self) -> dict:
        """Clear and rebuild all indexes"""
        pass
```

## Data Models

### ChunkMetadata

```python
@dataclass
class ChunkMetadata:
    chunk_id: str           # Unique identifier
    parent_id: str | None   # Parent chunk ID (None for parents)
    is_parent: bool         # True if this is a parent chunk
    document_id: str        # Source document identifier
    filename: str           # Original filename
    chunk_index: int        # Position in document
    char_start: int         # Start character position
    char_end: int           # End character position
```

### SearchResult

```python
@dataclass
class SearchResult:
    content: str            # Chunk content (parent content for context)
    score: float            # Relevance score
    metadata: dict          # Chunk metadata
    source: str             # Source document
```

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Parent-Child Chunk Integrity

*For any* document text processed by ParentChildChunker:
- All parent chunks SHALL have length between 1000 and 2500 characters
- All child chunks SHALL have length between 200 and 600 characters
- Every child chunk SHALL have a valid parent_id referencing an existing parent
- The content of every child chunk SHALL be contained within its parent chunk content

**Validates: Requirements 1.1, 1.2, 1.3**

### Property 2: Chunk Hierarchy Round-Trip

*For any* valid set of parent and child chunks, pretty-printing the hierarchy and then parsing it back SHALL produce equivalent chunk structures (same content, same parent-child relationships).

**Validates: Requirements 1.4, 1.5**

### Property 3: Hybrid Search Fusion Validity

*For any* search query executed against indexed documents:
- The hybrid search SHALL return results from both BM25 and vector search when both have matches
- The RRF fusion score for each document SHALL equal sum(1/(k + rank)) across all result lists where it appears
- Results SHALL be ordered by descending fusion score

**Validates: Requirements 2.1, 2.2**

### Property 4: Reranking Order Validity

*For any* set of search results reranked by the cross-encoder:
- The returned results SHALL be ordered by descending relevance score
- The number of returned results SHALL be at most top_k
- Each result SHALL have a score computed from query-document pair

**Validates: Requirements 3.1, 3.2, 3.4**

### Property 5: Dual Index Consistency

*For any* document added to the system:
- The document chunks SHALL exist in both the BM25 index and ChromaDB
- After rebuild, all previously added documents SHALL be present in both indexes

**Validates: Requirements 4.2, 4.4**

## Error Handling

| Error Condition | Handling Strategy |
|----------------|-------------------|
| BM25 index empty | Fall back to vector search only |
| Reranker model unavailable | Return results without reranking, log warning |
| ChromaDB connection fails | Raise exception with clear message |
| Document processing fails | Log error, continue with other documents |
| Invalid chunk metadata | Skip chunk, log warning |

## Testing Strategy

### Property-Based Testing

Se usara **Hypothesis** como framework de property-based testing para Python.

Cada propiedad de correctitud se implementara como un test de Hypothesis:
- Minimo 100 iteraciones por propiedad
- Generadores para: textos de documentos, queries, listas de resultados
- Tests anotados con referencia a la propiedad del diseno

### Unit Tests

- Test de inicializacion de componentes
- Test de edge cases (documentos vacios, queries vacias)
- Test de integracion entre componentes

### Test Configuration

```python
# pytest.ini or conftest.py
HYPOTHESIS_SETTINGS = {
    "max_examples": 100,
    "deadline": None,  # Disable deadline for slow operations
}
```

