# ChatHCE - Visión General del Proyecto

## Descripción

ChatHCE es un sistema avanzado de análisis clínico inteligente especializado en datos del Servicio de Urgencias. Combina inteligencia artificial con capacidades RAG (Retrieval-Augmented Generation) para proporcionar análisis de datos médicos del dataset MIMIC-IV-ED.

## Propósito

- **Análisis de Datos de Urgencias**: Consultas inteligentes sobre datos del Servicio de Urgencias hospitalarias
- **Búsqueda de Guías Clínicas**: Acceso a protocolos y documentos médicos mediante RAG
- **Visualizaciones Dinámicas**: Generación automática de gráficas médicas
- **Chat Unificado**: Interfaz única que integra todas las capacidades del sistema

## Características Principales

### 🎯 Chat Unificado
- Interfaz única para todas las consultas
- Selección automática de herramientas (Database, RAG, Visualización)
- Respuestas integradas de múltiples fuentes
- Conversaciones contextuales en español

### 🏥 Acceso a MIMIC-IV-ED
- Datos de pacientes de urgencias
- Signos vitales y triaje
- Diagnósticos con códigos ICD
- Medicamentos y administración
- Estancias y disposiciones

### 📚 Sistema RAG
- Indexación de documentos clínicos (PDF, DOCX, TXT)
- Búsqueda semántica con Supabase pgvector
- Embeddings con sentence-transformers
- Citación de fuentes

### 📊 Visualizaciones
- Generación dinámica con Plotly
- Código Python generado por IA
- Ejecución segura en sandbox
- 16+ tipos de gráficas

## Stack Tecnológico

### Backend
- **Python 3.8+**: Lenguaje principal
- **Streamlit**: Framework web
- **FastAPI**: API REST (opcional)
- **Supabase**: Base de datos PostgreSQL + pgvector (RAG)

### IA y ML
- **Claude (Anthropic)**: Agente médico principal y sistema RAG
- **LangChain**: Framework de agentes
- **sentence-transformers**: Embeddings
- **tiktoken**: Conteo de tokens

### Procesamiento
- **pandas/numpy**: Análisis de datos
- **plotly/matplotlib**: Visualizaciones
- **pypdf2/python-docx**: Procesamiento de documentos

## Arquitectura de Alto Nivel

```
Usuario → Streamlit UI → Unified Chat Agent (Claude)
                              ↓
                    ┌─────────┼─────────┐
                    ↓         ↓         ↓
              Database    RAG Tool   Viz Tool
                Tool        ↓           ↓
                 ↓      Supabase    Plotly
                        pgvector
              Supabase
            (MIMIC-IV-ED)
```

## Estructura de Directorios

```
hce-analyzer-pro/
├── config/          # Configuración (settings.py, constants.py)
├── services/        # Lógica de negocio
│   ├── unified_chat/    # Sistema de chat unificado
│   ├── medical_agent/   # Agente médico y visualización
│   ├── auth/            # Autenticación
│   └── *.py             # Servicios compartidos
├── ui/              # Interfaz Streamlit
├── data/            # Datos y almacenamiento
├── docs/            # Documentación
├── tests/           # Pruebas
└── main.py          # Punto de entrada
```

## Flujo de Trabajo Típico

1. **Usuario hace consulta** en el Chat Unificado
2. **Agente Claude analiza** la consulta
3. **Selecciona herramientas** apropiadas:
   - Database Tool para datos de pacientes
   - RAG Tool para guías clínicas
   - Visualization Tool para gráficas
4. **Ejecuta herramientas** y obtiene resultados
5. **Sintetiza respuesta** integrando toda la información
6. **Muestra resultado** con visualizaciones y fuentes

## Principios de Diseño

### Simplicidad
- Una sola interfaz para todo (Chat Unificado)
- Selección automática de herramientas
- Sin cambio de modos

### Inteligencia
- Comprensión de lenguaje natural en español
- Contexto conversacional
- Respuestas integradas

### Seguridad
- Validación de consultas SQL
- Sandbox para ejecución de código
- Autenticación con Supabase
- Datos anonimizados (MIMIC-IV-ED)

### Performance
- Cache de respuestas LLM
- Connection pooling
- Optimización de prompts
- Índices de base de datos

## Usuarios Objetivo

- **Médicos de Urgencias**: Análisis rápido de datos de pacientes
- **Investigadores**: Análisis de datos MIMIC-IV-ED
- **Estudiantes de Medicina**: Aprendizaje con datos reales
- **Administradores**: Análisis de métricas de urgencias

## Estado del Proyecto

- **Versión**: 2.0.0
- **Estado**: Producción
- **Última actualización**: Noviembre 2025
- **Sistema principal**: Chat Unificado (reemplaza interfaces legacy)

## Referencias Clave

- **README.md**: Documentación completa de instalación y uso
- **docs/UNIFIED_CHAT_ARCHITECTURE.md**: Arquitectura del chat unificado
- **docs/INDEX.md**: Índice de toda la documentación
- **config/settings.py**: Configuración completa del sistema

## Notas para el Asistente AI

- El sistema está en español (interfaz y respuestas)
- Priorizar el Chat Unificado sobre componentes legacy
- Claude API para agente médico y RAG
- MIMIC-IV-ED es el dataset principal (datos de urgencias)
- Siempre validar consultas SQL por seguridad
- Citar fuentes en respuestas RAG
