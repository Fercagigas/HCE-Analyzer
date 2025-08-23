
"""
Configuración central del sistema HCE Analyzer con RAG
"""
import os
from pathlib import Path
from .constants import *

# ================================
# CONFIGURACIÓN GENERAL
# ================================
APP_NAME = "HCE Analyzer"
APP_TAGLINE = "Análisis Clínico Inteligente con IA"
APP_DESCRIPTION = "Sistema avanzado de análisis de historias clínicas con consultas RAG"
APP_ICON = "🏥"

# ================================
# CONFIGURACIÓN DE API KEYS
# ================================
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINFACEHUB_API_TOKEN", "")

# ================================
# CONFIGURACIÓN DE MODELOS
# ================================
MODEL_CONFIG = {
    "models": [
        "llama-3.3-70b-versatile",           # Modelo primario
        "llama-3.1-70b-versatile",          # Modelo secundario  
        "llama-3.1-8b-instant",             # Modelo terciario
        "llama3-70b-8192"                   # Modelo de fallback
    ],
    "max_tokens": 2048,
    "temperature": 0.7,
    "top_p": 0.9
}

# ================================
# CONFIGURACIÓN RAG
# ================================
RAG_CONFIG = {
    # Modelo de embeddings
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    
    # Configuración de ChromaDB
    "persist_directory": "./data/chroma_db",
    "collection_name": "clinical_guidelines",
    
    # Configuración de búsqueda
    "search_type": "mmr",  # "similarity" o "mmr"
    "top_k": 5,
    "fetch_k": 20,
    
    # Modelo LLM para RAG
    "llm_model": "llama-3.3-70b-versatile",
    
    # Configuración de segmentación
    "chunk_size": 1200,
    "chunk_overlap": 200,
    
    # Configuración de procesamiento
    "max_file_size_mb": 50,
    "supported_formats": [".pdf"],
    "ocr_enabled": True
}

# ================================
# LÍMITES DE USO
# ================================
RATE_LIMITS = {
    "daily_analyses": 15,
    "daily_rag_queries": 50,
    "max_file_uploads_per_day": 10,
    "max_session_duration_hours": 8
}

# ================================
# CONFIGURACIÓN DE DIRECTORIOS
# ================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
LOGS_DIR = DATA_DIR / "logs"
TEMP_DIR = DATA_DIR / "temp"

# Crear directorios si no existen
for directory in [DATA_DIR, UPLOADS_DIR, LOGS_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ================================
# CONFIGURACIÓN DE LOGGING
# ================================
LOGGING_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    "file": str(LOGS_DIR / "hce_analyzer.log"),
    "max_bytes": 10 * 1024 * 1024,  # 10MB
    "backup_count": 5
}

# ================================
# CONFIGURACIÓN DE STREAMLIT
# ================================
STREAMLIT_CONFIG = {
    "page_title": f"{APP_ICON} {APP_NAME}",
    "page_icon": APP_ICON,
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}

# ================================
# CONFIGURACIÓN DE ESPECIALIDADES MÉDICAS
# ================================
MEDICAL_SPECIALTIES = {
    "urgencias": {
        "name": "Urgencias y Emergencias",
        "keywords": ["urgencia", "emergencia", "trauma", "shock", "reanimación"],
        "color": "#FF5722"
    },
    "cardiologia": {
        "name": "Cardiología",
        "keywords": ["corazón", "cardíaco", "arritmia", "infarto", "hipertensión"],
        "color": "#E91E63"
    },
    "neurologia": {
        "name": "Neurología",
        "keywords": ["cerebro", "neurológico", "ACV", "epilepsia", "cefalea"],
        "color": "#9C27B0"
    },
    "pediatria": {
        "name": "Pediatría",
        "keywords": ["niño", "pediátrico", "lactante", "adolescente", "neonato"],
        "color": "#2196F3"
    },
    "ginecologia": {
        "name": "Ginecología y Obstetricia",
        "keywords": ["ginecológico", "obstétrico", "embarazo", "parto", "menstrual"],
        "color": "#FF9800"
    },
    "traumatologia": {
        "name": "Traumatología",
        "keywords": ["fractura", "ortopédico", "hueso", "articulación", "lesión"],
        "color": "#795548"
    },
    "medicina_interna": {
        "name": "Medicina Interna",
        "keywords": ["interno", "sistémico", "diabetes", "endocrino", "metabólico"],
        "color": "#607D8B"
    },
    "cirugia": {
        "name": "Cirugía General",
        "keywords": ["quirúrgico", "operación", "cirugía", "postoperatorio", "anestesia"],
        "color": "#4CAF50"
    }
}

