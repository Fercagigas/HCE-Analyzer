
"""
Utilidades y funciones helper para HCE Analyzer
"""
import os
import re
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple, Union
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil
import json
import base64

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FileUtils:
    """Utilidades para manejo de archivos"""
    
    @staticmethod
    def validate_file(file_path: str, max_size_mb: int = 50, allowed_extensions: List[str] = None) -> Dict[str, Any]:
        """Valida un archivo antes del procesamiento"""
        if allowed_extensions is None:
            allowed_extensions = ['.pdf']
        
        try:
            file_path = Path(file_path)
            
            result = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'info': {}
            }
            
            # Verificar existencia
            if not file_path.exists():
                result['valid'] = False
                result['errors'].append("Archivo no encontrado")
                return result
            
            # Verificar extensión
            if file_path.suffix.lower() not in allowed_extensions:
                result['valid'] = False
                result['errors'].append(f"Extensión no permitida. Permitidas: {allowed_extensions}")
                return result
            
            # Verificar tamaño
            file_size = file_path.stat().st_size
            file_size_mb = file_size / (1024 * 1024)
            
            result['info']['size_bytes'] = file_size
            result['info']['size_mb'] = round(file_size_mb, 2)
            
            if file_size_mb > max_size_mb:
                result['valid'] = False
                result['errors'].append(f"Archivo muy grande ({file_size_mb:.1f}MB). Máximo: {max_size_mb}MB")
            
            # Verificar si es muy pequeño
            if file_size < 1024:  # 1KB
                result['warnings'].append("Archivo muy pequeño, podría estar vacío")
            
            # Información adicional
            result['info']['name'] = file_path.name
            result['info']['extension'] = file_path.suffix
            result['info']['modified'] = datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
            
            return result
            
        except Exception as e:
            return {
                'valid': False,
                'errors': [f"Error validando archivo: {str(e)}"],
                'warnings': [],
                'info': {}
            }
    
    @staticmethod
    def generate_safe_filename(filename: str, max_length: int = 100) -> str:
        """Genera un nombre de archivo seguro"""
        # Remover caracteres peligrosos
        safe_chars = re.sub(r'[^\w\s\-_\.]', '', filename)
        
        # Reemplazar espacios con guiones bajos
        safe_chars = re.sub(r'\s+', '_', safe_chars)
        
        # Limitar longitud
        if len(safe_chars) > max_length:
            name, ext = os.path.splitext(safe_chars)
            safe_chars = name[:max_length-len(ext)] + ext
        
        return safe_chars
    
    @staticmethod
    def create_temp_file(content: bytes, suffix: str = '.tmp') -> str:
        """Crea un archivo temporal"""
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
                temp_file.write(content)
                return temp_file.name
        except Exception as e:
            logger.error(f"Error creando archivo temporal: {e}")
            raise
    
    @staticmethod
    def cleanup_temp_files(temp_dir: str, max_age_hours: int = 24):
        """Limpia archivos temporales antiguos"""
        try:
            temp_path = Path(temp_dir)
            if not temp_path.exists():
                return
            
            cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
            
            for file_path in temp_path.iterdir():
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        logger.info(f"Archivo temporal eliminado: {file_path.name}")
                        
        except Exception as e:
            logger.error(f"Error limpiando archivos temporales: {e}")
    
    @staticmethod
    def get_file_hash(file_path: str) -> str:
        """Calcula hash MD5 de un archivo"""
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"Error calculando hash: {e}")
            return ""

