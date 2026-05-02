# Mapeo de Proveedores LLM - ChatHCE

**Última actualización**: Febrero 2026

## Resumen

ChatHCE usa **Claude API (Anthropic)** como proveedor único de LLM para todos los servicios, garantizando consistencia y simplicidad.

## Mapeo Servicio → Modelo

### 1. Agente del Chat Unificado → Claude Haiku 4.5

**Propósito**: Orquestación principal, análisis de intención, tool calling, síntesis de respuestas

| Campo | Valor |
|-------|-------|
| Modelo primario | `claude-haiku-4-5-20251001` |
| Modelo secundario | `claude-sonnet-4-5-20250929` |
| Modelo terciario | `claude-opus-4-20250514` |
| Framework | LangChain (AgentExecutor + bind_tools) |
| Configuración | `settings.claude_agent.*` |
| Max tokens | 4096 (primario), 8192 (secundario), 4096 (terciario) |
| Temperature | 0.1 |

**Archivos**:
- `services/unified_chat/unified_agent.py` - Agente principal
- `services/medical_agent/llm_manager.py` - ClaudeLLMManager con cadena de fallback

**Cadena de Fallback**:
```
Claude Haiku 4.5 (30s timeout)
    ↓ falla
Claude Sonnet 4.5 (45s timeout)
    ↓ falla
Claude Opus 4 (60s timeout)
```

---

### 2. QueryAugmenter (RAG) → Claude Haiku 4.5

**Propósito**: Augmentación de consultas antes de búsqueda RAG (Multi-Query + HyDE)

| Campo | Valor |
|-------|-------|
| Modelo | `claude-haiku-4-5-20251001` |
| API | Anthropic Python SDK directo (sin LangChain) |
| Configuración | `settings.rag.query_augmentation_model` |
| Max tokens | 300 (multi-query), 250 (HyDE) |
| Temperature | 0.4 (multi-query), 0.2 (HyDE) |

**Archivos**:
- `services/rag/query_augmenter.py`

---

### 3. RAG Service → Claude Haiku 4.5

**Propósito**: Generación de respuestas basadas en documentos clínicos recuperados

| Campo | Valor |
|-------|-------|
| Modelo primario | `claude-haiku-4-5-20251001` |
| Modelo secundario | `claude-sonnet-4-5-20250929` |
| Modelo terciario | `claude-opus-4-20250514` |
| Configuración | `settings.rag.*` |

**Archivos**:
- `services/rag_service.py` - Fachada
- `services/rag/improved_rag_service.py` - Implementación principal

---

### 4. VisualizationAgent → Claude Sonnet 4.5

**Propósito**: Generación de código Python para visualizaciones (solo como fallback cuando templates fallan)

| Campo | Valor |
|-------|-------|
| Modelo | `claude-sonnet-4-5-20250929` |
| Configuración | `settings.visualization.*` |
| Max tokens | 4000 |
| Temperature | 0.1 |
| Carga | Lazy loading (solo se inicializa cuando se necesita) |

**Archivos**:
- `services/medical_agent/visualization_agent.py`
- `services/medical_agent/llm_manager.py` → `create_visualization_llm()`

**Nota**: El sistema usa un enfoque template-first. Claude Sonnet solo se invoca si los templates Plotly fallan (~5-10% de los casos).

---

### 5. Embeddings → HuggingFace (Local)

**Propósito**: Generación de embeddings para búsqueda vectorial RAG

| Campo | Valor |
|-------|-------|
| Modelo | `sentence-transformers/all-MiniLM-L6-v2` |
| Dimensiones | 384 |
| Ejecución | Local (CPU/GPU) |
| Normalización | Habilitada |

**Archivos**:
- `services/rag/improved_rag_service.py`

---

### 6. Reranker → Cross-Encoder (Local)

**Propósito**: Reordenamiento de resultados de búsqueda por relevancia

| Campo | Valor |
|-------|-------|
| Modelo | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Ejecución | Local (CPU/GPU) |
| Fallback | Retorna resultados sin reranking si no disponible |

**Archivos**:
- `services/rag/reranker.py`

## Resumen Visual

```
┌─────────────────────────────────────────────────────┐
│                  Claude API (Anthropic)               │
│                                                       │
│  ┌─────────────────┐  ┌──────────────────────────┐  │
│  │ Claude Haiku 4.5│  │ Claude Sonnet 4.5        │  │
│  │ (Primario)      │  │ (Visualización/Fallback) │  │
│  │                 │  └──────────────────────────┘  │
│  │ • Chat Agent    │  ┌──────────────────────────┐  │
│  │ • QueryAugmenter│  │ Claude Opus 4            │  │
│  │ • RAG Service   │  │ (Fallback terciario)     │  │
│  └─────────────────┘  └──────────────────────────┘  │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│              Modelos Locales (HuggingFace)            │
│                                                       │
│  ┌─────────────────────┐  ┌──────────────────────┐  │
│  │ all-MiniLM-L6-v2   │  │ ms-marco-MiniLM-L-6  │  │
│  │ (Embeddings)        │  │ (Reranker)           │  │
│  └─────────────────────┘  └──────────────────────┘  │
└─────────────────────────────────────────────────────┘
```

## Configuración en settings.py

```python
# config/settings.py

class ClaudeAgentSettings(BaseSettings):
    anthropic_api_key: str
    primary_model: str = "claude-haiku-4-5-20251001"
    primary_model_version: str = "claude-haiku-4-5-20251001"
    secondary_model: str = "claude-sonnet-4-5-20250929"
    secondary_model_version: str = "claude-sonnet-4-5-20250929"
    tertiary_model: str = "claude-opus-4-20250514"
    tertiary_model_version: str = "claude-opus-4-20250514"
    max_tokens: int = 4096
    temperature: float = 0.1
    max_retries: int = 3
    retry_delay: float = 1.0
    backoff_multiplier: float = 2.0
    timeout_seconds: int = 30

class RAGSettings(BaseSettings):
    anthropic_api_key: str
    rag_model: str = "claude-haiku-4-5-20251001"
    query_augmentation_model: str = "claude-haiku-4-5-20251001"
    query_augmentation_enabled: bool = True
    query_augmentation_max_queries: int = 3

class VisualizationSettings(BaseSettings):
    model_name: str = "claude-sonnet-4-5-20250929"
    max_tokens: int = 4000
    temperature: float = 0.1
```

## ¿Por qué Claude para Todo?

- **Razonamiento superior**: Mejor análisis médico complejo
- **Tool calling nativo**: Soporte integrado para herramientas
- **Consistencia**: Un solo proveedor simplifica configuración y debugging
- **Fiabilidad**: API estable con buenos límites de rate
- **Contexto médico**: Mejor comprensión de terminología clínica

## Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| Agente no responde | API key inválida | Verificar `ANTHROPIC_API_KEY` en `.env` |
| Respuestas lentas | Rate limit | El sistema cambia automáticamente al modelo de fallback |
| RAG sin resultados | Sin documentos indexados | Subir documentos via Document Manager |
| Visualización falla | Template no disponible | Fallback automático a Claude Sonnet |
| Embeddings lentos | Sin GPU | Considerar GPU o reducir batch size |