# ================================
# TIPOS DE DOCUMENTOS CLÍNICOS
# ================================
DOCUMENT_TYPES = {
    "guia_clinica": {
        "name": "Guía Clínica",
        "description": "Guías de práctica clínica basadas en evidencia",
        "icon": "📋"
    },
    "protocolo": {
        "name": "Protocolo",
        "description": "Protocolos de actuación y procedimientos",
        "icon": "📝"
    },
    "manual": {
        "name": "Manual",
        "description": "Manuales de procedimientos y técnicas",
        "icon": "📖"
    },
    "algoritmo": {
        "name": "Algoritmo",
        "description": "Algoritmos de decisión clínica",
        "icon": "🔄"
    },
    "consenso": {
        "name": "Consenso",
        "description": "Documentos de consenso de sociedades médicas",
        "icon": "🤝"
    }
}

# ================================
# CONFIGURACIÓN DE ANÁLISIS
# ================================
ANALYSIS_TYPES = {
    "blood_test": {
        "name": "Análisis de Sangre",
        "description": "Interpretación de hemogramas y bioquímica sanguínea",
        "icon": "🩸",
        "prompt_key": "blood_analysis"
    },
    "imaging": {
        "name": "Estudios de Imagen",
        "description": "Interpretación de radiografías, TAC, RMN",
        "icon": "🔬",
        "prompt_key": "imaging_analysis"
    },
    "general_report": {
        "name": "Reporte General",
        "description": "Análisis de reportes médicos generales",
        "icon": "📄",
        "prompt_key": "general_analysis"
    },
    "pathology": {
        "name": "Anatomía Patológica",
        "description": "Interpretación de biopsias y citologías",
        "icon": "🔬",
        "prompt_key": "pathology_analysis"
    }
}

# ================================
# PROMPTS ESPECIALIZADOS
# ================================
CLINICAL_PROMPTS = {
    "blood_analysis": """
Eres un especialista en medicina de laboratorio. Analiza los siguientes resultados de análisis de sangre y proporciona:

1. **Resumen Ejecutivo**: Estado general de salud basado en los resultados
2. **Análisis por Sistemas**: Evaluación de cada sistema orgánico
3. **Valores Anómalos**: Explicación detallada de valores fuera de rango
4. **Posibles Diagnósticos**: Condiciones que podrían explicar los hallazgos
5. **Recomendaciones**: Estudios adicionales y seguimiento sugerido
6. **Nivel de Urgencia**: Clasificación de prioridad médica

Usa terminología médica precisa pero incluye explicaciones comprensibles.
""",
    
    "imaging_analysis": """
Eres un radiólogo especialista. Interpreta el siguiente reporte de imagen y proporciona:

1. **Hallazgos Principales**: Descripción sistemática de los hallazgos
2. **Interpretación Radiológica**: Significado clínico de las imágenes
3. **Diagnóstico Diferencial**: Posibles diagnósticos a considerar
4. **Correlación Clínica**: Necesidad de correlación con síntomas
5. **Recomendaciones**: Estudios complementarios o seguimiento
6. **Urgencia**: Nivel de prioridad de los hallazgos

Mantén la terminología radiológica estándar y sé preciso en las descripciones.
""",
    
    "general_analysis": """
Eres un médico clínico experimentado. Analiza el siguiente reporte médico y proporciona:

1. **Interpretación Clínica**: Significado médico de los hallazgos
2. **Síntesis Diagnóstica**: Integración de todos los datos
3. **Plan de Manejo**: Recomendaciones terapéuticas
4. **Pronóstico**: Expectativas de evolución
5. **Seguimiento**: Plan de monitoreo y controles
6. **Educación al Paciente**: Puntos clave para explicar

Enfócate en un análisis integral y basado en evidencia médica.
""",
    
    "rag_clinical_query": """
Basándote en las guías clínicas hospitalarias proporcionadas, responde la consulta médica de manera estructurada:

1. **Respuesta Directa**: Respuesta clara y concisa a la consulta
2. **Fundamento Científico**: Base de evidencia de la recomendación
3. **Protocolo Específico**: Pasos detallados del procedimiento
4. **Consideraciones Especiales**: Factores adicionales a considerar
5. **Contraindicaciones**: Situaciones donde no aplicar
6. **Referencias**: Guías y documentos consultados

Mantén un enfoque clínico profesional y cita las fuentes utilizadas.
"""
}