class TextUtils:
    """Utilidades para procesamiento de texto"""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """Limpia y normaliza texto"""
        if not text:
            return ""
        
        # Remover caracteres de control
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x84\x86-\x9f]', '', text)
        
        # Normalizar espacios en blanco
        text = re.sub(r'\s+', ' ', text)
        
        # Remover espacios al inicio y final
        text = text.strip()
        
        return text
    
    @staticmethod
    def extract_medical_terms(text: str) -> List[str]:
        """Extrae términos médicos del texto"""
        # Patrones comunes de términos médicos
        medical_patterns = [
            r'\b\w*itis\b',  # Inflamaciones
            r'\b\w*osis\b',  # Condiciones
            r'\b\w*emia\b',  # Condiciones sanguíneas
            r'\b\w*pathy\b', # Enfermedades
            r'\b\w*graphy\b', # Estudios
            r'\b\w*scopy\b',  # Procedimientos
        ]
        
        terms = []
        text_lower = text.lower()
        
        for pattern in medical_patterns:
            matches = re.findall(pattern, text_lower)
            terms.extend(matches)
        
        # Remover duplicados y ordenar
        return sorted(list(set(terms)))
    
    @staticmethod
    def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
        """Trunca texto a una longitud máxima"""
        if len(text) <= max_length:
            return text
        
        return text[:max_length - len(suffix)] + suffix
    
    @staticmethod
    def format_medical_text(text: str) -> str:
        """Formatea texto médico para mejor legibilidad"""
        if not text:
            return ""
        
        # Capitalizar después de puntos
        text = re.sub(r'(\. )([a-z])', lambda m: m.group(1) + m.group(2).upper(), text)
        
        # Formatear números con unidades
        text = re.sub(r'(\d+)\s*(mg|ml|g|kg|mmHg|bpm)', r'\1 \2', text)
        
        # Formatear rangos
        text = re.sub(r'(\d+)\s*-\s*(\d+)', r'\1-\2', text)
        
        return text

class ValidationUtils:
    """Utilidades para validación de datos"""
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Valida formato de email"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_medical_id(medical_id: str) -> bool:
        """Valida ID médico (formato personalizable)"""
        # Ejemplo: formato XXXXXX-X
        pattern = r'^\d{6}-\d{1}$'
        return bool(re.match(pattern, medical_id))
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 1000) -> str:
        """Sanitiza input del usuario"""
        if not text:
            return ""
        
        # Remover HTML/scripts
        text = re.sub(r'<[^>]+>', '', text)
        
        # Limitar longitud
        text = text[:max_length]
        
        # Limpiar texto
        text = TextUtils.clean_text(text)
        
        return text

class DateUtils:
    """Utilidades para manejo de fechas"""
    
    @staticmethod
    def format_datetime(dt: datetime, format_type: str = "standard") -> str:
        """Formatea datetime según el tipo especificado"""
        formats = {
            "standard": "%Y-%m-%d %H:%M:%S",
            "date_only": "%Y-%m-%d",
            "time_only": "%H:%M:%S",
            "human": "%d de %B de %Y a las %H:%M",
            "iso": "%Y-%m-%dT%H:%M:%S"
        }
        
        format_str = formats.get(format_type, formats["standard"])
        return dt.strftime(format_str)
    
    @staticmethod
    def parse_date_string(date_str: str) -> Optional[datetime]:
        """Parsea string de fecha en varios formatos"""
        formats = [
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d/%m/%Y",
            "%d-%m-%Y",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ"
        ]
        
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    @staticmethod
    def get_time_ago(dt: datetime) -> str:
        """Retorna tiempo transcurrido en formato legible"""
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 0:
            return f"hace {diff.days} día{'s' if diff.days > 1 else ''}"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"hace {hours} hora{'s' if hours > 1 else ''}"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"hace {minutes} minuto{'s' if minutes > 1 else ''}"
        else:
            return "hace unos segundos"

class SecurityUtils:
    """Utilidades de seguridad"""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hash de contraseña (usar con bcrypt en producción)"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    @staticmethod
    def generate_session_token() -> str:
        """Genera token de sesión"""
        import secrets
        return secrets.token_urlsafe(32)
    
    @staticmethod
    def mask_sensitive_data(text: str, patterns: List[str] = None) -> str:
        """Enmascara datos sensibles en texto"""
        if patterns is None:
            patterns = [
                r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b',  # Tarjetas de crédito
                r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
                r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'  # Emails
            ]
        
        masked_text = text
        for pattern in patterns:
            masked_text = re.sub(pattern, '***MASKED***', masked_text)
        
        return masked_text

