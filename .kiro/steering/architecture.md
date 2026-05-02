# Arquitectura del Sistema - ChatHCE

## Visión General

ChatHCE sigue una arquitectura de capas con separación clara de responsabilidades. El sistema está centrado en el **Chat Unificado** que orquesta múltiples herramientas especializadas.

## Capas de la Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│                    Capa de Presentación                  │
│                  (Streamlit UI - main.py)                │
│  - unified_chat_interface.py (interfaz principal)        │
│  - components/ (sidebar, auth, document manager)         │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Capa de Aplicación                     │
│              (services/unified_chat/)                    │
│  - unified_agent.py (orquestador principal)              │
│  - document_manager.py (gestión de documentos)           │
│  - config.py (configuración del chat)                    │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Capa de Herramientas                  │
│            (services/unified_chat/tools/)                │
│  - database_tool.py (consultas MIMIC-IV-ED)              │
│  - rag_tool.py (búsqueda de documentos)                  │
│  - visualization_tool.py (generación de gráficas)        │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                   Capa de Servicios                      │
│                    (services/)                           │
│  - rag_service.py (RAG con Claude)                         │
│  - cache_manager.py (caché de respuestas)                │
│  - connection_pool_manager.py (pool de conexiones)       │
│  - llm_optimizer.py (optimización de LLM)                │
│  - medical_agent/ (agente médico y visualización)        │
│  - auth/ (autenticación y sesiones)                      │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                    Capa de Datos                         │
│  - Supabase (PostgreSQL con MIMIC-IV-ED + pgvector RAG)       │
│  - File Storage (documentos clínicos)                    │
└─────────────────────────────────────────────────────────┘
```

## Componentes Principales

### 1. Unified Chat Agent

**Ubicación**: `services/unified_chat/unified_agent.py`

**Responsabilidades**:
- Orquestar el flujo de consultas del usuario
- Analizar intención y seleccionar herramientas apropiadas
- Coordinar ejecución de múltiples herramientas
- Sintetizar respuestas integradas
- Mantener contexto conversacional

**Tecnología**: Claude (Anthropic) con LangChain

**Flujo de Procesamiento**:
```
Usuario → process_message()
    ↓
Analizar consulta con Claude
    ↓
Seleccionar herramientas (database/rag/viz)
    ↓
Ejecutar herramientas en paralelo/secuencial
    ↓
Sintetizar respuesta
    ↓
Formatear y retornar
```

### 2. Database Tool

**Ubicación**: `services/unified_chat/tools/database_tool.py`

**Responsabilidades**:
- Ejecutar consultas SQL en MIMIC-IV-ED
- Validar seguridad de consultas
- Formatear resultados para el agente
- Manejar errores de base de datos

**Tipos de Consultas**:
- `patient_summary`: Información completa del paciente
- `vital_signs`: Signos vitales y tendencias
- `diagnoses`: Diagnósticos con códigos ICD
- `medications`: Medicamentos administrados
- `custom`: Consultas SQL personalizadas (validadas)

**Seguridad**:
- Prevención de SQL injection
- Whitelist de operaciones (solo SELECT)
- Límite de filas retornadas
- Timeout de consultas

### 3. RAG Tool

**Ubicación**: `services/unified_chat/tools/rag_tool.py`

**Responsabilidades**:
- Búsqueda semántica en documentos clínicos
- Recuperar contexto relevante
- Formatear fuentes para citación
- Filtrar por especialidad

**Tecnología**: 
- Supabase pgvector para almacenamiento vectorial
- sentence-transformers para embeddings
- Claude API (Anthropic) para generación de respuestas

**Pipeline RAG**:
```
Query → Embedding → Vector Search → Retrieve Docs
    ↓
Rank by Relevance → Format Sources → Return Context
```

### 4. Visualization Tool

**Ubicación**: `services/unified_chat/tools/visualization_tool.py`

**Responsabilidades**:
- Generar código Python para visualizaciones
- Ejecutar código en sandbox seguro
- Crear gráficas con Plotly/Matplotlib
- Retornar imágenes o HTML interactivo

**Tipos de Visualizaciones**:
- Líneas (tendencias temporales)
- Barras (comparaciones)
- Scatter (correlaciones)
- Histogramas (distribuciones)
- Box plots (estadísticas)
- Heatmaps (matrices)
- Y más (16+ tipos)

### 5. RAG Service

**Ubicación**: `services/rag_service.py`

**Responsabilidades**:
- Indexar documentos clínicos
- Generar embeddings
- Realizar búsquedas vectoriales
- Gestionar colecciones en Supabase pgvector

**Configuración**:
```python
RAG_CONFIG = {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "storage": "supabase_pgvector",
    "collection_name": "clinical_guidelines",
    "search_type": "hybrid",
    "top_k": 5,
    "chunk_size": 1200,
    "chunk_overlap": 200
}
```

### 6. Cache Manager

**Ubicación**: `services/cache_manager.py`

**Responsabilidades**:
- Cachear respuestas de LLM
- Cachear embeddings
- Cachear resultados de consultas
- Gestionar TTL y limpieza

**Estrategia de Caché**:
- LRU (Least Recently Used)
- TTL configurable por tipo
- Límite de memoria
- Invalidación selectiva

### 7. Connection Pool Manager

**Ubicación**: `services/connection_pool_manager.py`

**Responsabilidades**:
- Pool de conexiones a Supabase
- Reutilización de conexiones
- Manejo de timeouts
- Recuperación de errores

**Configuración**:
```python
POOL_CONFIG = {
    "pool_size": 10,
    "max_overflow": 20,
    "timeout": 30,
    "recycle": 3600
}
```

## Flujo de Datos

### Consulta Simple (Solo Database)

```
Usuario: "Muestra datos del paciente 10014729"
    ↓
