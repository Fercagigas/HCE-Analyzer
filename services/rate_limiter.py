"""
Rate Limiter - Sistema de limitación de tasa para ChatHCE.

Implementa un algoritmo de ventana deslizante (sliding window) para
prevenir abuso y ataques de denegación de servicio.

Características:
- Limitación por usuario (user_id)
- Limitación por IP (fallback para no autenticados)
- Limpieza automática de entradas expiradas
- Configuración desde settings.py
- Thread-safe con locks
"""

import time
import threading
import logging
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

from config.settings import settings

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuración de rate limiting"""
    max_requests_per_minute: int = 30
    max_requests_per_hour: int = 300
    max_message_length: int = 5000
    burst_limit: int = 5  # Máximo de requests en 10 segundos
    burst_window: float = 10.0
    cleanup_interval: float = 300.0  # Limpiar cada 5 minutos


@dataclass
class RateLimitEntry:
    """Entrada de rate limiting para un usuario/IP"""
    timestamps: list = field(default_factory=list)
    blocked_until: float = 0.0
    violation_count: int = 0


class RateLimitExceeded(Exception):
    """Excepción cuando se excede el límite de tasa"""
    def __init__(self, message: str, retry_after: float = 60.0):
        self.message = message
        self.retry_after = retry_after
        super().__init__(self.message)


class RateLimiter:
    """
    Rate limiter con ventana deslizante.
    
    Implementa múltiples niveles de protección:
    1. Burst limit: Máximo N requests en ventana corta (10s)
    2. Per-minute limit: Máximo N requests por minuto
    3. Per-hour limit: Máximo N requests por hora
    4. Bloqueo progresivo: Violaciones repetidas incrementan el tiempo de bloqueo
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Singleton pattern para compartir estado entre requests"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        
        self.config = RateLimitConfig(
            max_requests_per_minute=getattr(
                settings.security, 'rate_limit_per_minute', 30
            ),
            max_requests_per_hour=getattr(
                settings.security, 'rate_limit_per_hour', 300
            ),
            max_message_length=getattr(
                settings.security, 'max_message_length', 5000
            ),
        )
        
        self._entries: Dict[str, RateLimitEntry] = defaultdict(RateLimitEntry)
        self._entry_lock = threading.Lock()
        self._last_cleanup = time.time()
        
        logger.info(
            "Rate limiter inicializado: "
            f"{self.config.max_requests_per_minute}/min, "
            f"{self.config.max_requests_per_hour}/hora, "
            f"burst={self.config.burst_limit}/{self.config.burst_window}s"
        )

    def check_rate_limit(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Verificar si el request está dentro de los límites.
        
        Args:
            user_id: ID del usuario autenticado
            ip_address: Dirección IP (fallback)
            
        Returns:
            Tuple (allowed: bool, error_message: Optional[str])
            
        Raises:
            RateLimitExceeded: Si se excede el límite
        """
        key = self._get_key(user_id, ip_address)
        now = time.time()
        
        # Limpieza periódica
        if now - self._last_cleanup > self.config.cleanup_interval:
            self._cleanup_expired()
        
        with self._entry_lock:
            entry = self._entries[key]
            
            # Verificar si está bloqueado
            if entry.blocked_until > now:
                remaining = int(entry.blocked_until - now)
                msg = (
                    f"Demasiadas solicitudes. "
                    f"Intente de nuevo en {remaining} segundos."
                )
                logger.warning(
                    f"Rate limit: usuario bloqueado",
                    extra={"key": key[:20], "remaining_seconds": remaining}
                )
                raise RateLimitExceeded(msg, retry_after=remaining)
            
            # Limpiar timestamps expirados (más de 1 hora)
            cutoff_hour = now - 3600
            entry.timestamps = [
                t for t in entry.timestamps if t > cutoff_hour
            ]
            
            # Verificar burst limit (ventana corta)
            burst_cutoff = now - self.config.burst_window
            burst_count = sum(
                1 for t in entry.timestamps if t > burst_cutoff
            )
            if burst_count >= self.config.burst_limit:
                self._apply_violation(entry, now)
                msg = (
                    f"Demasiadas solicitudes rápidas. "
                    f"Espere {int(self.config.burst_window)} segundos."
                )
                raise RateLimitExceeded(msg, retry_after=self.config.burst_window)
            
            # Verificar límite por minuto
            minute_cutoff = now - 60
            minute_count = sum(
                1 for t in entry.timestamps if t > minute_cutoff
            )
            if minute_count >= self.config.max_requests_per_minute:
                self._apply_violation(entry, now)
                msg = (
                    f"Límite de {self.config.max_requests_per_minute} "
                    f"solicitudes por minuto alcanzado."
                )
                raise RateLimitExceeded(msg, retry_after=60.0)
            
            # Verificar límite por hora
            hour_count = len(entry.timestamps)
            if hour_count >= self.config.max_requests_per_hour:
                self._apply_violation(entry, now)
                msg = (
                    f"Límite de {self.config.max_requests_per_hour} "
                    f"solicitudes por hora alcanzado."
                )
                raise RateLimitExceeded(msg, retry_after=300.0)
            
            # Request permitido - registrar timestamp
            entry.timestamps.append(now)
            return True, None

    def validate_message_length(self, message: str) -> None:
        """
        Validar longitud del mensaje.
        
        Args:
            message: Mensaje del usuario
            
        Raises:
            ValueError: Si el mensaje excede el límite
        """
        if len(message) > self.config.max_message_length:
            raise ValueError(
                f"El mensaje excede el límite de "
                f"{self.config.max_message_length} caracteres "
                f"({len(message)} enviados)."
            )
        if len(message.strip()) == 0:
            raise ValueError("El mensaje no puede estar vacío.")

    def get_usage_stats(
        self,
        user_id: Optional[str] = None,
        ip_address: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Obtener estadísticas de uso para un usuario.
        
        Returns:
            Dict con contadores de uso
        """
        key = self._get_key(user_id, ip_address)
        now = time.time()
        
        with self._entry_lock:
            entry = self._entries.get(key, RateLimitEntry())
            
            minute_cutoff = now - 60
            hour_cutoff = now - 3600
            
            return {
                "requests_last_minute": sum(
                    1 for t in entry.timestamps if t > minute_cutoff
                ),
                "requests_last_hour": sum(
                    1 for t in entry.timestamps if t > hour_cutoff
                ),
                "limit_per_minute": self.config.max_requests_per_minute,
                "limit_per_hour": self.config.max_requests_per_hour,
                "is_blocked": entry.blocked_until > now,
                "violation_count": entry.violation_count,
            }

    def _get_key(
        self,
        user_id: Optional[str],
        ip_address: Optional[str]
    ) -> str:
        """Generar clave única para el rate limiter"""
        if user_id:
            return f"user:{user_id}"
        if ip_address:
            return f"ip:{ip_address}"
        return "anonymous"

    def _apply_violation(self, entry: RateLimitEntry, now: float) -> None:
        """
        Aplicar penalización por violación.
        Bloqueo progresivo: 30s, 60s, 120s, 300s, 600s
        """
        entry.violation_count += 1
        block_durations = [30, 60, 120, 300, 600]
        idx = min(entry.violation_count - 1, len(block_durations) - 1)
        block_time = block_durations[idx]
        entry.blocked_until = now + block_time
        
        logger.warning(
            f"Rate limit violation #{entry.violation_count}, "
            f"bloqueado por {block_time}s"
        )

    def _cleanup_expired(self) -> None:
        """Limpiar entradas expiradas del rate limiter"""
        now = time.time()
        cutoff = now - 7200  # 2 horas
        
        with self._entry_lock:
            keys_to_remove = []
            for key, entry in self._entries.items():
                # Remover si no tiene timestamps recientes y no está bloqueado
                if (not entry.timestamps or 
                    max(entry.timestamps) < cutoff) and \
                   entry.blocked_until < now:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self._entries[key]
            
            self._last_cleanup = now
            if keys_to_remove:
                logger.debug(
                    f"Rate limiter cleanup: {len(keys_to_remove)} entradas eliminadas"
                )


# Instancia global singleton
rate_limiter = RateLimiter()
