
"""
Utilidades y funciones helper para HCE Analyzer
"""
import os
import re
import hashlib
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
import tempfile

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



