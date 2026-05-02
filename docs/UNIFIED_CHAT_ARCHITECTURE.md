# Arquitectura del Chat Unificado

**Última actualización**: Febrero 2026
**Modelo**: Claude Haiku 4.5 (`claude-haiku-4-5-20251001`)

## Resumen

El Chat Unificado consolida las interfaces previamente separadas (Medical Agent y Clinical Chat) en una sola interfaz inteligente. Usa Claude Haiku 4.5 (Anthropic) como LLM primario con selección automática de herramientas para acceder a la base de datos MIMIC-IV-ED, documentos clínicos indexados (RAG) y generación de visualizaciones.

### Características Clave
- **Claude Haiku 4.5**: Modelo primario (`claude-haiku-4-5-20251001`)
- **Directivas Anti-Alucinación**: Prevención de fabricación de datos médicos
- **Citación de Fuentes**: Todas las respuestas citan herramientas y tablas usadas
- **Memoria Conversacional**: Datos de consultas previas disponibles para preguntas de seguimiento
- **Búsqueda RAG Avanzada**: Augmentación de consultas + búsqueda híbrida + reranking

## Diagrama de Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI Layer                        │
│                  (Unified Chat Interface)                    │
│                  ui/unified_chat_interface.py                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Unified Chat Agent                         │
│              services/unified_chat/unified_agent.py          │
│                                                              │
│  ┌────────────────────────────────────────────────────┐     │
│  │     Claude Haiku 4.5 + LangChain AgentExecutor     │     │
│  │     (Análisis de intención + Tool Calling)          │     │
│  └────────────────────────────────────────────────────┘     │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ DatabaseTool │  │   RAGTool    │  │ Visualization    │  │
│  │ (MIMIC-ED)   │  │ (Documentos) │  │ CollaborationTool│  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
└─────────┼──────────────────┼───────────────────┼────────────┘
          │                  │                   │
          ▼                  ▼                   ▼
   ┌────────────┐  ┌─────────────────┐  ┌────────────────┐
   │  Supabase  │  │ImprovedRAGService│  │Visualization   │
   │ (mimic_ed) │  │ + QueryAugmenter│  │    Agent       │
   └────────────┘  │ + Supabase     │  │(Claude Sonnet) │
                   │ + Reranker      │  └────────────────┘
                   └─────────────────┘
```

## Componentes Principales

### 1. Unified Chat Agent

**Ubicación**: `services/unified_chat/unified_agent.py`

Orquestador principal que coordina todas las herramientas del sistema.

```python
class UnifiedChatAgent:
    def __init__(self):
        self.llm_manager = ClaudeLLMManager()
        self.prompt_manager = PromptManager()
        self.tools = self._initialize_tools()
        self.agent_executor = self._create_agent_executor()
    
    def _initialize_tools(self) -> List:
        """Inicializa herramientas como StructuredTool de LangChain."""
        tools = []
        
        # Database Tool
        db_tool = create_database_tool()
        tools.append(db_tool.get_langchain_tool())
        
        # RAG Tool
        rag_tool = create_rag_tool()
        tools.append(rag_tool.get_langchain_tool())
        
        # Visualization Tool
        viz_tool = VisualizationCollaborationTool()
        tools.append(viz_tool.get_langchain_tool())
        
        return tools
    
    def _create_agent_executor(self) -> AgentExecutor:
        """Crea AgentExecutor de LangChain con tool calling."""
        llm = self.llm_manager.get_llm()
        llm_with_tools = llm.bind_tools(self.tools)
        
        agent = create_tool_calling_agent(
            llm=llm_with_tools,
            tools=self.tools,
            prompt=self._create_prompt_template()
        )
        
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            max_iterations=10,
            handle_parsing_errors=True
        )
    
    def process_message(self, message: str, context: List[Dict]) -> Dict[str, Any]:
        """
        Procesa mensaje del usuario con selección automática de herramientas.
        
        Returns:
            Dict con: content, tools_used, visualizations, sources, metadata
        """
```

**Flujo de Procesamiento**:
```
Usuario → process_message()
    ↓
