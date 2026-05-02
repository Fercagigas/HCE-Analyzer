# Sistema RAG de Vectorización - Verificación y Mejores Prácticas

**Fecha**: Marzo 2026
**Estado**: ✅ Verificado y Actualizado

## Resumen

Este documento verifica el uso correcto de todas las librerías involucradas en el sistema RAG de vectorización de documentos de ChatHCE. El sistema utiliza una arquitectura avanzada con búsqueda híbrida (pgvector + tsvector) en Supabase, chunking jerárquico padre-hijo, augmentación de consultas con Claude Haiku y reranking con cross-encoder.

## Arquitectura del Sistema RAG

```
Consulta del usuario
       ↓
QueryAugmenter (Claude Haiku 4.5)
  ├── Multi-Query: consultas alternativas con terminología médica variada
  └── HyDE: documento hipotético que respondería la consulta
       ↓
Para CADA consulta augmentada:
  ImprovedRAGService.search()
       ↓
  SupabaseVectorStore.hybrid_search()
    ├── pgvector (cosine similarity) → ranking semántico
    └── tsvector (full-text search) → ranking léxico
    └── RRF Fusion (en PostgreSQL) → combina ambos rankings
       ↓
  Reranker (cross-encoder/ms-marco-MiniLM-L-6-v2)
       ↓
  Parent Chunk Retrieval (desde Supabase)
       ↓
Deduplicación y merge de resultados
       ↓
Top-K resultados finales con fuentes
```

## Componente Principal: ImprovedRAGService

**Ubicación**: `services/rag/improved_rag_service.py`

`ImprovedRAGService` es la fuente única de verdad para todas las operaciones RAG. `RAGService` (`services/rag_service.py`) actúa como fachada delgada que delega a esta clase.

```python
class ImprovedRAGService:
    def __init__(
        self,
        parent_chunk_size: int = 1500,
        child_chunk_size: int = 400,
    ):
        # Componentes inicializados:
        # - ParentChildChunker (chunking jerárquico)
        # - HuggingFaceEmbeddings (sentence-transformers)
        # - SupabaseVectorStore (pgvector + tsvector)
        # - Reranker (cross-encoder)
        # - DocumentProcessor (Docling/PyPDF2)
```

### Flujo de Búsqueda

```python
def search(self, query, top_k=5, rerank=True):
    # 1. Búsqueda híbrida en child chunks (pgvector + tsvector)
    hybrid_results = self.store.hybrid_search(query, top_k=fetch_k)
    
    # 2. Reranking con cross-encoder (si disponible)
    reranked_results = self.reranker.rerank(query, hybrid_results, top_k)
    
    # 3. Recuperar parent chunks para contexto completo
    for result in reranked_results:
        parent = self.store.get_parent_chunk(result['parent_id'])
        # Retorna content del padre + child_content original
```

## Componentes Verificados

### 1. HuggingFace Embeddings ✅

**Librería**: `langchain-huggingface` (v0.1.0+)

**Implementación** (`services/rag/improved_rag_service.py`):
```python
from langchain_huggingface import HuggingFaceEmbeddings

# Detección automática de GPU
import torch
device = 'cuda' if torch.cuda.is_available() else 'cpu'

model_kwargs = {'device': device}
if HUGGINGFACE_API_TOKEN:
    model_kwargs['token'] = HUGGINGFACE_API_TOKEN

self.embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs=model_kwargs,
    encode_kwargs={'normalize_embeddings': True}
)
```

**Estado**: ✅ Correcto
- Modelo válido y ampliamente utilizado (384 dimensiones)
- Normalización habilitada para búsqueda por similitud coseno
- Detección automática de GPU/CPU
- Soporte para token de HuggingFace si está configurado (`HUGGINFACEHUB_API_TOKEN`)

---

### 2. Supabase pgvector Store ✅

**Librería**: `supabase-py`

**Implementación** (`services/rag/supabase_vector_store.py`):
```python
from supabase import create_client

class SupabaseVectorStore:
    TABLE_NAME = "rag_chunks"
    
    def __init__(self, embeddings):
        self.client = create_client(url, key)
        self.embeddings = embeddings
    
    def hybrid_search(self, query, top_k=10):
        embedding = self.embeddings.embed_query(query)
        result = self.client.rpc("hybrid_search", {
            "query_embedding": embedding,
            "query_text": query,
            "match_count": top_k,
            "rrf_k": 60,
        }).execute()
        return result.data
    
    def vector_search(self, query, top_k=10):
        embedding = self.embeddings.embed_query(query)
        result = self.client.rpc("vector_search", {
            "query_embedding": embedding,
            "match_count": top_k,
        }).execute()
        return result.data
```