# ================================
# CONFIGURACIÓN DE SEGURIDAD
# ================================
SECURITY_CONFIG = {
    "max_upload_size_mb": 50,
    "allowed_file_types": [".pdf"],
    "scan_uploads": True,
    "encrypt_sensitive_data": True,
    "session_timeout_minutes": 480,  # 8 horas
    "max_failed_logins": 5
}

# ================================
# CONFIGURACIÓN DE CACHE
# ================================
CACHE_CONFIG = {
    "enable_caching": True,
    "cache_ttl_seconds": 3600,  # 1 hora
    "max_cache_size_mb": 100,
    "cache_embeddings": True,
    "cache_llm_responses": False  # Por privacidad médica
}

# ================================
# CONFIGURACIÓN DE MONITOREO
# ================================
MONITORING_CONFIG = {
    "enable_analytics": True,
    "track_usage": True,
    "log_queries": True,
    "performance_monitoring": True,
    "error_reporting": True
}

# ================================
# MENSAJES DE LA INTERFAZ
# ================================
UI_MESSAGES = {
    "welcome": {
        "title": f"Bienvenido a {APP_NAME}",
        "subtitle": "Tu asistente inteligente para análisis clínico",
        "description": "Analiza historias clínicas y consulta guías médicas con IA avanzada"
    },
    "errors": {
        "no_session": "No hay sesión activa. Por favor, crea una nueva sesión.",
        "auth_required": "Debes iniciar sesión para acceder a esta funcionalidad.",
        "file_too_large": "El archivo es demasiado grande. Máximo permitido: {max_size}MB",
        "invalid_file_type": "Tipo de archivo no soportado. Solo se permiten: {types}",
        "processing_error": "Error procesando la solicitud. Inténtalo nuevamente.",
        "rate_limit_exceeded": "Límite de uso diario alcanzado. Inténtalo mañana."
    },
    "success": {
        "file_uploaded": "Archivo cargado exitosamente",
        "document_processed": "Documento procesado y añadido a la base de conocimiento",
        "analysis_completed": "Análisis completado exitosamente",
        "session_created": "Nueva sesión creada"
    },
    "info": {
        "processing": "Procesando solicitud...",
        "uploading": "Cargando archivo...",
        "analyzing": "Analizando datos clínicos...",
        "searching": "Buscando en guías clínicas..."
    }
}

# ================================
# VALIDACIÓN DE CONFIGURACIÓN
# ================================
def validate_config():
    """Valida la configuración del sistema"""
    errors = []
    warnings = []
    
    # Verificar API keys obligatorias
    if not GROQ_API_KEY:
        errors.append("GROQ_API_KEY no configurada")
    
    if not SUPABASE_URL:
        errors.append("SUPABASE_URL no configurada")
    
    if not SUPABASE_KEY:
        errors.append("SUPABASE_KEY no configurada")
    
    # Verificar API keys opcionales
    if not HUGGINGFACE_API_TOKEN:
        warnings.append("HUGGINFACEHUB_API_TOKEN no configurada - Los modelos de HuggingFace pueden tener limitaciones de rate limiting")
    
    # Verificar directorios
    for directory in [DATA_DIR, UPLOADS_DIR, LOGS_DIR, TEMP_DIR]:
        if not directory.exists():
            errors.append(f"Directorio no existe: {directory}")
    
    return {"errors": errors, "warnings": warnings}

# ================================
# CONFIGURACIÓN DE DESARROLLO
# ================================
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False").lower() == "true"

if DEVELOPMENT_MODE:
    # Configuraciones para desarrollo
    RATE_LIMITS["daily_analyses"] = 100
    RATE_LIMITS["daily_rag_queries"] = 200
    LOGGING_CONFIG["level"] = "DEBUG"