_enrich_message_with_context() → Añade datos de consultas previas
    ↓
_prepare_chat_history() → Prepara historial conversacional
    ↓
_invoke_agent() → Claude analiza y selecciona herramientas
    ↓
Ejecución de herramientas (database/rag/visualization)
    ↓
_format_response() → Extrae resultados, fuentes, visualizaciones
    ↓
_integrate_visualizations_in_response() → Inserta gráficas en respuesta
    ↓
Retorna respuesta integrada
```

### 2. Database Tool

**Ubicación**: `services/unified_chat/tools/database_tool.py`

Consultas a la base de datos MIMIC-IV-ED en Supabase (esquema `mimic_ed`).

```python
class DatabaseToolInput(BaseModel):
    query_type: str = Field(..., description="Tipo de consulta")
    subject_id: Optional[int] = Field(None, description="ID del paciente")
    stay_id: Optional[int] = Field(None, description="ID de estancia")
    icd_code: Optional[str] = Field(None, description="Código ICD")
    custom_query: Optional[str] = Field(None, description="SQL personalizado")
    limit: Optional[int] = Field(None, description="Límite de resultados")

class DatabaseTool(ClaudeToolAdapter):
    def __init__(self):
        super().__init__(
            tool_name="query_mimic_database",
            tool_description="...",
            args_schema=DatabaseToolInput
        )
        self.db_service = DatabaseService()
    
    def execute(self, query_type, subject_id=None, ...):
        # Despacha según query_type:
        # patient_summary, vital_signs, diagnoses, medications, custom
```

**Tipos de Consulta**:
| Tipo | Descripción | Tablas |
|------|-------------|--------|
| `patient_summary` | Resumen completo del paciente | edstays, triage |
| `vital_signs` | Signos vitales y tendencias | vitalsign |
| `diagnoses` | Diagnósticos con códigos ICD | diagnosis |
| `medications` | Medicamentos administrados | medrecon, pyxis |
| `custom` | SQL personalizado (validado) | Cualquiera |

**Seguridad**:
- Prevención de SQL injection (whitelist de operaciones)
- Solo consultas SELECT permitidas
- Límite de filas configurable
- Validación de parámetros con Pydantic

### 3. RAG Tool

**Ubicación**: `services/unified_chat/tools/rag_tool.py`

Búsqueda avanzada en documentos clínicos con augmentación de consultas.

```python
class RAGQueryInput(BaseModel):
    query: str = Field(..., description="Consulta de búsqueda")
    specialty: Optional[str] = Field(None, description="Especialidad médica")
    top_k: Optional[int] = Field(None, description="Número de resultados")

class RAGTool(ClaudeToolAdapter):
    def __init__(self):
        super().__init__(
            tool_name="search_clinical_documents",
            tool_description="...",
            args_schema=RAGQueryInput
        )
        self.rag_service = ImprovedRAGService()
        self.query_augmenter = QueryAugmenter()
    
    def execute(self, query, specialty=None, top_k=None):
        # 1. Augmentar consulta (Multi-Query + HyDE via Claude Haiku)
        augmented_queries = self.query_augmenter.augment(query)
        
        # 2. Buscar con cada consulta augmentada
        for aug_query in augmented_queries:
            results = self.rag_service.search(aug_query, top_k=k, rerank=True)
            # Deduplicar por hash de contenido
        
        # 3. Ordenar por score, retornar top_k con fuentes
```

**Pipeline de Búsqueda**:
```
Query → QueryAugmenter (Claude Haiku)
  ├── Multi-Query (terminología médica variada)
  └── HyDE (documento hipotético)
       ↓
Para cada consulta:
  ImprovedRAGService.search()
    ├── pgvector (semántico) + tsvector (léxico)
    ├── RRF Fusion
    ├── Reranking (cross-encoder)
    └── Parent chunk retrieval
       ↓
