"""
Configuración central del sistema HCE Analyzer - Archivo de compatibilidad

Este archivo re-exporta constantes desde constants.py y settings.py
para mantener compatibilidad con código existente.

NOTA: Para nuevo código, importar directamente desde:
- config.constants para constantes de aplicación
- config.settings para configuración dinámica
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Re-exportar constantes de aplicación
from .constants import (
    APP_NAME,
    APP_TAGLINE,
    APP_DESCRIPTION,
    APP_ICON,
    APP_VERSION,
)

# ================================
# CONFIGURACIÓN DE API KEYS
# ================================
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
HUGGINGFACE_API_TOKEN = os.getenv("HUGGINFACEHUB_API_TOKEN", "")

# ================================
# CONFIGURACIÓN DE MODELOS (Legacy - usar settings.rag para nuevo código)
# ================================
MODEL_CONFIG = {
    "models": [
        "claude-haiku-4-5-20251001",
        "claude-sonnet-4-5-20250929",
        "claude-opus-4-20250514",
    ],
    "max_tokens": 2048,
    "temperature": 0.7,
    "top_p": 0.9
}

# ================================
# CONFIGURACIÓN RAG
# ================================
RAG_CONFIG = {
    "embedding_model": "sentence-transformers/all-MiniLM-L6-v2",
    "storage": "supabase_pgvector",
    "collection_name": "clinical_guidelines",
    "search_type": "hybrid",
    "top_k": 3,
    "fetch_k": 20,
    "llm_model": "claude-haiku-4-5-20251001",
    "chunk_size": 2400,        # was 1200 — larger pre-split chunks for DocumentProcessor
    "chunk_overlap": 400,      # was 200
    "parent_chunk_size": 3000, # was 1500 — richer context returned to LLM
    "child_chunk_size": 800,   # was 400  — more meaningful search units
    "max_file_size_mb": 50,
    "supported_formats": [".pdf"],
    "ocr_enabled": True,
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
BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "storage"
LOGS_DIR = BASE_DIR / "logs"
TEMP_DIR = DATA_DIR / "temp"

# Crear directorios si no existen
for directory in [DATA_DIR, UPLOADS_DIR, LOGS_DIR, TEMP_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

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
# TIPOS DE ANÁLISIS
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
# CONFIGURACIÓN DE DESARROLLO
# ================================
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
DEVELOPMENT_MODE = os.getenv("DEVELOPMENT_MODE", "False").lower() == "true"

if DEVELOPMENT_MODE:
    RATE_LIMITS["daily_analyses"] = 100
    RATE_LIMITS["daily_rag_queries"] = 200