UnifiedChatAgent.process_message()
    ↓
Claude analiza → Selecciona database_tool
    ↓
DatabaseTool.execute(subject_id=10014729)
    ↓
Supabase query → Resultados
    ↓
Claude sintetiza respuesta en español
    ↓
UI muestra respuesta formateada
```

### Consulta Compleja (Database + RAG + Visualización)

```
Usuario: "Analiza signos vitales del paciente 10014729 según protocolos"
    ↓
UnifiedChatAgent.process_message()
    ↓
Claude analiza → Selecciona 3 herramientas
    ↓
┌─────────────┬──────────────┬─────────────────┐
│ Database    │ RAG          │ Visualization   │
│ Tool        │ Tool         │ Tool            │
└─────────────┴──────────────┴─────────────────┘
    ↓              ↓                ↓
Datos vitales  Protocolos      Gráfica
del paciente   de urgencias    de tendencias
    ↓              ↓                ↓
    └──────────────┴────────────────┘
                   ↓
    Claude sintetiza respuesta integrada
                   ↓
    UI muestra: texto + gráfica + fuentes
```

## Patrones de Diseño

### 1. Adapter Pattern
**Uso**: `ClaudeToolAdapter` para integrar herramientas con Claude
```python
class ClaudeToolAdapter:
    """Adapta herramientas al formato de Claude"""
    def to_claude_tool(self) -> Dict:
        """Convierte a formato de herramienta de Claude"""
        pass
```

### 2. Strategy Pattern
**Uso**: Diferentes estrategias de búsqueda RAG (similarity, MMR)
```python
class SearchStrategy:
    def search(self, query: str) -> List[Document]:
        pass

class SimilaritySearch(SearchStrategy):
    pass

class MMRSearch(SearchStrategy):
    pass
```

### 3. Factory Pattern
**Uso**: Creación de agentes y herramientas
```python
class AgentFactory:
    @staticmethod
    def create_unified_agent() -> UnifiedChatAgent:
        """Crea agente con todas las herramientas"""
        pass
```

### 4. Singleton Pattern
**Uso**: Settings, cache manager, connection pool
```python
class CacheManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
```

### 5. Observer Pattern
**Uso**: Monitoreo de performance y logging
```python
class PerformanceMonitor:
    def __init__(self):
        self.observers = []
    
    def notify(self, event: Dict):
        for observer in self.observers:
            observer.update(event)
```

## Decisiones de Arquitectura

### ¿Por qué Claude para el Agente?
- Mejor manejo de tool calling
- Límites de rate más generosos
- Prompts más eficientes (~3000 tokens vs ~6500)
- Mayor confiabilidad

### ¿Por qué Claude para RAG?
- Superior capacidad de razonamiento clínico
- Consistencia con el resto del sistema
- Mejor manejo de contexto largo
- Buena integración con LangChain

### ¿Por qué Separar Herramientas?
- Modularidad y mantenibilidad
- Testing independiente
- Reutilización en otros contextos
- Escalabilidad horizontal

### ¿Por qué Supabase pgvector para RAG?
- Integrado con la base de datos existente (Supabase)
- Búsqueda híbrida (vector + full-text) en una sola query SQL
- Sin dependencias locales adicionales
- Escalable y gestionado

### ¿Por qué Supabase?
- PostgreSQL completo
- Autenticación integrada
- API REST automática
- Escalable y gestionado

## Escalabilidad

### Horizontal
- Múltiples instancias de Streamlit
- Load balancer (nginx)
- Redis para caché compartido
- Supabase maneja múltiples conexiones

### Vertical
- Optimización de consultas SQL
- Índices en tablas MIMIC-IV-ED
- Cache de embeddings
- Connection pooling

### Límites Actuales
- ~100 usuarios concurrentes
- ~1000 documentos indexados
- ~10GB de datos vectoriales
- ~50 consultas/minuto por usuario

## Seguridad

### Autenticación
- Supabase Auth (JWT)
- Session management
- Role-based access control

### Validación
- SQL injection prevention
- Input sanitization
- Query complexity limits
- Rate limiting

### Datos
- Datos MIMIC-IV-ED anonimizados
- Encriptación en tránsito (HTTPS)
- Encriptación en reposo (Supabase)
- Logs sin PII

## Monitoreo

### Métricas Clave
- Tiempo de respuesta del agente
- Uso de herramientas (distribución)
- Errores por tipo
- Cache hit rate
- Uso de memoria
- Conexiones activas

### Logging
- Structured logging (JSON)
- Niveles: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Rotación de logs (10MB por archivo)
- Retención: 30 días

### Alertas
- Errores críticos → Email
- Performance degradation → Dashboard
- Límites de API → Notificación

## Dependencias Críticas

### Externas
- Claude API (Anthropic)
- Supabase (PostgreSQL + pgvector)

### Internas
- LangChain (framework de agentes)
- Streamlit (UI)
- Pydantic (validación)
- sentence-transformers (embeddings)

## Evolución Futura

### Corto Plazo
- Más tipos de visualizaciones
- Soporte para más formatos de documentos
- Mejoras en cache
- Optimización de prompts

### Medio Plazo
- API REST completa
- Integración con más LLMs
- Sistema de plugins para herramientas
- Dashboard de analytics

### Largo Plazo
- Multi-tenancy
- Despliegue en cloud
- Escalado automático
- ML para optimización de consultas

## Referencias

- **Documentación completa**: `docs/UNIFIED_CHAT_ARCHITECTURE.md`
- **Código fuente**: `services/unified_chat/`
- **Configuración**: `config/settings.py`
- **Tests**: `tests/integration/test_unified_chat/`