Deduplicación → Top-K → Citación de fuentes
```

### 4. Visualization Collaboration Tool

**Ubicación**: `services/medical_agent/tools/visualization_collaboration_tool.py`

Orquesta la generación de visualizaciones médicas dinámicas.

**Flujo**:
1. Obtiene datos del paciente via DatabaseService
2. Analiza métricas disponibles
3. Para cada métrica: VisualizationSelector → VisualizationTemplates (template-first)
4. Fallback a VisualizationAgent (Claude Sonnet 4.5) si template falla
5. Retorna imágenes base64

### 5. Document Manager

**Ubicación**: `services/unified_chat/document_manager.py`

Gestiona subida, indexación y eliminación de documentos clínicos.

```python
class DocumentManager:
    def __init__(self):
        self.rag_service = ImprovedRAGService()  # Usa ImprovedRAGService directamente
        self.document_processor = DocumentProcessor()
    
    def upload_document(self, file, metadata): ...
    def list_documents(self) -> List[Dict]: ...
    def delete_document(self, document_id: str) -> bool: ...
```

**Pipeline de Indexación**:
```
Archivo → Validación → Docling (extracción) → ParentChildChunker
  → Embeddings (HuggingFace) → Supabase pgvector (rag_chunks)
```

## Sistema Anti-Alucinación

### Directivas Implementadas

Las directivas se generan en `services/medical_agent/prompt_manager.py` via `get_anti_hallucination_directives()` y se integran en el system prompt del agente.

**Prohibiciones Absolutas**:
- NUNCA inventar subject_id, stay_id o hadm_id
- NUNCA fabricar valores de signos vitales
- NUNCA inventar diagnósticos o códigos ICD
- NUNCA crear medicamentos o dosis ficticias
- NUNCA generar fechas o timestamps falsos

**Manejo de Datos Faltantes**:
- Sin datos: "No encontré información sobre [X] en el dataset"
- Valores nulos: "Algunos registros tienen datos incompletos"
- Paciente inexistente: "El paciente [ID] no existe en MIMIC-IV-ED"

**Citación de Fuentes**:
- Indicar qué herramienta se usó
- Mencionar tabla de origen (edstays, triage, vitalsign, etc.)
- Para RAG, citar documento fuente

**Reconocimiento de Incertidumbre**:
- "Según los datos disponibles..." (datos verificados)
- "Los registros muestran..." (observaciones directas)
- "Esto podría indicar..." (interpretaciones)

**Limitaciones del Dataset**:
- MIMIC-IV-ED: dataset demo con 222 pacientes
- Solo datos de urgencias
- Sin acceso a información fuera del dataset

## Memoria Conversacional

El agente mantiene contexto entre mensajes de dos formas:

### 1. Historial de Chat
`_prepare_chat_history()` prepara los últimos N mensajes como contexto para Claude, respetando límites de tokens.

### 2. Enriquecimiento con Datos Previos
`_enrich_message_with_context()` detecta preguntas de seguimiento y añade datos de consultas anteriores al mensaje. Si el usuario preguntó por un paciente y luego dice "muestra sus medicamentos", el sistema inyecta el `subject_id` previo.

## Cadena de Fallback de Modelos

Gestionada por `ClaudeLLMManager` (`services/medical_agent/llm_manager.py`):

| Prioridad | Modelo | Versión | Max Tokens | Timeout |
|-----------|--------|---------|------------|---------|
| Primario | Claude Haiku 4.5 | `claude-haiku-4-5-20251001` | 4096 | 30s |
| Secundario | Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` | 8192 | 45s |
| Terciario | Claude Opus 4 | `claude-opus-4-20250514` | 4096 | 60s |

El sistema cambia automáticamente al siguiente modelo si el actual falla (rate limit, timeout, error de API).

## Integración con Componentes Existentes

### Componentes Reutilizados del Medical Agent