**Estado**: ✅ Correcto
- Tabla `rag_chunks` con columna `vector(384)` y índice HNSW
- Columna `tsvector` generada automáticamente para full-text search
- Funciones SQL `hybrid_search()` y `vector_search()` con RRF fusion
- RLS policies habilitadas para seguridad

---

### 3. Búsqueda Híbrida (Supabase RPC) ✅

La búsqueda híbrida se ejecuta completamente en PostgreSQL mediante funciones SQL:

```sql
-- hybrid_search: combina pgvector (cosine) + tsvector (full-text) con RRF
CREATE FUNCTION hybrid_search(
    query_embedding vector(384),
    query_text text,
    match_count int,
    rrf_k int DEFAULT 60
) RETURNS TABLE(...)
```

**Características**:
- RRF Fusion con constante k=60 (estándar)
- Búsqueda semántica via pgvector (cosine similarity)
- Búsqueda léxica via tsvector con `plainto_tsquery('spanish', ...)`
- Todo ejecutado en una sola query SQL (eficiente)

---

### 4. Reranker (Cross-Encoder) ✅

**Ubicación**: `services/rag/reranker.py`
**Modelo**: `cross-encoder/ms-marco-MiniLM-L-6-v2`

```python
class Reranker:
    def __init__(self, model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"):
        from sentence_transformers import CrossEncoder
        self.model = CrossEncoder(model_name)
    
    def rerank(self, query, documents, top_k=5):
        pairs = [(query, doc['content']) for doc in documents]
        scores = self.model.predict(pairs)
        # Ordena por score descendente, retorna top_k
```

**Estado**: ✅ Correcto
- Degradación elegante: si el modelo no carga, retorna resultados sin reranking
- Propiedad `is_available` para verificar disponibilidad
- Scores de relevancia añadidos como `rerank_score`

---

### 5. ParentChildChunker ✅

**Ubicación**: `services/rag/parent_child_chunker.py`

Implementa chunking jerárquico donde documentos se dividen en chunks padre (contexto amplio) y chunks hijo (granulares para búsqueda).

```python
class ParentChildChunker:
    def __init__(self, parent_size=1500, child_size=400):
        self.parent_size = parent_size
        self.child_size = child_size
    
    def chunk_document(self, text, metadata):
        # 1. Dividir en parent chunks (1500 chars)
        # 2. Cada parent se divide en child chunks (400 chars)
        # 3. Ambos se almacenan en Supabase rag_chunks (is_parent flag)
        return parent_chunks, child_chunks
```

**Ventajas**:
- Child chunks pequeños mejoran precisión de búsqueda
- Parent chunks proporcionan contexto completo al LLM
- Relación padre-hijo mantenida via `parent_id` en tabla rag_chunks

---

### 6. QueryAugmenter ✅

**Ubicación**: `services/rag/query_augmenter.py`
**Modelo**: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)

Augmenta consultas del usuario antes de la búsqueda usando dos técnicas:

```python
class QueryAugmenter:
    def augment(self, query, use_multi_query=True, use_hyde=True):
        queries = [query]  # Siempre incluye la original
        
        # Multi-Query: consultas alternativas con terminología médica variada
        alt_queries = self._generate_multi_queries(query)
        queries.extend(alt_queries)
        
        # HyDE: documento hipotético que respondería la consulta
        hyde_doc = self._generate_hypothetical_document(query)
        queries.append(hyde_doc)
        
        return queries
```

**Configuración** (`config/settings.py`):
```python
query_augmentation_enabled: bool = True
query_augmentation_model: str = "claude-haiku-4-5-20251001"
query_augmentation_max_queries: int = 3
```

---

### 7. Procesamiento de Documentos con Docling ✅

**Ubicación**: `src/processors/document_processor.py`

```python
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption
from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions

# Detección automática de GPU
device_str = _detect_accelerator()  # "cuda" si CUDA disponible, "cpu" si no
accel_device = AcceleratorDevice.CUDA if device_str == "cuda" else AcceleratorDevice.CPU

accelerator_options = AcceleratorOptions(
    device=accel_device,
    num_threads=4
)

pipeline_options = PdfPipelineOptions()
pipeline_options.do_ocr = True
pipeline_options.do_table_structure = True
pipeline_options.accelerator_options = accelerator_options

self.converter = DocumentConverter(
    format_options={
        InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
    }
)

result = self.converter.convert(str(file_path))
markdown_content = result.document.export_to_markdown()
```

**Estado**: ✅ Correcto
- OCR habilitado para documentos escaneados
- Extracción de estructura de tablas
- Exportación a Markdown para preservar estructura
- Aceleración GPU automática (CUDA si disponible, CPU como fallback)
- Fallback a PyPDF2 si Docling falla

---

