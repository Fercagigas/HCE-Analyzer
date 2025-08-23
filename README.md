# 🏥 HCE Analyzer - Sistema de Análisis Clínico Inteligente con RAG

## 📋 Descripción

HCE Analyzer es un sistema avanzado de análisis de historias clínicas que combina inteligencia artificial con capacidades RAG (Retrieval-Augmented Generation) para proporcionar análisis médicos precisos y consultas sobre guías clínicas hospitalarias.

### ✨ Características Principales

- **🔬 Análisis de Historias Clínicas**: Interpretación inteligente de reportes médicos, análisis de sangre, estudios de imagen y más
- **💬 Chat Clínico Especializado**: Consultas sobre protocolos médicos y guías clínicas del hospital
- **📚 Sistema RAG Integrado**: Base de conocimiento con guías clínicas indexadas y búsquedas semánticas
- **🤖 Multi-Modelo IA**: Sistema de cascada con múltiples modelos LLM para máxima disponibilidad
- **🔐 Autenticación Segura**: Sistema completo de usuarios con Supabase
- **📊 Interfaz Intuitiva**: Aplicación web moderna desarrollada con Streamlit

## 🏗️ Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                    HCE Analyzer + RAG                           │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (Streamlit)                                           │
│  ├── Análisis de Reportes                                       │
│  ├── Chat Clínico RAG                                          │
│  └── Gestión de Documentos                                     │
├─────────────────────────────────────────────────────────────────┤
│  Capa de Servicios                                             │
│  ├── AI Service (Análisis)                                     │
│  ├── RAG Service (Consultas)                                   │
│  └── Document Service (Procesamiento)                          │
├─────────────────────────────────────────────────────────────────┤
│  Capa de Agentes                                               │
│  ├── Analysis Agent (HCE)                                      │
│  ├── RAG Agent (Guías)                                         │
│  └── Clinical Chat Agent (Integrado)                           │
├─────────────────────────────────────────────────────────────────┤
│  Capa de Datos                                                 │
│  ├── Supabase (Usuarios/Sesiones)                             │
│  ├── ChromaDB (Vector Store)                                   │
│  └── File Storage (Documentos)                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 🚀 Instalación y Configuración

### Prerrequisitos

- Python 3.8 o superior
- pip (gestor de paquetes de Python)
- Cuenta en Groq (para modelos LLM)
- Cuenta en Supabase (para autenticación y base de datos)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/tu-usuario/hce-analyzer-rag.git
cd hce-analyzer-rag
```

### 2. Crear Entorno Virtual

```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz del proyecto:

```env
# API Keys
GROQ_API_KEY=tu_api_key_de_groq
SUPABASE_URL=tu_url_de_supabase
SUPABASE_KEY=tu_key_de_supabase

# HuggingFace API Token (Opcional - mejora el rendimiento de embeddings)
HUGGINFACEHUB_API_TOKEN=tu_token_de_huggingface

# Configuración opcional
DEBUG=False
DEVELOPMENT_MODE=False
```

### 5. Configurar Base de Datos (Supabase)

Ejecuta el siguiente SQL en tu proyecto de Supabase:

```sql
-- Tabla de usuarios
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    specialty TEXT,
    medical_license TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de sesiones de chat
CREATE TABLE chat_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de mensajes
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID REFERENCES chat_sessions(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de documentos clínicos (opcional)
CREATE TABLE clinical_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filename TEXT NOT NULL,
    title TEXT,
    document_type TEXT,
    specialty TEXT,
    upload_date TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    processed BOOLEAN DEFAULT FALSE,
    file_path TEXT,
    metadata JSONB
);

-- Índices para mejor rendimiento
CREATE INDEX idx_chat_sessions_user_id ON chat_sessions(user_id);
CREATE INDEX idx_chat_messages_session_id ON chat_messages(session_id);
CREATE INDEX idx_clinical_documents_specialty ON clinical_documents(specialty);
```

### 6. Ejecutar la Aplicación

```bash
streamlit run app.py
```

La aplicación estará disponible en `http://localhost:8501`

## 📖 Guía de Uso

### 🔐 Autenticación

1. **Registro**: Crea una cuenta nueva proporcionando:

   - Email profesional
   - Contraseña segura
   - Nombre completo
   - Especialidad médica
   - Número de colegiatura

2. **Inicio de Sesión**: Accede con tu email y contraseña

### 📊 Análisis de Historias Clínicas

1. **Crear Nueva Sesión**: Desde el inicio, selecciona "Nueva Sesión de Análisis"
2. **Subir Documento**:
   - Sube archivos PDF de historias clínicas
   - O introduce texto directamente
3. **Seleccionar Tipo**: Elige el tipo de análisis apropiado:
   - Análisis de Sangre
   - Estudios de Imagen
   - Reporte General
   - Anatomía Patológica
4. **Configurar Opciones**: Ajusta nivel de detalle y especialidad
5. **Obtener Resultados**: Recibe análisis detallado con interpretación médica

### 💬 Chat Clínico

1. **Iniciar Chat**: Selecciona "Chat Clínico" desde el menú
2. **Hacer Consultas**: Pregunta sobre:
   - Protocolos de actuación
   - Guías clínicas
   - Recomendaciones terapéuticas
   - Criterios diagnósticos
