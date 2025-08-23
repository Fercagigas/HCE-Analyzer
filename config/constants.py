
"""
Application constants
"""

# Application Information
APP_NAME = "HCE Analyzer Pro"
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
