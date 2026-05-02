# Requirements Document

## Introduction

Este documento especifica los requisitos para mejorar el sistema RAG (Retrieval-Augmented Generation) de ChatHCE. Las mejoras incluyen: chunking Parent-Child para mantener contexto, Hybrid Search combinando BM25 con busqueda vectorial, y reranking para mejorar la relevancia de los resultados.

## Glossary

- **RAG_System**: Sistema de Retrieval-Augmented Generation que busca documentos relevantes y genera respuestas basadas en ellos
- **Parent_Chunk**: Fragmento grande de documento (1500-2000 caracteres) que proporciona contexto completo
- **Child_Chunk**: Fragmento pequeno de documento (300-500 caracteres) usado para busqueda precisa
- **BM25**: Algoritmo de ranking basado en frecuencia de terminos (TF-IDF mejorado)
- **Vector_Search**: Busqueda semantica usando embeddings de texto
- **Hybrid_Search**: Combinacion de BM25 y Vector_Search con fusion de resultados
- **Reranker**: Modelo que reordena documentos por relevancia usando cross-encoder
- **ChromaDB**: Base de datos vectorial usada para almacenar embeddings

## Requirements

### Requirement 1

**User Story:** As a clinical user, I want the RAG system to return more relevant document chunks, so that I can get accurate answers to my medical queries.

#### Acceptance Criteria

1. WHEN a document is processed THEN the RAG_System SHALL create Parent_Chunks of 1500-2000 characters and Child_Chunks of 300-500 characters linked to their parents
2. WHEN a Child_Chunk is retrieved THEN the RAG_System SHALL return the corresponding Parent_Chunk to provide full context
3. WHEN storing chunks THEN the RAG_System SHALL maintain a mapping between Child_Chunks and their Parent_Chunks using metadata
4. WHEN a document is processed THEN the RAG_System SHALL generate a pretty-printed representation of the chunk hierarchy for debugging
5. WHEN parsing chunk metadata THEN the RAG_System SHALL validate the parent-child relationship structure

### Requirement 2

**User Story:** As a clinical user, I want the search to find documents using both keyword matching and semantic similarity, so that I can find relevant information even with different terminology.

#### Acceptance Criteria

1. WHEN a search query is executed THEN the RAG_System SHALL perform both BM25 keyword search and Vector_Search in parallel
2. WHEN combining search results THEN the RAG_System SHALL use Reciprocal Rank Fusion (RRF) to merge BM25 and Vector_Search results
3. WHEN no documents match the query THEN the RAG_System SHALL return an empty result set with appropriate message
4. WHEN the BM25 index is empty THEN the RAG_System SHALL fall back to Vector_Search only

### Requirement 3

**User Story:** As a clinical user, I want the most relevant documents to appear first in results, so that I can quickly find the information I need.

#### Acceptance Criteria

1. WHEN search results are obtained THEN the RAG_System SHALL apply a cross-encoder reranker to reorder results by relevance
2. WHEN reranking documents THEN the RAG_System SHALL use the query and document content to compute relevance scores
3. WHEN the reranker model is unavailable THEN the RAG_System SHALL return results without reranking and log a warning
4. WHEN reranking is complete THEN the RAG_System SHALL return the top_k most relevant documents

### Requirement 4

**User Story:** As a system administrator, I want the improved RAG system to properly manage its indexes, so that the system works reliably.

#### Acceptance Criteria

1. WHEN the improved RAG_System initializes THEN it SHALL create fresh BM25 and ChromaDB indexes if they do not exist
2. WHEN adding new documents THEN the RAG_System SHALL index them in both the BM25 index and ChromaDB
3. WHEN the BM25 index file does not exist THEN the RAG_System SHALL create a new empty index
4. WHEN rebuilding indexes THEN the RAG_System SHALL clear existing data and reindex all documents from scratch

