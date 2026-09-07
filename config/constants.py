
"""
Constantes de aplicacion (unico modulo de constantes; config.config se retiro en Fase 1).
"""

# Application Information
APP_NAME = "ChatHCE"
APP_TAGLINE = "Análisis Clínico Inteligente con IA"
APP_DESCRIPTION = "Sistema avanzado de análisis de historias clínicas médicas con inteligencia artificial"
APP_ICON = "🏥"
APP_VERSION = "2.0.0"

# UI Constants
SIDEBAR_WIDTH = 300
MAIN_CONTENT_WIDTH = 800
FOOTER_HEIGHT = 60

# Analysis Constants
MAX_FILE_SIZE_MB = 10
SUPPORTED_FILE_TYPES = ['pdf', 'txt', 'docx', 'doc']
MAX_ANALYSIS_TIME_SECONDS = 300

# Cache Constants
DEFAULT_CACHE_TTL = 3600  # 1 hour
ANALYSIS_CACHE_TTL = 7200  # 2 hours

# Pagination Constants
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

# Alert Constants
ALERT_RETENTION_DAYS = 90
MAX_ALERTS_PER_PAGE = 50

# Backup Constants
BACKUP_RETENTION_DAYS = 30
MAX_BACKUP_SIZE_GB = 10

# Rate Limiting
DEFAULT_RATE_LIMIT = 60  # requests per minute
BURST_RATE_LIMIT = 100

# Security Constants
SESSION_TIMEOUT_HOURS = 8
MAX_LOGIN_ATTEMPTS = 5
PASSWORD_MIN_LENGTH = 8

# Medical Constants
CRITICAL_LAB_VALUES = {
    'glucose': (70, 400),  # mg/dL
    'systolic_bp': (90, 180),  # mmHg
    'heart_rate': (60, 100),  # bpm
    'temperature': (96.8, 100.4)  # °F
}

HIGH_RISK_CONDITIONS = [
    'diabetes', 'hypertension', 'heart disease', 'stroke',
    'cancer', 'kidney disease', 'liver disease'
]

DRUG_INTERACTIONS = [
    ('warfarin', 'aspirin'),
    ('metformin', 'contrast'),
    ('digoxin', 'furosemide'),
    ('ace_inhibitor', 'potassium'),
    ('statin', 'fibrate')
]


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