class AnalyticsUtils:
    """Utilidades para analytics y métricas"""
    
    @staticmethod
    def calculate_text_stats(text: str) -> Dict[str, Any]:
        """Calcula estadísticas de texto"""
        if not text:
            return {
                'characters': 0,
                'words': 0,
                'sentences': 0,
                'paragraphs': 0
            }
        
        # Contar caracteres
        char_count = len(text)
        
        # Contar palabras
        words = re.findall(r'\b\w+\b', text)
        word_count = len(words)
        
        # Contar oraciones
        sentences = re.split(r'[.!?]+', text)
        sentence_count = len([s for s in sentences if s.strip()])
        
        # Contar párrafos
        paragraphs = text.split('\n\n')
        paragraph_count = len([p for p in paragraphs if p.strip()])
        
        return {
            'characters': char_count,
            'words': word_count,
            'sentences': sentence_count,
            'paragraphs': paragraph_count,
            'avg_words_per_sentence': round(word_count / max(sentence_count, 1), 2),
            'reading_time_minutes': round(word_count / 200, 1)  # 200 palabras por minuto
        }
    
    @staticmethod
    def track_usage_event(event_type: str, user_id: str, metadata: Dict[str, Any] = None):
        """Registra evento de uso (implementar con sistema de analytics)"""
        event_data = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'metadata': metadata or {}
        }
        
        # En producción, enviar a sistema de analytics
        logger.info(f"Usage event: {json.dumps(event_data)}")

class ErrorHandler:
    """Manejador centralizado de errores"""
    
    @staticmethod
    def log_error(error: Exception, context: str = "", user_id: str = None):
        """Registra error con contexto"""
        error_data = {
            'timestamp': datetime.now().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'user_id': user_id
        }
        
        logger.error(f"Error logged: {json.dumps(error_data)}")
    
    @staticmethod
    def format_error_message(error: Exception, user_friendly: bool = True) -> str:
        """Formatea mensaje de error para el usuario"""
        if user_friendly:
            # Mensajes amigables para errores comunes
            error_messages = {
                'FileNotFoundError': 'Archivo no encontrado',
                'PermissionError': 'Sin permisos para acceder al archivo',
                'ValueError': 'Datos inválidos proporcionados',
                'ConnectionError': 'Error de conexión',
                'TimeoutError': 'Tiempo de espera agotado'
            }
            
            error_type = type(error).__name__
            return error_messages.get(error_type, 'Ha ocurrido un error inesperado')
        else:
            return str(error)

class ConfigValidator:
    """Validador de configuración del sistema"""
    
    @staticmethod
    def validate_environment() -> Dict[str, Any]:
        """Valida el entorno del sistema"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'info': {}
        }
        
        # Verificar variables de entorno críticas
        required_env_vars = ['ANTHROPIC_API_KEY', 'SUPABASE_URL', 'SUPABASE_KEY']
        
        for var in required_env_vars:
            if not os.getenv(var):
                validation_result['valid'] = False
                validation_result['errors'].append(f"Variable de entorno requerida: {var}")
        
        # Verificar directorios
        from config.config import DATA_DIR, UPLOADS_DIR, LOGS_DIR, TEMP_DIR
        
        for directory in [DATA_DIR, UPLOADS_DIR, LOGS_DIR, TEMP_DIR]:
            if not directory.exists():
                validation_result['warnings'].append(f"Directorio no existe: {directory}")
        
        # Información del sistema
        validation_result['info'] = {
            'python_version': os.sys.version,
            'platform': os.name,
            'working_directory': os.getcwd()
        }
        
        return validation_result