| Componente | Ubicación | Uso |
|-----------|-----------|-----|
| `ClaudeLLMManager` | `services/medical_agent/llm_manager.py` | Gestión de LLM y fallback |
| `PromptManager` | `services/medical_agent/prompt_manager.py` | Optimización de prompts |
| `ErrorHandler` | `services/medical_agent/error_handler.py` | Manejo de errores |
| `AgentPerformanceMonitor` | `services/medical_agent/agent_performance_monitor.py` | Métricas |
| `VisualizationAgent` | `services/medical_agent/visualization_agent.py` | Generación de gráficas |
| `CodeExecutor` | `services/medical_agent/code_executor.py` | Ejecución segura de código |
| `DatabaseService` | `services/medical_agent/services/database_service.py` | Acceso a Supabase |

### Integración con RAG Service

```python
# RAGTool usa ImprovedRAGService directamente
from services.rag.improved_rag_service import ImprovedRAGService
self.rag_service = ImprovedRAGService()

# RAGService (services/rag_service.py) es fachada delgada sobre ImprovedRAGService
```

### Integración con Supabase

```python
# DatabaseTool usa DatabaseService para acceder a Supabase
from services.medical_agent.services.database_service import DatabaseService
self.db_service = DatabaseService()

# Tablas MIMIC-IV-ED en esquema mimic_ed
result = supabase.schema('mimic_ed').table('edstays').select('*').execute()

# Tablas de aplicación en esquema public (default)
result = supabase.table('users').select('*').execute()
```

## Configuración

### Variables de Entorno Requeridas

```bash
ANTHROPIC_API_KEY=your_anthropic_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SECRET_KEY=your_secret_key
```

### Settings del Chat Unificado

```python
# services/unified_chat/config.py
class UnifiedChatConfig:
    max_context_messages: int = 10
    enable_caching: bool = True
    cache_ttl: int = 300
    max_tokens: int = 4000
    temperature: float = 0.1
```

## Manejo de Errores

### Categorías

1. **Errores de Base de Datos**: Conexión, consultas inválidas, datos faltantes
2. **Errores RAG**: Sin documentos relevantes, fallos de embedding
3. **Errores LLM**: Rate limits, timeouts → fallback automático a siguiente modelo
4. **Errores de Herramientas**: Parámetros inválidos, timeouts de ejecución

### Estrategia

- Cada herramienta maneja sus propios errores y retorna mensajes descriptivos
- `ErrorHandler` centraliza el formateo de mensajes de error en español
- El agente continúa funcionando aunque una herramienta falle
- Fallback automático de modelos LLM

## Rendimiento

### Estrategia de Caché

| Tipo | TTL | Clave |
|------|-----|-------|
| Consultas de BD | 5 min | query + parámetros |
| Búsqueda RAG | 30 min | query + especialidad |
| Respuestas LLM | 5 min | query + hash de contexto |

### Optimizaciones
- Connection pooling para Supabase
- Lazy loading de componentes (VisualizationAgent)
- Truncamiento de contexto cuando excede límites de tokens

## Seguridad

- Prevención de SQL injection en DatabaseTool
- Sandbox para ejecución de código de visualización
- Validación de inputs con Pydantic
- Datos MIMIC-IV-ED anonimizados
- API keys en variables de entorno (nunca en código)
- Autenticación con Supabase Auth (JWT)

## Archivos del Sistema

```
services/unified_chat/
├── unified_agent.py          # Agente principal (orquestador)
├── config.py                 # Configuración del chat
├── document_manager.py       # Gestión de documentos
├── tools/
│   ├── database_tool.py      # Consultas MIMIC-IV-ED
│   ├── rag_tool.py           # Búsqueda RAG con augmentación
│   └── __init__.py
└── __init__.py

services/medical_agent/
├── llm_manager.py            # Gestión de LLM y fallback
├── prompt_manager.py         # Prompts y anti-alucinación
├── error_handler.py          # Manejo de errores
├── visualization_agent.py    # Generación de visualizaciones
├── visualization_selector.py # Selección automática de tipo
├── visualization_templates.py # Templates Plotly
├── code_executor.py          # Ejecución segura
├── tools/
│   ├── claude_adapter.py     # Clase base ClaudeToolAdapter
│   └── visualization_collaboration_tool.py
└── services/
    └── database_service.py   # Acceso a Supabase
```

---

**Versión**: 2.0
**Sistema**: ChatHCE - Chat Unificado