### 8. Text Splitting con LangChain ✅

**Implementación** (`src/processors/document_processor.py`):
```python
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import MarkdownHeaderTextSplitter

self.text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200,
    chunk_overlap=200,
    length_function=len,
    separators=["\n\n", "\n", ". ", " ", ""]
)
```

**Nota**: El `DocumentProcessor` se usa para la extracción inicial. El chunking jerárquico padre-hijo lo realiza `ParentChildChunker` dentro de `ImprovedRAGService`.

## Flujo de Integración Completo

### Flujo de Indexación

```
1. Subida de documento (DocumentManager)
       ↓
2. Validación de formato y tamaño
       ↓
3. Extracción de texto (Docling → Markdown)
       ↓
4. Chunking jerárquico (ParentChildChunker)
   ├── Parent chunks (1500 chars) → rag_chunks (is_parent=TRUE)
   └── Child chunks (400 chars) → rag_chunks (is_parent=FALSE)
       ↓
5. Generación de embeddings (HuggingFace all-MiniLM-L6-v2, 384 dims)
       ↓
6. Almacenamiento en Supabase (tabla rag_chunks con vector(384))
       ↓
7. tsvector generado automáticamente por PostgreSQL
```

### Flujo de Búsqueda

```
1. Consulta del usuario
       ↓
2. Augmentación de consulta (QueryAugmenter + Claude Haiku)
   ├── Original: "protocolo hipertensión"
   ├── Multi-Query: "manejo crisis hipertensiva", "tratamiento HTA severa"
   └── HyDE: "El protocolo de hipertensión establece que..."
       ↓
3. Para CADA consulta augmentada:
   a. Búsqueda híbrida (pgvector + tsvector + RRF Fusion en SQL)
   b. Reranking con cross-encoder
   c. Recuperación de parent chunks
       ↓
4. Deduplicación por hash de contenido
       ↓
5. Ordenar por score, retornar top_k
       ↓
6. Formateo con citación de fuentes
```

## Checklist de Verificación

- [x] Todos los paquetes requeridos en requirements.txt
- [x] Imports correctos y actualizados
- [x] Uso correcto de APIs según documentación
- [x] Manejo de errores implementado
- [x] Caché para rendimiento
- [x] Búsqueda híbrida (pgvector + tsvector) funcionando
- [x] Reranking con cross-encoder operativo
- [x] Chunking padre-hijo implementado
- [x] Augmentación de consultas con Claude Haiku
- [x] Degradación elegante en todos los componentes
- [x] Almacenamiento vectorial en Supabase pgvector

## Problemas Comunes y Soluciones

### Problema 1: Reranker no disponible
**Síntoma**: `Reranker model not available, returning original results`
**Solución**: `pip install sentence-transformers` - El sistema funciona sin reranking (degradación elegante)

### Problema 2: Supabase connection error
**Síntoma**: Error al conectar con Supabase para búsqueda RAG
**Solución**: Verificar `SUPABASE_URL` y `SUPABASE_KEY` en `.env`. Verificar que la tabla `rag_chunks` y las funciones `hybrid_search`/`vector_search` existan.

### Problema 3: QueryAugmenter falla
**Síntoma**: `Query augmentation failed, using original`
**Solución**: Verificar `ANTHROPIC_API_KEY`. El sistema usa la consulta original como fallback.

### Problema 4: Docling falla en conversión
**Síntoma**: Texto vacío o ilegible
**Solución**: Habilitar OCR (`do_ocr=True`), verificar que el PDF no esté protegido. Fallback automático a PyPDF2.

## Optimización de Rendimiento

### Optimizaciones Actuales ✅
1. **Búsqueda híbrida en SQL**: Una sola query combina vector + text search
2. **Índice HNSW**: Búsqueda vectorial eficiente en pgvector
3. **Índice GIN**: Full-text search eficiente con tsvector
4. **Parent chunks en Supabase**: Acceso rápido sin almacenamiento local
5. **Detección automática de GPU**: Usa CUDA si está disponible
6. **Degradación elegante**: Cada componente tiene fallback

### Métricas Recomendadas
- Tiempo de generación de embeddings
- Tamaño de la tabla rag_chunks
- Hit rate de caché
- Tiempo de respuesta de búsqueda
- Distribución de scores de reranking

## Referencias

- [LangChain Documentation](https://python.langchain.com/)
- [Supabase pgvector](https://supabase.com/docs/guides/ai/vector-columns)
- [Docling](https://github.com/docling-project/docling)
- [HuggingFace Sentence Transformers](https://www.sbert.net/)
- [HyDE Paper](https://arxiv.org/abs/2212.10496)

---

**Última verificación**: Marzo 2026
**Próxima revisión**: Abril 2026