3. **Filtrar por Especialidad**: Enfoca las búsquedas en tu área
4. **Ver Fuentes**: Revisa las guías consultadas para cada respuesta

### 📚 Gestión de Documentos

1. **Añadir Contexto**: Accede al gestor de documentos
2. **Subir Guías**: Carga PDFs de guías clínicas y protocolos
3. **Clasificar**: Asigna especialidad y tipo de documento
4. **Procesar**: El sistema indexa automáticamente el contenido
5. **Gestionar**: Visualiza, busca y elimina documentos existentes

## 🔧 Configuración Avanzada

### Modelos de IA

El sistema utiliza múltiples modelos LLM con fallback automático:

1. **Primario**: `llama-3.3-70b-versatile`
2. **Secundario**: `llama-3.1-70b-versatile`
3. **Terciario**: `llama-3.1-8b-instant`
4. **Fallback**: `llama3-70b-8192`

### Configuración RAG

```python
RAG_CONFIG = {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "persist_directory": "./data/chroma_db",
    "collection_name": "clinical_guidelines",
    "search_type": "mmr",  # "similarity" o "mmr"
    "top_k": 5,
    "chunk_size": 1200,
    "chunk_overlap": 200
}
```

### Límites de Uso

```python
RATE_LIMITS = {
    "daily_analyses": 15,
    "daily_rag_queries": 50,
    "max_file_uploads_per_day": 10,
    "max_session_duration_hours": 8
}
```

## 📁 Estructura del Proyecto

```
hce_analyzer_rag/
├── app.py                      # Aplicación principal Streamlit
├── config.py                   # Configuración central
├── requirements.txt            # Dependencias Python
├── README.md                   # Documentación
├── agents.py                   # Sistema de agentes IA
├── rag_service.py             # Servicio RAG principal
├── document_processor.py      # Procesamiento de PDFs
├── vector_store_manager.py    # Gestión de ChromaDB
├── clinical_chat.py           # Chat clínico especializado
├── utils.py                   # Utilidades generales
├── auth/                      # Módulo de autenticación
│   ├── __init__.py
│   ├── auth_service.py        # Servicio de autenticación
│   └── session_manager.py     # Gestión de sesiones
├── components/                # Componentes de UI
│   ├── __init__.py
│   ├── auth_pages.py          # Páginas de login/registro
│   ├── sidebar.py             # Barra lateral
│   ├── analysis_form.py       # Formulario de análisis
│   ├── document_manager.py    # Gestor de documentos
│   └── footer.py              # Footer de la aplicación
└── data/                      # Directorio de datos
    ├── chroma_db/             # Base de datos vectorial
    ├── uploads/               # Archivos subidos
    ├── logs/                  # Logs del sistema
    └── temp/                  # Archivos temporales
```

## 🔒 Seguridad y Privacidad

### Medidas de Seguridad

- **Autenticación Robusta**: Sistema completo con Supabase Auth
- **Encriptación**: Datos sensibles encriptados en tránsito y reposo
- **Validación**: Validación exhaustiva de inputs y archivos
- **Rate Limiting**: Límites de uso para prevenir abuso
- **Logging**: Registro detallado de actividades para auditoría

### Cumplimiento Médico

- **HIPAA Compliance**: Protección de información médica
- **Anonimización**: Enmascaramiento de datos sensibles
- **Retención**: Políticas de retención de datos configurables
- **Backup**: Respaldo automático de información crítica

## 🧪 Testing

### Ejecutar Tests

```bash
# Tests unitarios
pytest tests/

# Tests de integración
pytest tests/integration/

# Tests de cobertura
pytest --cov=. tests/
```

### Usuarios de Demo

Para pruebas, puedes usar estos usuarios:

- **Email**: `demo@hospital.com` | **Password**: `demo123`
- **Email**: `admin@hce.com` | **Password**: `admin123`

## 📊 Monitoreo y Analytics

### Métricas Disponibles

- Número de análisis realizados
- Consultas RAG procesadas
- Documentos indexados
- Tiempo de respuesta promedio
- Usuarios activos
- Errores y excepciones

### Logs

Los logs se almacenan en `./data/logs/hce_analyzer.log` con rotación automática.

## 🤝 Contribución

### Cómo Contribuir

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. Commit tus cambios (`git commit -am 'Añadir nueva funcionalidad'`)
4. Push a la rama (`git push origin feature/nueva-funcionalidad`)
5. Crea un Pull Request

### Estándares de Código

- Seguir PEP 8 para Python
- Documentar funciones y clases
- Incluir tests para nuevas funcionalidades
- Mantener cobertura de tests > 80%

## 🐛 Solución de Problemas

### Problemas Comunes

**Error: "GROQ_API_KEY no configurada"**

- Solución: Configura la variable de entorno en el archivo `.env`

**Error: "ChromaDB no inicializado"**

- Solución: Verifica que el directorio `./data/chroma_db` tenga permisos de escritura

**Error: "Supabase connection failed"**

- Solución: Verifica las credenciales de Supabase en `.env`

**Análisis muy lento**

- Solución: Verifica la conexión a internet y el estado de los servicios de Groq

### Logs de Debug

Para habilitar logs detallados:

```bash
export DEBUG=True
streamlit run app.py
```

---
